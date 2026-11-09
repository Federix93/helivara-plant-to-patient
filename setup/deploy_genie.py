#!/usr/bin/env python3
"""Create the 2 Genie Agents on the workspace via POST /api/2.0/genie/spaces.

Parameterized for Terraform. Reads from environment variables:
  DBX_PROFILE, WAREHOUSE_ID, CATALOG, SCHEMA, OWNER_ID
"""
import json, subprocess, uuid, os

DBX_PROFILE = os.getenv("DBX_PROFILE", "fr-stable")
WAREHOUSE_ID = os.getenv("WAREHOUSE_ID", "797d1d487d654063")
CATALOG = os.getenv("CATALOG", "fr_stable_catalog")
SCHEMA = os.getenv("SCHEMA", "supply_chain")
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "federico.rizzo@databricks.com")
S = f"{CATALOG}.{SCHEMA}"

def api(method, path, body=None):
    cmd = ["databricks", "api", method.lower(), path, "--profile", DBX_PROFILE]
    if body is not None:
        cmd += ["--json", json.dumps(body)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except:
        return {"_err": (r.stdout or r.stderr)[:250]}

def tid():
    return uuid.uuid4().hex

def space(tables, instr, samples):
    return {
        "version": 2,
        "data_sources": {"tables": [{"identifier": f"{S}.{t}"} for t in sorted(tables)]},
        "instructions": {"text_instructions": [{"id": tid(), "content": [instr]}]},
        "config": {"sample_questions": [{"id": tid(), "question": [q]} for q in samples]},
    }

demand_instr = (
    "You are the Demand & Supply domain assistant for Helivara pharma operations. Help S&OP, demand "
    "planners and supply chain managers with forecast accuracy/bias by therapeutic area and cluster/BU, "
    "launch readiness (master data, serialization, artwork), OTIF by market, and days of inventory / "
    "expiry-at-risk. Prefer the metric views and wrap measures in MEASURE(): mv_demand "
    "(MEASURE(forecast_accuracy), MEASURE(forecast_bias)), mv_launch_readiness "
    "(MEASURE(avg_launch_readiness), MEASURE(master_data_ready_rate)), mv_service (MEASURE(otif)), "
    "mv_inventory (MEASURE(avg_days_of_inventory), MEASURE(total_expiry_at_risk)). Context: Zyvanta "
    "(immunology, launch) is AT RISK - master data and artwork not ready; always flag it. Oribex is in "
    "phase-out (US sales = 0 after 2025-11). For launch questions, name the blocker (master data, "
    "serialization, or artwork). Users may ask in Italian - answer in Italian. Cite the metric view used."
)

mfg_instr = (
    "You are the Manufacturing & Reliability domain assistant for Helivara's production network. Help "
    "plant/quality/maintenance leaders with OEE and its availability/performance/quality breakdown, "
    "right-first-time and yield, quality deviations and CAPA, and equipment reliability / predicted "
    "failures. Prefer the metric views with MEASURE(): mv_manufacturing (MEASURE(oee), "
    "MEASURE(availability), MEASURE(performance), MEASURE(quality)), mv_production (MEASURE(rft_rate), "
    "MEASURE(schedule_adherence)), mv_quality (MEASURE(deviation_count), MEASURE(capa_on_time_rate)), "
    "mv_reliability (MEASURE(unplanned_downtime_hours), MEASURE(total_maintenance_cost)). Use "
    "fact_predicted_failure for equipment predicted to fail. Report all three OEE components for OEE "
    "questions. Downtime cascades to supply: lower OEE -> schedule miss -> stockout / lower OTIF (esp. "
    "Zyvanta coating at Valmora). Users may ask in Italian - answer in Italian. Cite the metric view used."
)

AGENTS = [
    {
        "title": "Demand and Supply Agent",
        "desc": "Demand forecasting, S&OP, launch readiness, service and inventory for Helivara (synthetic demo).",
        "tables": ["mv_demand", "mv_launch_readiness", "mv_service", "mv_inventory", "dim_product", "dim_launch"],
        "instr": demand_instr,
        "samples": [
            "How is forecast accuracy trending by therapeutic area, and where is bias worst?",
            "Which launches are at risk, and is it master data, serialization, or artwork blocking them?",
            "Which SKUs have the highest expiry-at-risk and low OTIF?",
            "Quali lanci sono a rischio e cosa li blocca?"
        ]
    },
    {
        "title": "Manufacturing and Reliability Agent",
        "desc": "OEE, quality, reliability and predictive maintenance for Helivara (synthetic demo).",
        "tables": ["mv_manufacturing", "mv_production", "mv_quality", "mv_reliability", "fact_predicted_failure", "dim_equipment"],
        "instr": mfg_instr,
        "samples": [
            "What is our OEE by plant, with availability, performance and quality?",
            "What are the top root causes of major deviations?",
            "Which critical equipment is predicted to fail in the next 30 days, and what production is at risk?",
            "Qual e l'OEE per stabilimento?"
        ]
    },
]

def main():
    for a in AGENTS:
        ss = space(a["tables"], a["instr"], a["samples"])
        body = {
            "warehouse_id": WAREHOUSE_ID,
            "title": a["title"],
            "description": a["desc"],
            "parent_path": f"/Users/{OWNER_EMAIL}",
            "serialized_space": json.dumps(ss)
        }
        r = api("POST", "/api/2.0/genie/spaces", body)
        print(a["title"], "->", json.dumps(r)[:200])

    print("\n=== our genie spaces ===")
    for s in api("GET", "/api/2.0/genie/spaces").get("spaces", []):
        if "Helivara" in (s.get("description") or "") or s.get("title") in [a["title"] for a in AGENTS]:
            print(" ", s.get("space_id"), "|", s.get("title"))

if __name__ == "__main__":
    main()
