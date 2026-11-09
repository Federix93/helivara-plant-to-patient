"""Job task: upsert gold serving views into Lakebase (control_tower.*). Idempotent (upsert by PK + prune)."""
import argparse
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True)
ap.add_argument("--fq", default="fr_stable_catalog.supply_chain")
args = ap.parse_args()
sys.path.insert(0, args.src)

from pyspark.sql import SparkSession  # noqa: E402

from helivara.lakebase_sync import SERVING, pg_connect, sync_rows  # noqa: E402

spark = SparkSession.builder.getOrCreate()
conn = pg_connect()
for spec in SERVING:
    df = spark.sql(spec["source_sql"].format(fq=args.fq)).select(*spec["columns"])
    rows = [tuple(r) for r in df.collect()]
    n = sync_rows(conn, spec["table"], spec["columns"], spec["pk"], rows, prune=True)
    cur = conn.cursor()
    cur.execute(f"SELECT count(*) FROM {spec['table']}")
    print(f"{spec['table']}: upserted {n}, now {cur.fetchone()[0]} rows")
conn.close()
