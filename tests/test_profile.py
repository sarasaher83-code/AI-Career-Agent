import json

import pytest

from app.profile.loader import ProfileError, load_profile


def test_loads_and_indexes_evidence(profile):
    assert profile.name == "Test Candidate"
    ids = {e.id for e in profile.evidence}
    assert {"EXAMPLE-role", "EXAMPLE-h1", "EXAMPLE-h2", "SAMPLE-h1", "PRJ-1", "EDU-1", "CERT-1", "TL-1"} <= ids
    assert "12 residential projects" in profile.evidence_by_id("EXAMPLE-h2").text
    company = profile.evidence_by_id("EXAMPLE-company")
    assert company.kind == "employer" and "2001" in company.text


def test_private_sections_are_not_evidence(profile):
    text = profile.evidence_text()
    assert "7777" not in text              # salary preference
    assert "9999" not in text              # phone number
    assert "1,234" not in text             # excluded figure


def test_missing_file(tmp_path):
    with pytest.raises(ProfileError, match="not found"):
        load_profile(tmp_path / "nope.json")


def test_invalid_json(tmp_path):
    path = tmp_path / "p.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ProfileError, match="not valid JSON"):
        load_profile(path)


def test_missing_required_section(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"identity": {"name": "X"}, "experience": [{}]}), encoding="utf-8")
    with pytest.raises(ProfileError, match="education"):
        load_profile(path)
