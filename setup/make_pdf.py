#!/usr/bin/env python3
"""Generate the Helivara Genie knowledge / grounding document as a styled PDF."""
# requires: pip install fpdf2 (Arial TTFs from macOS /System/Library/Fonts/Supplemental)
from fpdf import FPDF

from pathlib import Path
OUT = str(Path(__file__).resolve().parents[1] / "docs" / "knowledge" / "Helivara_Genie_Knowledge.pdf")
Path(OUT).parent.mkdir(parents=True, exist_ok=True)
FONT_DIR = "/System/Library/Fonts/Supplemental"

# Databricks-ish palette
TEAL = (27, 81, 97)       # headings
DARK = (27, 48, 55)       # body
RED  = (255, 54, 32)      # accents
MUTED= (97, 135, 147)     # captions
LGREY= (241, 241, 241)    # table zebra / callout bg
BORDER=(200, 210, 214)

class PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Arial", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 8, "Helivara Supply Chain - Genie Knowledge Document", align="L")
        self.cell(0, 8, "Synthetic demo - not a real company", align="R")
        self.ln(10)

    def footer(self):
        self.set_y(-14)
        self.set_font("Arial", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")

pdf = PDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=18)
pdf.set_margins(20, 18, 20)
pdf.add_font("Arial", "", f"{FONT_DIR}/Arial.ttf")
pdf.add_font("Arial", "B", f"{FONT_DIR}/Arial Bold.ttf")
pdf.add_font("Arial", "I", f"{FONT_DIR}/Arial Italic.ttf")
EPW = pdf.epw  # effective page width

def h1(t):
    pdf.set_font("Arial", "B", 15); pdf.set_text_color(*TEAL)
    pdf.ln(2); pdf.multi_cell(0, 7, t); pdf.set_draw_color(*RED)
    pdf.set_line_width(0.6); y=pdf.get_y(); pdf.line(pdf.l_margin, y, pdf.l_margin+18, y)
    pdf.ln(3)

def h2(t):
    pdf.set_font("Arial", "B", 11.5); pdf.set_text_color(*DARK)
    pdf.ln(1.5); pdf.multi_cell(0, 6, t); pdf.ln(0.5)

def body(t):
    pdf.set_font("Arial", "", 10); pdf.set_text_color(*DARK)
    pdf.multi_cell(0, 5.2, t); pdf.ln(1)

def bullet(t, label=None):
    pdf.set_font("Arial", "", 10); pdf.set_text_color(*DARK)
    x = pdf.get_x()
    pdf.set_text_color(*RED); pdf.cell(5, 5.2, chr(0x2022))
    pdf.set_text_color(*DARK)
    if label:
        pdf.set_font("Arial", "B", 10); pdf.cell(pdf.get_string_width(label+"  "), 5.2, label)
        pdf.set_font("Arial", "", 10)
    pdf.set_x(x+5)
    pdf.multi_cell(0, 5.2, (label+"  " if label else "")+t if False else t)
    # re-render cleanly (label handled inline above)

def bullet2(label, t):
    """Bullet with a bold lead-in label then normal text."""
    pdf.set_font("Arial", "", 10); pdf.set_text_color(*DARK)
    x0 = pdf.l_margin
    pdf.set_x(x0)
    pdf.set_text_color(*RED); pdf.cell(5, 5.2, chr(0x2022)); pdf.set_text_color(*DARK)
    seg = []
    if label:
        seg.append(("B", label+": "))
    seg.append(("", t))
    # simple wrap: use write() with indent handled via left margin bump
    pdf.set_left_margin(x0+5); pdf.set_x(x0+5)
    for style, s in seg:
        pdf.set_font("Arial", style, 10)
        pdf.write(5.2, s)
    pdf.ln(5.2)
    pdf.set_left_margin(x0); pdf.set_x(x0)

def callout(title, lines):
    pdf.ln(1)
    pad = 3; inner = EPW-2*pad-4; lh_t = 5.4; lh = 4.9
    # 1) measure height up front (no drawing)
    pdf.set_font("Arial", "B", 10.5)
    th = len(pdf.multi_cell(inner, lh_t, title, dry_run=True, output="LINES")) * lh_t
    pdf.set_font("Arial", "", 9.5)
    bh = sum(len(pdf.multi_cell(inner, lh, ln, dry_run=True, output="LINES")) * lh for ln in lines)
    total = pad + th + bh + pad
    # 2) keep the whole box on one page
    if pdf.get_y() + total > pdf.h - pdf.b_margin:
        pdf.add_page()
    x0, y0 = pdf.l_margin, pdf.get_y()
    # 3) draw the box, then the text (auto-break off so nothing splits)
    prev_auto = pdf.auto_page_break
    pdf.set_auto_page_break(False)
    pdf.set_draw_color(*RED); pdf.set_line_width(0.4)
    pdf.rect(x0, y0, EPW, total, style="D")
    pdf.set_fill_color(*RED); pdf.rect(x0, y0, 1.6, total, style="F")
    pdf.set_xy(x0+pad+2, y0+pad)
    pdf.set_font("Arial", "B", 10.5); pdf.set_text_color(*RED)
    pdf.multi_cell(inner, lh_t, title)
    pdf.set_text_color(*DARK); pdf.set_font("Arial", "", 9.5)
    for ln in lines:
        pdf.set_x(x0+pad+2); pdf.multi_cell(inner, lh, ln)
    pdf.set_auto_page_break(prev_auto, margin=pdf.b_margin)
    pdf.set_xy(x0, y0+total+2)

def table(headers, rows, widths):
    scale = EPW/sum(widths); widths=[w*scale for w in widths]
    pdf.set_font("Arial", "B", 8.6); pdf.set_fill_color(*TEAL); pdf.set_text_color(255,255,255)
    pdf.set_draw_color(*BORDER); pdf.set_line_width(0.2)
    for h,w in zip(headers,widths): pdf.cell(w, 6.6, " "+h, border=0, fill=True)
    pdf.ln()
    pdf.set_font("Arial", "", 8.4); pdf.set_text_color(*DARK)
    for i,row in enumerate(rows):
        fill = (i%2==1)
        pdf.set_fill_color(*(LGREY if fill else (255,255,255)))
        # compute row height by wrapping
        line_h=4.4
        heights=[]
        for c,w in zip(row,widths):
            n=max(1, pdf.multi_cell(w-2, line_h, str(c), dry_run=True, output="LINES").__len__())
            heights.append(n)
        rh=max(heights)*line_h+1.4
        x0=pdf.get_x(); y0=pdf.get_y()
        if y0+rh > pdf.h - pdf.b_margin:
            pdf.add_page(); y0=pdf.get_y()
            # repeat header
            pdf.set_font("Arial","B",8.6); pdf.set_fill_color(*TEAL); pdf.set_text_color(255,255,255)
            for h,w in zip(headers,widths): pdf.cell(w,6.6," "+h,border=0,fill=True)
            pdf.ln(); y0=pdf.get_y()
            pdf.set_font("Arial","",8.4); pdf.set_text_color(*DARK); pdf.set_fill_color(*(LGREY if fill else (255,255,255)))
        x=x0
        for c,w in zip(row,widths):
            pdf.rect(x,y0,w,rh, style="DF")
            pdf.set_xy(x+1,y0+0.7)
            pdf.multi_cell(w-2, line_h, str(c), align="L")
            x+=w; pdf.set_xy(x,y0)
        pdf.set_xy(x0, y0+rh)
    pdf.ln(2)

# ---------------- COVER ----------------
pdf.add_page()
pdf.ln(30)
pdf.set_font("Arial", "B", 9); pdf.set_text_color(*RED)
pdf.cell(0, 6, "GENIE GROUNDING / KNOWLEDGE DOCUMENT")
pdf.ln(14)
pdf.set_font("Arial", "B", 30); pdf.set_text_color(*TEAL)
pdf.multi_cell(0, 12, "Helivara Supply Chain\n& Manufacturing")
pdf.ln(4)
pdf.set_font("Arial", "", 13); pdf.set_text_color(*DARK)
pdf.multi_cell(0, 6.5, "Reference context for the Genie conversational agents: portfolio, "
    "manufacturing network, governed metric views, and the demo's hero facts.")
pdf.ln(6)
pdf.set_draw_color(*RED); pdf.set_line_width(0.8)
pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin+40, pdf.get_y()); pdf.ln(8)
pdf.set_font("Arial", "I", 10); pdf.set_text_color(*MUTED)
pdf.multi_cell(0, 5.5, "Helivara is a FICTIONAL pharmaceutical company. All data is synthetic and "
    "generated for demonstration purposes; the business processes and reasoning are industry-realistic. "
    "Product brand names are used only as illustrative examples.")
pdf.ln(3)
pdf.set_font("Arial", "", 9.5); pdf.set_text_color(*DARK)
pdf.multi_cell(0, 5.2,
    "Platform: Databricks (Unity Catalog, Genie, AI/BI, Discover)\n"
    "Catalog / schema: fr_stable_catalog.supply_chain\n"
    "Demo anchor date (\"today\"): 2026-09-22\n"
    "Document version: 2026-11-09")

# ---------------- 1. OVERVIEW ----------------
pdf.add_page()
h1("1. Purpose & how to use this document")
body("This document is the shared knowledge base for Helivara's Genie agents. Attach it to a Genie "
     "space (or store it in a Unity Catalog Volume and reference it) so the assistant can ground its "
     "answers in consistent business context: what the products are, how the network is structured, "
     "which governed metrics to use, and which facts define the demo storyline.")
h2("The two Genie agents")
bullet2("Demand & Supply Agent", "S&OP, demand forecast accuracy and bias, launch readiness, "
        "order service (OTIF), inventory and expiry-at-risk.")
bullet2("Manufacturing & Reliability Agent", "OEE and its components, right-first-time and yield, "
        "quality deviations and CAPA, equipment reliability and predicted failures.")
h2("Answering rules for the assistant")
bullet2("Use the governed metric views", "prefer the mv_* views and wrap every metric in MEASURE(). "
        "Do not recompute metrics from raw fact tables when a metric view exists.")
bullet2("Cite the source", "name the metric view used in each answer.")
bullet2("Bilingual", "users may ask in Italian; answer in Italian when they do.")
bullet2("Always flag the launch at risk", "if a question touches launches or Zyvanta, surface that "
        "it is at risk and name the blocker (master data / artwork).")

# ---------------- 2. COMPANY & NETWORK ----------------
h1("2. Company & manufacturing network")
body("Helivara is a mid-size specialty + consumer-health pharmaceutical manufacturer. The demo models "
     "an end-to-end \"plant-to-patient\" flow: Demand & S&OP -> Supply & Inventory -> Manufacturing & "
     "Quality -> Reliability & Maintenance.")
h2("Plants (5)")
table(["Plant","Site type","Country","Role"],
    [["Valmora","OSD","Italy","Primary oral-solid-dose hub; Zyvanta coating & packaging"],
     ["Castelverde","API","Italy","Active ingredient (granulation / processing)"],
     ["Roccalba","OSD","Italy","Oral-solid-dose compression"],
     ["Riberal","OSD","Spain","Oral-solid-dose compression"],
     ["Ashbury Ridge","OSD","USA","Oral-solid-dose compression & packaging"]],
    [16,12,14,58])
h2("Markets & distribution")
body("Markets: Italy, Spain, EU, US, RoW (regions: Europe, Americas, Global). Each market is served by "
     "a distribution centre (DC_Italy, DC_Spain, DC_EU, DC_US, DC_RoW).")

# ---------------- 3. PORTFOLIO ----------------
h1("3. Product portfolio (11 brands)")
body("Four therapeutic clusters/BUs: Immunology, Gastroenterology (GI), Vascular, Consumer Health. "
     "Launch phase drives the storyline: one launch (Zyvanta), one phase-out (Oribex), the rest mature.")
table(["Brand","Therapeutic area","Cluster/BU","Phase","Notes"],
    [["Zyvanta","Immunology","Immunology","LAUNCH","Hero: launch AT RISK (see sec. 5)"],
     ["Oribex","Immunology","Immunology","phase-out","US sales = 0 after 2025-11"],
     ["Gastrelle","Gastroenterology","GI","mature",""],
     ["Colvera","Gastroenterology","GI","mature",""],
     ["Florabis","Gastroenterology","GI","mature","Short shelf life (12 mo)"],
     ["Lactavio","Gastroenterology","GI","mature",""],
     ["Refluxa","Gastroenterology","GI","mature",""],
     ["Venoria","Vascular","Vascular","mature",""],
     ["Faringel","Consumer Health","Consumer","mature","Serialization exempt"],
     ["Digestin","Consumer Health","Consumer","mature","Serialization exempt"],
     ["Citralux","Consumer Health","Consumer","mature","Serialization exempt"]],
    [26,30,18,16,40])

# ---------------- 4. METRIC VIEWS ----------------
h1("4. Governed metric views")
body("Eight Unity Catalog metric views define the certified business metrics. Query measures with "
     "MEASURE(<name>) and group by the listed dimensions. These are the assistant's preferred source.")
table(["Metric view","Key measures (use MEASURE())","Answers"],
    [["mv_demand","forecast_accuracy, forecast_bias, consensus_vs_statistical_gap",
      "Forecast accuracy & bias by therapeutic area, market, cluster/BU"],
     ["mv_launch_readiness","avg_launch_readiness, master_data_ready_rate, artwork_ready_rate, serialization_ready_rate",
      "Launch readiness and which gate is blocking"],
     ["mv_service","otif, total_stockout_days, total_backorder_qty",
      "On-time-in-full service by market / brand"],
     ["mv_inventory","avg_days_of_inventory, total_on_hand, total_expiry_at_risk",
      "Days of inventory and expiry-at-risk by DC / market"],
     ["mv_manufacturing","oee, availability, performance, quality, total_downtime_min",
      "OEE and its three components by plant / line / shift"],
     ["mv_production","rft_rate, avg_yield, schedule_adherence, batch_count",
      "Right-first-time, yield, schedule adherence by plant"],
     ["mv_quality","deviation_count, major_count, critical_count, capa_on_time_rate",
      "Deviations, severity and CAPA on-time by plant / root cause"],
     ["mv_reliability","unplanned_downtime_hours, mttr_min, total_maintenance_cost, wo_count",
      "Reliability, downtime and maintenance cost by equipment"]],
    [26,44,34])
body("Rule of thumb: OEE questions must report all three components (availability x performance x "
     "quality). Downtime cascades to supply: lower OEE -> schedule miss -> stockout -> lower OTIF "
     "(especially Zyvanta coating at Valmora).")

# ---------------- 5. HERO FACTS ----------------
h1("5. Hero facts (the demo storyline)")
callout("Zyvanta (immunology) - launch AT RISK",
    ["Overall launch readiness: 0.33 (lowest in the portfolio).",
     "Master data ready rate: 0%  -> BLOCKER (material master incomplete).",
     "Artwork ready rate: 0%  -> BLOCKER (artwork still in review).",
     "Serialization ready rate: 100%  -> this gate is NOT the problem.",
     "So: the launch is blocked by master data and artwork, NOT serialization.",
     "Manufacturing link: Zyvanta is coated & packaged at Valmora; OEE loss there",
     "puts the launch supply at further risk."])
callout("Oribex (immunology) - phase-out",
    ["Being phased out; US sales = 0 after 2025-11.",
     "Master data / artwork / serialization all complete (readiness ~0.9).",
     "Do not treat declining Oribex demand as a forecasting error - it is planned."])
body("Launch-readiness gates explained: a launch is 'ready' only when three governance gates pass - "
     "(1) material master data complete, (2) serialization status set, (3) artwork approved. Readiness "
     "is the average of the three, so a single failed gate materially lowers the score.")

# ---------------- 6. DOMAINS ----------------
h1("6. Discover domains")
body("The catalog is organised into four governed domains, each with two subdomains, used in the "
     "Databricks Discover experience.")
table(["Domain","Subdomains"],
    [["Demand and Sales Operations","Forecast; Consensus S&OP"],
     ["Supply and Inventory","Production Planning; Inventory and Service"],
     ["Manufacturing and Quality","Batch Execution and OEE; Quality and Deviations"],
     ["Reliability and Maintenance","Asset Telemetry; Maintenance and Downtime"]],
    [40,60])

# ---------------- 7. GLOSSARY ----------------
h1("7. Glossary of key terms")
gl = [
 ("S&OP","Sales & Operations Planning - the monthly cross-functional process aligning demand, supply and finance on one plan."),
 ("Forecast bias","Systematic over- or under-forecasting. Positive bias = over-forecast; near zero is healthy."),
 ("Forecast accuracy","How close the forecast was to actual sales (higher is better)."),
 ("Launch readiness","Composite gate score (master data + serialization + artwork) that says whether a new product can launch."),
 ("Master data","The governed product/material record (material master). Must be complete before launch."),
 ("Serialization","Unique-code marking of packs for anti-counterfeiting / track-and-trace (some consumer packs are exempt)."),
 ("Artwork","Approved packaging/label content; must be signed off before launch."),
 ("OTIF","On-Time-In-Full - orders delivered complete and on schedule."),
 ("Days of inventory (DIO)","How many days of demand current stock covers."),
 ("Expiry-at-risk","Stock likely to expire before it can be sold."),
 ("OEE","Overall Equipment Effectiveness = Availability x Performance x Quality."),
 ("RFT","Right First Time - share of batches produced correctly without rework."),
 ("Deviation / CAPA","A quality event and its Corrective And Preventive Action; on-time CAPA closure is a compliance KPI."),
 ("MTTR","Mean Time To Repair - average time to restore failed equipment."),
 ("Unplanned downtime","Equipment stoppage that was not scheduled - the costly kind."),
]
for term,defn in gl:
    bullet2(term, defn)

# ---------------- 8. OPERATIONAL LAYER ----------------
h1("8. Operational layer: predictions, value and actions")
bullet2("Failure risk (risk_score)", "fact_predicted_failure is scored daily by the Unity Catalog model "
        "equipment_failure_model (alias champion), trained on equipment telemetry. risk_score is the calibrated "
        "probability (0-1) of an UNPLANNED failure within the next 30 days. 0.6 or more = act now (book "
        "preventive maintenance); 0.3-0.6 = monitor.")
bullet2("Revenue at risk", "launch_value estimates the revenue a launch delay would cost: weekly planned units x "
        "net price x weeks of delay avoided. All inputs live in value_assumptions and are ESTIMATES that the "
        "business can edit.")
bullet2("Action brief", "launch_action_brief contains an AI-generated (ai_query) summary of why a launch is at "
        "risk and what to do, in English and Italian. It is advice, not a decision.")
bullet2("Actions", "Planners escalate blockers in the Control Tower app; actions are stored in Lakebase and "
        "copied to ops_launch_actions. An open action has an owner and a due date.")

# ---------------- 9. GOLDEN QUESTIONS ----------------
h1("9. Example questions the agents handle")
h2("Demand & Supply")
for qn in ["How is forecast accuracy trending by therapeutic area, and where is bias worst?",
           "Which launches are at risk, and is it master data, serialization, or artwork blocking them?",
           "Which SKUs have the highest expiry-at-risk and low OTIF?",
           "Quali lanci sono a rischio e cosa li blocca? (IT)"]:
    bullet2(None, qn)
h2("Manufacturing & Reliability")
for qn in ["What is our OEE by plant, with availability, performance and quality?",
           "What are the top root causes of major deviations?",
           "Which critical equipment is predicted to fail in the next 30 days, and what production is at risk?",
           "Qual e l'OEE per stabilimento? (IT)"]:
    bullet2(None, qn)

pdf.output(OUT)
print("WROTE", OUT)
