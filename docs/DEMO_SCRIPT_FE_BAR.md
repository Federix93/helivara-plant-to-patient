# FE Bar roleplay: demo script and objection bank

**Audience:** the business stakeholder (executive sponsor, e.g. COO / Head of Global Supply Chain) and the technical
stakeholder (enterprise data architect). About 10 minutes of presenting, then Q&A.
**Before you start:** run `uv run python setup/reset_demo.py` (clears the actions), open the app and the deck, and ask Genie
one question to warm it up (the first answer can take 20–30 s).
**App:** https://helivara-control-tower-7474648220918581.aws.databricksapps.com · numbers as of the demo date, 22 Sep 2026.

## 0 · Setup (60 s) · deck slides 1–4
> "Thank you both for the time. Helivara launches two or three products a year, and right now its most important immunology
> launch, **Zyvanta**, is at risk. The data exists. The problem is that nobody sees the blockers until the monthly S&OP review,
> and every week of delay costs about **€2 million** in revenue. Today I'll show you how your Global Demand & S&OP Manager finds
> that risk in seconds, understands why, discovers a manufacturing risk nobody had connected to it, and acts, all on one
> governed platform. Then we'll put a number on it: about **€9.7 million a year**."

(Slide 3, executive summary: say the outcome and the ask in one breath. Slide 4: the three gates; two of them are open.)

## 1 · Tell (20 s) · slide 5–7 (value, persona, journey), then slide 8
> "Three moments: **see** the risk, **understand** it, **act** on it. Then I'll take 90 seconds for [architect's name] on how it's
> built and governed."

## 2 · Show (5–6 min) · the app

1. **See:** the launch board.
   > "This is the Control Tower. Zyvanta: **33% readiness, €7.9M at risk**. Master data and artwork are red, serialization is
   > green. This screen reads from Lakebase, our operational database, so it loads instantly for hundreds of planners."
2. **Understand:** Genie, in Italian. Click *"Perché Zyvanta è a rischio?"*
   > "Your teams can ask in their own language. Genie answers *master data and artwork*, and here's the SQL it used. It
   > queries the certified metric views, the same definition finance and the dashboards use, so there's no second version
   > of the truth."
3. **The hidden risk:** the red box on the card.
   > "Here's what nobody had connected: the coater on line L_OSD_001 at **Valmora**, the line that coats Zyvanta, has a **94%
   > probability of an unplanned failure in the next 30 days**. That comes from a predictive-maintenance model trained on the
   > machine's telemetry. So even if we fix the paperwork, supply is at risk."
   (Optional: open the *AI action brief*, switch to IT. "Generated from governed facts only. It's advice, not a decision.")
4. **Act:** click **Escalate**, then **Confirm 3 actions**.
   > "One click turns the insight into owned decisions: master data to the Master Data Lead, artwork to Regulatory, preventive
   > maintenance to the site. Each has a due date, and they're stored in Lakebase with an audit trail. Click again and nothing
   > gets duplicated." (The board shows *3 actions tracked*; Open actions = 3.)
5. **For the architect (90 s):** switch to the workspace.
   - The Lakeflow pipeline graph: bronze → silver with **10 data-quality rules**; **518 bad rows quarantined** that never reached gold.
   - Unity Catalog lineage: raw Volume files → bronze → silver → certified gold → metric views, plus the model
     `equipment_failure_model@champion` with its AUC of 0.82.
   - The daily Lakeflow Job: ingest → publish → score → value + brief → Lakebase → copy-back, all serverless.
   > "One copy of the data, governed once, and every stage feeds the next. Genie and the app run with each user's
   > permissions."
6. **Close the loop (optional):** in Genie, ask *"Which actions are open on our launches?"* After the daily job runs, Genie sees
   the decisions too.

## 3 · Tell (45 s) · slides 9 and 12
> "So what does this mean for Helivara? The blockers become visible about **four weeks earlier**, which protects roughly
> **€7.85 million on this launch alone**. Add OTIF, unplanned downtime and expiry write-offs and it comes to about
> **€9.7 million a year**. Every assumption is in a table your team can challenge. What I'd propose is a **six-week pilot on
> your next two launches**: success means every blocker is flagged at least four weeks before S&OP. Can we agree on a sponsor
> and the two launches this week?"

## 4 · If something is slow or breaks (60-second fallback)
- **Genie is slow:** "While it thinks: it's generating SQL against the certified views. Here's the answer from a minute ago"
  (show `evidence/genie/transcripts.md` or the screenshot on slide 8).
- **The app doesn't load:** use slide 8's screenshot and the dashboard *Helivara Plant-to-Patient Control Tower*.
- Never apologise more than once. Bring it back to the outcome.

---

## Objection bank

### Business stakeholder (cost, risk, time to value)
| Objection | Answer (executive altitude) |
|---|---|
| "We already have SAP IBP / a planning tool." | "Keep it. This doesn't replace planning; it reads from it and adds what IBP doesn't have: launch-gate governance across systems, predictive maintenance and natural-language answers. The pilot runs alongside it." |
| "What does it cost?" | "It's serverless and pay-per-use, and Lakebase scales to zero. The pilot costs less than one week of Zyvanta delay (about €2M of revenue). We'll size the run cost with you in week one." |
| "Are these numbers real?" | "They're estimates from the data with editable assumptions, and the pilot measures them. The biggest lever is simple: forecast packs × net price × weeks earlier." |
| "What's the risk?" | "It reads from your systems and writes only to its own actions table. No change to SAP. Data quality rules stop bad data before anyone sees it." |
| "How long until value?" | "Six weeks, on data you already have. Week 1–2: connect master data and artwork; week 3–4: the two launches live; week 5–6: measure." |
| "Will people use it?" | "It answers in Italian, inside one screen, with an action button. The S&OP Manager owns it; it replaces the report chasing, it isn't one more tool." |
| "Can AI be trusted for GxP decisions?" | "AI recommends, people decide. Every number traces back to a certified table, and every action has an owner and an audit trail." |

### Technical stakeholder (architecture, data quality, security, integration)
| Objection | Answer (with detail) |
|---|---|
| "How do you integrate SAP?" | "Lakeflow Connect or SAP Business Data Cloud for production; here we simulate extracts in a Volume. Auto Loader picks up new files incrementally." |
| "How do you guarantee data quality?" | "Pipeline expectations drop bad rows into `*_quarantine` with the failed rule (518 rows today), a schema contract checks gold, and metric views define each KPI once." |
| "Security / who sees what?" | "Unity Catalog governs everything. In the app, Genie and SQL run on behalf of the signed-in user, so row filters and grants apply. The app's service principal only has SELECT on serving tables and INSERT on actions in Lakebase." |
| "Why Lakebase and not the warehouse?" | "The app needs millisecond reads and transactional writes with constraints (one open action per launch and type). Lakebase is managed Postgres next to the lakehouse; a job keeps it in sync, and in your metastore we'd use managed synced tables." |
| "How accurate is Genie?" | "It's grounded on certified metric views and instructions, shows its SQL, and we keep a golden-question set (15 Q&A in the repo) as a regression test." |
| "Model drift / MLOps?" | "MLflow tracking, Unity Catalog registry with a champion alias set only if AUC ≥ 0.75, monthly retraining, and Lakehouse Monitoring on the scores in production." |
| "CI/CD and environments?" | "Everything is a Databricks Asset Bundle (pipeline, jobs, app): dev → prod targets, `bundle validate` and the test suite in CI." |
| "Lock-in?" | "Open formats (Delta/Iceberg), standard Postgres, standard Python, sklearn and MLflow. The code and data are yours." |
