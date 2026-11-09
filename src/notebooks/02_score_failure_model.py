# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Score equipment with `equipment_failure_model@champion`
# MAGIC Scores every machine as of the demo date (2026-09-22) and writes:
# MAGIC * `fact_predicted_failure`: alerts (risk ≥ 0.30) in the governed table the Manufacturing Genie agent already uses
# MAGIC   (overwritten in place, so certification and Genie links stay);
# MAGIC * `equipment_risk_drivers`: every machine's probability plus the sensor that drives it most (for the app).

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.abspath(".."))
import mlflow
import numpy as np
import pandas as pd
from helivara.features import FEATURES, SIGNALS, make_features

CATALOG, SCHEMA = "fr_stable_catalog", "supply_chain"
FQ = f"{CATALOG}.{SCHEMA}"
MODEL = f"{FQ}.equipment_failure_model"
ALERT = 0.30
mlflow.set_registry_uri("databricks-uc")
model = mlflow.sklearn.load_model(f"models:/{MODEL}@champion")
as_of = pd.Timestamp(spark.table(f"{FQ}.demo_config").first()["demo_date"])

tel = spark.table(f"{FQ}.fact_equipment_telemetry").toPandas()
maint = spark.table(f"{FQ}.fact_maintenance").toPandas()
equip = spark.table(f"{FQ}.dim_equipment").toPandas()
feats = make_features(tel, maint)
now = feats[feats.date == as_of].copy()
now["p"] = model.predict_proba(now[FEATURES])[:, 1]

# top driver = signal feature furthest above its fleet-wide historical norm (z-score)
hist = feats[feats.date < as_of]
drivers = [f"{s}_ratio_7_60" for s in SIGNALS.values()] + [f"{s}_slope_14" for s in SIGNALS.values()]
z = (now[drivers] - hist[drivers].mean()) / hist[drivers].std()
now["top_driver"] = z.idxmax(axis=1)
now["top_driver_value"] = [round(float(now.loc[i, c]), 3) for i, c in zip(now.index, now["top_driver"])]
now["rul_days"] = np.clip(np.round(30 * (1 - now["p"])), 1, 30).astype(int)

modes = (maint[maint.maintenance_type == "unplanned"].merge(equip[["equipment", "equipment_class"]], on="equipment")
         .groupby("equipment_class").failure_mode.agg(lambda s: s.value_counts().index[0]))
now = now.merge(equip[["equipment", "equipment_class"]], on="equipment")
now["failure_mode"] = now.equipment_class.map(modes).fillna("bearing_failure")
print(now.sort_values("p", ascending=False)[["equipment", "equipment_class", "p", "rul_days", "top_driver"]].to_string(index=False))

# COMMAND ----------

alerts = now[now.p >= ALERT].assign(
    predicted_failure_id=lambda d: "PF_" + d.equipment,
    predicted_failure_date=lambda d: as_of + pd.to_timedelta(d.rul_days, unit="D"))
spark.createDataFrame(alerts[["predicted_failure_id", "equipment", "predicted_failure_date", "rul_days", "p", "failure_mode"]]
                      .rename(columns={"p": "risk_score"})).createOrReplaceTempView("scored")
spark.sql(f"""INSERT OVERWRITE {FQ}.fact_predicted_failure
  SELECT predicted_failure_id, equipment, CAST(predicted_failure_date AS TIMESTAMP_NTZ), CAST(rul_days AS BIGINT),
         CAST(risk_score AS DOUBLE), failure_mode FROM scored""")

spark.createDataFrame(now[["equipment", "p", "rul_days", "top_driver", "top_driver_value"]]
                      .rename(columns={"p": "failure_prob_30d"}).assign(scored_as_of=as_of.date().isoformat())) \
    .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{FQ}.equipment_risk_drivers")
spark.sql(f"COMMENT ON TABLE {FQ}.equipment_risk_drivers IS 'Daily model scores for every machine: calibrated "
          f"probability of unplanned failure within 30 days (failure_prob_30d), estimated days to failure (rul_days) and "
          f"the sensor feature that most drives the risk (top_driver). Written by notebook 02 from {MODEL}@champion.'")
print("alerts written:", len(alerts), "| machines scored:", len(now))
