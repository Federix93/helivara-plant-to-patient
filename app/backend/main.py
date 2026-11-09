"""Helivara Launch & Supply Control Tower API (Databricks App). Synthetic data, fictional company."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Header, Query, Response
from fastapi.staticfiles import StaticFiles

from .models import ActionIn, GenieAsk

DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


def create_app(repo=None, genie=None) -> FastAPI:
    app = FastAPI(title="Helivara Control Tower")
    state = {"repo": repo, "genie": genie}

    def r():
        if state["repo"] is None:
            from .db import PgRepo
            state["repo"] = PgRepo()
        return state["repo"]

    def g():
        if state["genie"] is None:
            from .genie import GenieClient
            state["genie"] = GenieClient.from_env()
        return state["genie"]

    @app.get("/api/health")
    def health():
        return {"ok": True}

    @app.get("/api/launches")
    def launches():
        return sorted(r().list_launches(), key=lambda x: (x.get("readiness") is None, x.get("readiness")))

    @app.get("/api/equipment-risk")
    def equipment(limit: int = Query(10, ge=1, le=100)):
        return r().list_equipment(limit)

    @app.get("/api/actions")
    def actions(launch_id: str | None = None):
        return r().list_actions(launch_id)

    @app.post("/api/actions", status_code=201)
    def create(body: ActionIn, response: Response, x_forwarded_email: str | None = Header(default=None)):
        row, created = r().create_action(body.model_dump(), x_forwarded_email or "unknown")
        if not created:
            response.status_code = 200
        return row

    @app.post("/api/genie/ask")
    def ask(body: GenieAsk, x_forwarded_access_token: str | None = Header(default=None)):
        return g().ask(body.question, body.space, body.conversation_id, x_forwarded_access_token)

    if DIST.exists():
        app.mount("/", StaticFiles(directory=DIST, html=True), name="ui")
    return app


app = create_app()
