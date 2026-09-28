"""Loads the locked master profile and indexes every fact as a citable evidence item."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Sections that are never used as evidence or as a source of "verified" numbers.
NON_EVIDENCE_SECTIONS = {"_meta", "identity", "private_preferences", "excluded_content", "portfolio_assets"}


class ProfileError(Exception):
    pass


@dataclass(frozen=True)
class Evidence:
    id: str
    kind: str
    text: str


@dataclass
class Profile:
    raw: dict[str, Any]
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.raw["identity"]["name"]

    @property
    def status(self) -> str:
        return self.raw.get("_meta", {}).get("status", "")

    @property
    def forbidden_phrases(self) -> list[str]:
        return list(self.raw.get("_meta", {}).get("forbidden_phrases", []))

    @property
    def current_role(self) -> dict[str, Any]:
        return self.raw["experience"][0]

    def evidence_by_id(self, evidence_id: str) -> Evidence | None:
        return next((e for e in self.evidence if e.id == evidence_id), None)

    def evidence_text(self) -> str:
        """All verified statements as one text: the reference for fact checking."""
        return "\n".join(e.text for e in self.evidence)


REQUIRED = ["identity", "experience", "education"]


def _slug(employer: str) -> str:
    word = re.sub(r"[^A-Za-z]", "", employer.split()[0]) if employer.strip() else "ROLE"
    return word.upper() or "ROLE"


def build_evidence(raw: dict[str, Any]) -> list[Evidence]:
    items: list[Evidence] = []
    for role in raw.get("experience", []):
        prefix = _slug(role.get("employer", ""))
        end = role.get("end") or "present"
        header = (f"{role.get('title')} at {role.get('employer')}, {role.get('location')}, "
                  f"{role.get('start')} to {end}")
        extras = [f"{k.replace('_', ' ')}: {role[k]}" for k in ("reports_to", "direct_team", "external_parties")
                  if role.get(k)]
        items.append(Evidence(f"{prefix}-role", "experience", "; ".join([header, *extras])))
        if role.get("employer_profile"):
            # Facts about the employer, not achievements of the candidate
            items.append(Evidence(f"{prefix}-company", "employer", role["employer_profile"]))
        for n, text in enumerate(role.get("highlights", []), start=1):
            items.append(Evidence(f"{prefix}-h{n}", "experience", text))
    for n, p in enumerate(raw.get("projects", []), start=1):
        status = f" ({p['status']})" if p.get("status") else ""
        items.append(Evidence(f"PRJ-{n}", "project", f"{p['name']}, {p.get('location', '')}{status}: {p.get('desc', '')}"))
    for n, e in enumerate(raw.get("education", []), start=1):
        thesis = f"; thesis: {e['thesis']}" if e.get("thesis") else ""
        items.append(Evidence(f"EDU-{n}", "education",
                              f"{e['degree']}, {e['institution']}, {e.get('start')} to {e.get('end')}{thesis}"))
    for n, c in enumerate(raw.get("certifications_and_training", []), start=1):
        date = f", {c['date']}" if c.get("date") else ""
        items.append(Evidence(f"CERT-{n}", "certification", f"{c['name']}, {c['issuer']}{date}"))
    for group, values in raw.get("skills", {}).items():
        items.append(Evidence(f"SKILL-{group}", "skill", ", ".join(values)))
    for n, t in enumerate(raw.get("thought_leadership", []), start=1):
        items.append(Evidence(f"TL-{n}", "thought_leadership", f"{t['title']} ({t.get('year', '')})"))
    for key, value in raw.get("headline_metrics", {}).items():
        shown = ", ".join(value) if isinstance(value, list) else value
        items.append(Evidence(f"MET-{key}", "metric", f"{key.replace('_', ' ')}: {shown}"))
    for n, lang in enumerate(raw.get("identity", {}).get("languages", []), start=1):
        items.append(Evidence(f"LANG-{n}", "language", f"{lang['language']}: {lang['level']}"))
    return items


def load_profile(path: Path) -> Profile:
    if not path.exists():
        raise ProfileError(f"master profile not found at {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProfileError(f"master profile is not valid JSON: {exc}") from exc
    missing = [k for k in REQUIRED if not raw.get(k)]
    if missing:
        raise ProfileError(f"master profile is missing: {', '.join(missing)}")
    if not raw["identity"].get("name"):
        raise ProfileError("master profile has no identity.name")
    return Profile(raw=raw, evidence=build_evidence(raw))
