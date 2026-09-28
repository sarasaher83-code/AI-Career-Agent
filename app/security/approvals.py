"""Human approval workflow for anything that could leave the system.

The system itself never sends, posts or submits. A draft only becomes `approved` when the candidate
approves it, and `completed` when she confirms she performed the external action herself.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.security.audit import AuditLog

DRAFT, APPROVED, REJECTED, COMPLETED = "draft", "approved", "rejected", "completed"

TRANSITIONS: dict[str, set[str]] = {
    DRAFT: {APPROVED, REJECTED},
    APPROVED: {COMPLETED, REJECTED},
    REJECTED: {DRAFT},
    COMPLETED: set(),
}


class ApprovalError(Exception):
    pass


@dataclass(frozen=True)
class Approval:
    id: int
    kind: str
    title: str
    payload: dict[str, Any]
    status: str
    fact_check_passed: bool
    note: str
    created_at: str
    updated_at: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _from_row(r: sqlite3.Row) -> Approval:
    return Approval(r["id"], r["kind"], r["title"], json.loads(r["payload"]), r["status"],
                    bool(r["fact_check_passed"]), r["note"], r["created_at"], r["updated_at"])


class ApprovalQueue:
    def __init__(self, conn: sqlite3.Connection, audit: AuditLog):
        self._conn = conn
        self._audit = audit

    def create(self, kind: str, title: str, payload: dict[str, Any], fact_check_passed: bool) -> Approval:
        now = _now()
        cur = self._conn.execute(
            "INSERT INTO approvals (kind, title, payload, status, fact_check_passed, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (kind, title, json.dumps(payload, ensure_ascii=False), DRAFT, int(fact_check_passed), now, now),
        )
        self._conn.commit()
        self._audit.record("approval.created", f"approval:{cur.lastrowid}",
                           {"kind": kind, "title": title, "fact_check_passed": fact_check_passed})
        return self.get(cur.lastrowid)

    def get(self, approval_id: int) -> Approval:
        row = self._conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if row is None:
            raise ApprovalError(f"approval {approval_id} not found")
        return _from_row(row)

    def list(self, status: str | None = None) -> list[Approval]:
        if status:
            rows = self._conn.execute("SELECT * FROM approvals WHERE status = ? ORDER BY id DESC", (status,))
        else:
            rows = self._conn.execute("SELECT * FROM approvals ORDER BY id DESC")
        return [_from_row(r) for r in rows]

    def transition(self, approval_id: int, new_status: str, note: str = "", actor: str = "candidate") -> Approval:
        item = self.get(approval_id)
        if new_status not in TRANSITIONS[item.status]:
            raise ApprovalError(f"cannot move from {item.status} to {new_status}")
        if new_status == APPROVED and not item.fact_check_passed:
            raise ApprovalError("draft failed the fact check; fix it before approving")
        self._conn.execute("UPDATE approvals SET status = ?, note = ?, updated_at = ? WHERE id = ?",
                           (new_status, note, _now(), approval_id))
        self._conn.commit()
        self._audit.record(f"approval.{new_status}", f"approval:{approval_id}",
                           {"from": item.status, "note": note}, actor=actor)
        return self.get(approval_id)
