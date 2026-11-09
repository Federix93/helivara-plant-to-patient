#!/usr/bin/env python3
"""End-to-end smoke test of the deployed Control Tower app (user OAuth token). Usage: app_smoke.py <app_url>"""
import json
import subprocess
import sys
import time

import httpx

url = sys.argv[1].rstrip("/")
tok = json.loads(subprocess.run(["databricks", "auth", "token", "--profile", "fr-stable"],
                                capture_output=True, text=True, check=True).stdout)["access_token"]
H = {"Authorization": f"Bearer {tok}"}
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)


print(f"# app smoke test {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} against {url}")
r = httpx.get(f"{url}/", headers=H, timeout=60)
check("UI served", r.status_code == 200 and "Control Tower" in r.text, r.status_code)
L = httpx.get(f"{url}/api/launches", headers=H, timeout=60).json()
z = next((x for x in L if x["launch_id"] == "ZYV-001"), None)
check("launch board (Lakebase) contains Zyvanta at risk", bool(z) and round(z["readiness"], 2) == 0.33
      and z["blocking_gates"] == "master data, artwork", json.dumps({k: z[k] for k in ("brand", "readiness", "blocking_gates", "revenue_at_risk_eur", "linked_equipment", "linked_failure_prob")} if z else None))
E = httpx.get(f"{url}/api/equipment-risk?limit=3", headers=H, timeout=60).json()
check("equipment risk top-1 is the Valmora coater", E and E[0]["equipment"] == "L_OSD_001_EQ_01",
      f"{E[0]['equipment']} p={E[0]['failure_prob_30d']:.2f}" if E else "")
body = {"launch_id": "ZYV-001", "action_type": "escalate_artwork", "owner": "Regulatory Artwork Manager",
        "due_date": "2026-09-29", "note": "smoke test: perché è urgente"}
a1 = httpx.post(f"{url}/api/actions", json=body, headers=H, timeout=60)
a2 = httpx.post(f"{url}/api/actions", json=body, headers=H, timeout=60)
check("escalate twice -> one open action (201 then 200, same id)", a1.status_code == 201 and a2.status_code == 200
      and a1.json()["action_id"] == a2.json()["action_id"], f"{a1.status_code}/{a2.status_code} id={a1.json().get('action_id')}")
check("action note UTF-8 round trip + created_by is the signed-in user", a1.json().get("note", "").endswith("perché è urgente")
      and "@" in (a1.json().get("created_by") or ""), f"created_by={a1.json().get('created_by')}")
bad = httpx.post(f"{url}/api/actions", json={**body, "action_type": "drop_table"}, headers=H, timeout=60)
check("invalid action rejected with 422", bad.status_code == 422, bad.status_code)
for q, space, must in [("Perché Zyvanta è a rischio?", "demand", "artwork"),
                       ("Cosa rende un lancio pronto?", "demand", ""),
                       ("Which machines are most likely to fail in the next 30 days?", "manufacturing", "L_OSD_001_EQ_01")]:
    t0 = time.time()
    g = httpx.post(f"{url}/api/genie/ask", json={"question": q, "space": space}, headers=H, timeout=120).json()
    blob = (g.get("text", "") + json.dumps(g.get("rows") or [])).lower()
    check(f"genie[{space}] '{q}'", g.get("status") == "ok" and must.lower() in blob,
          f"{time.time() - t0:.0f}s status={g.get('status')} sql={'yes' if g.get('sql') else 'no'} :: {g.get('text', '')[:160]!r}")
print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
