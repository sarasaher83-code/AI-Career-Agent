"""Fact-check a text file against a master profile.

Usage: python -m cloud.fact_check_cli <text file> <master_profile.json>
Exit code 0 = passed, 1 = blocked. Prints each finding.
"""

from __future__ import annotations

import sys
from pathlib import Path

from app.profile.fact_check import check_text
from app.profile.loader import load_profile


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    result = check_text(Path(argv[0]).read_text(encoding="utf-8"), load_profile(Path(argv[1])))
    for v in result.violations:
        print(f"{v.severity.upper():5} {v.rule:22} {v.excerpt}  ->  {v.message}")
    print("PASSED" if result.passed else "BLOCKED")
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
