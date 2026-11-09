# AI as a force multiplier: how this was built

**Tool:** Claude Code (CLI) as a pair engineer, working against the live workspace through the Databricks CLI, plus the
Superpowers workflow skills (brainstorming → written design → implementation plan → test-driven execution → final review).
The human set the goals, made every business call and approved every destructive or outward-facing action.
The conversation ID is supplied in the submission form.

## Workflow and patterns

| Phase | What the AI did | What the human decided | Artifact |
|---|---|---|---|
| Gap analysis | Compared the existing Genie/UC demo to the FE Bar stages; inventoried the live workspace (tables, Lakebase, apps, pipelines) | Scope: build what's missing in the same workspace | chat |
| Brainstorm | Proposed the hero moment (insight → € → decision in ~60 s); asked only questions that change the build | Predictive maintenance as the ML piece; FastAPI + React; fictional names everywhere | `docs/superpowers/specs/…-design.md` (public copy) |
| Design review | A fresh **subagent "builder check"** read the design cold and listed the questions it would have to guess | Answered the ones only the human could (names, deadline) | design §8 |
| Plan | 12 tasks with exact interfaces, test names and live checks; a *Review Focus* list of failure modes (Genie text-only answers, token expiry, double-click, Italian accents, job re-runs) | Native (inline) execution | `docs/superpowers/plans/…-build.md` (public copy) |
| Execute | Red → green tests for every pure function (55 tests); a `checks/verify_live.py` gate after each live stage; every deviation recorded as a ruling | Explicit OK to run the pipeline and overwrite gold, and to publish this repo | commits, `evidence/` |

### Prompt patterns that worked
- **"Contract first"**: snapshot the live gold schemas and hero numbers, then make every new stage prove it matches
  (`evidence/contracts/`, 53/53 checks). This made the refactor from CTAS loads to Lakeflow safe on live tables.
- **"Prove equivalence"**: the new generator is tested against the legacy generator's output (same random draws), so only
  the names changed.
- **"Never hard-code the headline number"**: € at risk and failure % flow from tables to the UI and the deck. Assumptions
  live in a table with their source.
- **"Fail loudly, render gracefully"**: backend tests pin Genie failure modes to an HTTP 200 with a readable message.

## Where the AI was wrong, and how it got caught
| Issue | Caught by | Fix |
|---|---|---|
| The first model reached only AUC 0.64: daily sensor noise of ±50% and a wear ramp shorter than the 30-day label horizon | local sanity run before writing notebooks | per-machine baseline + 10% noise, 30-day quadratic wear ramp → AUC 0.82 |
| Net price of €950 per 14-tablet pack (not credible: about €68 a tablet) | reviewing the value output | €450 (~€30/day of therapy), recorded as an editable assumption |
| Renaming the snapshot file truncated it before reading | quarantine/row-count check failed to load the file | re-snapshotted from untouched gold before publishing |
| Real names would have leaked through the rename map and tests | design review of what gets published | fingerprint (SHA-256) scanner; the rename map stays local; public history squashed |
| Genie `PATCH` is a full replace (a partial body wipes the space) | earlier incident, kept in memory | patch script always sends GET → modify → full body, and asserts the content count after |
| The train/test split had no embargo (train labels saw June failures), so the AUC was slightly optimistic | final code review (fresh reviewer subagent) | `time_split` with a 30-day embargo, test-first; AUC 0.82 → 0.81 |
| Isotonic calibration saturated the hero machine at p = 1.00 (overconfident on a slide) | reviewing the scores after the retrain | sigmoid calibration: same AUC, coater 0.90 |
| The value table added a one-time launch amount into an "annual" total | final code review | `value_type` column: one-time per launch vs recurring; year-one framing everywhere |
| The serving sync would empty the app's board if a source query returned 0 rows | final code review | refuse to prune on an empty source (test-first) + a non-empty guard before publishing gold |
| A phase-out product showed three false "blocking" gates (flags 0.9 < 1) | visual review of the app | gate blocks below 0.5; 0.5–0.99 shows as partial |

## Verified by hand
Visual click-through of the hero flow (board → Escalate → tracked), reading every Genie transcript, reading the AI brief, and
checking the value table against the formulas.
