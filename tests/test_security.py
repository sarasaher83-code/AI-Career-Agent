import sqlite3

import pytest

from app.config.settings import Settings, mask_secret
from app.security.approvals import APPROVED, COMPLETED, DRAFT, REJECTED, ApprovalError, ApprovalQueue


def test_audit_chain_and_redaction(audit, conn):
    audit.record("a.one", details={"api_key": "sk-ant-should-not-appear", "count": 1})
    audit.record("a.two", details={"nested": {"password": "x"}})
    assert audit.verify_chain()
    rows = conn.execute("SELECT details FROM audit_events").fetchall()
    assert all("sk-ant" not in r["details"] and '"x"' not in r["details"] for r in rows)


def test_audit_log_is_append_only(audit, conn):
    audit.record("a.one")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("UPDATE audit_events SET action = 'tampered'")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("DELETE FROM audit_events")


def test_audit_detects_tampering(audit, conn):
    audit.record("a.one")
    audit.record("a.two")
    conn.execute("DROP TRIGGER audit_no_update")          # simulate someone editing the file directly
    conn.execute("UPDATE audit_events SET action = 'forged' WHERE id = 1")
    assert not audit.verify_chain()


def test_approval_lifecycle(conn, audit):
    queue = ApprovalQueue(conn, audit)
    item = queue.create("cover_letter", "Letter for Example Co", {"text": "..."}, fact_check_passed=True)
    assert item.status == DRAFT
    assert queue.transition(item.id, APPROVED).status == APPROVED
    assert queue.transition(item.id, COMPLETED, note="Submitted by candidate").status == COMPLETED
    with pytest.raises(ApprovalError):
        queue.transition(item.id, DRAFT)
    actions = [e.action for e in audit.recent()]
    assert {"approval.created", "approval.approved", "approval.completed"} <= set(actions)


def test_cannot_approve_failed_fact_check(conn, audit):
    queue = ApprovalQueue(conn, audit)
    item = queue.create("cv", "CV", {}, fact_check_passed=False)
    with pytest.raises(ApprovalError, match="fact check"):
        queue.transition(item.id, APPROVED)
    assert queue.transition(item.id, REJECTED).status == REJECTED


def test_settings_defaults_and_masking(tmp_path):
    s = Settings.load(env={}, env_file=tmp_path / "none.env")
    assert s.claude_model == "claude-opus-5"
    assert not s.enable_aggregators and not s.has_anthropic_key
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=sk-ant-abcdef123456\nENABLE_AGGREGATORS=true\n", encoding="utf-8")
    s = Settings.load(env={}, env_file=env_file)
    assert s.has_anthropic_key and s.enable_aggregators
    assert mask_secret(s.anthropic_api_key) == "sk-ant…3456"
    assert mask_secret("") == "not set"


def test_commit_guard_blocks_personal_data():
    from scripts.check_commit import problems
    files = ["private/master_profile.json", ".env", "app/x.py", "notes.txt", ".env.example",
             "tests/fixtures/sample_profile.json", "app/settings.py", "docs/guide.md"]
    contents = {
        "app/x.py": "KEY = 'sk-ant-api03-" + "a1B2c3D4e5F6g7H8i9J0k1L2" + "'",
        "notes.txt": "ANTHROPIC_API_KEY=" + "realLookingValue123456",
        ".env.example": "ANTHROPIC_API_KEY=",
        "app/settings.py": 'anthropic_api_key=values.get("ANTHROPIC_API_KEY", "")',
        "docs/guide.md": "   ANTHROPIC_API_KEY=sk-ant-...(your key)",
    }
    found = problems(files, lambda p: contents.get(p, ""))
    flagged = {f.split(":")[0] for f in found}
    assert flagged == {"private/master_profile.json", ".env", "app/x.py", "notes.txt"}
