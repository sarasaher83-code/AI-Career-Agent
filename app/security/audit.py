"""Tamper-evident, append-only log of every system action.

Each event stores the hash of the previous event, so any later edit to the database file
breaks the chain and is detected by `verify_chain`.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

GENESIS = "0" * 64

_SECRET_KEYS = {"password", "api_key", "apikey", "token", "secret", "cookie", "authorization"}


def _redact(details: dict[str, Any]) -> dict[str, Any]:
    """Never let a credential reach the log, even by mistake."""
    clean: dict[str, Any] = {}
    for key, value in details.items():
        if any(s in key.lower() for s in _SECRET_KEYS):
            clean[key] = "[redacted]"
        elif isinstance(value, dict):
            clean[key] = _redact(value)
        else:
            clean[key] = value
    return clean


def _event_hash(prev_hash: str, ts: str, actor: str, action: str, target: str, details: str) -> str:
    material = json.dumps([prev_hash, ts, actor, action, target, details], ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuditEvent:
    id: int
    ts: str
    actor: str
    action: str
    target: str
    details: dict[str, Any]


class AuditLog:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def record(self, action: str, target: str = "", details: dict[str, Any] | None = None,
               actor: str = "system") -> AuditEvent:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        details_json = json.dumps(_redact(details or {}), ensure_ascii=False, sort_keys=True)
        row = self._conn.execute("SELECT hash FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
        prev_hash = row["hash"] if row else GENESIS
        event_hash = _event_hash(prev_hash, ts, actor, action, target, details_json)
        cur = self._conn.execute(
            "INSERT INTO audit_events (ts, actor, action, target, details, prev_hash, hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ts, actor, action, target, details_json, prev_hash, event_hash),
        )
        self._conn.commit()
        return AuditEvent(cur.lastrowid, ts, actor, action, target, json.loads(details_json))

    def recent(self, limit: int = 50) -> list[AuditEvent]:
        rows = self._conn.execute(
            "SELECT id, ts, actor, action, target, details FROM audit_events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [AuditEvent(r["id"], r["ts"], r["actor"], r["action"], r["target"], json.loads(r["details"]))
                for r in rows]

    def verify_chain(self) -> bool:
        prev_hash = GENESIS
        for r in self._conn.execute("SELECT * FROM audit_events ORDER BY id"):
            if r["prev_hash"] != prev_hash:
                return False
            expected = _event_hash(prev_hash, r["ts"], r["actor"], r["action"], r["target"], r["details"])
            if r["hash"] != expected:
                return False
            prev_hash = r["hash"]
        return True
