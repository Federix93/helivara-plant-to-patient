#!/usr/bin/env python3
"""Update both Genie agents in place: GET the current space, rename any legacy names, add new tables
(only those that exist) and an instruction block for them, then PATCH the COMPLETE body
(PATCH /api/2.0/genie/spaces/{id} is a full replace - never send a partial body)."""
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from helivara import names  # noqa: E402
from helivara.dbx import CATALOG, FQ, SCHEMA, api, sql  # noqa: E402

SPACES = {
    "01f1bc08a109177a8d192afb82da3e2b": {
        "extra_tables": ["launch_value", "launch_action_brief", "ops_launch_actions", "dim_routing"],
        "extra_instruction": (
            "Operational context: launch_value holds the estimated revenue at risk per launch (EUR, estimate from "
            "value_assumptions); launch_action_brief holds an AI-generated action brief per launch (brief_en, brief_it); "
            "ops_launch_actions lists the actions planners took in the Control Tower app (owner, due_date, status). "
            "dim_routing links each SKU to its primary production line. When asked about a launch at risk, also report "
            "revenue at risk and any open actions."),
    },
    "01f1bc08a1471942bf4433f530ef8537": {
        "extra_tables": ["dim_routing", "equipment_risk_drivers"],
        "extra_instruction": (
            "Operational context: fact_predicted_failure is scored daily by the UC model equipment_failure_model@champion: risk_score is the "
            "calibrated probability of an unplanned failure within 30 days. equipment_risk_drivers gives the top sensor "
            "driver per equipment. dim_routing maps SKUs to lines, so you can say which brands a failing machine puts at risk."),
    },
}
MARK = "Operational context:"  # idempotency marker for the extra instruction


def existing(tables):
    have = {r[0] for r in sql(f"SELECT table_name FROM {CATALOG}.information_schema.tables WHERE table_schema='{SCHEMA}'")}
    return [t for t in tables if t in have]


def patch(space_id, cfg):
    cur = api("GET", f"/api/2.0/genie/spaces/{space_id}?include_serialized_space=true")
    raw = json.dumps(cur)
    if names.load_real_names(missing_ok=True):
        raw = names.rename(raw)
    cur = json.loads(raw)
    ss = json.loads(cur["serialized_space"])
    ids = {t["identifier"] for t in ss["data_sources"]["tables"]}
    for t in existing(cfg["extra_tables"]):
        ids.add(f"{FQ}.{t}")
    ss["data_sources"]["tables"] = [{"identifier": i} for i in sorted(ids)]
    ti = ss["instructions"]["text_instructions"]
    if not any(MARK in "".join(x["content"]) for x in ti):
        ti[0]["content"] = ["".join(ti[0]["content"]) + "\n\n" + cfg["extra_instruction"]]
    body = {k: cur[k] for k in ("warehouse_id", "title", "description", "parent_path")}
    body["serialized_space"] = json.dumps(ss)
    api("PATCH", f"/api/2.0/genie/spaces/{space_id}", body)
    after = json.loads(api("GET", f"/api/2.0/genie/spaces/{space_id}?include_serialized_space=true")["serialized_space"])
    n = (len(after["instructions"]["text_instructions"]), len(after["config"]["sample_questions"]),
         len(after["data_sources"]["tables"]))
    print(f"{cur['title']}: instructions={n[0]} samples={n[1]} tables={n[2]}")
    assert n[0] >= 1 and n[1] >= 4 and n[2] >= 6, "space lost content"


if __name__ == "__main__":
    for sid, cfg in SPACES.items():
        patch(sid, cfg)
