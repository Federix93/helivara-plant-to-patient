"""Helivara plant-to-patient Lakeflow Declarative Pipeline (synthetic data, fictional company).

raw Volume (simulated SAP / MES / IoT / CMMS extracts)
  -> bronze_<entity>   streaming tables, Auto Loader, everything as STRING + lineage columns
  -> silver_<entity>   typed to the gold contract, deduplicated, expectations drop bad rows
  -> <entity>_quarantine  the rows the expectations rejected, with the failed rule names
  -> <entity>          gold: the EXISTING governed tables (same names the metric views, Genie agents
                       and dashboard use) are refreshed from silver by the job's publish task
                       (src/sql/publish_gold.sql), so their certification, domains and comments stay.
"""
import dlt
from pyspark.sql import Window
from pyspark.sql import functions as F

from spec import CONTRACT, DEDUP_KEYS, RULES, SOURCES

NTZ = {"delta.feature.timestampNtz": "supported"}
RAW = spark.conf.get("raw_root", "/Volumes/fr_stable_catalog/supply_chain/raw")  # noqa: F821


def _typed(entity: str):
    df = dlt.read(f"bronze_{entity}")
    cols = [F.expr(f"try_cast(`{c}` AS {t})").alias(c) for c, t in CONTRACT[entity]]
    out = df.select(*cols, "_source_file", "_ingested_at")
    key = DEDUP_KEYS.get(entity)
    w = Window.partitionBy(key).orderBy("_ingested_at") if key else None
    return out.withColumn("_dup_rank", F.row_number().over(w) if key else F.lit(1))


def _make(entity: str):
    src = SOURCES[entity]
    rules = RULES.get(entity, {})

    @dlt.table(name=f"bronze_{entity}",
               comment=f"Bronze: raw {src['system'].upper()} extract for {entity}, ingested by Auto Loader.")
    def bronze():
        reader = (spark.readStream.format("cloudFiles")  # noqa: F821
                  .option("cloudFiles.format", src["format"])
                  .option("cloudFiles.inferColumnTypes", "false"))
        if src["format"] == "csv":
            reader = reader.option("header", "true")
        return (reader.load(f"{RAW}/{src['system']}/{entity}/")
                .withColumn("_source_file", F.col("_metadata.file_path"))
                .withColumn("_ingested_at", F.current_timestamp()))

    @dlt.table(name=f"silver_{entity}", comment=f"Silver: typed, deduplicated and validated {entity}.",
               table_properties=NTZ)
    @dlt.expect_all_or_drop(rules)
    def silver():
        return _typed(entity)

    if rules:
        failed = F.concat_ws(",", *[F.when(~F.expr(f"coalesce({p}, false)"), F.lit(n)) for n, p in rules.items()])

        @dlt.table(name=f"{entity}_quarantine",
                   comment=f"Quarantine: {entity} rows rejected by data-quality rules ({', '.join(rules)}).",
                   table_properties=NTZ)
        def quarantine():
            bad = " OR ".join(f"NOT coalesce({p}, false)" for p in rules.values())
            return _typed(entity).where(bad).withColumn("_failed_rules", failed)


for _entity in CONTRACT:
    _make(_entity)
