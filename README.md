# Helivara · Plant to Patient: catching launch risk before it costs €7.9M

> **Helivara is a fictional specialty and consumer-health pharma company. Every number here comes from synthetic data.**
> The processes (S&OP, launch governance, OEE, predictive maintenance) work the way they do in real pharma operations.

## 1. The business problem and the outcome

Helivara's most important launch, **Zyvanta** (immunology), is at risk, and nobody can see it in time.
Two of its three launch gates are open: **material master data is 0% complete and artwork is not approved**. Those blockers
only come up at the monthly S&OP review. Meanwhile the **Valmora coater**, the machine that coats Zyvanta, is wearing out,
and maintenance doesn't know the launch depends on it. To answer "is my launch safe, and why?" a planner has to chase
ERP, MES and maintenance reports for days.

**What this build delivers.** In one governed app, the Global Demand & S&OP Manager:
1. sees **Zyvanta at 33% readiness with €7.9M revenue at risk** (estimate);
2. asks Genie in Italian *"Perché Zyvanta è a rischio?"* and gets **master data + artwork**, answered from certified metrics;
3. sees that the predictive model gives the Valmora coater a **94% chance of failing within 30 days**, a second, hidden risk;
4. clicks **Escalate**, which creates three owned, dated actions (master data, artwork, preventive maintenance), stored in Lakebase
   and copied back to the lakehouse so Genie and the dashboard can see what was decided.

From days of report chasing to **about 60 seconds from signal to tracked decision**.

## 2. Value (estimates, computed from the data)

Produced by notebook `src/notebooks/03_value_and_brief.py` from gold tables × the editable `value_assumptions` table
(full table and sources: [`evidence/value/value_summary.md`](evidence/value/value_summary.md)).

| Lever | Annual value | How it's computed | Who cares |
|---|---:|---|---|
| **Launch protection (Zyvanta)** | **€7.85M** | 4,361 packs/week (Q4 consensus forecast) × €450 net/pack × 4 weeks of delay avoided | Executive sponsor (COO / Head of Global Supply Chain) |
| Unplanned downtime avoided | €0.73M | 457 unplanned h/yr × €8,000/h × 20% reduction | Plant and reliability leaders |
| OTIF improvement | €1.00M | 5 OTIF points × €200k/point (penalties, lost sales) | Commercial / supply chain |
| Expiry write-off avoided | €0.11M | 35,626 units at risk/yr × €12 × 25% | Finance |
| **Total** | **≈ €9.7M / year** | Run cost: serverless, pay-per-use (pipeline + jobs + Lakebase CU + app) | |

**Domain owner value (Global Demand & S&OP Manager):** launch-gate status every day instead of once a month, one certified
definition of readiness and accuracy shared with finance, and self-service answers in Italian with the SQL visible.

## 3. The integrated journey

```mermaid
flowchart LR
  subgraph Sources["Simulated sources (synthetic)"]
    SAP[SAP extracts CSV] --- MES[MES JSON] --- IOT[IoT telemetry JSON] --- CMMS[CMMS CSV]
  end
  Sources -->|UC Volume raw/| B[bronze_* · Auto Loader]
  subgraph Lakeflow["Lakeflow Declarative Pipeline: helivara_plant_to_patient"]
    B --> S[silver_* · typed, deduped, 10 expectations] --> Q[*_quarantine · 518 bad rows]
  end
  S -->|publish task, INSERT OVERWRITE| G[(Governed gold: 21 tables, certified, in 4 Discover domains)]
  G --> MV[8 metric views · mv_*]
  G -->|telemetry + maintenance| ML[equipment_failure_model@champion · AUC 0.82]
  ML --> PF[fact_predicted_failure · equipment_risk_drivers]
  G --> VAL[value_assumptions → launch_value · value_summary]
  PF & VAL --> AI[ai_query brief EN/IT · launch_action_brief]
  MV & PF & AI --> GENIE[2 Genie agents + knowledge PDF]
  PF & VAL & AI -->|sync job, pg8000 upsert| LB[(Lakebase: control_tower.*)]
  LB --> APP[Databricks App: Control Tower]
  GENIE --> APP
  APP -->|Escalate| ACT[(Lakebase: control_tower.actions)]
  ACT -->|copy-back job| OPS[ops_launch_actions · visible to Genie]
```

| FE Bar stage | What's built | Code | Execution evidence (text) |
|---|---|---|---|
| **Lakeflow** | Serverless declarative pipeline: Auto Loader bronze → silver with 10 expectations → quarantine; daily Lakeflow Job with 6 tasks | `src/pipeline/`, `src/sql/publish_gold.sql`, `resources/` | [`evidence/pipeline/run_2026-11-09.md`](evidence/pipeline/run_2026-11-09.md), [`verify.txt`](evidence/pipeline/verify.txt) (53/53), [`jobs/helivara_daily/run_summary.md`](evidence/jobs/helivara_daily/run_summary.md) |
| **Unity Catalog** | Bilingual comments on every gold table, 8 metric views, certification + a deprecated decoy, 4 domains / 8 subdomains, UC-registered model, lineage from the raw Volume files through bronze/silver to gold and the scored tables | `setup/` | [`evidence/contracts/`](evidence/contracts/) (schema contract, name scan 0 hits) |
| **ML / GenAI** | Calibrated gradient-boosting failure model (MLflow, UC registry, `@champion` only if AUC ≥ 0.75); `ai_query` brief; Genie knowledge PDF | `src/helivara/features.py`, `src/notebooks/` | [`evidence/ml/model_card.md`](evidence/ml/model_card.md), [`metrics.json`](evidence/ml/metrics.json), [`train_run_output.txt`](evidence/ml/train_run_output.txt), [`evidence/value/launch_action_brief.md`](evidence/value/launch_action_brief.md) |
| **Lakebase** | Autoscaling Postgres project `helivara`: serving tables (idempotent upsert) + `actions` (app-owned, one open action per launch × type) | `src/helivara/lakebase_sync.py`, `setup/lakebase_init.sql` | [`evidence/lakebase/verify.txt`](evidence/lakebase/verify.txt), [`synced_table_attempt.txt`](evidence/lakebase/synced_table_attempt.txt) |
| **Genie Agent** | Demand & Supply and Manufacturing & Reliability agents on metric views + ML/value/action tables; embedded in the app | `setup/patch_genie.py` | [`evidence/genie/transcripts.md`](evidence/genie/transcripts.md) (15 Q&A with SQL) |
| **Databricks App** | FastAPI + React Control Tower: Lakebase board, model risk, Genie (on behalf of the signed-in user), Escalate write-back | `app/` | [`evidence/app/smoke_2026-11-09.log`](evidence/app/smoke_2026-11-09.log) (9/9 against the deployed app) |

Screenshots (supplementary): [board](docs/img/control_tower_board.png) · [escalate](docs/img/control_tower_escalate.png) · [tracked](docs/img/control_tower_tracked.png).

## 4. Decisions and trade-offs (summary; details in [`docs/DECISIONS.md`](docs/DECISIONS.md))

- **The pipeline feeds the existing governed gold tables instead of replacing them** (publish via `INSERT OVERWRITE`). Certification, domains, Genie
  and metric-view links survive. *Trade-off:* gold lineage shows a job SQL step instead of a pipeline-managed view.
- **Lakebase for the app, not the SQL warehouse.** It gives millisecond reads, transactional write-back and a uniqueness constraint
  (a double click can't create a second action). *Trade-off:* a sync step, because managed synced tables need CREATE CATALOG,
  which this shared metastore doesn't grant ([attempt recorded](evidence/lakebase/synced_table_attempt.txt)).
- **Classical ML for failure prediction, an LLM only for the narrative.** Probabilities have to be calibrated and auditable, and the brief has to be readable.
- **Genie grounded on metric views.** Every KPI has one certified definition, so Genie's answers match finance and the dashboard.
- **Genie runs as the signed-in user** (`user_api_scopes`), so Unity Catalog permissions apply to each person.

## 5. AI as a force multiplier

Built with Claude Code as a pair engineer: brainstorm → written design → plan → test-driven execution, with live
verification scripts after each stage. Prompts, patterns and what was checked by hand: [`docs/AI_USAGE.md`](docs/AI_USAGE.md).

## 6. How to run it

```bash
uv sync                                   # Python 3.12 env (pandas, scikit-learn, pg8000, fastapi…)
uv run pytest                             # 55 unit tests (generator, features, value, sync, app API)
uv run python setup/upload_raw.py         # generate synthetic sources → UC Volume raw/
databricks bundle deploy                  # pipeline, 3 jobs, app (profile in databricks.yml)
databricks bundle run helivara_train      # train + register + score the model
uv run python setup/lakebase_init.py      # Lakebase database + control_tower schema
databricks bundle run helivara_daily      # ingest → publish → score → value/brief → Lakebase → copy-back
uv run python setup/lakebase_grant_app.py # Lakebase role for the app's service principal
databricks bundle run helivara_control_tower
uv run python checks/verify_live.py --contract --hero --quarantine --ml --value --lakebase
uv run python checks/app_smoke.py <app-url>
uv run python setup/reset_demo.py         # clean actions before presenting
```

Architecture detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · evidence index: [`evidence/README.md`](evidence/README.md) ·
demo script and objection bank: [`docs/DEMO_SCRIPT_FE_BAR.md`](docs/DEMO_SCRIPT_FE_BAR.md) ·
business deck (PDF): [`docs/deck/Helivara_FE_Bar.pdf`](docs/deck/Helivara_FE_Bar.pdf).
