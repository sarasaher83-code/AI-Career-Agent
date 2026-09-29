"""Job Discovery section: vacancy list, filters, imports, manual entry, career-page watch-list, exports."""

from __future__ import annotations

import urllib.parse
from datetime import date

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.dashboard.routes import _render
from app.exports.tables import to_csv, to_xlsx
from app.ingestion.models import Vacancy
from app.ingestion.normalize import parse_experience, parse_location
from app.ingestion.pipeline import import_alert_emails
from app.ingestion.sources import ats_boards
from app.ingestion.sources.gmail_imap import GmailAlertReader, GmailError, to_alert_email
from app.ingestion.store import STATUSES
from app.security.urls import UnsafeUrlError, clean_job_url

router = APIRouter(prefix="/discovery")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
EXPORT_COLUMNS = [
    ("title", "Job title"), ("employer", "Employer"), ("city", "City"), ("country", "Country"),
    ("published_date", "Published"), ("deadline", "Deadline"), ("salary_text", "Salary"),
    ("experience_min", "Experience from (yrs)"), ("experience_max", "Experience to (yrs)"),
    ("status", "Status"), ("sources", "Sources"), ("apply_url", "Application link"), ("first_seen", "First seen"),
]


def _back(message: str, path: str = "/discovery") -> RedirectResponse:
    return RedirectResponse(f"{path}?msg={urllib.parse.quote(message)}", status_code=303)


def _summary_text(summary: dict) -> str:
    return (f"{summary.get('emails', 0)} emails read · {summary.get('job_cards', 0)} jobs found · "
            f"{summary.get('new', 0)} new · {summary.get('merged', 0)} merged duplicates · "
            f"{summary.get('seen_again', 0)} already known")


def _filters(request: Request) -> dict:
    q = request.query_params
    return {"country": q.get("country", ""), "status": q.get("status", ""),
            "source": q.get("source", ""), "q": q.get("q", "").strip()}


@router.get("", response_class=HTMLResponse)
def discovery(request: Request):
    state = request.app.state
    f = _filters(request)
    rows = state.vacancies.list(country_code=f["country"], status=f["status"], query=f["q"], source=f["source"])
    return _render(request, "discovery.html", "discovery", rows=rows, filters=f, statuses=STATUSES,
                   countries=state.vacancies.countries(), sources=state.vacancies.sources(),
                   counts=state.vacancies.counts(), gmail_ready=state.settings.has_gmail,
                   message=request.query_params.get("msg", ""))


@router.post("/import-gmail")
def import_gmail(request: Request, days: int = Form(14)):
    state = request.app.state
    if not state.settings.has_gmail:
        return _back("Gmail is not set up yet: add GMAIL_ADDRESS and GMAIL_APP_PASSWORD to the .env file.")
    reader = GmailAlertReader(state.settings.gmail_address, state.settings.gmail_app_password)
    try:
        emails = reader.fetch(days=max(1, min(days, 90)))
    except GmailError as exc:
        state.audit.record("jobs.import_emails_failed", "gmail", {"reason": str(exc)})
        return _back(str(exc))
    return _back(_summary_text(import_alert_emails(emails, state.vacancies, state.audit)))


@router.post("/upload")
async def upload_alert(request: Request, file: UploadFile = File(...)):
    """Import a saved job-alert email (.eml), for when Gmail access isn't set up."""
    state = request.app.state
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        return _back("That file is too large (limit 5 MB).")
    if not (file.filename or "").lower().endswith(".eml"):
        return _back("Please upload an email saved as .eml (in Gmail: ⋮ → Download message).")
    summary = import_alert_emails([to_alert_email(raw)], state.vacancies, state.audit, origin="upload")
    return _back(_summary_text(summary))


@router.post("/manual")
def add_manual(request: Request, title: str = Form(...), employer: str = Form(...), location: str = Form(""),
               url: str = Form(""), description: str = Form(""), experience: str = Form(""),
               deadline: str = Form(""), salary: str = Form("")):
    state = request.app.state
    clean = ""
    if url.strip():
        try:
            clean = clean_job_url(url)
        except UnsafeUrlError as exc:
            return _back(f"The link was not saved: {exc}. Paste the public job page link instead.")
    city, country, code = parse_location(location)
    low, high = parse_experience(experience)
    try:
        deadline_date = date.fromisoformat(deadline) if deadline else None
    except ValueError:
        deadline_date = None
    vacancy = Vacancy(title=title.strip(), employer=employer.strip(), source="manual",
                      source_job_id=clean or f"{title.strip()}|{employer.strip()}|{location.strip()}".lower(),
                      location_raw=location, city=city, country=country, country_code=code, apply_url=clean,
                      description=description.strip(), experience_min=low, experience_max=high,
                      deadline=deadline_date, salary_text=salary.strip(), published_date=None)
    vacancy_id, outcome = state.vacancies.add(vacancy)
    state.audit.record("jobs.add_manual", f"vacancy:{vacancy_id}", {"outcome": outcome}, actor="candidate")
    label = {"new": "Vacancy added.", "merged": "This vacancy was already listed; details merged.",
             "seen_again": "This vacancy is already in the list."}[outcome]
    return _back(label)


@router.get("/export/{fmt}")
def export(request: Request, fmt: str):
    state = request.app.state
    f = _filters(request)
    rows = state.vacancies.list(country_code=f["country"], status=f["status"], query=f["q"], source=f["source"],
                                limit=10000)
    state.audit.record("export", "vacancies", {"format": fmt, "rows": len(rows)}, actor="candidate")
    stamp = date.today().isoformat()
    if fmt == "csv":
        return Response(to_csv(rows, EXPORT_COLUMNS), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="vacancies-{stamp}.csv"'})
    if fmt == "xlsx":
        return Response(to_xlsx(rows, EXPORT_COLUMNS, "Vacancies"),
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f'attachment; filename="vacancies-{stamp}.xlsx"'})
    return Response("Unknown format", status_code=404)


@router.get("/boards", response_class=HTMLResponse)
def boards(request: Request):
    return _render(request, "boards.html", "discovery", boards=request.app.state.boards.list(),
                   systems=sorted(ats_boards.ADAPTERS), message=request.query_params.get("msg", ""))


@router.post("/boards/add")
def boards_add(request: Request, employer: str = Form(...), ats: str = Form(...), token: str = Form(...)):
    state = request.app.state
    try:
        state.boards.add(employer, ats, token)
    except ValueError as exc:
        return _back(str(exc), "/discovery/boards")
    state.audit.record("boards.add", f"{ats}:{token}", {"employer": employer}, actor="candidate")
    return _back(f"{employer} added to the watch-list.", "/discovery/boards")


@router.post("/boards/{board_id}/remove")
def boards_remove(request: Request, board_id: int):
    state = request.app.state
    state.boards.remove(board_id)
    state.audit.record("boards.remove", f"board:{board_id}", actor="candidate")
    return _back("Removed from the watch-list.", "/discovery/boards")


@router.post("/boards/check")
def boards_check(request: Request):
    state = request.app.state
    summary = state.boards.check_all(state.vacancies, state.audit)
    text = (f"{summary.get('new', 0)} new · {summary.get('merged', 0)} merged · "
            f"{summary.get('seen_again', 0)} already known · {summary.get('failed_boards', 0)} boards failed")
    return _back(text, "/discovery/boards")


@router.get("/{vacancy_id}", response_class=HTMLResponse)
def vacancy_detail(request: Request, vacancy_id: int):
    item = request.app.state.vacancies.get(vacancy_id)
    if item is None:
        return HTMLResponse("Not found", status_code=404)
    return _render(request, "vacancy.html", "discovery", v=item, statuses=STATUSES)


@router.post("/{vacancy_id}/status")
def vacancy_status(request: Request, vacancy_id: int, status: str = Form(...), back: str = Form("/discovery")):
    state = request.app.state
    try:
        state.vacancies.set_status(vacancy_id, status)
    except ValueError:
        return _back("Unknown status.")
    state.audit.record("jobs.status", f"vacancy:{vacancy_id}", {"status": status}, actor="candidate")
    target = back if back.startswith("/discovery") else "/discovery"
    return RedirectResponse(target, status_code=303)
