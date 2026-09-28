"""Pre-commit guard: refuses commits that would publish personal data or secrets.

Enable once with:  git config core.hooksPath .githooks
"""

from __future__ import annotations

import re
import subprocess
import sys

BLOCKED_PATHS = re.compile(r"^(private/|\.env$|.*\.db$|.*master_profile.*\.json$)")
SECRET_PATTERNS = [
    re.compile(r"sk-ant-(?:api\d{2}-)?[A-Za-z0-9_\-]{20,}"),                             # Anthropic API key
    re.compile(r"(?m)^\s*(ANTHROPIC_API_KEY|GMAIL_APP_PASSWORD)\s*=\s*(?!\S*\.\.\.)\S{12,}"),  # filled-in .env line (placeholders with "..." allowed)
]
ALLOWED_FILES = {".env.example"}


def staged_files() -> list[str]:
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                         capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


def problems(files: list[str], read) -> list[str]:
    found = []
    for path in files:
        if BLOCKED_PATHS.match(path) and not path.startswith("tests/fixtures/"):
            found.append(f"{path}: personal-data or secrets file must never be committed")
            continue
        if path in ALLOWED_FILES or path.startswith("tests/"):
            continue  # test files hold deliberately fake keys
        text = read(path)
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                found.append(f"{path}: looks like it contains a secret ({pattern.pattern[:30]}…)")
    return found


def _read_staged(path: str) -> str:
    result = subprocess.run(["git", "show", f":{path}"], capture_output=True)
    return result.stdout.decode("utf-8", errors="ignore")


def main() -> int:
    found = problems(staged_files(), _read_staged)
    for message in found:
        print(f"BLOCKED: {message}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
