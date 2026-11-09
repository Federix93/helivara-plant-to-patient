# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Train the equipment-failure model (predictive maintenance)
# MAGIC **Question:** will this machine have an *unplanned* failure in the next 30 days?
# MAGIC Features come from IoT telemetry (rolling means, 14-day slopes, 7-vs-60-day ratios) and maintenance history,
# MAGIC built by `helivara.features` (the same code the local unit tests exercise). Model: gradient boosting with
# MAGIC sigmoid (Platt) calibration, so the score reads as a probability without saturating at 0 or 1. Registered in Unity Catalog; alias `champion`
# MAGIC is set only if the out-of-time test AUC is at least 0.75. *Synthetic data, fictional company.*

# COMMAND ----------

import json, os, sys
sys.path.insert(0, os.path.abspath(".."))  # bundle files: src/ holds the helivara package

import mlflow
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import brier_score_loss, confusion_matrix, roc_auc_score
from sklearn.inspection import permutation_importance

from helivara.features import FEATURES, make_features, make_labels, time_split

CATALOG, SCHEMA = "fr_stable_catalog", "supply_chain"
MODEL = f"{CATALOG}.{SCHEMA}.equipment_failure_model"
ARTIFACTS = f"/Volumes/{CATALOG}/{SCHEMA}/raw/_artifacts"
TEST_START, TEST_END = "2026-06-01", "2026-08-22"  # labels need 30 days of future
HORIZON = 30

mlflow.set_registry_uri("databricks-uc")
user = spark.sql("SELECT current_user()").first()[0]
mlflow.set_experiment(f"/Users/{user}/helivara_equipment_failure")

# COMMAND ----------

tel = spark.table(f"{CATALOG}.{SCHEMA}.fact_equipment_telemetry").toPandas()
maint = spark.table(f"{CATALOG}.{SCHEMA}.fact_maintenance").toPandas()
feats = make_features(tel, maint)
y = make_labels(feats, maint, horizon_days=30)
tr, te = time_split(feats.date, TEST_START, TEST_END, HORIZON)  # 30-day embargo: no label leakage
TRAIN_END = str((pd.Timestamp(TEST_START) - pd.Timedelta(days=HORIZON)).date())
print(f"rows={len(feats)} train={tr.sum()} test={te.sum()} positive_rate={y.mean():.3f}")

# COMMAND ----------

with mlflow.start_run(run_name="hgb_isotonic") as run:
    params = dict(max_iter=200, learning_rate=0.05, max_depth=4, random_state=42)
    model = CalibratedClassifierCV(HistGradientBoostingClassifier(**params), method="sigmoid", cv=3)
    model.fit(feats.loc[tr, FEATURES], y[tr])
    p = model.predict_proba(feats.loc[te, FEATURES])[:, 1]
    yt = y[te].values
    k = 5
    order = np.argsort(-p)
    metrics = {
        "test_auc": float(roc_auc_score(yt, p)),
        "test_brier": float(brier_score_loss(yt, p)),
        "test_positive_rate": float(yt.mean()),
        f"test_precision_at_{k}pct": float(yt[order[: max(1, len(order) * k // 100)]].mean()),
    }
    tn, fp, fn, tp = confusion_matrix(yt, (p >= 0.5).astype(int)).ravel()
    metrics.update(tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp))
    imp = permutation_importance(model, feats.loc[te, FEATURES], yt, scoring="roc_auc", n_repeats=5, random_state=0)
    importance = dict(sorted(zip(FEATURES, imp.importances_mean.round(4).tolist()), key=lambda kv: -kv[1]))
    mlflow.log_params({**params, "calibration": "sigmoid", "horizon_days": HORIZON, "train_end_exclusive_embargoed": TRAIN_END,
                       "test_window": f"{TEST_START}..{TEST_END}", "features": ",".join(FEATURES)})
    mlflow.log_metrics({k_: v for k_, v in metrics.items()})
    mlflow.log_dict(importance, "permutation_importance.json")
    X_ex = feats.loc[te, FEATURES].head(5)
    info = mlflow.sklearn.log_model(model, name="model", registered_model_name=MODEL,
                                    signature=infer_signature(X_ex, model.predict_proba(X_ex)[:, 1]),
                                    input_example=X_ex)
    version = info.registered_model_version
print(json.dumps(metrics, indent=1)); print(json.dumps(importance, indent=1)); print("registered", MODEL, "v", version)

# COMMAND ----------

from mlflow import MlflowClient
client = MlflowClient()
promoted = metrics["test_auc"] >= 0.75
if promoted:
    client.set_registered_model_alias(MODEL, "champion", version)
client.update_registered_model(MODEL, description=(
    "Calibrated probability of an unplanned equipment failure within 30 days, from IoT telemetry and "
    "maintenance history (Helivara, synthetic data). Owner: reliability engineering. Retrain monthly."))
summary = {"model": MODEL, "version": int(version), "run_id": run.info.run_id, "champion": promoted,
           "metrics": metrics, "permutation_importance": importance,
           "split": {"train_label_window_ends_before": TEST_START, "train_dates_before": TRAIN_END, "embargo_days": HORIZON, "test": [TEST_START, TEST_END]}, "features": FEATURES}
os.makedirs(ARTIFACTS, exist_ok=True)
with open(f"{ARTIFACTS}/metrics.json", "w") as fh:
    json.dump(summary, fh, indent=1)
print(json.dumps(summary, indent=1))
