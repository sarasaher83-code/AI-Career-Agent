"""Public career-page job feeds published by applicant-tracking systems.

Each of these endpoints is intended for public job boards and needs no login:
  Greenhouse       https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
  Lever            https://api.lever.co/v0/postings/{token}?mode=json
  SmartRecruiters  https://api.smartrecruiters.com/v1/companies/{token}/postings
  Workable         https://apply.workable.com/api/v1/widget/accounts/{token}
"""

from __future__ import annotations

import html
import json
import re
import urllib.request
from datetime import date, datetime, timezone
from typing import Callable

from app.ingestion.models import Vacancy
from app.ingestion.normalize import parse_location

USER_AGENT = "CareerIntelligence/0.1 (personal job search; contact via repository)"
TIMEOUT_SECONDS = 20


def fetch_json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def _plain(markup: str) -> str:
    text = html.unescape(markup or "")
    text = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", text)).strip()


def _date(value) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):                       # Lever: milliseconds since epoch
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date()
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _vacancy(source: str, job_id, title: str, employer: str, location: str, url: str, **extra) -> Vacancy:
    city, country, code = parse_location(location)
    return Vacancy(title=title.strip(), employer=employer, source=source, source_job_id=str(job_id),
                   location_raw=location, city=city, country=country, country_code=code, apply_url=url, **extra)


def greenhouse(token: str, employer: str, fetch: Callable = fetch_json) -> list[Vacancy]:
    data = fetch(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true")
    return [_vacancy("greenhouse", j["id"], j["title"], employer, (j.get("location") or {}).get("name", ""),
                     j.get("absolute_url", ""), description=_plain(j.get("content", "")),
                     published_date=_date(j.get("updated_at")))
            for j in data.get("jobs", [])]


def lever(token: str, employer: str, fetch: Callable = fetch_json) -> list[Vacancy]:
    data = fetch(f"https://api.lever.co/v0/postings/{token}?mode=json")
    return [_vacancy("lever", j["id"], j["text"], employer, (j.get("categories") or {}).get("location", ""),
                     j.get("hostedUrl", ""), description=j.get("descriptionPlain", "") or _plain(j.get("description", "")),
                     published_date=_date(j.get("createdAt")))
            for j in data]


def smartrecruiters(token: str, employer: str, fetch: Callable = fetch_json) -> list[Vacancy]:
    data = fetch(f"https://api.smartrecruiters.com/v1/companies/{token}/postings")
    out = []
    for j in data.get("content", []):
        loc = j.get("location") or {}
        location = ", ".join(p for p in (loc.get("city"), loc.get("country", "").upper()) if p)
        out.append(_vacancy("smartrecruiters", j["id"], j["name"], (j.get("company") or {}).get("name") or employer,
                            location, f"https://jobs.smartrecruiters.com/{token}/{j['id']}",
                            published_date=_date(j.get("releasedDate"))))
    return out


def workable(token: str, employer: str, fetch: Callable = fetch_json) -> list[Vacancy]:
    data = fetch(f"https://apply.workable.com/api/v1/widget/accounts/{token}")
    return [_vacancy("workable", j.get("shortcode") or j.get("url"), j["title"], data.get("name") or employer,
                     ", ".join(p for p in (j.get("city"), j.get("country")) if p), j.get("url", ""),
                     published_date=_date(j.get("published_on")))
            for j in data.get("jobs", [])]


ADAPTERS: dict[str, Callable[..., list[Vacancy]]] = {
    "greenhouse": greenhouse, "lever": lever, "smartrecruiters": smartrecruiters, "workable": workable,
}
