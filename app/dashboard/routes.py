"""Dashboard pages."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config.settings import mask_secret
from app.profile.fact_check import check_text

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
router = APIRouter()

# The ten dashboard sections from the brief, with the build stage that delivers each one.
SECTIONS = [
    ("overview", "Executive Career Overview", "/", None),
    ("discovery", "Job Discovery", "/discovery", None),
    ("matching", "Job Matching", "/section/matching", "S2"),
    ("pipeline", "Application Pipeline", "/section/pipeline", "S3"),
    ("cv-library", "Tailored CV Library", "/section/cv-library", "S4"),
    ("linkedin", "LinkedIn Optimization", "/section/linkedin", "S5"),
    ("networking", "Networking Opportunities", "/section/networking", "S6"),
    ("content", "Content Calendar", "/section/content", "S6"),
    ("recruiters", "Recruiter Directory", "/section/recruiters", "S7"),
    ("analytics", "Performance Analytics", "/section/analytics", "S7"),
]
TOOLS = [
    ("fact-check", "Fact Checker", "/fact-check"),
    ("audit", "Audit Log", "/audit"),
]


def _render(request: Request, template: str, active: str, **context) -> HTMLResponse:
    return templates.TemplateResponse(request, template, {
        "sections": SECTIONS, "tools": TOOLS, "active": active, **context,
    })


@router.get("/", response_class=HTMLResponse)
def overview(request: Request):
    state = request.app.state
    settings, profile = state.settings, state.profile
    checklist = [
        ("Master profile loaded", profile is not None,
         f"{profile.name}: {profile.status}" if profile else state.profile_error),
        ("Claude API key configured", settings.has_anthropic_key,
         mask_secret(settings.anthropic_api_key) if settings.has_anthropic_key
         else "Add ANTHROPIC_API_KEY to the .env file (see docs/SETUP_WINDOWS.md)"),
        ("Gmail job-alert access configured", settings.has_gmail,
         settings.gmail_address if settings.has_gmail else "Needed from stage S1 (Gmail app password)"),
        ("Scraping aggregators disabled", not settings.enable_aggregators,
         "Off (recommended)" if not settings.enable_aggregators else "ENABLED: review this setting"),
        ("Audit log intact", state.audit.verify_chain(), "Tamper-evident hash chain verified"),
    ]
    return _render(request, "overview.html", "overview", profile=profile, checklist=checklist,
                   settings=settings, events=state.audit.recent(8))


@router.get("/section/{key}", response_class=HTMLResponse)
def section_placeholder(request: Request, key: str):
    section = next((s for s in SECTIONS if s[0] == key), None)
    if section is None:
        return HTMLResponse("Not found", status_code=404)
    if section[3] is None:                       # section already built: go to the real page
        return RedirectResponse(section[2], status_code=307)
    return _render(request, "placeholder.html", key, section=section)


@router.get("/fact-check", response_class=HTMLResponse)
def fact_check_form(request: Request):
    return _render(request, "fact_check.html", "fact-check", text="", result=None)


@router.post("/fact-check", response_class=HTMLResponse)
def fact_check_submit(request: Request, text: str = Form("")):
    state = request.app.state
    if state.profile is None:
        return _render(request, "fact_check.html", "fact-check", text=text, result=None,
                       error="Load the master profile first.")
    result = check_text(text, state.profile)
    state.audit.record("fact_check.run", details={
        "characters": len(text), "passed": result.passed,
        "blocking": len(result.blocking), "warnings": len(result.warnings),
    }, actor="candidate")
    return _render(request, "fact_check.html", "fact-check", text=text, result=result)


@router.get("/audit", response_class=HTMLResponse)
def audit_log(request: Request):
    audit = request.app.state.audit
    return _render(request, "audit.html", "audit", events=audit.recent(200), intact=audit.verify_chain())


@router.get("/health")
def health(request: Request):
    return {"status": "ok", "profile_loaded": request.app.state.profile is not None}
