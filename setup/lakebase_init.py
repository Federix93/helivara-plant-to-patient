#!/usr/bin/env python3
"""Create the Lakebase database `helivara` (if missing) and apply setup/lakebase_init.sql."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import pg8000.dbapi  # noqa: E402
from databricks.sdk import WorkspaceClient  # noqa: E402

from helivara import lakebase_sync as L  # noqa: E402
from helivara.dbx import PROFILE  # noqa: E402

w = WorkspaceClient(profile=PROFILE)
user = w.current_user.me().user_name


def connect(db):
    tok = w.postgres.generate_database_credential(endpoint=L.PROJECT_ENDPOINT).token
    return pg8000.dbapi.connect(host=L.PG_HOST, port=5432, database=db, user=user, password=tok, ssl_context=True)


c = connect("databricks_postgres")
c.autocommit = True
cur = c.cursor()
cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (L.PG_DATABASE,))
if not cur.fetchone():
    cur.execute(f"CREATE DATABASE {L.PG_DATABASE}")
    print("created database", L.PG_DATABASE)
c.close()

c = connect(L.PG_DATABASE)
cur = c.cursor()
sql_text = "\n".join(line for line in (ROOT / "setup/lakebase_init.sql").read_text().splitlines()
                     if not line.strip().startswith("--"))
for body in [s.strip() for s in sql_text.split(";")]:
    if body:
        cur.execute(body)
c.commit()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='control_tower' ORDER BY 1")
print("control_tower tables:", [r[0] for r in cur.fetchall()])
