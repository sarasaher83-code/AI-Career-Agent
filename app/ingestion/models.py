"""The common vacancy record every source is converted into."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Vacancy:
    title: str
    employer: str
    source: str                      # e.g. "naukrigulf_email", "greenhouse", "manual"
    source_job_id: str               # stable id within that source (job id, or the clean URL)
    location_raw: str = ""
    city: str = ""
    country: str = ""
    country_code: str = ""
    published_date: date | None = None
    deadline: date | None = None
    salary_text: str = ""
    description: str = ""
    experience_min: int | None = None
    experience_max: int | None = None
    qualifications: str = ""
    apply_url: str = ""
    employer_profile: str = ""
    easy_apply: bool = False
    notes: list[str] = field(default_factory=list)
