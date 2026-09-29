"""Reads job-alert emails from Gmail over IMAP with an app password. Read-only by construction.

* The mailbox is opened with `readonly=True` and messages are fetched with BODY.PEEK, so nothing is marked as
  read, moved, labelled or deleted.
* Only emails from known job-alert senders are requested (Gmail's own search syntax via X-GM-RAW).
"""

from __future__ import annotations

import email
import imaplib
from datetime import date, datetime
from email import policy
from email.utils import parseaddr, parsedate_to_datetime

from app.ingestion.sources.email_alerts import AlertEmail

ALERT_SENDERS = ("naukrigulf.com", "linkedin.com", "bayt.com", "gulftalent.com", "indeed.com")


class GmailError(Exception):
    pass


def _html_part(message: email.message.EmailMessage) -> str:
    part = message.get_body(preferencelist=("html",))
    if part is None:
        return ""
    try:
        return part.get_content()
    except (LookupError, UnicodeDecodeError):
        return part.get_payload(decode=True).decode("utf-8", errors="replace")


def _received(message: email.message.EmailMessage) -> date:
    try:
        return parsedate_to_datetime(message["Date"]).date()
    except (TypeError, ValueError):
        return datetime.now().date()


def to_alert_email(raw: bytes) -> AlertEmail:
    message = email.message_from_bytes(raw, policy=policy.default)
    return AlertEmail(sender=parseaddr(message.get("From", ""))[1].lower(), subject=str(message.get("Subject", "")),
                      received=_received(message), html_body=_html_part(message))


class GmailAlertReader:
    def __init__(self, address: str, app_password: str, host: str = "imap.gmail.com", imap_factory=None):
        self._address = address
        self._password = app_password
        self._host = host
        self._factory = imap_factory or imaplib.IMAP4_SSL

    def fetch(self, days: int = 14, senders: tuple[str, ...] = ALERT_SENDERS, limit: int = 200) -> list[AlertEmail]:
        try:
            conn = self._factory(self._host)
        except OSError as exc:
            raise GmailError(f"could not reach Gmail: {exc}") from exc
        try:
            try:
                conn.login(self._address, self._password)
            except imaplib.IMAP4.error as exc:
                raise GmailError("Gmail refused the login. Check GMAIL_ADDRESS and the app password.") from exc
            status, _ = conn.select("INBOX", readonly=True)
            if status != "OK":
                raise GmailError("could not open the inbox")
            query = f'from:({" OR ".join(senders)}) newer_than:{int(days)}d'
            status, data = conn.search(None, "X-GM-RAW", f'"{query}"')
            if status != "OK":
                raise GmailError("Gmail search failed")
            ids = data[0].split()[-limit:] if data and data[0] else []
            emails = []
            for msg_id in ids:
                status, parts = conn.fetch(msg_id, "(BODY.PEEK[])")
                if status == "OK" and parts and isinstance(parts[0], tuple):
                    emails.append(to_alert_email(parts[0][1]))
            return emails
        finally:
            try:
                conn.logout()
            except Exception:  # logout failures don't matter; the session is discarded
                pass
