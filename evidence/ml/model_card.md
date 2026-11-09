# Model card — `fr_stable_catalog.supply_chain.equipment_failure_model` (v1, alias `@champion`)

**Purpose.** Calibrated probability that a production machine has an **unplanned failure within 30 days**,
so reliability engineers can book preventive maintenance before a breakdown hits supply (for example the
Valmora coater that coats the Zyvanta launch). *Synthetic data; Helivara is fictional.*

| Item | Value |
|---|---|
| Algorithm | `HistGradientBoostingClassifier` (200 iters, depth 4, lr 0.05) + `CalibratedClassifierCV(isotonic, cv=3)` |
| Features (12) | 7-day means, 14-day slopes, 7-vs-60-day ratios of vibration / temperature / motor current; 7-day max anomaly score; days since last maintenance (`src/helivara/features.py`, unit-tested for no look-ahead) |
| Label | 1 if an `unplanned` work order starts in (day, day+30] (`make_labels`) |
| Data | `fact_equipment_telemetry` (7,740 machine-days, 20 machines) + `fact_maintenance`, both from the Lakeflow pipeline |
| Split | time-based: train < 2026-06-01; test 2026-06-01 … 2026-08-22 (labels need 30 future days) |
| **Test AUC** | **0.816** |
| Brier score | 0.135 (base rate 0.336) |
| Precision in top 5% | 1.00 |
| Confusion @0.5 | TN 1098 · FP 4 · FN 286 · TP 272 |
| Top drivers (permutation importance, AUC drop) | vib_ratio_7_60 0.043 · days_since_maint 0.028 · temp_mean_7 0.023 · vib_slope_14 0.018 |
| Promotion rule | alias `champion` only if test AUC ≥ 0.75 (met) |
| Scoring | notebook 02 → `fact_predicted_failure` (alerts, p ≥ 0.30) + `equipment_risk_drivers` (all machines) |
| Hero result (as of 2026-09-22) | `L_OSD_001_EQ_01` (Valmora coater, Zyvanta's line): **p = 0.94**, rank 1 of 20 |

**Limits.** It ranks well but is conservative at 0.5: recall there is about 49%, so the app uses 0.30 to raise alerts
and ≥ 0.60 for "act now". It's trained on synthetic wear patterns: on real plant data, expect to re-engineer the features
(sensor sampling rates, per-asset baselines) and to monitor drift. Retrain monthly; compare challenger vs. champion on AUC and Brier.

Evidence: `metrics.json` (MLflow run summary), `train_run_output.txt` / `score_run_output.txt` (notebook outputs as
text), `*_run.html` (full notebook exports with outputs).
