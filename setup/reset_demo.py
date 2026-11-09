#!/usr/bin/env python3
"""Reset the demo before presenting: remove all actions (Lakebase + Delta copy) so the hero
'Escalate' click starts from a clean board. Demo data only."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from databricks.sdk import WorkspaceClient  # noqa: E402

from helivara.dbx import FQ, PROFILE, sql  # noqa: E402
from helivara.lakebase_sync import pg_connect  # noqa: E402

conn = pg_connect(workspace_client=WorkspaceClient(profile=PROFILE))
cur = conn.cursor()
cur.execute("DELETE FROM control_tower.actions")
n = cur.rowcount
conn.commit()
conn.close()
sql(f"DELETE FROM {FQ}.ops_launch_actions")
print(f"removed {n} action(s) from Lakebase and cleared {FQ}.ops_launch_actions")
