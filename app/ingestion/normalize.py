"""Normalisation helpers: locations, experience ranges, posting dates, and text keys for de-duplication."""

from __future__ import annotations

import re
from datetime import date, timedelta

# Country name variants -> (ISO code, display name). GCC first, then others that appear in alerts.
_COUNTRIES = {
    "saudi arabia": ("SA", "Saudi Arabia"), "ksa": ("SA", "Saudi Arabia"), "kingdom of saudi arabia": ("SA", "Saudi Arabia"),
    "المملكة العربية السعودية": ("SA", "Saudi Arabia"), "السعودية": ("SA", "Saudi Arabia"),
    "united arab emirates": ("AE", "United Arab Emirates"), "uae": ("AE", "United Arab Emirates"),
    "الإمارات": ("AE", "United Arab Emirates"),
    "qatar": ("QA", "Qatar"), "قطر": ("QA", "Qatar"),
    "kuwait": ("KW", "Kuwait"), "الكويت": ("KW", "Kuwait"),
    "bahrain": ("BH", "Bahrain"), "البحرين": ("BH", "Bahrain"),
    "oman": ("OM", "Oman"), "sultanate of oman": ("OM", "Oman"), "عمان": ("OM", "Oman"),
    "egypt": ("EG", "Egypt"), "مصر": ("EG", "Egypt"),
}
# Cities that identify a country even when the country is missing.
_CITIES = {
    "riyadh": "SA", "jeddah": "SA", "jiddah": "SA", "dammam": "SA", "khobar": "SA", "al khobar": "SA",
    "diriyah": "SA", "dhahran": "SA", "mecca": "SA", "makkah": "SA", "medina": "SA", "madinah": "SA",
    "neom": "SA", "alula": "SA", "al ula": "SA", "tabuk": "SA", "jubail": "SA",
    "dubai": "AE", "abu dhabi": "AE", "sharjah": "AE", "ajman": "AE", "ras al khaimah": "AE",
    "doha": "QA", "lusail": "QA", "kuwait city": "KW", "manama": "BH", "muscat": "OM",
    "cairo": "EG", "giza": "EG", "alexandria": "EG", "new cairo": "EG",
}
GCC = {"SA", "AE", "QA", "KW", "BH", "OM"}
_NAMES = {code: name for code, name in _COUNTRIES.values()}


def parse_location(raw: str) -> tuple[str, str, str]:
    """'Dubai - United Arab Emirates (UAE)' -> ('Dubai', 'United Arab Emirates', 'AE')."""
    text = re.sub(r"\([^)]*\)", "", raw or "").strip()
    parts = [p.strip() for p in re.split(r"\s+-\s+|,|،|\|", text) if p.strip()]
    code, city = "", ""
    for part in parts:
        key = part.lower()
        if key in _COUNTRIES and not code:
            code = _COUNTRIES[key][0]
        elif key in _CITIES:
            city = part.title() if part.isupper() or part.islower() else part
            code = code or _CITIES[key]
        elif not city and key not in _COUNTRIES:
            city = part
    if city and city.lower() in _COUNTRIES:
        city = ""
    return city, _NAMES.get(code, ""), code


def parse_experience(raw: str) -> tuple[int | None, int | None]:
    """'12 - 15 Years' -> (12, 15); '10+ years' -> (10, None)."""
    m = re.search(r"(\d+)\s*(?:-|to|–)\s*(\d+)\s*(?:years|yrs)", raw or "", re.IGNORECASE)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d+)\s*\+?\s*(?:years|yrs)", raw or "", re.IGNORECASE)
    return (int(m.group(1)), None) if m else (None, None)


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def parse_posted(raw: str, received: date) -> date | None:
    """Relative ('5d', '3 days ago', 'today') or short ('17 Aug') posting dates, resolved against the email date."""
    text = (raw or "").strip().lower()
    if text in ("today", "just now", "new"):
        return received
    if text == "yesterday":
        return received - timedelta(days=1)
    m = re.fullmatch(r"(\d+)\s*(d|days?|days? ago|h|hours? ago|w|weeks? ago)", text)
    if m:
        n, unit = int(m.group(1)), m.group(2)[0]
        return received - timedelta(days=n * 7 if unit == "w" else (0 if unit == "h" else n))
    m = re.fullmatch(r"(\d{1,2})\s+([a-z]{3})[a-z]*", text)
    if m and m.group(2) in _MONTHS:
        candidate = date(received.year, _MONTHS[m.group(2)], int(m.group(1)))
        return candidate if candidate <= received else date(received.year - 1, candidate.month, candidate.day)
    return None


_TITLE_SYNONYMS = {"sr": "senior", "snr": "senior", "mgr": "manager", "jr": "junior", "dir": "director",
                   "&": "and", "asst": "assistant"}
_EMPLOYER_NOISE = {"llc", "l.l.c", "pjsc", "p.j.s.c", "psc", "company", "co", "ltd", "limited", "private",
                   "fz", "fze", "fz-llc", "wll", "w.l.l", "inc", "the", "est", "establishment"}


def title_key(title: str) -> str:
    words = re.findall(r"[a-z0-9؀-ۿ&]+", (title or "").lower())
    return " ".join(_TITLE_SYNONYMS.get(w, w) for w in words)


def employer_key(employer: str) -> str:
    words = re.findall(r"[a-z0-9؀-ۿ.\-]+", (employer or "").lower())
    return " ".join(w.strip(".") for w in words if w.strip(".") not in _EMPLOYER_NOISE)


def is_confidential(employer: str) -> bool:
    key = employer_key(employer)
    return not key or key.startswith(("confidential", "client of", "leading", "a leading", "reputed"))
