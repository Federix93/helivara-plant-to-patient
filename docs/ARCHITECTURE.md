# Architecture

All assets live in workspace `fevm-fr-stable`, catalog.schema `fr_stable_catalog.supply_chain`, and are deployed with
the Databricks Asset Bundle in `databricks.yml` + `resources/`. Synthetic data; Helivara is fictional.

## Data flow, table by table

| Step | Producer | Output | Notes |
|---|---|---|---|
| 1 | `setup/upload_raw.py` → `src/helivara/generate.py` | Volume `raw/{sap,mes,iot,cmms,config}/<entity>/` | 21 entities as CSV/JSON plus ~1.5% injected dirty rows (`_dirty_manifest.json`) |
| 2 | Pipeline `helivara_plant_to_patient` (serverless) | `bronze_<entity>` streaming tables | Auto Loader, strings only, `_source_file` and `_ingested_at` lineage columns |
| 3 | same pipeline | `silver_<entity>` + `<entity>_quarantine` | cast to the gold contract (`evidence/contracts/gold_schemas.json`), dedupe on business keys, 10 `expect_all_or_drop` rules; rejected rows kept with `_failed_rules` |
| 4 | Job task `publish_gold` (`src/sql/publish_gold.sql`) | the 21 governed gold tables | `assert_true` guard (silver not empty), then `INSERT OVERWRITE` keeps table identity (certification, domain tags, Genie, metric views) |
| 5 | existing UC layer | 8 metric views `mv_*`, certification, 4 domains / 8 subdomains | metric views queried with `MEASURE()` by Genie and the dashboard |
| 6 | `01_train_failure_model.py` (job `helivara_train`) | UC model `equipment_failure_model` (`@champion`) | out-of-time split with a 30-day embargo; sigmoid calibration; promoted only if test AUC ≥ 0.75 |
| 7 | `02_score_failure_model.py` | `fact_predicted_failure` (alerts ≥ 0.30), `equipment_risk_drivers` (all machines) | scores as of demo date 2026-09-22 |
| 8 | `03_value_and_brief.py` | `value_assumptions`, `launch_value`, `value_summary`, `launch_action_brief` | `ai_query` on `databricks-claude-sonnet-5-5`, grounded on governed facts |
| 9 | `src/jobs/sync_to_lakebase.py` | Lakebase `control_tower.launch_risk_board`, `equipment_risk` | pg8000 upsert by PK + prune (idempotent; refuses to prune from an empty source) |
| 10 | App `helivara-control-tower` | Lakebase `control_tower.actions` | partial unique index: one open action per (launch, action type) |
| 11 | `src/jobs/copy_actions_back.py` | Delta `ops_launch_actions` | closes the loop: Genie can answer "which actions are open?" |

Daily orchestration: job `helivara_daily` = steps 2 → 4 → 7 → 8 → 9 → 11 (6 tasks, about 6.5 minutes end to end, see
`evidence/jobs/helivara_daily/run_summary.md`).

## App

- **Backend** (`app/backend`): FastAPI. `db.py` opens pg8000 connections with a Lakebase OAuth credential cached until 5 minutes
  before it expires. `genie.py` wraps the Genie Conversation API and never raises (status `ok | no_data | error`). `main.py` exposes the routes.
- **Frontend** (`app/frontend`): React + Vite, built to `dist/` and served by FastAPI.
- **Identity**: Genie and SQL run **on behalf of the signed-in user** (`user_api_scopes: [sql, dashboards.genie]`), so UC permissions
  apply per person. Lakebase is accessed by the app's service principal through a Postgres role limited to SELECT on serving
  tables and SELECT/INSERT on `actions` (`setup/lakebase_grant_app.py`).
- Bundle resources give the app CAN_USE on the warehouse and CAN_RUN on both Genie spaces.

## Security and governance

- No credentials in code: workspace OAuth (CLI profile locally, service principal / user tokens in the app and jobs).
- Least privilege in Lakebase. The app service principal has no Unity Catalog data grants; Genie runs with the user's rights.
- Data quality is enforced, not just reported: bad rows never reach gold, and they stay inspectable in `*_quarantine`.
- Name safety: `src/helivara/names.py` keeps real-world names out of the repo and the workspace (fingerprint scanner,
  `checks/scan_live_names.py` → 0 hits).

## Productionising (what we'd do next)

Lakeflow Connect / SAP Business Data Cloud instead of file extracts; separate dev/prod bundle targets and CI (`bundle
validate` + `pytest`); Lakehouse Monitoring on the scored table for drift; row filters by market on gold; managed synced
tables once a catalog can be created for Lakebase; an approval workflow (status transitions) on `actions`.
