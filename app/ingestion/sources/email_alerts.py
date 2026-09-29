"""Parses job-alert emails into vacancies.

Only the listing fields visible in the email are extracted. Tracker and auto-login links are reduced to the
public job page; the raw email is never stored.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import date

from app.ingestion.models import Vacancy
from app.ingestion.normalize import parse_experience, parse_location, parse_posted
from app.security.urls import UnsafeUrlError, clean_job_url


@dataclass(frozen=True)
class AlertEmail:
    sender: str
    subject: str
    received: date
    html_body: str


@dataclass
class ParseResult:
    vacancies: list[Vacancy]
    skipped: int = 0            # job cards that could not be read safely
    parser: str = ""


_ANCHOR_START = re.compile(r"<a\b[^>]*\bhref=\"([^\"]+)\"[^>]*>", re.IGNORECASE)
_EXPERIENCE = re.compile(r"^\d+\s*-\s*\d+\s*Years?$", re.IGNORECASE)


def _text_lines(fragment: str) -> list[str]:
    text = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", fragment, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "\n", text)
    return [line.strip() for line in html.unescape(text).split("\n") if line.strip()]


def parse_naukrigulf(email: AlertEmail) -> ParseResult:
    """Naukrigulf 'recommended jobs' emails. Each job card is a link whose text is:
    title / employer / 'N - M Years' / location / ['Easy Apply'] / posted."""
    result = ParseResult([], parser="naukrigulf")
    body = email.html_body
    # Cards can contain nested links (e.g. a company link), so a card is everything from its first job link
    # up to the next job link with a different job id.
    starts: list[tuple[int, str, str]] = []            # (position, job id, clean url)
    for m in _ANCHOR_START.finditer(body):
        try:
            url = clean_job_url(html.unescape(m.group(1)))
        except UnsafeUrlError:
            continue
        job = re.search(r"jid-(\d+)", url)
        if job and (not starts or starts[-1][1] != job.group(1)):
            starts.append((m.start(), job.group(1), url))
    for i, (pos, job_id, url) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(body)
        lines = _text_lines(body[pos:end])
        if len(lines) < 4 or not _EXPERIENCE.match(lines[2]):
            result.skipped += 1
            continue
        title, employer, experience, location = lines[:4]
        rest = lines[4:6]
        easy_apply = any(r.lower() == "easy apply" for r in rest)
        posted_raw = next((r for r in rest if r.lower() != "easy apply"), "")
        city, country, code = parse_location(location)
        low, high = parse_experience(experience)
        result.vacancies.append(Vacancy(
            title=title, employer=employer, source="naukrigulf_email",
            source_job_id=job_id,
            location_raw=location, city=city, country=country, country_code=code,
            published_date=parse_posted(posted_raw, email.received),
            experience_min=low, experience_max=high, apply_url=url, easy_apply=easy_apply,
        ))
    return result


# Sender domain -> parser. Parsers are added only once a real sample email has been verified.
PARSERS = {
    "naukrigulf.com": parse_naukrigulf,
}
# Senders that send account notices or marketing, not job listings.
NON_JOB_SUBJECT = re.compile(r"(viewed your (cv|profile)|appeared in \d+ searches|interview|update your cv|"
                             r"profile is looking|welcome to|showed interest|professionally written cv)",
                             re.IGNORECASE)


def parser_for(sender: str):
    domain = sender.rsplit("@", 1)[-1].lower()
    for known, parser in PARSERS.items():
        if domain == known or domain.endswith("." + known):
            return parser
    return None


def parse_alert(email: AlertEmail) -> ParseResult | None:
    """Returns None when the email is not a supported job-alert email."""
    if NON_JOB_SUBJECT.search(email.subject):
        return None
    parser = parser_for(email.sender)
    return parser(email) if parser else None
