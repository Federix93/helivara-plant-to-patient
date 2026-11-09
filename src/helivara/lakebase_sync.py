"""Gold (Delta) -> Lakebase (Postgres) serving sync, plus the Lakebase connection helper.

Serving tables are upserted by primary key (idempotent; re-running the job never duplicates rows) and
optionally pruned of keys no longer in gold. The app-owned `actions` table is never touched here.
pg8000 is used because psycopg's binary wheel aborts on Databricks serverless job compute.
"""
from __future__ import annotations

import os

PROJECT_ENDPOINT = os.getenv("LAKEBASE_ENDPOINT", "projects/helivara/branches/production/endpoints/primary")
PG_HOST = os.getenv("PGHOST", "ep-long-credit-d7nhfvsv.database.eu-central-1.cloud.databricks.com")
PG_DATABASE = os.getenv("PGDATABASE", "helivara")
PG_SCHEMA = "control_tower"

BOARD = {
    "table": f"{PG_SCHEMA}.launch_risk_board", "pk": "launch_id",
    "columns": ["launch_id", "sku", "brand", "therapeutic_area", "phase", "readiness", "master_data_ready",
                "artwork_ready", "serialization_ready", "blocking_gates", "revenue_at_risk_eur", "brief_en",
                "brief_it", "primary_line", "plant", "linked_equipment", "linked_failure_prob", "refreshed_at"],
    "source_sql": """
SELECT l.launch_id, l.sku, p.brand, p.therapeutic_area, l.phase, l.launch_readiness_score AS readiness,
       l.master_data_ready_flag AS master_data_ready, l.artwork_ready_flag AS artwork_ready,
       l.serialization_ready_flag AS serialization_ready,
       concat_ws(', ', CASE WHEN l.master_data_ready_flag < 0.5 THEN 'master data' END,
                       CASE WHEN l.artwork_ready_flag < 0.5 THEN 'artwork' END,
                       CASE WHEN l.serialization_ready_flag < 0.5 THEN 'serialization' END) AS blocking_gates,
       v.revenue_at_risk_eur, b.brief_en, b.brief_it, r.primary_line, r.plant,
       max_by(d.equipment, d.failure_prob_30d) AS linked_equipment, max(d.failure_prob_30d) AS linked_failure_prob,
       current_timestamp() AS refreshed_at
FROM {fq}.dim_launch l JOIN {fq}.dim_product p USING (sku)
LEFT JOIN {fq}.launch_value v USING (launch_id)
LEFT JOIN {fq}.launch_action_brief b USING (launch_id)
LEFT JOIN {fq}.dim_routing r ON r.sku = l.sku
LEFT JOIN {fq}.dim_equipment e ON e.line = r.primary_line
LEFT JOIN {fq}.equipment_risk_drivers d ON d.equipment = e.equipment
GROUP BY ALL""",
}

EQUIPMENT = {
    "table": f"{PG_SCHEMA}.equipment_risk", "pk": "equipment",
    "columns": ["equipment", "plant", "line", "equipment_class", "criticality", "failure_prob_30d", "rul_days",
                "top_driver", "impacted_brands", "refreshed_at"],
    "source_sql": """
SELECT d.equipment, e.plant, e.line, e.equipment_class, e.criticality, d.failure_prob_30d, d.rul_days, d.top_driver,
       concat_ws(', ', sort_array(collect_set(p.brand))) AS impacted_brands, current_timestamp() AS refreshed_at
FROM {fq}.equipment_risk_drivers d JOIN {fq}.dim_equipment e USING (equipment)
LEFT JOIN {fq}.dim_routing r ON r.primary_line = e.line
LEFT JOIN {fq}.dim_product p ON p.sku = r.sku
GROUP BY ALL""",
}

SERVING = [BOARD, EQUIPMENT]


def upsert_sql(table: str, columns: list[str], pk: str) -> str:
    cols = ", ".join(columns)
    marks = ", ".join(["%s"] * len(columns))
    sets = ", ".join(f"{c} = EXCLUDED.{c}" for c in columns if c != pk)
    return f"INSERT INTO {table} ({cols}) VALUES ({marks}) ON CONFLICT ({pk}) DO UPDATE SET {sets}"


def sync_rows(conn, table: str, columns: list[str], pk: str, rows: list[tuple], prune: bool = False) -> int:
    """Upsert `rows` into `table` in one transaction; with prune=True delete keys absent from `rows`."""
    cur = conn.cursor()
    cur.executemany(upsert_sql(table, columns, pk), rows)
    if prune:
        i = columns.index(pk)
        cur.execute(f"DELETE FROM {table} WHERE {pk} <> ALL(%s)", ([r[i] for r in rows],))
    conn.commit()
    return len(rows)


def pg_connect(user: str | None = None, workspace_client=None):
    """pg8000 connection authenticated with a fresh Lakebase OAuth credential."""
    import pg8000.dbapi
    from databricks.sdk import WorkspaceClient

    w = workspace_client or WorkspaceClient()
    token = w.postgres.generate_database_credential(endpoint=PROJECT_ENDPOINT).token
    return pg8000.dbapi.connect(host=PG_HOST, port=5432, database=PG_DATABASE,
                                user=user or w.current_user.me().user_name, password=token, ssl_context=True)
