#!/usr/bin/env python3
"""Give the app's service principal a Lakebase role: read the serving tables, insert/read actions."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from databricks.sdk import WorkspaceClient  # noqa: E402

from helivara.dbx import PROFILE  # noqa: E402
from helivara.lakebase_sync import PG_DATABASE, pg_connect  # noqa: E402

APP = "helivara-control-tower"
sp = json.loads(subprocess.run(["databricks", "apps", "get", APP, "--profile", PROFILE, "-o", "json"],
                               capture_output=True, text=True, check=True).stdout)["service_principal_client_id"]
conn = pg_connect(workspace_client=WorkspaceClient(profile=PROFILE))
conn.autocommit = True
cur = conn.cursor()
cur.execute("CREATE EXTENSION IF NOT EXISTS databricks_auth")
cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (sp,))
if not cur.fetchone():
    cur.execute("SELECT databricks_create_role(%s, 'SERVICE_PRINCIPAL')", (sp,))
ident = '"' + sp + '"'
for stmt in [f"GRANT CONNECT ON DATABASE {PG_DATABASE} TO {ident}",
             f"GRANT USAGE ON SCHEMA control_tower TO {ident}",
             f"GRANT SELECT ON control_tower.launch_risk_board, control_tower.equipment_risk TO {ident}",
             f"GRANT SELECT, INSERT ON control_tower.actions TO {ident}",
             f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA control_tower TO {ident}"]:
    cur.execute(stmt)
cur.execute("SELECT table_name, privilege_type FROM information_schema.role_table_grants WHERE grantee = %s ORDER BY 1, 2", (sp,))
print(sp, cur.fetchall())
