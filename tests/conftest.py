from pathlib import Path
import shutil

import pytest

from app.config.settings import Settings
from app.db import connect
from app.profile.loader import load_profile
from app.security.audit import AuditLog

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def profile():
    return load_profile(FIXTURES / "sample_profile.json")


@pytest.fixture
def conn(tmp_path):
    connection = connect(tmp_path / "test.db")
    yield connection
    connection.close()


@pytest.fixture
def audit(conn):
    return AuditLog(conn)


@pytest.fixture
def settings(tmp_path):
    shutil.copy(FIXTURES / "sample_profile.json", tmp_path / "master_profile.json")
    return Settings.load(env={"CAREER_DATA_DIR": str(tmp_path)}, env_file=tmp_path / "missing.env")
