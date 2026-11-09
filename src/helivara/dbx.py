"""Thin helpers around the Databricks CLI (SQL statements API, REST calls)."""
from __future__ import annotations

import json
import os
import subprocess
import time

PROFILE = os.getenv("DBX_PROFILE", "fr-stable")
WAREHOUSE_ID = os.getenv("WAREHOUSE_ID", "797d1d487d654063")
CATALOG = os.getenv("CATALOG", "fr_stable_catalog")
SCHEMA = os.getenv("SCHEMA", "supply_chain")
FQ = f"{CATALOG}.{SCHEMA}"


def api(method: str, path: str, body: dict | None = None) -> dict:
    cmd = ["databricks", "api", method.lower(), path, "--profile", PROFILE]
    if body is not None:
        cmd += ["--json", json.dumps(body)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = r.stdout[r.stdout.find("{"):] if "{" in r.stdout else r.stdout
    try:
        return json.loads(out) if out.strip() else {}
    except json.JSONDecodeError:
        return {"_error": (r.stdout + r.stderr)[:500]}


def sql(statement: str, timeout_s: int = 600) -> list[list]:
    """Run a statement on the warehouse; return rows (strings) or raise RuntimeError."""
    d = api("POST", "/api/2.0/sql/statements", {"warehouse_id": WAREHOUSE_ID, "statement": statement,
                                                "wait_timeout": "50s", "on_wait_timeout": "CONTINUE"})
    t0 = time.time()
    while d.get("status", {}).get("state") in ("PENDING", "RUNNING"):
        if time.time() - t0 > timeout_s:
            raise RuntimeError("statement timeout")
        time.sleep(3)
        d = api("GET", f"/api/2.0/sql/statements/{d['statement_id']}")
    st = d.get("status", {})
    if st.get("state") != "SUCCEEDED":
        raise RuntimeError(f"{st.get('state')}: {st.get('error', {}).get('message', d)}"[:800])
    rows = list(d.get("result", {}).get("data_array") or [])
    chunk = d.get("result", {}).get("next_chunk_internal_link")
    while chunk:
        c = api("GET", chunk)
        rows += c.get("data_array") or []
        chunk = c.get("next_chunk_internal_link")
    return rows
