#!/usr/bin/env python3
"""Scan the live workspace assets for forbidden real-world names. Exits 1 on any hit.
Covers: string values of every table in the schema, table/column comments, metric-view definitions,
both Genie spaces, the dashboard, our Discover domains, and PDFs in the `knowledge` Volume."""
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from helivara.dbx import CATALOG, FQ, PROFILE, SCHEMA, api, sql  # noqa: E402
from helivara.names import find_forbidden  # noqa: E402

GENIE = ["01f1bc08a109177a8d192afb82da3e2b", "01f1bc08a1471942bf4433f530ef8537"]
DASHBOARD = "01f1bc0ce3801f2499977bbb1277a65c"
DOMAIN_ROOTS = ("Demand and Sales", "Supply and Inventory", "Manufacturing and Quality", "Reliability and Maintenance")
hits = {}


def scan(asset, text):
    f = find_forbidden(text)
    if f:
        hits[asset] = len(f)
    print(f"{'HIT ' if f else 'ok  '} {asset}" + (f"  ({len(f)})" if f else ""))


cols = sql(f"SELECT table_name, column_name, data_type, comment FROM {CATALOG}.information_schema.columns "
           f"WHERE table_schema='{SCHEMA}' ORDER BY table_name, ordinal_position")
by_t = {}
for t, c, ty, cm in cols:
    by_t.setdefault(t, []).append((c, ty, cm))
tcom = dict(sql(f"SELECT table_name, coalesce(comment,'') FROM {CATALOG}.information_schema.tables WHERE table_schema='{SCHEMA}'"))
kinds = dict(sql(f"SELECT table_name, table_type FROM {CATALOG}.information_schema.tables WHERE table_schema='{SCHEMA}'"))
for t, cs in sorted(by_t.items()):
    scan(f"comments {t}", tcom.get(t, "") + " " + " ".join((cm or "") for _, _, cm in cs))
    strs = [c for c, ty, _ in cs if ty == "STRING" and not c.startswith("_")]
    if strs and kinds.get(t) != "METRIC_VIEW":
        agg = ", ".join(f"concat_ws(' ', collect_set(`{c}`))" for c in strs)
        row = sql(f"SELECT {agg} FROM {FQ}.{t}")[0]
        scan(f"values {t}", " ".join(v or "" for v in row))
for t, d in sql(f"SELECT table_name, view_definition FROM {CATALOG}.information_schema.views WHERE table_schema='{SCHEMA}'"):
    scan(f"definition {t}", d or "")
for g in GENIE:
    scan(f"genie {g}", json.dumps(api("GET", f"/api/2.0/genie/spaces/{g}?include_serialized_space=true")))
scan(f"dashboard {DASHBOARD}", json.dumps(api("GET", f"/api/2.0/lakeview/dashboards/{DASHBOARD}")))
doms = [d for d in api("GET", "/api/2.0/domains").get("domains", []) if d.get("tag_key", "").startswith(DOMAIN_ROOTS)]
scan(f"domains ({len(doms)})", json.dumps(doms))
from pypdf import PdfReader  # noqa: E402

ls = subprocess.run(["databricks", "fs", "ls", f"dbfs:/Volumes/{CATALOG}/{SCHEMA}/knowledge", "--profile", PROFILE],
                    capture_output=True, text=True).stdout.split()
for f in [x for x in ls if x.lower().endswith(".pdf")]:
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["databricks", "fs", "cp", f"dbfs:/Volumes/{CATALOG}/{SCHEMA}/knowledge/{f}", d,
                        "--profile", PROFILE], check=True, capture_output=True)
        text = " ".join(p.extract_text() or "" for p in PdfReader(Path(d) / f).pages)
    scan(f"pdf {f}", text)
print(f"\nassets with hits: {len(hits)}  total hits: {sum(hits.values())}")
sys.exit(1 if hits else 0)
