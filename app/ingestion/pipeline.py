"""Runs each job source and records what happened in the audit log."""

from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import datetime, timezone
from typing import Callable

from app.ingestion.models import Vacancy
from app.ingestion.sources import ats_boards
from app.ingestion.sources.email_alerts import AlertEmail, parse_alert
from app.ingestion.store import VacancyStore
from app.security.audit import AuditLog

BOARDS_SCHEMA = """
CREATE TABLE IF NOT EXISTS career_boards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employer TEXT NOT NULL, ats TEXT NOT NULL, token TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1, last_checked TEXT, last_result TEXT,
    UNIQUE (ats, token)
);
"""


def store_all(store: VacancyStore, vacancies: list[Vacancy]) -> Counter:
    outcomes = Counter()
    for v in vacancies:
        outcomes[store.add(v)[1]] += 1
    return outcomes


def import_alert_emails(emails: list[AlertEmail], store: VacancyStore, audit: AuditLog,
                        origin: str = "gmail") -> dict:
    summary = Counter(emails=len(emails))
    for message in emails:
        result = parse_alert(message)
        if result is None:
            summary["not_job_alerts"] += 1
            continue
        summary["job_cards"] += len(result.vacancies)
        summary["unreadable_cards"] += result.skipped
        summary.update(store_all(store, result.vacancies))
    audit.record("jobs.import_emails", origin, dict(summary))
    return dict(summary)


class CareerBoards:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        conn.executescript(BOARDS_SCHEMA)

    def add(self, employer: str, ats: str, token: str) -> None:
        if ats not in ats_boards.ADAPTERS:
            raise ValueError(f"unsupported career-page system: {ats}")
        token = token.strip().strip("/")
        if not token or "/" in token or " " in token:
            raise ValueError("the board name should be a single word, e.g. 'acme' from boards.greenhouse.io/acme")
        self._conn.execute("INSERT OR IGNORE INTO career_boards (employer, ats, token) VALUES (?, ?, ?)",
                           (employer.strip(), ats, token))
        self._conn.commit()

    def list(self) -> list[dict]:
        return [dict(r) for r in self._conn.execute("SELECT * FROM career_boards ORDER BY employer")]

    def remove(self, board_id: int) -> None:
        self._conn.execute("DELETE FROM career_boards WHERE id = ?", (board_id,))
        self._conn.commit()

    def check_all(self, store: VacancyStore, audit: AuditLog, fetch: Callable = ats_boards.fetch_json) -> dict:
        summary = Counter()
        for board in self.list():
            if not board["enabled"]:
                continue
            adapter = ats_boards.ADAPTERS[board["ats"]]
            try:
                vacancies = adapter(board["token"], board["employer"], fetch=fetch)
                outcome = store_all(store, vacancies)
                summary.update(outcome)
                result = f"{len(vacancies)} jobs ({outcome.get('new', 0)} new)"
            except Exception as exc:  # one failing board must not stop the others
                summary["failed_boards"] += 1
                result = f"failed: {type(exc).__name__}"
            self._conn.execute("UPDATE career_boards SET last_checked = ?, last_result = ? WHERE id = ?",
                               (datetime.now(timezone.utc).isoformat(timespec="seconds"), result, board["id"]))
            audit.record("jobs.check_board", f"{board['ats']}:{board['token']}", {"result": result})
        self._conn.commit()
        return dict(summary)
