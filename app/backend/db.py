"""Lakebase (Postgres) access for the app: pg8000 connections with a cached OAuth credential that is
refreshed 5 minutes before it expires, so a long-running app never uses a stale token."""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from typing import Callable

ENDPOINT = os.getenv("LAKEBASE_ENDPOINT", "projects/helivara/branches/production/endpoints/primary")
PGHOST = os.getenv("PGHOST", "ep-long-credit-d7nhfvsv.database.eu-central-1.cloud.databricks.com")
PGDATABASE = os.getenv("PGDATABASE", "helivara")

ACTION_COLUMNS = ["action_id", "launch_id", "action_type", "equipment", "owner", "due_date", "note", "status",
                  "created_by", "created_at"]
ACTION_INSERT_SQL = (
    "INSERT INTO control_tower.actions (launch_id, action_type, equipment, owner, due_date, note, created_by) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s) "
    "ON CONFLICT (launch_id, action_type) WHERE status = 'open' DO NOTHING "
    f"RETURNING {', '.join(ACTION_COLUMNS)}")


class CredentialCache:
    def __init__(self, fetch: Callable[[], tuple[str, float]], clock: Callable[[], float] = time.time,
                 margin_s: float = 300):
        self._fetch, self._clock, self._margin = fetch, clock, margin_s
        self._token, self._expires = None, 0.0
        self._lock = threading.Lock()

    def get(self) -> str:
        with self._lock:
            if self._token is None or self._clock() >= self._expires - self._margin:
                self._token, self._expires = self._fetch()
            return self._token


def to_epoch(exp, now: float | None = None) -> float:
    """Credential expiry (str / datetime / SDK Timestamp / None) -> epoch seconds; None means 1 hour from now."""
    if exp is None:
        return (time.time() if now is None else now) + 3600
    if hasattr(exp, "ToDatetime"):
        exp = exp.ToDatetime()
    if isinstance(exp, str):
        exp = datetime.fromisoformat(exp.replace("Z", "+00:00"))
    if isinstance(exp, datetime):
        return exp.replace(tzinfo=exp.tzinfo or timezone.utc).timestamp()
    return float(exp)


def _sdk_fetch():
    from databricks.sdk import WorkspaceClient
    cred = WorkspaceClient().postgres.generate_database_credential(endpoint=ENDPOINT)
    return cred.token, to_epoch(getattr(cred, "expire_time", None))


class PgRepo:
    def __init__(self, user: str | None = None, credentials: CredentialCache | None = None):
        self.user = user or os.getenv("PGUSER") or os.getenv("DATABRICKS_CLIENT_ID")
        self.credentials = credentials or CredentialCache(_sdk_fetch)

    def _conn(self):
        import pg8000.dbapi
        return pg8000.dbapi.connect(host=PGHOST, port=5432, database=PGDATABASE, user=self.user,
                                    password=self.credentials.get(), ssl_context=True, timeout=15)

    def _query(self, sql: str, params=()) -> list[dict]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
        finally:
            conn.close()

    def list_launches(self) -> list[dict]:
        return self._query("SELECT * FROM control_tower.launch_risk_board ORDER BY readiness ASC")

    def list_equipment(self, limit: int) -> list[dict]:
        return self._query("SELECT * FROM control_tower.equipment_risk ORDER BY failure_prob_30d DESC LIMIT %s", (limit,))

    def list_actions(self, launch_id: str | None = None) -> list[dict]:
        if launch_id:
            return self._query(f"SELECT {', '.join(ACTION_COLUMNS)} FROM control_tower.actions WHERE launch_id = %s "
                               "ORDER BY created_at DESC", (launch_id,))
        return self._query(f"SELECT {', '.join(ACTION_COLUMNS)} FROM control_tower.actions ORDER BY created_at DESC")

    def create_action(self, payload: dict, created_by: str) -> tuple[dict, bool]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(ACTION_INSERT_SQL, (payload["launch_id"], payload["action_type"], payload.get("equipment"),
                                            payload["owner"], payload["due_date"], payload.get("note"), created_by))
            row = cur.fetchone()
            conn.commit()
            if row:
                return dict(zip(ACTION_COLUMNS, row)), True
            cur.execute(f"SELECT {', '.join(ACTION_COLUMNS)} FROM control_tower.actions "
                        "WHERE launch_id = %s AND action_type = %s AND status = 'open'",
                        (payload["launch_id"], payload["action_type"]))
            return dict(zip(ACTION_COLUMNS, cur.fetchone())), False
        finally:
            conn.close()
