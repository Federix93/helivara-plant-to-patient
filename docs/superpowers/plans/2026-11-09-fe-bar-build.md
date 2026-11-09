# FE Bar Build — Helivara "Plant to Patient" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing Helivara Genie/UC demo into an integrated FE Bar build (Lakeflow → UC →
ML/GenAI → Lakebase → Genie → App) with fictional names, text evidence, a public repo, a
restructured deck and a speech.

**Architecture:** A refactored generator writes raw "SAP/MES/IoT/CMMS" files to a UC Volume. A
serverless Lakeflow Declarative Pipeline builds bronze → silver (expectations + quarantine) → gold
with the SAME 20 gold table names/schemas used today, so the metric views, Genie agents and dashboard
keep working. Notebooks train/score a failure model and write an `ai_query` brief plus a value model.
A job syncs the serving tables to Lakebase, and a FastAPI + React app reads them, asks Genie and
writes actions back. Everything is packaged as a Databricks Asset Bundle.

**Tech Stack:** Python 3.12 (uv venv), pandas/numpy, pytest, Databricks CLI + Asset Bundles, Lakeflow
Declarative Pipelines (Python `dlt`/`pyspark.pipelines`), MLflow + UC model registry, scikit-learn,
`ai_query`, Lakebase Autoscaling (Postgres 17, pg8000), FastAPI, React + Vite, Google Slides API.

**Spec:** `docs/superpowers/specs/2026-11-09-fe-bar-design.md`

## Global Constraints

- Workspace profile `fr-stable`; warehouse `797d1d487d654063`; catalog.schema `fr_stable_catalog.supply_chain`.
- Demo "today" = `2026-09-22`; seed `42`; telemetry history ends 2026-09-22; failure horizon = 30 days.
- Hero facts (must hold in gold and in `mv_launch_readiness`): Zyvanta (SKU_001, launch_id `ZYV-001`)
  readiness **0.33**, master data **0.0**, artwork **0.0**, serialization **1.0**; Oribex (SKU_002,
  `ORB-001`) readiness 0.9, phase-out, **no US rows from 2025-11 onward**.
- Fictional names: single source `src/helivara/names.py`; the real→fictional mapping is kept outside the repo; only fictional names are published.
  Gastrelle→Gastrelle, Colvera→Colvera, Florabis→Florabis, Lactavio→Lactavio, Refluxa→Refluxa,
  Venoria→Venoria, Faringel→Faringel, Digestin→Digestin, Citralux→Citralux,
  Valmora→Valmora, Castelverde→Castelverde, Roccalba→Roccalba, Riberal→Riberal, Ashbury Ridge→Ashbury Ridge,
  supplier Castelverde Chem→Castelverde Chem. Launch ids ZYV-001→ZYV-001, ORB-001→ORB-001.
- FORBIDDEN in workspace text/data, repo, app and deck: every real-world company, brand, plant and person name (checked by fingerprint in `src/helivara/names.py`). People appear only as role titles.
  `[redacted]`, `[redacted]`, `[redacted]`. People appear only as role titles ("Global Demand & S&OP Manager").
- Genie spaces: Demand and Supply `01f1bc08a109177a8d192afb82da3e2b`, Manufacturing and Reliability
  `01f1bc08a1471942bf4433f530ef8537`. `PATCH /api/2.0/genie/spaces/{id}` is a FULL REPLACE: always send
  `{warehouse_id,title,description,parent_path,serialized_space}`; tables sorted by identifier.
- Dashboard `01f1bc0ce3801f2499977bbb1277a65c` (PATCH display_name + serialized_dashboard + warehouse_id).
- Metric views are queried with `MEASURE()`. Shared metastore: no `CREATE CATALOG`. Serverless only.
- Lakebase from job compute: **pg8000** only (psycopg[binary] crashes there).
- Every commit message ends with `Co-authored-by: Isaac <no-reply@databricks.com>`.
- Displayed numbers (€ at risk, failure %) come from tables, never hard-coded in the UI or deck.
- Palette: teal `#1B5161`, dark `#1B3037`, red `#FF3620`, light gray `#F1F1F1`.

## Review Focus

1. Genie returns a text-only answer (the PDF/conceptual question), `FAILED`, or no reply within 60 s →
   the app shows the text or a friendly error, never a 500 (Task 9: `test_genie_text_only_and_failure`).
2. Lakebase OAuth credential expires (~1 h) while the app keeps running → new connections get a fresh
   credential (Task 9: `test_connection_refreshes_expired_credential`).
3. Double-clicking Escalate → no duplicate open action for the same `(launch_id, action_type)`
   (Task 9: `test_post_action_is_idempotent_for_open_action`).
4. Italian text (`è`, `à`) in briefs, Genie answers and action notes survives gold → Lakebase → app
   (Task 8: `test_sync_rows_roundtrip_utf8`).
5. Re-running the daily job leaves no duplicate serving rows and keeps app-written actions
   (Task 8: `test_upsert_sql_is_idempotent`, Task 8 live re-run check).

---

## File Structure

```
(repo root = demos/helivara_supply_chain, git repo → github.com/Federix93/helivara-plant-to-patient)
README.md                       outcome-first front door (Task 11)
databricks.yml                  DAB: volume, pipeline, jobs, app (Task 4, extended in 6–10)
pyproject.toml / .gitignore     uv project; ignores .venv, legacy/, *.parquet, raw_out/
src/helivara/names.py           mapping + FORBIDDEN list + scan helper (Task 1)
src/helivara/generate.py        build_tables() / write_raw() (Task 2)
src/helivara/features.py        telemetry → model features + labels (Task 6)
src/helivara/value.py           € value formulas (Task 7)
src/helivara/lakebase_sync.py   upsert SQL builders + pg8000 sync (Task 8)
src/helivara/uc_text.py         COMMENTS dict (from comments.py, renamed) shared by pipeline + setup
src/pipeline/{bronze,silver,gold}.py     Lakeflow pipeline (Task 4)
src/notebooks/01_train_failure_model.ipynb, 02_score_failure_model.ipynb (Task 6)
src/notebooks/03_value_and_brief.ipynb  (Task 7)
src/jobs/{sync_to_lakebase.py, copy_actions_back.py} (Task 8)
setup/{upload_raw.py, drop_legacy_tables.py, metric_views.py, certify.py, deploy_domains.py,
       deploy_genie.py, patch_dashboard.py, make_pdf.py}   (Tasks 3–5; moved from terraform/scripts)
checks/{verify_live.py, scan_live_names.py}   SQL/API checks against the workspace
app/  backend/ (FastAPI), frontend/ (React+Vite), app.yaml   (Tasks 9–10)
tests/  pytest unit tests
evidence/  committed text outputs (contracts/, pipeline/, ml/, value/, lakebase/, genie/, app/)
docs/  ARCHITECTURE.md, DECISIONS.md, AI_USAGE.md, DEMO_SCRIPT_FE_BAR.md, deck/ (Tasks 11–12)
legacy/  old briefs/runbooks (gitignored; contain real names)
```

---

### Task 1: Repo scaffold, names module, scanner

**Files:** Create `pyproject.toml`, `.gitignore`, `src/helivara/__init__.py`, `src/helivara/names.py`,
`tests/test_names.py`. Move `AGENT_BRIEF.md DEMO_SCRIPT.md GENIE_SETUP.md GLOSSARY.md PHASE_3_SUMMARY.md
README.md RUNBOOK_discover.md REGEN_SPEC.md SA_PRESENTATION_SCRIPT.md *.py(root copies) terraform/`
into `legacy/`. Move `terraform/scripts/*.py` into `setup/` (canonical, env-parameterized copies).

**Interfaces — Produces:**
- `BRAND_MAP: dict[str,str]`, `PLANT_MAP: dict[str,str]`, `SUPPLIER_MAP`, `LAUNCH_ID_MAP` (values per Global Constraints)
- `FORBIDDEN: tuple[str,...]` (all real keys + [redacted]/[redacted]/[redacted]/[redacted]/[redacted])
- `find_forbidden(text: str) -> list[str]` (case-insensitive, whole-word; returns hits)
- `rename(text: str) -> str` applies all maps (longest key first)

- [ ] **Step 1:** `git init`, `uv init --python 3.12`, add deps: pandas numpy pyarrow pytest scikit-learn mlflow fastapi httpx pg8000 databricks-sdk.
- [ ] **Step 2: Failing tests** in `tests/test_names.py`:
  `test_find_forbidden_flags_real_names` (`find_forbidden("Zyvanta at Valmora, ask [redacted]") == ["Zyvanta","Valmora","[redacted]"]`),
  `test_find_forbidden_clean` (`find_forbidden("Zyvanta at Valmora") == []`),
  `test_rename_roundtrip` (`rename("Faringel and Gastrelle, ZYV-001") == "Faringel and Gastrelle, ZYV-001"`),
  `test_maps_have_no_forbidden_values` (no map value hits `find_forbidden`).
- [ ] **Step 3:** Run `uv run pytest tests/test_names.py -v` → FAIL (import error).
- [ ] **Step 4:** Implement `names.py`.
- [ ] **Step 5:** Run → PASS. Add `uv run python -m helivara.names <path>...` CLI that prints hits and exits 1 on any (used later for repo scans).
- [ ] **Step 6:** Commit `chore: scaffold repo, fictional name map and scanner`.

### Task 2: Generator — fictional names, raw multi-format files, learnable telemetry, dirty rows

**Files:** Create `src/helivara/generate.py` (from `setup/generate_data.py`), `tests/test_generate.py`.

**Interfaces — Produces:**
- `build_tables(seed: int = 42) -> dict[str, pd.DataFrame]` — the 20 gold-shaped tables (all of today's
  except `fact_predicted_failure` and `fact_oee_legacy`), fictional names.
- `write_raw(tables, out_dir: Path, dirty_rate: float = 0.015) -> dict[str, Path]` — writes raw files:
  `sap/{dim_*,fact_demand_forecast,fact_inventory,fact_service}.csv`, `mes/{fact_batch,fact_batch_genealogy,
  fact_oee,fact_qc_release,fact_deviation}.json` (JSON lines), `iot/fact_equipment_telemetry.json`,
  `cmms/fact_maintenance.csv`, `config/demo_config.json`. Injects dirty rows (null key, negative qty,
  duplicate id, sensor out of range) at `dirty_rate` per fact file and returns their counts in `out_dir/_dirty_manifest.json`.

**Rules the implementer cannot infer:**
- Keep the existing global-RNG draw order: the legacy telemetry and predicted-failure loops still run
  (results discarded) so every other table equals the old output after renaming.
- After generation (no RNG): set `dim_line` L_OSD_001 `process_step='coating'`; set `L_OSD_001_EQ_01`
  `equipment_class='coater'`, `criticality='high'` (Valmora coater that serves Zyvanta).
- Extra failures: own RNG `np.random.default_rng(4242)` appends ~120 `unplanned` rows to
  `fact_maintenance` (dates 2025-09-15..2026-09-01, ids continue the `WO_` sequence).
- New telemetry (own RNG `default_rng(777)`), daily 2025-09-01..2026-09-22 per equipment: baseline as
  today; in the 14 days before each unplanned failure, vibration +40–80 %, temperature +5–10 °C,
  motor_current +15–30 % (linear ramp); `L_OSD_001_EQ_01` ramps over its last 14 days with no failure
  recorded (degrading now). `anomaly_score` keeps today's formula.

- [ ] **Step 1: Failing tests** in `tests/test_generate.py` (module-scoped fixture `t = build_tables()`):
  - `test_hero_launch_facts`: ZYV-001 readiness 1/3 (±1e-9), master 0.0, artwork 0.0, serialization 1.0; ORB-001 readiness 0.9.
  - `test_oribex_no_us_after_2025_11`: no `fact_demand_forecast`/`fact_service` rows with brand Oribex (via sku SKU_002), market US, month ≥ "2025-11".
  - `test_no_forbidden_names`: `find_forbidden` over all string cells of all tables == [].
  - `test_unchanged_tables_match_legacy`: run `legacy/generate_data.py`'s logic (import with OUT_DIR patched to tmp) → for `fact_demand_forecast, fact_service, fact_inventory, fact_oee, fact_batch, fact_deviation, dim_launch`: `rename()`-mapped legacy frame equals new frame (`pd.testing.assert_frame_equal`, check_like=True).
  - `test_telemetry_has_failure_signal`: mean vibration in the 7 days before unplanned failures ≥ 1.3 × mean on days with no failure in the next 30.
  - `test_valmora_coater_degrading`: `L_OSD_001_EQ_01` mean vibration over the last 7 days ≥ 1.3 × its first-90-day mean; `dim_equipment` class == "coater".
  - `test_write_raw_dirty_rate` (tmp_path): manifest total dirty rows / total fact rows in [0.01, 0.02]; files exist in sap/mes/iot/cmms/config.
- [ ] **Step 2:** Run `uv run pytest tests/test_generate.py -v` → FAIL.
- [ ] **Step 3:** Implement `build_tables` / `write_raw`.
- [ ] **Step 4:** Run → PASS. Run full suite.
- [ ] **Step 5:** Commit `feat: fictional-name generator with raw source files and failure signal`.

### Task 3: Snapshot contracts and stage raw files in the Volume

**Files:** Create `setup/upload_raw.py`, `evidence/contracts/gold_schemas.json`, `evidence/contracts/hero_before.json`.

- [ ] **Step 1:** Export today's live gold column names+types (information_schema, 20 tables, excluding `fact_predicted_failure`, `fact_oee_legacy`) to `evidence/contracts/gold_schemas.json` as `{table: [[col, type], ...]}` in ordinal order. Export hero values (`SELECT brand, MEASURE(avg_launch_readiness), MEASURE(master_data_ready_rate), MEASURE(artwork_ready_rate), MEASURE(serialization_ready_rate) FROM mv_launch_readiness GROUP BY brand`) to `hero_before.json`.
- [ ] **Step 2:** `setup/upload_raw.py`: create Volume `fr_stable_catalog.supply_chain.raw` if missing; `build_tables` → `write_raw` to `raw_out/` → `databricks fs cp -r raw_out/ dbfs:/Volumes/fr_stable_catalog/supply_chain/raw/ --overwrite`.
- [ ] **Step 3:** Run it; verify `databricks fs ls dbfs:/Volumes/fr_stable_catalog/supply_chain/raw/sap` lists the CSVs. Save the listing to `evidence/pipeline/raw_landing.txt`.
- [ ] **Step 4:** Commit `feat: contracts snapshot and raw landing upload`.

### Task 4: Lakeflow Declarative Pipeline (bronze → silver → gold) + bundle

**Files:** Create `databricks.yml`, `resources/pipeline.yml`, `src/pipeline/bronze.py`, `silver.py`, `gold.py`,
`src/helivara/uc_text.py` (COMMENTS dict from `setup/comments.py`, passed through `rename`, "[redacted]'s world" removed),
`setup/drop_legacy_tables.py`, `checks/verify_live.py`.

**Interfaces — Produces:** pipeline `helivara_plant_to_patient` (serverless, catalog `fr_stable_catalog`,
schema `supply_chain`); tables `bronze_<entity>` (Auto Loader, `_ingested_at`, `_source_file`),
`silver_<entity>`, `<entity>_quarantine`, and gold MVs named exactly as the contract. `checks/verify_live.py
--contract --hero` exits 0 only if gold schemas equal `gold_schemas.json` and hero facts hold.

- [ ] **Step 1:** Write `checks/verify_live.py` (SQL via statements API) with checks: `contract` (column names + types per table identical to the contract), `hero` (Global Constraints values via `mv_launch_readiness` and `fact_demand_forecast`), `quarantine` (each `*_quarantine` count > 0 and equals the `_dirty_manifest.json` count for that entity ±0).
- [ ] **Step 2:** Run `verify_live.py --contract` against today's live tables → PASS (sanity of the checker itself), `--quarantine` → FAIL (tables absent).
- [ ] **Step 3:** Implement bronze (cloudFiles csv/json, schema hints from contract types), silver (cast to contract types incl. `TIMESTAMP_NTZ`, dedupe on business key, `@expect_all_or_drop` rules: non-null keys, qty ≥ 0, sensor values in physical range), quarantine tables (same rules inverted), gold (select contract columns, table + column comments from `uc_text.COMMENTS`).
- [ ] **Step 4:** `setup/drop_legacy_tables.py` drops the 20 legacy managed tables (NOT `fact_oee_legacy`, NOT `fact_predicted_failure`, NOT metric views). Run it, then `databricks bundle deploy -t dev` and `databricks bundle run helivara_plant_to_patient`.
- [ ] **Step 5:** Run `verify_live.py --contract --hero --quarantine` → PASS. Save pipeline event-log summary (flow names, row counts, expectation pass/fail per rule from `event_log()`) to `evidence/pipeline/run_<date>.md` and the verify output to `evidence/pipeline/verify.txt`.
- [ ] **Step 6:** Commit `feat: Lakeflow pipeline replacing CTAS load`.

### Task 5: Re-apply the UC layer and rename every downstream asset

**Files:** Modify `setup/metric_views.py`, `setup/certify.py`, `setup/deploy_domains.py` (assignment only),
`setup/deploy_genie.py` (PATCH mode, renamed text, extra tables), create `setup/patch_dashboard.py`,
`setup/make_pdf.py` (from the knowledge-PDF generator, renamed), `checks/scan_live_names.py`.

- [ ] **Step 1:** Write `checks/scan_live_names.py`: scans with `find_forbidden` all string columns of every table in the schema (distinct values), all table/column comments, both Genie spaces (`?include_serialized_space=true`), the dashboard JSON, our 13 domains, and the PDF text in Volume `knowledge`. Prints hits per asset; exits 1 on any. Run it → FAIL (Genie/dashboard/PDF still have real names).
- [ ] **Step 2:** Re-run `metric_views.py` (CREATE OR REPLACE over the pipeline gold) and `certify.py`; re-assert domain asset assignments; `verify_live.py --hero` → PASS.
- [ ] **Step 3:** `deploy_genie.py --patch`: full-body PATCH of both spaces with `rename()`d instructions/samples; Demand space tables add `launch_action_brief`, `launch_value`, `ops_launch_actions` (created in Tasks 7–8; re-run this step after Task 8). `patch_dashboard.py`: GET → `rename()` → PATCH. `make_pdf.py`: regenerate `Helivara_Genie_Knowledge.pdf` with fictional names, upload to `/Volumes/fr_stable_catalog/supply_chain/knowledge/`.
- [ ] **Step 4:** `scan_live_names.py` → PASS (0 hits). Ask the Demand agent "Which launches are at risk and what blocks them?" via the Conversation API; answer must name Zyvanta, master data, artwork. Save Q/SQL/result to `evidence/genie/after_rename.json`.
- [ ] **Step 5:** Commit `feat: reapply UC metadata and rename Genie, dashboard, knowledge PDF`.

### Task 6: Predictive-maintenance model (train, register, score)

**Files:** Create `src/helivara/features.py`, `tests/test_features.py`, `src/notebooks/01_train_failure_model.ipynb`,
`02_score_failure_model.ipynb`, `resources/jobs.yml` (job `helivara_train`).

**Interfaces — Produces:**
- `make_features(telemetry: pd.DataFrame, as_of_col="date") -> pd.DataFrame` — per (equipment, date): 7/14-day rolling mean & slope of vibration, temperature, motor_current; anomaly_score 7-day max; days since last maintenance.
- `make_labels(features, maintenance, horizon_days=30) -> pd.Series[int]` — 1 if an unplanned failure occurs in (date, date+30].
- UC model `fr_stable_catalog.supply_chain.equipment_failure_model`, alias `champion`.
- Gold table `fact_predicted_failure` with its existing contract columns, where `risk_score` = calibrated P(failure ≤ 30 d) as of 2026-09-22, `rul_days` = model-implied days (bucketed 1–30), `predicted_failure_date` = 2026-09-22 + rul_days, `failure_mode` = most frequent historical mode for the equipment class. Plus table `equipment_risk_drivers(equipment, top_driver, top_driver_value)`.

- [ ] **Step 1: Failing tests** `tests/test_features.py`: `test_rolling_features_no_lookahead` (features at date d unchanged when rows after d are removed), `test_labels_horizon` (failure on d+30 → 1, d+31 → 0, d itself → 0), `test_features_on_generated_data_separate_classes` (mean 14-day vibration slope higher for label 1 than 0 on `build_tables()` data).
- [ ] **Step 2:** Run → FAIL; implement `features.py`; run → PASS.
- [ ] **Step 3:** Train notebook: time-based split (train < 2026-06-01, test ≥ 2026-06-01 to 2026-08-22), gradient boosting + `CalibratedClassifierCV(method="isotonic")`; log AUC, precision@5, Brier, confusion matrix, feature importances to MLflow; register in UC and set `champion` if test AUC ≥ 0.75. Notebook writes `metrics.json` to `/Volumes/.../raw/_artifacts/`.
- [ ] **Step 4:** Score notebook writes `fact_predicted_failure` + `equipment_risk_drivers`. Live check (add to `verify_live.py --ml`): `L_OSD_001_EQ_01` is rank 1 by `risk_score` and `risk_score ≥ 0.6`; all scores in [0,1].
- [ ] **Step 5:** Run job `helivara_train`, then the score notebook; `verify_live.py --ml` → PASS. Export run outputs (`databricks jobs export-run --views-to-export ALL`) to `evidence/ml/` as HTML and copy `metrics.json` + a `model_card.md` (metrics, features, split, limits) there.
- [ ] **Step 6:** Commit `feat: predictive maintenance model registered in UC with scoring`.

### Task 7: Value model and GenAI launch brief

**Files:** Create `src/helivara/value.py`, `tests/test_value.py`, `src/notebooks/03_value_and_brief.ipynb`.

**Interfaces — Produces:**
- `launch_revenue_at_risk(weekly_units: float, net_price_eur: float, weeks_delay_avoided: float) -> float`
- `downtime_value(unplanned_hours_per_year: float, cost_per_hour_eur: float, reduction: float) -> float`
- `expiry_value(expiry_at_risk_units: float, unit_cost_eur: float, reduction: float) -> float`
- Tables: `value_assumptions(key STRING, value DOUBLE, unit STRING, source STRING)` seeded with
  `zyvanta_net_price_eur=950`, `weeks_delay_avoided=4`, `downtime_cost_per_hour_eur=8000`,
  `downtime_reduction=0.20`, `unit_cost_eur=12`, `expiry_reduction=0.25`, `otif_value_per_point_eur=200000`, `otif_points=5`;
  `launch_value(launch_id, brand, weekly_units, revenue_at_risk_eur, ...)`; `value_summary(lever, annual_value_eur, formula)`;
  `launch_action_brief(launch_id, brief_en, brief_it, model_endpoint, generated_at)`.
- Zyvanta `weekly_units` = mean consensus_forecast for 2026-10..2026-12 summed over markets ÷ 4.345.

- [ ] **Step 1: Failing tests** `tests/test_value.py`: `launch_revenue_at_risk(1000, 950, 4) == 3_800_000`; `downtime_value(500, 8000, 0.2) == 800_000`; `expiry_value(10_000, 12, 0.25) == 30_000`; negative inputs raise `ValueError`.
- [ ] **Step 2:** Run → FAIL; implement; run → PASS.
- [ ] **Step 3:** Notebook: seed `value_assumptions` (only if empty, so edits survive), compute `launch_value` and `value_summary` from gold + assumptions; `ai_query` (a Foundation Model endpoint available in the workspace; record its name) over readiness gates + linked equipment risk + revenue at risk → 4-sentence brief in EN and IT into `launch_action_brief`.
- [ ] **Step 4:** Run it; `verify_live.py --value` → PASS (Zyvanta row exists, revenue_at_risk_eur > 0, brief mentions master data and artwork in both languages). Save outputs to `evidence/value/` (summary table as markdown + brief text).
- [ ] **Step 5:** Commit `feat: value model and ai_query launch brief`.

### Task 8: Lakebase serving + write-back loop + daily job

**Files:** Create `src/helivara/lakebase_sync.py`, `tests/test_lakebase_sync.py`, `src/jobs/sync_to_lakebase.py`,
`src/jobs/copy_actions_back.py`, `setup/lakebase_init.sql`, extend `resources/jobs.yml` (job `helivara_daily`).

**Interfaces — Produces:**
- Lakebase project `helivara`, database `helivara`, schema `control_tower`:
  `launch_risk_board(launch_id PK, sku, brand, therapeutic_area, readiness, master_data_ready, artwork_ready,
  serialization_ready, blocking_gates TEXT, revenue_at_risk_eur, brief_en, brief_it, linked_equipment,
  linked_failure_prob, refreshed_at)`; `equipment_risk(equipment PK, plant, line, equipment_class,
  failure_prob_30d, rul_days, top_driver, impacted_brands TEXT, refreshed_at)`;
  `actions(action_id BIGSERIAL PK, launch_id, action_type CHECK IN ('escalate_master_data','escalate_artwork','book_maintenance'),
  equipment NULL, owner, due_date DATE, note TEXT, status DEFAULT 'open', created_by, created_at DEFAULT now())`
  + partial unique index on `(launch_id, action_type) WHERE status='open'`.
- `upsert_sql(table: str, columns: list[str], pk: str) -> str` (INSERT … ON CONFLICT (pk) DO UPDATE)
- `sync_rows(conn, table, columns, pk, rows: list[tuple]) -> int`
- Delta table `ops_launch_actions` (same columns as `actions`), overwritten by `copy_actions_back.py`.
- Job `helivara_daily`: pipeline update → `02_score` → `03_value_and_brief` → `sync_to_lakebase` → `copy_actions_back`.

- [ ] **Step 1: Failing tests** `tests/test_lakebase_sync.py`: `test_upsert_sql_is_idempotent` (SQL contains `ON CONFLICT (launch_id) DO UPDATE` and updates every non-pk column), `test_sync_rows_roundtrip_utf8` (fake conn records params; "Perché è a rischio" passed unchanged), `test_sync_rows_returns_count`.
- [ ] **Step 2:** Run → FAIL; implement; run → PASS.
- [ ] **Step 3:** Create the Lakebase project (`databricks postgres create-project helivara`), run `lakebase_init.sql`. Try a UC synced table for `launch_risk_board` once; if it errors (expected: no CREATE CATALOG), keep the pg8000 job and record the error text in `docs/DECISIONS.md` material (`evidence/lakebase/synced_table_attempt.txt`).
- [ ] **Step 4:** Deploy and run `helivara_daily` twice. Live check `verify_live.py --lakebase`: row counts equal gold source counts after both runs; Zyvanta row values equal gold; an action inserted by hand before run 2 still exists and appears in `ops_launch_actions`. Save outputs to `evidence/lakebase/`.
- [ ] **Step 5:** Re-run Task 5 Step 3 (Genie Demand space gets `ops_launch_actions`, `launch_action_brief`, `launch_value`).
- [ ] **Step 6:** Commit `feat: Lakebase serving tables, action write-back loop, daily job`.

### Task 9: App backend (FastAPI)

**Files:** Create `app/backend/{main.py, db.py, genie.py, models.py}`, `tests/app/test_api.py`, `tests/app/test_genie.py`, `tests/app/test_db.py`.

**Interfaces — Produces (HTTP):**
- `GET /api/launches` → `list[LaunchCard]` from `launch_risk_board` (ordered by readiness asc)
- `GET /api/equipment-risk?limit=10` → `list[EquipmentRisk]` ordered by failure_prob_30d desc
- `GET /api/actions?launch_id=` → `list[Action]`; `POST /api/actions` body `{launch_id, action_type, owner, due_date, equipment?, note?}` → 201 `Action`, or 200 with the existing open action if one already exists for `(launch_id, action_type)`; 422 on unknown action_type / missing owner.
- `POST /api/genie/ask` body `{question, space: "demand"|"manufacturing", conversation_id?}` → `{conversation_id, text, sql?, columns?, rows?, status}`; `status` ∈ `ok|no_data|error`.
- `db.get_conn()` opens pg8000 connections with a credential cached until 5 min before expiry (`databricks-sdk` Lakebase credential API); `genie.ask()` uses the user's forwarded token (`x-forwarded-access-token`) and falls back to the app SP when absent; polls up to 60 s.

- [ ] **Step 1: Failing tests** (FastAPI `TestClient`, repository and Genie client injected via dependency overrides):
  `test_list_launches_sorted`, `test_post_action_validation_422`, `test_post_action_is_idempotent_for_open_action`,
  `test_genie_text_only_and_failure` (text-only → status ok, sql None; FAILED → status error with message; timeout → status error, HTTP 200),
  `test_connection_refreshes_expired_credential` (fake clock past expiry → credential fetched again), `test_utf8_note_roundtrip`.
- [ ] **Step 2:** Run `uv run pytest tests/app -v` → FAIL; implement; run → PASS.
- [ ] **Step 3:** Commit `feat: control tower API (Lakebase, actions, Genie)`.

### Task 10: App frontend, deploy, smoke test

**Files:** Create `app/frontend/` (React + Vite), `app/app.yaml`, `resources/app.yml`, `checks/app_smoke.py`.

- [ ] **Step 1:** UI (my layout call, Databricks palette): header "Helivara Launch & Supply Control Tower"; row of launch cards (readiness gauge, blocking gates, "€ at risk (estimate)" from `revenue_at_risk_eur`, linked equipment + failure %); right panel "Ask Genie" (space toggle, Italian placeholder "Perché Zyvanta è a rischio?", shows text, collapsible SQL, small result table); Escalate dialog (action type, owner, due date, note) → shows "Tracked" badge + actions list; equipment risk table.
- [ ] **Step 2:** `app.yaml`: `uvicorn` serving built frontend; env for Lakebase host/db, Genie space ids, warehouse; resources: Lakebase database, SQL warehouse, Genie spaces (CAN_RUN); `user_api_scopes: [sql, dashboards.genie]`. Grant the app SP: SELECT on the Genie tables, Lakebase role with rights on `control_tower`.
- [ ] **Step 3:** `databricks bundle deploy` + start app. `checks/app_smoke.py <url>` (user token): GET launches contains Zyvanta; equipment-risk top = `L_OSD_001_EQ_01`; POST escalate_artwork twice → one open action; Genie ask "Perché Zyvanta è a rischio?" → status ok and text mentions artwork; Genie ask "Cosa rende un lancio pronto?" → status ok. Output to `evidence/app/smoke_<date>.log` → all PASS.
- [ ] **Step 4:** Commit `feat: control tower app deployed`.

### Task 11: Evidence pack, docs, final scan, publish

**Files:** Create `README.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/AI_USAGE.md`, `evidence/README.md`, `evidence/genie/transcripts.md`.

- [ ] **Step 1:** Genie transcripts: run the golden set (5 data questions on each agent, 3 PDF-only questions, the OEE contrast pair) via the Conversation API → `evidence/genie/transcripts.json` + readable `.md` (question, answer, SQL, first rows).
- [ ] **Step 2:** README order: (1) business problem + outcome in 5 lines; (2) value table from `value_summary` (numbers + formulas + "estimates" label); (3) hero moment walkthrough; (4) journey diagram (Mermaid) raw → Lakeflow → UC → ML/GenAI → Lakebase → Genie → App with table names on edges; (5) decisions & trade-offs (link DECISIONS.md: pipeline MVs vs CTAS, Lakebase vs warehouse serving, pg8000 sync vs synced tables + the recorded error, classical ML vs LLM for failure, metric views as Genie's source, OBO vs SP); (6) AI as force multiplier (link AI_USAGE.md: Claude Code session, prompts/patterns, subagent reviews, what was verified by hand); (7) how to run (`uv sync`, `setup/upload_raw.py`, `databricks bundle deploy && run`); (8) evidence index (each FE Bar stage → evidence file).
- [ ] **Step 2b:** Describe people by role only; mark all data synthetic and Helivara fictional.
- [ ] **Step 3:** `uv run python -m helivara.names $(git ls-files)` → 0 hits; `checks/scan_live_names.py` → 0 hits; full `pytest` → PASS.
- [ ] **Step 4:** Commit, then `gh repo create Federix93/helivara-plant-to-patient --public --source . --push` (account Federix93: `gh auth switch -u Federix93`). Verify anonymous read: `curl -s -o /dev/null -w '%{http_code}' https://github.com/Federix93/helivara-plant-to-patient` → 200.

### Task 12: Deck copy (outcome-first) and speech

**Files:** Create `docs/deck/Helivara_FE_Bar.pdf`, `docs/DEMO_SCRIPT_FE_BAR.md`.

- [ ] **Step 1:** Copy deck `1CdPHh6Zkri2uNa-DGI6bm9NMXY9esohBcY7hozMEY1Y` → "Helivara – Plant to Patient (FE Bar)". Original untouched. No sharing changes.
- [ ] **Step 2:** New order: title (old 19) → hook (old 25) → NEW exec summary → NEW problem → NEW value table (numbers from `value_summary`) → NEW value by persona (sponsor = COO / Head of Global Supply Chain; domain owner = Global Demand & S&OP Manager) → NEW journey diagram → demo (old 8, retitled with 3 beats) → NEW "what this means" → NEW decisions & trade-offs → NEW security, governance & cost → NEW 30/60/90 pilot + ask (fill old 26) → section "Appendix" → old 11, 12–18, 20–24. Delete old 1 (agenda for 30+ people) and old 2–10. Apply `rename()` to all text incl. notes; speaker notes on new slides = the speech lines.
- [ ] **Step 3:** Run builder `validate`; scan exported text with `find_forbidden` → 0; export PDF to `docs/deck/`.
- [ ] **Step 4:** `DEMO_SCRIPT_FE_BAR.md`: ~10-min tell-show-tell (setup, tell, 6 show beats matching the app, tell with real numbers), objection bank (business: cost, risk, time to value, adoption, "we have IBP"; technical: SAP integration, data quality, security/row filters, Genie accuracy, why Lakebase, drift, GxP/audit, CI/CD), and the 60-second fallback if the app or Genie is slow.
- [ ] **Step 5:** Commit + push `docs: FE Bar deck and demo script`.
