"""Vacancy storage with duplicate detection.

A vacancy seen again from the same source (same job id) only updates `last_seen`. The same job arriving from a
different source is merged when title, employer and location match closely, and both sources are kept.
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict
from datetime import date, datetime, timezone
from difflib import SequenceMatcher

from app.ingestion.models import Vacancy
from app.ingestion.normalize import employer_key, is_confidential, title_key

SCHEMA = """
CREATE TABLE IF NOT EXISTS vacancies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL, employer TEXT NOT NULL,
    title_key TEXT NOT NULL, employer_key TEXT NOT NULL,
    location_raw TEXT, city TEXT, country TEXT, country_code TEXT,
    published_date TEXT, deadline TEXT, salary_text TEXT, description TEXT,
    experience_min INTEGER, experience_max INTEGER, qualifications TEXT,
    apply_url TEXT, employer_profile TEXT, easy_apply INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'new',
    first_seen TEXT NOT NULL, last_seen TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vacancy_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vacancy_id INTEGER NOT NULL REFERENCES vacancies(id),
    source TEXT NOT NULL, source_job_id TEXT NOT NULL, url TEXT, seen_at TEXT NOT NULL,
    UNIQUE (source, source_job_id)
);
CREATE INDEX IF NOT EXISTS idx_vacancies_country ON vacancies(country_code);
"""

STATUSES = ("new", "shortlisted", "dismissed")
TITLE_MATCH = 0.90
EMPLOYER_MATCH = 0.85


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


class VacancyStore:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        conn.executescript(SCHEMA)

    def _find_duplicate(self, v: Vacancy, tkey: str, ekey: str) -> int | None:
        rows = self._conn.execute(
            "SELECT id, title_key, employer_key, city, experience_min, experience_max FROM vacancies "
            "WHERE country_code = ?", (v.country_code,)).fetchall()
        for r in rows:
            if v.city and r["city"] and v.city.lower() != r["city"].lower():
                continue
            if _similar(tkey, r["title_key"]) < TITLE_MATCH:
                continue
            if is_confidential(v.employer) or is_confidential(r["employer_key"]):
                # Anonymous employers are only merged when title and experience range are identical.
                if tkey == r["title_key"] and (v.experience_min, v.experience_max) == (r["experience_min"], r["experience_max"]):
                    return r["id"]
                continue
            if _similar(ekey, r["employer_key"]) >= EMPLOYER_MATCH:
                return r["id"]
        return None

    def add(self, v: Vacancy) -> tuple[int, str]:
        """Store a vacancy. Returns (vacancy id, outcome) with outcome 'new', 'seen_again' or 'merged'."""
        now = _now()
        known = self._conn.execute("SELECT vacancy_id FROM vacancy_sources WHERE source = ? AND source_job_id = ?",
                                   (v.source, v.source_job_id)).fetchone()
        if known:
            self._conn.execute("UPDATE vacancies SET last_seen = ? WHERE id = ?", (now, known["vacancy_id"]))
            self._conn.commit()
            return known["vacancy_id"], "seen_again"

        tkey, ekey = title_key(v.title), employer_key(v.employer)
        duplicate = self._find_duplicate(v, tkey, ekey)
        if duplicate:
            vacancy_id, outcome = duplicate, "merged"
            self._fill_missing(vacancy_id, v, now)
        else:
            cur = self._conn.execute(
                "INSERT INTO vacancies (title, employer, title_key, employer_key, location_raw, city, country, "
                "country_code, published_date, deadline, salary_text, description, experience_min, experience_max, "
                "qualifications, apply_url, employer_profile, easy_apply, first_seen, last_seen) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (v.title, v.employer, tkey, ekey, v.location_raw, v.city, v.country, v.country_code,
                 _iso(v.published_date), _iso(v.deadline), v.salary_text, v.description, v.experience_min,
                 v.experience_max, v.qualifications, v.apply_url, v.employer_profile, int(v.easy_apply), now, now))
            vacancy_id, outcome = cur.lastrowid, "new"
        self._conn.execute("INSERT INTO vacancy_sources (vacancy_id, source, source_job_id, url, seen_at) "
                           "VALUES (?, ?, ?, ?, ?)", (vacancy_id, v.source, v.source_job_id, v.apply_url, now))
        self._conn.commit()
        return vacancy_id, outcome

    def _fill_missing(self, vacancy_id: int, v: Vacancy, now: str) -> None:
        """A second source may carry fields the first lacked (e.g. description, salary, deadline)."""
        row = self._conn.execute("SELECT * FROM vacancies WHERE id = ?", (vacancy_id,)).fetchone()
        updates = {"last_seen": now}
        for column, value in (("description", v.description), ("salary_text", v.salary_text),
                              ("deadline", _iso(v.deadline)), ("qualifications", v.qualifications),
                              ("published_date", _iso(v.published_date)), ("employer_profile", v.employer_profile)):
            if value and not row[column]:
                updates[column] = value
        assignments = ", ".join(f"{c} = ?" for c in updates)
        self._conn.execute(f"UPDATE vacancies SET {assignments} WHERE id = ?", (*updates.values(), vacancy_id))

    def list(self, country_code: str = "", status: str = "", query: str = "", source: str = "",
             limit: int = 500) -> list[dict]:
        sql = ("SELECT v.*, GROUP_CONCAT(DISTINCT s.source) AS sources FROM vacancies v "
               "JOIN vacancy_sources s ON s.vacancy_id = v.id WHERE 1 = 1")
        params: list = []
        if country_code:
            sql += " AND v.country_code = ?"
            params.append(country_code)
        if status:
            sql += " AND v.status = ?"
            params.append(status)
        if query:
            sql += " AND (v.title LIKE ? OR v.employer LIKE ?)"
            params += [f"%{query}%", f"%{query}%"]
        if source:
            sql += " AND v.id IN (SELECT vacancy_id FROM vacancy_sources WHERE source = ?)"
            params.append(source)
        sql += " GROUP BY v.id ORDER BY COALESCE(v.published_date, v.first_seen) DESC, v.id DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self._conn.execute(sql, params)]

    def get(self, vacancy_id: int) -> dict | None:
        row = self._conn.execute("SELECT * FROM vacancies WHERE id = ?", (vacancy_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["source_records"] = [dict(r) for r in self._conn.execute(
            "SELECT source, source_job_id, url, seen_at FROM vacancy_sources WHERE vacancy_id = ?", (vacancy_id,))]
        return item

    def set_status(self, vacancy_id: int, status: str) -> None:
        if status not in STATUSES:
            raise ValueError(f"unknown status {status}")
        self._conn.execute("UPDATE vacancies SET status = ? WHERE id = ?", (status, vacancy_id))
        self._conn.commit()

    def counts(self) -> dict:
        total = self._conn.execute("SELECT COUNT(*) FROM vacancies").fetchone()[0]
        by_country = {r[0] or "?": r[1] for r in self._conn.execute(
            "SELECT country_code, COUNT(*) FROM vacancies GROUP BY country_code ORDER BY 2 DESC")}
        return {"total": total, "by_country": by_country}

    def countries(self) -> list[tuple[str, str]]:
        return [(r[0], r[1]) for r in self._conn.execute(
            "SELECT DISTINCT country_code, country FROM vacancies WHERE country_code != '' ORDER BY country")]

    def sources(self) -> list[str]:
        return [r[0] for r in self._conn.execute("SELECT DISTINCT source FROM vacancy_sources ORDER BY source")]


def vacancy_as_dict(v: Vacancy) -> dict:
    return asdict(v)
