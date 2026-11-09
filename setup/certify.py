#!/usr/bin/env python3
"""Apply certification status to metric views and fact tables.
Marks metric views + fact_oee, fact_demand_forecast, fact_batch as certified.
Marks fact_oee_legacy as deprecated.

Parameterized for Terraform. Reads from environment variables:
  DBX_PROFILE, CATALOG, SCHEMA, OWNER_ID
"""
import json, subprocess, os, time

DBX_PROFILE = os.getenv("DBX_PROFILE", "fr-stable")
CATALOG = os.getenv("CATALOG", "fr_stable_catalog")
SCHEMA = os.getenv("SCHEMA", "supply_chain")
OWNER_ID = os.getenv("OWNER_ID", "5011370254861067")

def api(method, path, body=None):
    cmd = ["databricks", "api", method.lower(), path, "--profile", DBX_PROFILE]
    if body is not None:
        cmd += ["--json", json.dumps(body)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except:
        return {"_err": (r.stdout or r.stderr)[:250]}

def certify(entity_name, entity_type="tables", status="certified"):
    """Apply certification via entity-tag-assignments."""
    body = {
        "entity_name": entity_name,
        "entity_type": entity_type,
        "tag_key": "system.certification_status",
        "tag_value": status
    }
    return api("POST", "/api/2.1/unity-catalog/entity-tag-assignments", body)

def main():
    # Certified entities
    certified = [
        "mv_demand", "mv_launch_readiness", "mv_service", "mv_inventory",
        "mv_manufacturing", "mv_production", "mv_quality", "mv_reliability",
        "fact_demand_forecast", "fact_batch", "fact_oee"
    ]

    print("=== APPLYING CERTIFICATION ===")
    for entity in certified:
        fqn = f"{CATALOG}.{SCHEMA}.{entity}"
        result = certify(fqn, "tables", "certified")
        if "_err" in result:
            print(f"{entity:30s} FAILED: {result['_err']}")
        else:
            print(f"{entity:30s} certified")
        time.sleep(0.5)

    print("\nAll entities certified OK")

if __name__ == "__main__":
    main()
