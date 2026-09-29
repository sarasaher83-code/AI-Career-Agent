from datetime import date
from pathlib import Path

import pytest

from app.ingestion.models import Vacancy
from app.ingestion.normalize import employer_key, parse_experience, parse_location, parse_posted, title_key
from app.ingestion.pipeline import CareerBoards, import_alert_emails
from app.ingestion.sources import ats_boards
from app.ingestion.sources.email_alerts import AlertEmail, parse_alert
from app.ingestion.sources.gmail_imap import GmailAlertReader, GmailError
from app.ingestion.store import VacancyStore
from app.security.urls import UnsafeUrlError, clean_job_url

FIXTURE = Path(__file__).parent / "fixtures" / "naukrigulf_alert.html"


def alert(subject="Top 15 jobs for you today", sender="recommendedjobs@naukrigulf.com"):
    return AlertEmail(sender, subject, date(2026, 9, 29), FIXTURE.read_text(encoding="utf-8"))


# --- link safety ---------------------------------------------------------------------------------

def test_tracker_and_login_token_are_removed():
    tracked = ("https://ccs-tracking.naukrigulf.com?data=x&redirect=https%3A%2F%2Fwww.naukrigulf.com%2Fnglogin%2Fuser"
               "%2FmailerLogin%3Fconmailer%3DSECRET%26rUrl%3Dhttps%253A%252F%252Fwww.naukrigulf.com%252Fdesign-"
               "manager-jid-123%253Futm_source%253Dreco")
    assert clean_job_url(tracked) == "https://www.naukrigulf.com/design-manager-jid-123"


def test_login_pages_are_refused_but_normal_words_allowed():
    with pytest.raises(UnsafeUrlError):
        clean_job_url("https://www.naukrigulf.com/nglogin/user/mailerLogin?conmailer=SECRET")
    with pytest.raises(UnsafeUrlError):
        clean_job_url("javascript:alert(1)")
    assert clean_job_url("https://jobs.example.com/diriyah-authority-design-manager?ref=x") == \
        "https://jobs.example.com/diriyah-authority-design-manager"


# --- normalisation -------------------------------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("Dubai - United Arab Emirates (UAE)", ("Dubai", "United Arab Emirates", "AE")),
    ("Riyadh - Saudi Arabia", ("Riyadh", "Saudi Arabia", "SA")),
    ("United Arab Emirates - United Arab Emirates", ("", "United Arab Emirates", "AE")),
    ("Jeddah", ("Jeddah", "Saudi Arabia", "SA")),
    ("Doha, Qatar", ("Doha", "Qatar", "QA")),
    ("الرياض، السعودية", ("الرياض", "Saudi Arabia", "SA")),
])
def test_parse_location(raw, expected):
    assert parse_location(raw) == expected


def test_parse_experience_and_dates():
    assert parse_experience("12 - 15 Years") == (12, 15)
    assert parse_experience("10+ years") == (10, None)
    received = date(2026, 9, 29)
    assert parse_posted("5d", received) == date(2026, 9, 24)
    assert parse_posted("17 Aug", received) == date(2026, 8, 17)
    assert parse_posted("20 Dec", received) == date(2025, 12, 20)      # a date "in the future" is last year
    assert parse_posted("today", received) == received
    assert parse_posted("soon", received) is None


def test_keys_ignore_noise():
    assert title_key("Sr. Design Mgr") == title_key("Senior Design Manager")
    assert employer_key("ESG Emirates Stallions Group P.J.S.C.") == employer_key("ESG Emirates Stallions Group")


# --- Naukrigulf parser (sanitised real email) ----------------------------------------------------

def test_naukrigulf_email_parses_all_cards():
    result = parse_alert(alert())
    assert result.parser == "naukrigulf" and result.skipped == 0
    assert len(result.vacancies) == 15
    first = result.vacancies[0]
    assert first.title == "Senior Project Manager-Interior Fit out Industry"
    assert first.employer == "Confidential Company"                    # card with a nested company link
    assert (first.city, first.country_code) == ("Dubai", "AE")
    assert (first.experience_min, first.experience_max) == (5, 10)
    assert first.published_date == date(2026, 9, 24) and first.easy_apply
    assert first.source_job_id == "230926000212"
    riyadh = [v for v in result.vacancies if v.country_code == "SA"]
    assert riyadh and riyadh[0].city == "Riyadh"


def test_no_tokens_or_trackers_survive():
    for v in parse_alert(alert()).vacancies:
        assert v.apply_url.startswith("https://www.naukrigulf.com/") and "-jid-" in v.apply_url
        assert "?" not in v.apply_url and "login" not in v.apply_url.lower() and "FAKE" not in v.apply_url


def test_non_job_emails_are_ignored():
    assert parse_alert(alert(subject="You appeared in 3 searches last week!")) is None
    assert parse_alert(alert(sender="someone@unknown-site.com")) is None


# --- store & de-duplication ----------------------------------------------------------------------

def vac(**kw):
    base = dict(title="Senior Design Manager", employer="Example Developments LLC", source="manual",
                source_job_id="1", city="Riyadh", country="Saudi Arabia", country_code="SA",
                experience_min=10, experience_max=15)
    base.update(kw)
    return Vacancy(**base)


def test_same_source_same_id_is_seen_again(conn):
    store = VacancyStore(conn)
    first_id, outcome = store.add(vac())
    assert outcome == "new"
    assert store.add(vac()) == (first_id, "seen_again")


def test_cross_source_duplicate_is_merged_and_fills_gaps(conn):
    store = VacancyStore(conn)
    vid, _ = store.add(vac(source="naukrigulf_email", source_job_id="A"))
    merged_id, outcome = store.add(vac(title="Sr. Design Manager", employer="Example Developments",
                                       source="greenhouse", source_job_id="B", description="Full description"))
    assert (merged_id, outcome) == (vid, "merged")
    item = store.get(vid)
    assert item["description"] == "Full description"
    assert {s["source"] for s in item["source_records"]} == {"naukrigulf_email", "greenhouse"}
    assert store.counts()["total"] == 1


def test_different_city_or_title_is_not_merged(conn):
    store = VacancyStore(conn)
    store.add(vac(source_job_id="1"))
    assert store.add(vac(source_job_id="2", city="Jeddah"))[1] == "new"
    assert store.add(vac(source_job_id="3", title="Senior Project Manager"))[1] == "new"


def test_confidential_employers_need_identical_details(conn):
    store = VacancyStore(conn)
    store.add(vac(employer="Confidential Company", source_job_id="1"))
    assert store.add(vac(employer="Confidential Company", source_job_id="2", experience_min=5))[1] == "new"
    assert store.add(vac(employer="Confidential Company", source_job_id="3", source="bayt_email"))[1] == "merged"


def test_filters_and_status(conn):
    store = VacancyStore(conn)
    vid, _ = store.add(vac())
    store.add(vac(source_job_id="9", title="Head of Technical Office", city="Dubai", country="United Arab Emirates",
                  country_code="AE"))
    assert len(store.list(country_code="AE")) == 1
    assert len(store.list(query="technical")) == 1
    store.set_status(vid, "shortlisted")
    assert [r["id"] for r in store.list(status="shortlisted")] == [vid]
    with pytest.raises(ValueError):
        store.set_status(vid, "applied-automatically")


def test_import_pipeline_is_idempotent_and_audited(conn, audit):
    store = VacancyStore(conn)
    first = import_alert_emails([alert(), alert(subject="Employer viewed your CV")], store, audit)
    assert first["new"] == 15 and first["not_job_alerts"] == 1
    second = import_alert_emails([alert()], store, audit)
    assert second["seen_again"] == 15 and store.counts()["total"] == 15
    assert any(e.action == "jobs.import_emails" for e in audit.recent())


# --- Gmail reader (fake IMAP server: never touches a real mailbox) ---------------------------------

class FakeImap:
    instances = []

    def __init__(self, host):
        self.calls = []
        FakeImap.instances.append(self)

    def login(self, user, password):
        self.calls.append(("login", user))

    def select(self, mailbox, readonly=False):
        self.calls.append(("select", mailbox, readonly))
        return "OK", [b"1"]

    def search(self, charset, *criteria):
        self.calls.append(("search", criteria))
        return "OK", [b"1"]

    def fetch(self, msg_id, parts):
        self.calls.append(("fetch", parts))
        html = FIXTURE.read_text(encoding="utf-8")
        raw = ("From: Naukrigulf <recommendedjobs@naukrigulf.com>\r\nSubject: Top 15 jobs for you today\r\n"
               "Date: Tue, 29 Sep 2026 03:31:26 +0000\r\nMIME-Version: 1.0\r\n"
               "Content-Type: text/html; charset=utf-8\r\n\r\n" + html).encode("utf-8")
        return "OK", [(b"1 (BODY[] {1})", raw), b")"]

    def logout(self):
        self.calls.append(("logout",))


def test_gmail_reader_is_read_only():
    reader = GmailAlertReader("user@example.com", "app-password", imap_factory=FakeImap)
    emails = reader.fetch(days=14)
    calls = FakeImap.instances[-1].calls
    assert ("select", "INBOX", True) in calls                       # read-only mailbox
    assert ("fetch", "(BODY.PEEK[])") in calls                      # PEEK: does not mark as read
    assert calls[-1] == ("logout",)
    search = next(c for c in calls if c[0] == "search")[1]
    assert search[0] == "X-GM-RAW" and "naukrigulf.com" in search[1] and "newer_than:14d" in search[1]
    assert emails[0].sender == "recommendedjobs@naukrigulf.com" and emails[0].received == date(2026, 9, 29)
    assert len(parse_alert(emails[0]).vacancies) == 15


def test_gmail_bad_password_gives_clear_error():
    import imaplib

    class Refusing(FakeImap):
        def login(self, user, password):
            raise imaplib.IMAP4.error("AUTHENTICATIONFAILED")

    with pytest.raises(GmailError, match="app password"):
        GmailAlertReader("user@example.com", "wrong", imap_factory=Refusing).fetch()


# --- public career-page feeds (recorded responses; no network) -------------------------------------

FEEDS = {
    "greenhouse": {"jobs": [{"id": 11, "title": "Design Manager", "updated_at": "2026-09-20T10:00:00Z",
                             "location": {"name": "Riyadh, Saudi Arabia"}, "absolute_url": "https://boards.greenhouse.io/ex/jobs/11",
                             "content": "&lt;p&gt;Lead design&lt;/p&gt;&lt;ul&gt;&lt;li&gt;BIM&lt;/li&gt;&lt;/ul&gt;"}]},
    "lever": [{"id": "ab-1", "text": "Head of Technical Office", "createdAt": 1790000000000,
               "categories": {"location": "Dubai"}, "hostedUrl": "https://jobs.lever.co/ex/ab-1",
               "descriptionPlain": "Technical office leadership"}],
    "smartrecruiters": {"content": [{"id": "743", "name": "Development Manager", "releasedDate": "2026-09-01T08:00:00.000Z",
                                     "location": {"city": "Jeddah", "country": "sa"}, "company": {"name": "Example Co"}}]},
    "workable": {"name": "Example Studio", "jobs": [{"title": "Interior Design Manager", "shortcode": "XYZ1",
                                                     "city": "Doha", "country": "Qatar",
                                                     "url": "https://apply.workable.com/ex/j/XYZ1", "published_on": "2026-09-15"}]},
}


@pytest.mark.parametrize("system", sorted(FEEDS))
def test_ats_adapters(system):
    jobs = ats_boards.ADAPTERS[system]("ex", "Example", fetch=lambda url: FEEDS[system])
    assert len(jobs) == 1
    job = jobs[0]
    assert job.source == system and job.title and job.apply_url.startswith("https://")
    assert job.country_code in {"SA", "AE", "QA"} and job.published_date is not None
    if system == "greenhouse":
        assert "Lead design" in job.description and "<" not in job.description


def test_career_boards_check_isolates_failures(conn, audit):
    boards = CareerBoards(conn)
    store = VacancyStore(conn)
    boards.add("Example", "greenhouse", "ex")
    boards.add("Broken", "lever", "broken")

    def fetch(url):
        if "broken" in url:
            raise OSError("network down")
        return FEEDS["greenhouse"]

    summary = boards.check_all(store, audit, fetch=fetch)
    assert summary["new"] == 1 and summary["failed_boards"] == 1
    results = {b["token"]: b["last_result"] for b in boards.list()}
    assert results["ex"].startswith("1 jobs") and results["broken"].startswith("failed")
    with pytest.raises(ValueError):
        boards.add("Bad", "greenhouse", "https://boards.greenhouse.io/x")
