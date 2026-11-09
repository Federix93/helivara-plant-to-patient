#!/usr/bin/env python3
"""Rename legacy names inside the Control Tower dashboard and republish it."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from helivara import names  # noqa: E402
from helivara.dbx import WAREHOUSE_ID, api  # noqa: E402

DASH = "01f1bc0ce3801f2499977bbb1277a65c"

if __name__ == "__main__":
    d = api("GET", f"/api/2.0/lakeview/dashboards/{DASH}")
    ser = d["serialized_dashboard"]
    if names.load_real_names(missing_ok=True):
        ser = names.rename(ser)
    api("PATCH", f"/api/2.0/lakeview/dashboards/{DASH}",
        {"display_name": d["display_name"], "serialized_dashboard": ser, "warehouse_id": WAREHOUSE_ID})
    r = api("POST", f"/api/2.0/lakeview/dashboards/{DASH}/published",
            {"warehouse_id": WAREHOUSE_ID, "embed_credentials": True})
    after = api("GET", f"/api/2.0/lakeview/dashboards/{DASH}")
    print(after["display_name"], "| forbidden hits:", len(names.find_forbidden(after["serialized_dashboard"])),
          "| published:", r.get("revision_create_time", r))
