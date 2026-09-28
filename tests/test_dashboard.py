from fastapi.testclient import TestClient

from app.main import create_app


def client_for(settings):
    return TestClient(create_app(settings))


def test_overview_shows_profile_and_readiness(settings):
    with client_for(settings) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "Test Candidate" in page.text
        assert "System readiness" in page.text
        assert "Add ANTHROPIC_API_KEY" in page.text
        assert "7777" not in page.text                 # private preferences never rendered


def test_all_sections_render(settings):
    with client_for(settings) as client:
        for key in ["discovery", "matching", "pipeline", "cv-library", "linkedin", "networking",
                    "content", "recruiters", "analytics"]:
            assert client.get(f"/section/{key}").status_code == 200
        assert client.get("/section/unknown").status_code == 404
        assert client.get("/audit").status_code == 200
        assert client.get("/health").json()["profile_loaded"] is True


def test_fact_checker_page_and_audit(settings):
    with client_for(settings) as client:
        ok = client.post("/fact-check", data={"text": "Led 12 residential projects."})
        assert "Passed" in ok.text
        bad = client.post("/fact-check", data={"text": "Managed SAR 90 million of works."})
        assert "Blocked" in bad.text
        log = client.get("/audit").text
        assert "fact_check.run" in log and "verified" in log


def test_missing_profile_is_reported(tmp_path):
    from app.config.settings import Settings
    s = Settings.load(env={"CAREER_DATA_DIR": str(tmp_path)}, env_file=tmp_path / "none.env")
    with TestClient(create_app(s)) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "master profile not found" in page.text
