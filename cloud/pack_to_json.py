"""Bundle one job's generated files into a Career Desk `packs/<code>` document (files base64-encoded).

Usage: python -m cloud.pack_to_json <code> <output dir from app_builder> <tailoring.json> <result.json>
Keep each pack under the database's 256 KiB document limit (a CV + letter in Word and PDF is ~200 KiB).
"""

from __future__ import annotations

import base64
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LIMIT = 250_000


def bundle(code: str, out_dir: Path, tailoring: dict) -> dict:
    files = []
    for path in sorted(out_dir.glob(f"{code}_*")):
        if path.suffix not in (".docx", ".pdf"):
            continue
        kind = ("CV" if "_CV_" in path.name else "Cover letter") + (" (Word)" if path.suffix == ".docx" else " (PDF)")
        files.append({"filename": path.name, "kind": kind, "b64": base64.b64encode(path.read_bytes()).decode()})
    if not files:
        raise FileNotFoundError(f"no files for {code} in {out_dir}")
    letter = tailoring.get("letter", {})
    doc = {
        "code": code, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": files,
        "letter_text": "\n\n".join([letter.get("salutation", "Dear Hiring Team,"), *letter.get("paragraphs", []),
                                    letter.get("closing", "Kind regards,")]),
        "summary": tailoring.get("summary", ""),
    }
    size = len(json.dumps(doc))
    if size > LIMIT:
        raise ValueError(f"pack for {code} is {size} bytes, over the {LIMIT} limit")
    return doc


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    code, out_dir, tailoring, result = argv
    doc = bundle(code, Path(out_dir), json.loads(Path(tailoring).read_text(encoding="utf-8")))
    Path(result).write_text(json.dumps(doc), encoding="utf-8")
    print(f"{result} ({len(json.dumps(doc))} bytes, {len(doc['files'])} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
