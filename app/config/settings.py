"""Application settings, read from environment variables and an optional `.env` file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parents[2]

_TRUE = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    anthropic_api_key: str
    claude_model: str
    monthly_budget_usd: float
    gmail_address: str
    gmail_app_password: str
    gmail_label: str
    enable_aggregators: bool

    @property
    def db_path(self) -> Path:
        return self.data_dir / "career.db"

    @property
    def profile_path(self) -> Path:
        return self.data_dir / "master_profile.json"

    @property
    def has_anthropic_key(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def has_gmail(self) -> bool:
        return bool(self.gmail_address and self.gmail_app_password)

    @classmethod
    def load(cls, env: Mapping[str, str] | None = None, env_file: Path | None = None) -> "Settings":
        """Build settings. Real environment variables take precedence over the `.env` file."""
        values: dict[str, str] = {}
        env_file = env_file if env_file is not None else REPO_ROOT / ".env"
        if env_file.exists():
            values.update({k: v for k, v in dotenv_values(env_file).items() if v is not None})
        values.update(env if env is not None else os.environ)

        data_dir = values.get("CAREER_DATA_DIR", "").strip()
        return cls(
            data_dir=Path(data_dir) if data_dir else REPO_ROOT / "private",
            anthropic_api_key=values.get("ANTHROPIC_API_KEY", "").strip(),
            claude_model=values.get("CLAUDE_MODEL", "").strip() or "claude-opus-5",
            monthly_budget_usd=float(values.get("MONTHLY_BUDGET_USD", "").strip() or 50),
            gmail_address=values.get("GMAIL_ADDRESS", "").strip(),
            gmail_app_password=values.get("GMAIL_APP_PASSWORD", "").strip(),
            gmail_label=values.get("GMAIL_LABEL", "").strip() or "Job Alerts",
            enable_aggregators=values.get("ENABLE_AGGREGATORS", "false").strip().lower() in _TRUE,
        )


def mask_secret(value: str) -> str:
    """Show only enough of a secret to confirm which one is configured."""
    if not value:
        return "not set"
    if len(value) <= 8:
        return "set (hidden)"
    return f"{value[:6]}…{value[-4:]}"
