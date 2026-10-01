from pathlib import Path

import pytest
from docx import Document

from cloud.interview_prep import PrepError, build

FIXTURE = Path(__file__).parent / "fixtures" / "sample_profile.json"


def prep(answer="I led 12 residential projects in Riyadh."):
    return {"code": "PREP-T", "title": "Interview Preparation", "sections": [
        {"heading": "Questions", "bullets": ["Ask about the team."], "qa": [{"q": "Tell us about your work.", "a": answer}]}]}


def test_builds_document(tmp_path):
    files = build(FIXTURE, prep(), tmp_path, pdf=False)
    text = "\n".join(p.text for p in Document(files[0]).paragraphs)
    assert "Tell us about your work." in text and "12 residential projects" in text


def test_blocks_invented_answers(tmp_path):
    with pytest.raises(PrepError, match="Currency"):
        build(FIXTURE, prep("I managed SAR 3 billion of works."), tmp_path, pdf=False)
