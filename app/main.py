"""Web application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config.settings import Settings
from app.dashboard.discovery import router as discovery_router
from app.dashboard.routes import router
from app.db import connect
from app.ingestion.pipeline import CareerBoards
from app.ingestion.store import VacancyStore
from app.profile.loader import ProfileError, load_profile
from app.security.approvals import ApprovalQueue
from app.security.audit import AuditLog

STATIC_DIR = Path(__file__).parent / "dashboard" / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.load()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        conn = connect(settings.db_path)
        audit = AuditLog(conn)
        app.state.settings = settings
        app.state.conn = conn
        app.state.audit = audit
        app.state.approvals = ApprovalQueue(conn, audit)
        app.state.vacancies = VacancyStore(conn)
        app.state.boards = CareerBoards(conn)
        try:
            app.state.profile = load_profile(settings.profile_path)
            app.state.profile_error = None
        except ProfileError as exc:
            app.state.profile = None
            app.state.profile_error = str(exc)
        audit.record("system.started", details={
            "profile_loaded": app.state.profile is not None,
            "anthropic_key_configured": settings.has_anthropic_key,
            "gmail_configured": settings.has_gmail,
            "aggregators_enabled": settings.enable_aggregators,
        })
        yield
        audit.record("system.stopped")
        conn.close()

    app = FastAPI(title="Executive Career Intelligence", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(router)
    app.include_router(discovery_router)
    return app


app = create_app()
