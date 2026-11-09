"""Job task: copy app-written actions (Lakebase control_tower.actions) to Delta ops_launch_actions,
so Genie and the dashboard can see the decisions taken in the app (closes the loop)."""
import argparse
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True)
ap.add_argument("--fq", default="fr_stable_catalog.supply_chain")
args = ap.parse_args()
sys.path.insert(0, args.src)

from pyspark.sql import SparkSession  # noqa: E402

from helivara.lakebase_sync import pg_connect  # noqa: E402

SCHEMA = ("action_id BIGINT, launch_id STRING, action_type STRING, equipment STRING, owner STRING, due_date DATE, "
          "note STRING, status STRING, created_by STRING, created_at TIMESTAMP")
spark = SparkSession.builder.getOrCreate()
conn = pg_connect()
cur = conn.cursor()
cur.execute("SELECT action_id, launch_id, action_type, equipment, owner, due_date, note, status, created_by, created_at "
            "FROM control_tower.actions ORDER BY action_id")
rows = [tuple(r) for r in cur.fetchall()]
conn.close()
spark.createDataFrame(rows, SCHEMA).write.mode("overwrite").option("overwriteSchema", "true") \
    .saveAsTable(f"{args.fq}.ops_launch_actions")
spark.sql(f"COMMENT ON TABLE {args.fq}.ops_launch_actions IS 'Actions taken by planners in the Control Tower app "
          f"(escalations, maintenance bookings), copied daily from Lakebase control_tower.actions. One open action per "
          f"launch and action type.'")
print(f"ops_launch_actions: {len(rows)} rows")
