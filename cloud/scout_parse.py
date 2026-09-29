"""Parse one saved job-alert email into JSON vacancies (clean links only).

Usage: python -m cloud.scout_parse <email.html> <sender address> <received YYYY-MM-DD>
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

from app.ingestion.sources.email_alerts import AlertEmail, parse_alert


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    path, sender, received = argv
    email = AlertEmail(sender, "job alert", date.fromisoformat(received), Path(path).read_text(encoding="utf-8"))
    result = parse_alert(email)
    if result is None:
        print(json.dumps({"supported": False, "vacancies": []}))
        return 0
    print(json.dumps({"supported": True, "parser": result.parser, "skipped": result.skipped,
                      "vacancies": [asdict(v) for v in result.vacancies]}, default=str, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
