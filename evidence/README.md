# Evidence index (all text; produced by real runs on 2026-11-09)

| Stage | File | What it proves |
|---|---|---|
| Contracts | `contracts/gold_schemas.json`, `contracts/hero_before.json` | gold schema and hero numbers snapshotted from the live tables before the pipeline took over |
| Raw landing | `pipeline/raw_landing.txt`, `pipeline/dirty_manifest.json` | simulated source files in the UC Volume; dirty rows injected per entity |
| Lakeflow | `pipeline/run_2026-11-09.md` | event log: 52 flows, rows per flow, expectations passed/failed per rule |
| Lakeflow + UC | `pipeline/verify.txt` | 53/53: contract identical, hero facts intact, row counts equal, quarantine = injected bad rows |
| Orchestration | `jobs/helivara_daily/run_summary.md`, `*_run_output.txt`, `*_log.txt` | the 6-task daily job succeeded; scoring/value notebook outputs; sync and copy-back logs |
| ML | `ml/model_card.md`, `ml/metrics.json`, `ml/train_run_output.txt`, `ml/score_run_output.txt`, `ml/*_run.html`, `ml/verify.txt` | training run (AUC 0.82), UC registration + `@champion`, scores (Valmora coater 0.94) |
| GenAI + value | `value/value_summary.md`, `value/launch_action_brief.md`, `value/value_and_brief_run_output.txt`, `value/verify.txt` | € value per lever with formulas; the ai_query brief in EN and IT with its grounding facts |
| Lakebase | `lakebase/verify.txt`, `lakebase/synced_table_attempt.txt` | serving rows = gold, no duplicates after re-runs; app action survives and reaches Delta; why synced tables weren't used |
| Genie | `genie/transcripts.md` (+ `.json`), `genie/after_rename.json` | 15 questions with answers, generated SQL and result rows (data, knowledge, contrast pair) |
| App | `app/smoke_2026-11-09.log` | 9/9 against the deployed app: UI, Lakebase board, model risk, idempotent escalate, 422 validation, Genie in IT/EN |
| Name safety | `contracts/scan_live_names.txt` | 0 real-world names in data, comments, Genie, dashboard, domains and PDF |
