"""Blocks generated text that states anything the master profile cannot support.

Checks, in order of severity:
  * financial data (currency amounts, "million", investment metrics next to a number)  -> BLOCK
  * phrases the candidate has ruled out (e.g. unsupported figures or titles)            -> BLOCK
  * professional credentials that are not in the profile (e.g. MBA, PMP)                -> BLOCK
  * numbers that do not appear anywhere in the verified profile                          -> BLOCK
  * investment terms without a number (e.g. "ROI-driven")                               -> WARN
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.profile.loader import NON_EVIDENCE_SECTIONS, Profile

BLOCK, WARN = "block", "warn"

# Standard names that contain digits but are not claims about the candidate.
ALLOWED_PHRASES = ["Vision 2030", "ISO 19650", "ISO 9001", "Saudi Vision 2030"]

_CURRENCY = re.compile(
    r"(\b(SAR|USD|AED|QAR|KWD|BHD|OMR|EGP|EUR|GBP|SR)\b|[$€£]|ريال|درهم|\bdollars?\b|\briyals?\b)",
    re.IGNORECASE)
_LARGE_MONEY = re.compile(r"\b(million|billion|mn|bn)\b", re.IGNORECASE)
_FIN_TERMS = re.compile(r"\b(IRR|ROI|CAPEX|OPEX|GOP|NOI|payback|return on (capital|investment)|profit margin|"
                        r"revenue|sales value|budget of|valued at)\b", re.IGNORECASE)
_NUMBER = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?")
_CREDENTIALS = ["MBA", "EMBA", "PMP", "PgMP", "PMI-RMP", "RICS", "MRICS", "FRICS", "CFA", "LEED", "PRINCE2",
                "CCM", "CEng", "Chartered", "Dr."]


@dataclass(frozen=True)
class Violation:
    severity: str
    rule: str
    excerpt: str
    message: str


@dataclass
class FactCheckResult:
    violations: list[Violation] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(v.severity == BLOCK for v in self.violations)

    @property
    def blocking(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == BLOCK]

    @property
    def warnings(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == WARN]


def _normalize_number(integer: str, decimals: str | None) -> str:
    value = integer.replace(",", "").lstrip("0") or "0"
    if decimals and decimals.strip("0"):
        value += "." + decimals.rstrip("0")
    return value


def _strings(node) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, (int, float)):
        return [str(node)]
    if isinstance(node, dict):
        return [s for v in node.values() for s in _strings(v)]
    if isinstance(node, list):
        return [s for v in node for s in _strings(v)]
    return []


def verified_numbers(profile: Profile) -> set[str]:
    """Every number that appears in an evidence section of the master profile."""
    numbers: set[str] = set()
    for key, section in profile.raw.items():
        if key in NON_EVIDENCE_SECTIONS:
            continue
        for text in _strings(section):
            for m in _NUMBER.finditer(text):
                numbers.add(_normalize_number(m.group(1), m.group(2)))
    return numbers


def _excerpt(text: str, start: int, end: int, pad: int = 40) -> str:
    left = max(0, start - pad)
    right = min(len(text), end + pad)
    return ("…" if left else "") + text[left:right].strip() + ("…" if right < len(text) else "")


def _sentences(text: str) -> list[tuple[int, str]]:
    out, pos = [], 0
    for part in re.split(r"(?<=[.!?؟\n])\s+", text):
        idx = text.find(part, pos)
        out.append((idx, part))
        pos = idx + len(part)
    return out


def check_text(text: str, profile: Profile) -> FactCheckResult:
    result = FactCheckResult()
    add = result.violations.append
    lowered = text.lower()

    # 1. Financial data
    for m in _CURRENCY.finditer(text):
        add(Violation(BLOCK, "financial_data", _excerpt(text, m.start(), m.end()),
                      "Currency amounts are not allowed in any output."))
    for m in _LARGE_MONEY.finditer(text):
        add(Violation(BLOCK, "financial_data", _excerpt(text, m.start(), m.end()),
                      "Monetary scale words (million/billion) are not allowed."))
    for _, sentence in _sentences(text):
        for m in _FIN_TERMS.finditer(sentence):
            has_number = bool(_NUMBER.search(sentence))
            add(Violation(BLOCK if has_number else WARN, "financial_metric", _excerpt(sentence, m.start(), m.end()),
                          "Investment metrics with figures are not allowed." if has_number
                          else "Investment term used; make sure no confidential figure is implied."))

    # 2. Phrases the candidate has ruled out
    for phrase in profile.forbidden_phrases:
        idx = lowered.find(phrase.lower())
        if idx >= 0:
            add(Violation(BLOCK, "forbidden_phrase", _excerpt(text, idx, idx + len(phrase)),
                          f'"{phrase}" is excluded from the verified profile.'))

    # 3. Credentials that are not held
    reference = profile.evidence_text()
    for cred in _CREDENTIALS:
        pattern = re.compile(rf"(?<![\w-]){re.escape(cred)}(?![\w-])")
        m = pattern.search(text)
        if m and not pattern.search(reference):
            add(Violation(BLOCK, "unverified_credential", _excerpt(text, m.start(), m.end()),
                          f'"{cred}" is not a credential in the verified profile.'))

    # 4. Numbers not found in the profile
    scrubbed = text
    for phrase in ALLOWED_PHRASES:
        scrubbed = re.sub(re.escape(phrase), " " * len(phrase), scrubbed, flags=re.IGNORECASE)
    allowed = verified_numbers(profile)
    for m in _NUMBER.finditer(scrubbed):
        value = _normalize_number(m.group(1), m.group(2))
        if value not in allowed:
            add(Violation(BLOCK, "unverified_number", _excerpt(text, m.start(), m.end()),
                          f"The number {m.group(0)} does not appear in the verified profile."))

    return result
