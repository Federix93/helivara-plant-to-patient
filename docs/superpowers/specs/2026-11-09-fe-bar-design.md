# FE Bar submission — Helivara "Plant to Patient" (design)

Date: 2026-11-09 · Owner: Federico Rizzo · Workspace: fevm-fr-stable (profile `fr-stable`,
warehouse `797d1d487d654063`) · Catalog/schema: `fr_stable_catalog.supply_chain`

## 1. Intent and the why

Federico must pass the **FE Bar**: a working, *integrated* end-to-end prototype for a real industry
problem (Lakeflow → Unity Catalog → Lakebase → ML/GenAI → Genie Agent → Databricks App), a public
GitHub repo with **text-readable execution evidence**, a business deck, and a live AI roleplay
(business + technical stakeholder). An AI evaluator reads the repo as text only.

The existing Helivara demo already covers UC governance (bilingual comments, 8 metric views,
certification, 4 domains/8 subdomains), 2 Genie Agents (+ a knowledge PDF) and an AI/BI
dashboard. It is **missing**: a Lakeflow pipeline (data was loaded by a one-off CTAS script),
Lakebase, a real ML model (`fact_predicted_failure` is random synthetic data, and telemetry is
pure noise), a Databricks App, a repo, and execution evidence. This project adds exactly those,
wired into the existing assets so the journey is one flow, not stitched demos.

**Business problem (pharma, specialty + consumer health):** Helivara's most important launch,
Zyvanta (immunology), is at risk. Its readiness blockers (material master data 0%, artwork 0%)
only surface at the monthly S&OP review, and the Valmora line that coats/packs it has a hidden
equipment-failure risk. Each week of launch delay ≈ €2.3M revenue (estimate). Answering "is my
launch safe and why" today takes days across ERP/MES/maintenance systems.

## 2. The hero moment (agreed with Federico)

In the app, in ~60 seconds:
1. Launch board (served from Lakebase): **Zyvanta — readiness 0.33 — ~€X M revenue at risk**.
2. User asks embedded Genie in Italian *"Perché Zyvanta è a rischio?"* → master data 0%,
   artwork 0%, serialization OK, citing `mv_launch_readiness`.
3. Next to it, the **ML model** flags the Valmora coater at **~Y% failure probability in 30
   days** — the line that coats Zyvanta → second, hidden risk.
4. User clicks **Escalate** → owner + due date for artwork, preventive maintenance booked →
   written to Lakebase instantly → board shows it as tracked.

X and Y are produced by the value notebook and the model, never hard-coded in the UI.

## 3. Goals

- G1 Every FE Bar stage is real, running, and connected through shared tables (UC lineage
  from raw file to the app's serving table must be visible).
- G2 The hero moment works live in the app.
- G3 Public repo `github.com/Federix93/helivara-plant-to-patient` whose README leads with the
  business outcome and value, then journey, decisions & trade-offs, AI-usage, run instructions,
  and an evidence index.
- G4 Execution evidence committed **as text**: notebooks with outputs, pipeline event/expectation
  metrics, job run output, model metrics, Lakebase query output, Genie Q&A transcripts (question,
  generated SQL, result), app smoke-test log.
- G5 Quantified value computed from the data with explicit, editable assumptions.
- G6 FE Bar deck = a **copy** of Federico's deck (`1CdPHh6Zkri2uNa-DGI6bm9NMXY9esohBcY7hozMEY1Y`),
  restructured outcome-first; original untouched. Export PDF into the repo.
- G7 Speech + objection-handling script committed (`docs/DEMO_SCRIPT_FE_BAR.md`).

## 4. Non-goals / anti-goals

- Non-goal: replacing the existing Genie agents, metric views, domains or dashboard — reuse them.
- Non-goal: real SAP/MES connectors; sources are simulated as files in a Volume.
- Non-goal: production hardening (CI pipelines, multi-env). One `dev` target is enough.
- **Anti-goal:** stages that exist but don't feed each other (the #1 FE Bar failure mode).
- **Anti-goal:** evidence that is only screenshots.
- **Anti-goal:** a hard-coded "78%"/"€9M" in the app or deck that the data doesn't support.
- **Anti-goal:** breaking the existing hero facts (hero-launch readiness 0.33, master data 0%,
  artwork 0%, serialization 100%; phase-out US = 0 after 2025-11) or the live Genie agents.
- **Anti-goal:** real people's names in the repo (see §8).

## 5. Architecture (decided)

```
generate_data.py (seed 42)  ──►  UC Volume /Volumes/fr_stable_catalog/supply_chain/raw/
  simulated source extracts:      sap/   (CSV: dims, demand, inventory, service, launch register)
                                  mes/   (JSON: batches, OEE, QC, deviations)
                                  iot/   (JSON: equipment telemetry)  cmms/ (CSV: maintenance)
          │ Lakeflow Spark Declarative Pipeline `helivara_plant_to_patient` (serverless)
          ▼
  bronze_* streaming tables (Auto Loader)  →  silver (typed, deduped, expectations;
  bad rows quarantined to *_quarantine)  →  gold tables with the SAME names as today
  (dim_*, fact_*) in fr_stable_catalog.supply_chain
          │                                   │
          ▼                                   ▼
  existing 8 metric views (unchanged)    ML: predictive maintenance (MLflow, UC model
  → existing 2 Genie Agents + PDF        `equipment_failure_model`, alias @champion)
  → existing dashboard                   batch scoring → gold `fact_predicted_failure`
          │                              GenAI: ai_query → gold `launch_action_brief`
          ▼
  Lakebase (Autoscaling project `helivara`, db `helivara`):
    serving: launch_risk_board, equipment_risk   (synced from gold)
    operational: actions  (written by the app; copied back to Delta `ops_launch_actions`
                           so Genie/dashboard see decisions — closes the loop)
          ▼
  Databricks App `helivara-control-tower` (FastAPI + React):
    Launch board · Equipment risk · Ask Genie (Conversation API) · Escalate → Lakebase
```

Orchestration: one Lakeflow **Job** `helivara_daily` — pipeline update → score model →
ai_query brief → sync gold→Lakebase → copy actions Lakebase→Delta. Training is a separate job
task/notebook (run once, re-runnable).

Packaging: a **Databricks Asset Bundle** at repo root (pipeline, jobs, app). Existing
Terraform/scripts stay in `legacy/` or `setup/` for the UC metadata steps.

### Decided details
- **Gold names stay identical** so metric views, Genie spaces and dashboard keep working. The
  existing CTAS tables are dropped and recreated by the pipeline; afterwards re-run
  `comments.py`, `certify.py` and the domain asset assignment (they are lost on drop). Prefer
  putting table/column comments in the pipeline definitions themselves.
- **Hero facts preserved:** existing RNG draw order in `generate_data.py` must not change. New
  telemetry/failure logic uses its own RNG (`np.random.default_rng(...)`). Force one Valmora
  equipment to `coater` serving Zyvanta's line.
- **Telemetry gets a learnable signal:** degradation (vibration/temperature/current drift)
  in the days before unplanned maintenance events; label = unplanned failure within 30 days.
  Valmora coater ends the history in a degrading state so the model scores it high.
- **Dirty rows on purpose** (~1–2%: null keys, negative qty, duplicate IDs, out-of-range
  sensor values) so expectations quarantine something visible.
- Model: classical tabular classifier (e.g. gradient boosting) with rolling-window features;
  log metrics (AUC, precision@k, confusion matrix), feature importance, register in UC.
- Value notebook: computes € at risk per launch, downtime cost, expiry write-off and OTIF impact
  from gold tables × assumptions table (`value_assumptions`, editable); outputs committed.
- App auth: app service principal for Lakebase; Genie calls on-behalf-of the user (user's UC
  permissions apply — governance talking point). Builder may fall back to SP if OBO blocks.

## 6. Constraints / known gotchas (from past work on this workspace)

- Serverless-only workspace; no classic clusters.
- Genie `PATCH /api/2.0/genie/spaces/{id}` is a **full replace** — always send the full body.
- Shared metastore: **no CREATE CATALOG**. Lakebase→Delta CDF does not work here
  (ES-1940670). Gold→Lakebase: try synced tables first; if unavailable, a job task pushing rows
  with **pg8000** (psycopg[binary] crashes on serverless job compute).
- Metric views must be queried with `MEASURE()`.
- Existing Genie spaces: Demand and Supply `01f1bc08a109177a8d192afb82da3e2b`, Manufacturing and
  Reliability `01f1bc08a1471942bf4433f530ef8537`. Dashboard `01f1bc0ce3801f2499977bbb1277a65c`.
- Git commits must end with `Co-authored-by: Isaac <no-reply@databricks.com>` (managed setting).

## 7. Left to the builder

Exact bronze/silver schemas and expectation rules; feature set and model family; UI layout and
styling (Databricks palette); ai_query model endpoint choice; how evidence files are captured;
DAB vs. extending Terraform for UC metadata steps; deck slide visuals.

## 8. Resolved decisions

- **Real names → fictional, in place (Federico's decision):** the real-brand version isn't needed
  any more. Rename all real brands and plants to fictional names **in this workspace** (data, UC
  comments, both Genie agents, dashboard, knowledge PDF, deck copy, app, repo) using ONE mapping
  table applied by the generator and every script. Story roles and numbers stay identical. No
  people's names anywhere (role titles only, e.g. "Global Demand & S&OP Manager"); drop
  "[redacted]'s world" from `comments.py:38`. The public repo can stay up after the evaluation.
  (the real→fictional mapping is kept outside the repo; only fictional names are published; see `src/helivara/names.py` for the fictional brand and plant lists.)
  Acceptance check: a scan of the catalog (data values + comments), Genie spaces, dashboard,
  PDF, repo and deck finds 0 real brand, plant or person names.
- **As-of date (my call):** keep demo "today" = 2026-09-22 so the hero facts and metric views stay
  consistent. Telemetry history ends there; the 30-day failure horizon points forward from it.
- **€ at risk (my call):** revenue base = Zyvanta planned volume (gold forecast) × an assumed net
  price, both in `value_assumptions`. Delay avoided = assumed weeks (default 4) in the same table.
  The app shows the computed number with an "estimate" label.
- **Y% (my call):** shown as a calibrated probability (calibrated classifier); the raw score
  stays in the table too.
- **Genie auth (my call):** on-behalf-of the user is preferred. Falling back to the service
  principal is acceptable if OBO blocks; record which one was used in the evidence.
- **Deadline / cut order (my call, no date given):** build in this order: pipeline → model →
  Lakebase → app → evidence/README → deck → speech. No stage is dropped. If time runs short, cut
  polish first: app styling, then the actions→Delta copy-back, then extra evidence files.
