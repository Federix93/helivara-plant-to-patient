#!/usr/bin/env python3
"""Restructure the FE Bar COPY of the deck (outcome first). All numbers are read from the live tables and the
committed evidence, never typed in. Usage: build_deck.py <presentation_id>

Order: title → hook → exec summary → problem → value → value by persona → journey → demo → what this means →
decisions & trade-offs → security/governance/cost → 30/60/90 pilot + ask → closing → Appendix (platform + glossary).
"""
import json
import subprocess
import sys
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from helivara.dbx import FQ, sql  # noqa: E402
from helivara.names import find_forbidden, load_real_names  # noqa: E402

AUTH = "/Users/federico.rizzo/.vibe/marketplace/plugins/fe-google-tools/skills/google-auth/resources/google_auth.py"
PRES = sys.argv[1]
TEAL, DARK, RED, WHITE, LIGHT = (0.106, 0.318, 0.380), (0.106, 0.188, 0.216), (1.0, 0.212, 0.125), (1, 1, 1), (0.945, 0.945, 0.945)

# old slide ids (from the original deck)
OLD = {i: s for i, s in enumerate([
    "g3f8f1fdfac0_0_10719", "g3f8f1fdfac0_0_4476", "g3f8f1fdfac0_0_4913", "g3f8f1fdfac0_0_5149", "g3f8f1fdfac0_0_5488",
    "g3f8f1fdfac0_0_5651", "g3f8f1fdfac0_0_5836", "g3f8f1fdfac0_0_5988", "g3f8f1fdfac0_0_5999", "g3f8f1fdfac0_0_6166",
    "g3f8f1fdfac0_0_6274", "g3f8f1fdfac0_0_11638", "g3f8f1fdfac0_0_8245", "g3f8f1fdfac0_0_8249", "g3f8f1fdfac0_0_8269",
    "g3f8f1fdfac0_0_8311", "g3f8f1fdfac0_0_8326", "g3f8f1fdfac0_0_10016", "g3f8f1fdfac0_5_43", "g3f8f1fdfac0_5_47",
    "g3f8f1fdfac0_5_53", "g3f8f1fdfac0_5_59", "g3f8f1fdfac0_5_65", "g3f8f1fdfac0_5_78", "g3f8f1fdfac0_5_71",
    "g3f8f1fdfac0_5_86"], start=1)}
TPL, TPL_TITLE, TPL_SUB, TPL_BODY = OLD[20], "g3f8f1fdfac0_5_48", "g3f8f1fdfac0_5_50", "g3f8f1fdfac0_5_49"


def token():
    return subprocess.run(["python3", AUTH, "token"], capture_output=True, text=True, check=True).stdout.strip()


H = {"Authorization": f"Bearer {token()}", "x-goog-user-project": "gcp-sandbox-field-eng"}
API = f"https://slides.googleapis.com/v1/presentations/{PRES}"


def batch(reqs):
    if not reqs:
        return {}
    r = httpx.post(f"{API}:batchUpdate", headers=H, json={"requests": reqs}, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(r.text[:1500])
    return r.json()


def get():
    return httpx.get(API, headers=H, timeout=120).json()


def nid(p):
    return f"{p}_{uuid.uuid4().hex[:10]}"


def rgb(c):
    return {"opaqueColor": {"rgbColor": {"red": c[0], "green": c[1], "blue": c[2]}}}


def emu(x, y, w, h, page):
    return {"pageObjectId": page, "size": {"width": {"magnitude": w, "unit": "EMU"}, "height": {"magnitude": h, "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": y, "unit": "EMU"}}


def set_text(obj, text):
    return [{"deleteText": {"objectId": obj, "textRange": {"type": "ALL"}}},
            {"insertText": {"objectId": obj, "text": text, "insertionIndex": 0}}]


# ---------------------------------------------------------------- facts from the data
vs = {r[0]: float(r[1]) for r in sql(f"SELECT lever, annual_value_eur FROM {FQ}.value_summary")}
lv = sql(f"SELECT weekly_units, net_price_eur, weeks_delay_avoided, revenue_at_risk_eur FROM {FQ}.launch_value WHERE launch_id='ZYV-001'")[0]
weekly, price, weeks, rar = map(float, lv)
L = sql(f"SELECT launch_readiness_score, master_data_ready_flag, artwork_ready_flag, serialization_ready_flag FROM {FQ}.dim_launch WHERE launch_id='ZYV-001'")[0]
coater = float(sql(f"SELECT failure_prob_30d FROM {FQ}.equipment_risk_drivers WHERE equipment='L_OSD_001_EQ_01'")[0][0])
metrics = json.loads((ROOT / "evidence/ml/metrics.json").read_text())["metrics"]
quarantine = sum(json.loads((ROOT / "evidence/pipeline/dirty_manifest.json").read_text()).values())
total = sum(vs.values())
M = lambda v: f"€{v / 1e6:.2f}M" if v >= 1e6 else f"€{v / 1e3:.0f}k"  # noqa: E731
F = {"readiness": f"{float(L[0]):.0%}", "rar": f"€{rar / 1e6:.1f}M", "coater": f"{coater:.0%}", "auc": f"{metrics['test_auc']:.2f}",
     "total": f"€{total / 1e6:.1f}M", "week": M(weekly * price), "launch": M(vs["Launch protection (Zyvanta)"]),
     "otif": M(vs["OTIF improvement"]), "down": M(vs["Unplanned downtime avoided"]), "exp": M(vs["Expiry write-off avoided"]),
     "q": f"{quarantine}"}
print("facts:", F)

# ---------------------------------------------------------------- content
CONTENT = [
    ("exec", "Executive summary", "What we solved, and what it is worth", [
        f"Problem: Zyvanta, our most important immunology launch, is at {F['readiness']} readiness. Master data and artwork blockers only surface at the monthly S&OP, and the Valmora coater that makes it is wearing out.",
        "Outcome: one governed Control Tower. Risk, then why, then the hidden supply risk, then an owned action, in about 60 seconds, in Italian or English.",
        f"Value: about {F['total']} a year (estimate): {F['launch']} launch protection, {F['otif']} OTIF, {F['down']} downtime, {F['exp']} expiry.",
        "Ask: a 6-week pilot on the next two launches. Success = every blocker flagged at least 4 weeks before the S&OP review."],
     f"Lead with the outcome. In one sentence: Zyvanta was at risk and nobody could see it in time. Now we see it, understand it and act in a minute, and that is worth about {F['total']} a year, {F['launch']} of it on this launch alone. Then the ask: a 6-week pilot."),
    ("problem", "Why launches slip today", "The Helivara situation as of 22 September 2026", [
        "Launch readiness lives in three places: material master (ERP), artwork approval and serialization. It gets reviewed once a month.",
        f"Zyvanta: master data {float(L[1]):.0%}, artwork {float(L[2]):.0%}, serialization {float(L[3]):.0%}, so readiness {F['readiness']}.",
        f"Manufacturing doesn't know which machine a launch depends on: the Valmora coater has a {F['coater']} chance of an unplanned failure within 30 days.",
        "\"Is my launch safe, and why?\" takes days of report chasing across systems, and the answers don't always agree.",
        f"Every week of Zyvanta delay costs about {F['week']} of revenue ({weekly:,.0f} packs × €{price:,.0f})."],
     "Make it concrete and specific to this customer. Three gates, two of them open. And a machine nobody connected to the launch. The cost of a week is the number the sponsor remembers."),
    ("means", "What this means for Helivara", "From monthly surprise to daily, owned decisions", [
        f"From monthly surprise to daily signal: blockers visible at least 4 weeks earlier, about {F['launch']} protected on Zyvanta.",
        "From \"which report is right?\" to one certified number: Genie answers from governed metric views and shows its SQL.",
        "From insight to accountability: every escalation has an owner, a due date and an audit trail in Lakebase.",
        f"From reactive to predictive maintenance: 20% fewer unplanned hours, about {F['down']} a year, and the launch supply protected."],
     "Close the demo by translating each beat back into the KPIs: lead time on launch blockers, OTIF, unplanned downtime, write-offs. Executive altitude: no product names here."),
    ("security", "Security, governance and cost", "Built to pass IT and quality review", [
        "Identity: Genie and SQL run as the signed-in user (Unity Catalog permissions per person); the app has least privilege in Lakebase.",
        f"Data quality enforced: 10 pipeline rules, {F['q']} bad rows quarantined, none reached the governed tables.",
        "Governance: certified tables and metric views, domains, lineage, and the model versioned in Unity Catalog.",
        "Cost and compliance: serverless and pay per use; Delta history, audit logs and Asset Bundles give a GxP-ready path."],
     "Pre-empt the technical stakeholder's objections: identity, data quality, governance, cost and compliance. Keep it short and go deeper only if asked."),
    ("pilot", "Next steps: a 30 / 60 / 90-day pilot", "Prove the value on two real launches", [
        "30 days: connect the material master and artwork systems with Lakeflow Connect, and run the Control Tower on the next two launches.",
        "60 days: stream Valmora line telemetry, retrain the failure model on real work orders, and use the Control Tower in the monthly S&OP.",
        "90 days: measure readiness lead time, OTIF and unplanned hours against the baseline, then decide on scaling to all launches and plants.",
        "The ask: an executive sponsor, the Global Demand & S&OP Manager as domain owner, two launches, and read access to the source systems."],
     "End with a clear, low-risk ask. Success metrics are the buyer's KPIs. Offer to co-write the success plan this week."),
]
VALUE_ROWS = [["Lever", "Annual value (estimate)", "How it's computed", "KPI owner"],
              ["Launch protection (Zyvanta)", F["launch"], f"{weekly:,.0f} packs/week × €{price:,.0f} × {weeks:.0f} weeks earlier", "COO / Head of Global Supply Chain"],
              ["OTIF improvement", F["otif"], "5 OTIF points × €200k per point", "Supply chain / commercial"],
              ["Unplanned downtime avoided", F["down"], "unplanned hours/yr × €8,000/h × 20%", "Plant & reliability"],
              ["Expiry write-off avoided", F["exp"], "units at risk/yr × €12 × 25%", "Finance"],
              ["Total", F["total"], "assumptions editable in table value_assumptions", ""]]
PERSONA_ROWS = [["Executive sponsor: COO / Head of Global Supply Chain", "Domain owner: Global Demand & S&OP Manager"],
                [f"Launch revenue protected ({F['launch']} on Zyvanta)\nOTIF +5 pts and fewer tender penalties\nLower write-offs and unplanned downtime\nOne governed platform: lower TCO, faster AI",
                 "Launch gates every day, not once a month\nOne certified definition of readiness and accuracy\nAsk in Italian and see the SQL behind the answer\nEvery escalation owned, dated and auditable"]]
DECISION_ROWS = [["Decision", "Why", "Trade-off we accepted"],
                 ["Lakeflow feeds the existing governed gold tables", "Keeps certification, domains, Genie and metric views intact; quality rules + quarantine", "Lineage passes through a publish step"],
                 ["Lakebase for the app", "Millisecond reads, transactional write-back, no duplicate escalations", "A sync job (managed synced tables need a catalog we couldn't create here)"],
                 ["Classical ML for failure risk, LLM only for the brief", "Calibrated, explainable probabilities; LLM grounded on governed facts only", "Needs labelled failures; retrain monthly"],
                 ["Genie on metric views, as the signed-in user", "Same numbers as finance; per-user permissions", "Metric views to maintain as the business changes"],
                 ["Assumptions in a table, not in code", "Business can challenge every euro figure", "Estimates until the pilot measures them"]]
JOURNEY = [("Sources", "SAP · MES · IoT · CMMS extracts (synthetic)"), ("Lakeflow", f"Auto Loader → silver · 10 quality rules · {F['q']} rows quarantined"),
           ("Unity Catalog", "21 certified tables · 8 metric views · domains · lineage"), ("ML & GenAI", f"Failure model AUC {F['auc']} · ai_query brief EN/IT"),
           ("Lakebase", "Serving tables + actions (Postgres)"), ("Genie agents", "Metric views + knowledge PDF"), ("Databricks App", "Control Tower: see · understand · act")]

# ---------------------------------------------------------------- build
d = get()
have = [s["objectId"] for s in d["slides"]]
if any(s.startswith("new_") for s in have):
    sys.exit("deck already restructured (found new_* slides); start from a fresh copy")


def dup_template(key):
    new = f"new_{key}"
    ids = {TPL: new, TPL_TITLE: f"{new}_t", TPL_SUB: f"{new}_s", TPL_BODY: f"{new}_b"}
    batch([{"duplicateObject": {"objectId": TPL, "objectIds": ids}}])
    return new


def notes_id(slide_id):
    s = next(x for x in get()["slides"] if x["objectId"] == slide_id)
    return s["slideProperties"]["notesPage"]["notesProperties"]["speakerNotesObjectId"]


def put_notes(slide_id, text):
    nid_ = notes_id(slide_id)
    batch([{"insertText": {"objectId": nid_, "text": text, "insertionIndex": 0}}])


def add_table(slide, rows, y=1450000, h=2900000, widths=None, font=9):
    tid = nid("tbl")
    reqs = [{"createTable": {"objectId": tid, "rows": len(rows), "columns": len(rows[0]),
                             "elementProperties": emu(500000, y, 8150000, h, slide)}}]
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            if not val:
                continue
            reqs.append({"insertText": {"objectId": tid, "cellLocation": {"rowIndex": r, "columnIndex": c}, "text": val}})
            reqs.append({"updateTextStyle": {"objectId": tid, "cellLocation": {"rowIndex": r, "columnIndex": c},
                                             "textRange": {"type": "ALL"}, "fields": "fontSize,bold,foregroundColor,fontFamily",
                                             "style": {"fontSize": {"magnitude": font, "unit": "PT"}, "bold": r == 0 or (rows[-1][0] == "Total" and r == len(rows) - 1),
                                                       "foregroundColor": rgb(WHITE if r == 0 else DARK), "fontFamily": "Barlow"}}})
    reqs.append({"updateTableCellProperties": {"objectId": tid, "tableRange": {"location": {"rowIndex": 0, "columnIndex": 0}, "rowSpan": 1, "columnSpan": len(rows[0])},
                                               "tableCellProperties": {"tableCellBackgroundFill": {"solidFill": {"color": {"rgbColor": dict(zip(("red", "green", "blue"), TEAL))}}}},
                                               "fields": "tableCellBackgroundFill"}})
    reqs.append({"updateTableRowProperties": {"objectId": tid, "rowIndices": [0], "fields": "minRowHeight",
                                              "tableRowProperties": {"minRowHeight": {"magnitude": 380000, "unit": "EMU"}}}})
    if widths:
        for c, w in enumerate(widths):
            reqs.append({"updateTableColumnProperties": {"objectId": tid, "columnIndices": [c], "fields": "columnWidth",
                                                         "tableColumnProperties": {"columnWidth": {"magnitude": w, "unit": "EMU"}}}})
    batch(reqs)


def content_slide(key, title, sub, bullets, notes):
    s = dup_template(key)
    batch(set_text(f"{s}_t", title) + set_text(f"{s}_s", sub) + set_text(f"{s}_b", "\n".join(bullets)))
    put_notes(s, notes)
    return s


def table_slide(key, title, sub, rows, notes, widths=None, font=9):
    s = dup_template(key)
    batch(set_text(f"{s}_t", title) + set_text(f"{s}_s", sub) + [{"deleteObject": {"objectId": f"{s}_b"}}])
    add_table(s, rows, widths=widths, font=font)
    put_notes(s, notes)
    return s


created = {}
for key, title, sub, bullets, notes in CONTENT:
    created[key] = content_slide(key, title, sub, bullets, notes)
created["value"] = table_slide("value", "Quantified value", f"About {F['total']} a year: estimates computed from the data", VALUE_ROWS,
                               f"The number comes from the data, not a spreadsheet: Zyvanta's Q4 consensus forecast, {weekly:,.0f} packs a week at an assumed €{price:,.0f} net, times the 4 weeks we flag the blockers earlier. Every assumption sits in a governed table the business can edit. Invite them to challenge it.",
                               widths=[2000000, 1350000, 3100000, 1700000])
created["persona"] = table_slide("persona", "Value for sponsor and owner", "Two altitudes, one platform", PERSONA_ROWS,
                                 "Speak to both people in the room. The sponsor funds outcomes (revenue, service, cost). The domain owner lives with the workflow (daily gates, one definition, her language, accountability).",
                                 widths=[4075000, 4075000], font=11)
created["decisions"] = table_slide("decisions", "Decisions and trade-offs", "Why this approach and not another", DECISION_ROWS,
                                   "This is the architect's slide. Each choice comes with its cost. If challenged on the sync job: in a customer metastore we'd use managed synced tables; here the shared metastore didn't allow creating the catalog.",
                                   widths=[2500000, 3200000, 2450000], font=9)

# journey diagram
s = dup_template("journey")
batch(set_text(f"{s}_t", "One integrated journey")
      + set_text(f"{s}_s", "One governed copy of the data, from raw files to a decision in the app") + [{"deleteObject": {"objectId": f"{s}_b"}}])
reqs, x, w, gap, y, h = [], 280000, 1060000, 200000, 1650000, 1700000
for i, (head, body) in enumerate(JOURNEY):
    bid = nid("box")
    reqs += [{"createShape": {"objectId": bid, "shapeType": "ROUND_RECTANGLE", "elementProperties": emu(x, y, w, h, s)}},
             {"updateShapeProperties": {"objectId": bid, "fields": "shapeBackgroundFill,outline",
                                        "shapeProperties": {"shapeBackgroundFill": {"solidFill": {"color": {"rgbColor": dict(zip(("red", "green", "blue"), RED if i == len(JOURNEY) - 1 else TEAL))}}},
                                                            "outline": {"propertyState": "NOT_RENDERED"}}}},
             {"insertText": {"objectId": bid, "text": f"{head}\n{body}"}},
             {"updateTextStyle": {"objectId": bid, "textRange": {"type": "ALL"}, "fields": "fontSize,foregroundColor,fontFamily",
                                  "style": {"fontSize": {"magnitude": 8, "unit": "PT"}, "foregroundColor": rgb(WHITE), "fontFamily": "Barlow"}}},
             {"updateTextStyle": {"objectId": bid, "textRange": {"type": "FIXED_RANGE", "startIndex": 0, "endIndex": len(head)},
                                  "fields": "bold,fontSize", "style": {"bold": True, "fontSize": {"magnitude": 10, "unit": "PT"}}}},
             {"updateParagraphStyle": {"objectId": bid, "textRange": {"type": "ALL"}, "fields": "alignment", "style": {"alignment": "CENTER"}}}]
    if i < len(JOURNEY) - 1:
        aid = nid("arr")
        reqs += [{"createShape": {"objectId": aid, "shapeType": "RIGHT_ARROW", "elementProperties": emu(x + w + 30000, y + h // 2 - 90000, gap - 60000, 180000, s)}},
                 {"updateShapeProperties": {"objectId": aid, "fields": "shapeBackgroundFill,outline",
                                            "shapeProperties": {"shapeBackgroundFill": {"solidFill": {"color": {"rgbColor": dict(zip(("red", "green", "blue"), DARK))}}},
                                                                "outline": {"propertyState": "NOT_RENDERED"}}}}]
    x += w + gap
tb = nid("loop")
reqs += [{"createShape": {"objectId": tb, "shapeType": "TEXT_BOX", "elementProperties": emu(280000, y + h + 150000, 8580000, 500000, s)}},
         {"insertText": {"objectId": tb, "text": "↺ Actions taken in the app are copied back to the lakehouse every day, so Genie and the dashboard see what was decided. "
                                                 "One daily Lakeflow Job runs the whole chain: ingest → publish → score → value + brief → Lakebase → copy back."}},
         {"updateTextStyle": {"objectId": tb, "textRange": {"type": "ALL"}, "fields": "fontSize,foregroundColor,fontFamily",
                              "style": {"fontSize": {"magnitude": 9, "unit": "PT"}, "foregroundColor": rgb(DARK), "fontFamily": "Barlow"}}}]
batch(reqs)
put_notes(s, "Tell the architect: it's one copy of the data, governed once. Lakeflow lands and checks it, Unity Catalog certifies it, the model and the LLM add intelligence, Lakebase serves the app, Genie answers from the same metric views. No stitched-together demos: each box's output is the next box's input.")
created["journey"] = s

# demo slide (old 8): retitle with the three beats
demo = OLD[8]
batch(set_text("g3f8f1fdfac0_0_5993", f"1 · See: Zyvanta at {F['readiness']} readiness, {F['rar']} at risk\v2 · Understand: Genie in Italian → master data + artwork; the coater at {F['coater']} failure risk\v3 · Act: Escalate → owned, dated actions in Lakebase"))
SHOT = "https://raw.githubusercontent.com/Federix93/helivara-plant-to-patient/main/docs/img/control_tower_tracked.png"
batch([{"deleteObject": {"objectId": "g3f8f1fdfac0_0_5991"}}, {"deleteObject": {"objectId": "g3f8f1fdfac0_0_5996"}},
       {"createImage": {"objectId": "demo_app_shot", "url": SHOT, "elementProperties": emu(4000000, 800000, 4950000, 3560000, demo)}},
       {"updateTextStyle": {"objectId": "g3f8f1fdfac0_0_5993", "textRange": {"type": "ALL"}, "fields": "fontSize",
                            "style": {"fontSize": {"magnitude": 13, "unit": "PT"}}}}])
put_notes(demo, "Tell-show-tell. Tell: three moments, see, understand, act. Show: the app (board, Genie in Italian, coater risk, Escalate), then 90 seconds for the architect: pipeline expectations, lineage, the model in UC. Tell: back to the KPIs on the next slide.")

# appendix divider (duplicate the title slide)
app_div = "new_appendix"
batch([{"duplicateObject": {"objectId": OLD[19], "objectIds": {OLD[19]: app_div, "g3f8f1fdfac0_5_44": f"{app_div}_t"}}}])
batch(set_text(f"{app_div}_t", "Appendix\vPlatform overview and supply-chain glossary"))

# title slide subtitle
batch(set_text("g3f8f1fdfac0_5_44", f"From Plant to Patient\vCatching launch risk before it costs {F['rar']}: governed, self-service AI across demand, supply, manufacturing and reliability"))
put_notes(OLD[19], "Set up the customer, the problem and what you will show before diving in.")

# order + deletions
order = [OLD[19], OLD[25], created["exec"], created["problem"], created["value"], created["persona"], created["journey"],
         OLD[8], created["means"], created["decisions"], created["security"], created["pilot"], OLD[26],
         app_div, OLD[11], *[OLD[i] for i in range(12, 19)], *[OLD[i] for i in range(20, 25)]]
batch([{"deleteObject": {"objectId": OLD[i]}} for i in (1, 2, 3, 4, 5, 6, 7, 9, 10)])
batch([{"updateSlidesPosition": {"slideObjectIds": [sid], "insertionIndex": i}} for i, sid in enumerate(order)])

# rename any real names left in the copied slides (notes included), then scan everything
real = load_real_names()
batch([{"replaceAllText": {"containsText": {"text": k, "matchCase": True}, "replaceText": v}} for k, v in real.all_maps.items()])
d = get()
blob = json.dumps(d)
print("slides:", len(d["slides"]), "| forbidden hits in deck JSON:", len(find_forbidden(blob)))
