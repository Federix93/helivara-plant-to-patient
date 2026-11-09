#!/usr/bin/env python3
"""Live checks against the workspace. Usage: verify_live.py --contract --hero --quarantine [--ml --value --lakebase]
Prints one PASS/FAIL line per check and exits non-zero on any failure."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from helivara.dbx import CATALOG, FQ, SCHEMA, sql  # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def contract():
    want = json.loads((ROOT / "evidence/contracts/gold_schemas.json").read_text())
    want.pop("_scored")
    rows = sql(f"SELECT table_name, column_name, data_type FROM {CATALOG}.information_schema.columns "
               f"WHERE table_schema='{SCHEMA}' ORDER BY table_name, ordinal_position")
    have = {}
    for t, c, ty in rows:
        have.setdefault(t, []).append([c, ty])
    for t, cols in sorted(want.items()):
        check(f"contract {t}", have.get(t) == cols, "" if have.get(t) == cols else f"have={have.get(t)}")


def hero():
    r = {row[0]: row[1:] for row in sql(
        f"SELECT brand, ROUND(MEASURE(avg_launch_readiness),2), MEASURE(master_data_ready_rate), "
        f"MEASURE(artwork_ready_rate), MEASURE(serialization_ready_rate) FROM {FQ}.mv_launch_readiness GROUP BY brand")}
    check("hero Zyvanta readiness 0.33 / md 0 / art 0 / ser 1",
          r.get("Zyvanta") == ["0.33", "0.0", "0.0", "1.0"], str(r.get("Zyvanta")))
    check("hero Oribex readiness 0.9", (r.get("Oribex") or [None])[0] == "0.9", str(r.get("Oribex")))
    n = sql(f"SELECT COUNT(*) FROM {FQ}.fact_demand_forecast WHERE sku='SKU_002' AND market='US' AND month>='2025-11'")
    check("hero Oribex no US demand from 2025-11", n[0][0] == "0", n[0][0])
    before = json.loads((ROOT / "evidence/contracts/hero_before.json").read_text())["row_counts"]
    for t, c in sorted(before.items()):
        if t == "fact_maintenance":
            continue  # grows by design (extra unplanned failures)
        got = sql(f"SELECT COUNT(*) FROM {FQ}.{t}")[0][0]
        check(f"row count {t} = {c}", got == c, got)


def quarantine():
    man = json.loads((ROOT / "evidence/pipeline/dirty_manifest.json").read_text())
    for t, n in sorted(man.items()):
        try:
            got = sql(f"SELECT COUNT(*) FROM {FQ}.{t}_quarantine")[0][0]
        except RuntimeError as e:
            got = f"error: {str(e)[:80]}"
        check(f"quarantine {t}_quarantine = {n}", got == str(n), got)


def value():
    v = sql(f"SELECT launch_id, revenue_at_risk_eur FROM {FQ}.launch_value WHERE launch_id='ZYV-001'")
    check("value Zyvanta revenue_at_risk_eur > 0", bool(v) and float(v[0][1]) > 0, str(v))
    b = sql(f"SELECT lower(brief_en), lower(brief_it) FROM {FQ}.launch_action_brief WHERE launch_id='ZYV-001'")
    ok = bool(b) and all(k in b[0][0] for k in ("master data", "artwork")) and "artwork" in b[0][1] and \
        any(k in b[0][1] for k in ("anagrafic", "master data"))
    check("value brief mentions master data + artwork in EN and IT", ok)
    n = sql(f"SELECT count(*) FROM {FQ}.value_summary")[0][0]
    check("value_summary has 4 levers", n == "4", n)


def _pg():
    from databricks.sdk import WorkspaceClient
    from helivara.dbx import PROFILE
    from helivara.lakebase_sync import pg_connect
    return pg_connect(workspace_client=WorkspaceClient(profile=PROFILE))


def lakebase():
    from helivara.lakebase_sync import SERVING
    conn = _pg()
    cur = conn.cursor()
    for spec in SERVING:
        cur.execute(f"SELECT count(*), count(DISTINCT {spec['pk']}) FROM {spec['table']}")
        n, d = cur.fetchone()
        src = sql(f"SELECT count(*) FROM ({spec['source_sql'].format(fq=FQ)})")[0][0]
        check(f"lakebase {spec['table']} rows = gold source ({src}), no duplicate keys", str(n) == src and n == d,
              f"lakebase={n} distinct={d}")
    cur.execute("SELECT readiness, blocking_gates, revenue_at_risk_eur, linked_equipment FROM "
                "control_tower.launch_risk_board WHERE launch_id='ZYV-001'")
    lb = cur.fetchone()
    g = sql(f"SELECT round(l.launch_readiness_score,4), round(v.revenue_at_risk_eur,0) FROM {FQ}.dim_launch l "
            f"JOIN {FQ}.launch_value v USING (launch_id) WHERE launch_id='ZYV-001'")[0]
    ok = lb and round(lb[0], 4) == float(g[0]) and round(lb[2]) == float(g[1]) and \
        lb[1] == "master data, artwork" and lb[3] == "L_OSD_001_EQ_01"
    check("lakebase Zyvanta board row equals gold (readiness, gates, EUR at risk, linked coater)", bool(ok), str(lb))
    cur.execute("SELECT action_id FROM control_tower.actions WHERE note = 'verify_live probe'")
    ids = [r[0] for r in cur.fetchall()]
    conn.close()
    back = sql(f"SELECT count(*) FROM {FQ}.ops_launch_actions WHERE note = 'verify_live probe'")[0][0]
    check("lakebase probe action survives job re-run and is copied to Delta ops_launch_actions",
          len(ids) == 1 and back == "1", f"lakebase={ids} delta={back}")


def ml():
    want = json.loads((ROOT / "evidence/contracts/gold_schemas.json").read_text())["_scored"]["fact_predicted_failure"]
    have = sql(f"SELECT column_name, data_type FROM {CATALOG}.information_schema.columns WHERE table_schema='{SCHEMA}' "
               f"AND table_name='fact_predicted_failure' ORDER BY ordinal_position")
    check("contract fact_predicted_failure (scored)", have == want, str(have))
    top = sql(f"SELECT equipment, risk_score FROM {FQ}.fact_predicted_failure ORDER BY risk_score DESC LIMIT 1")
    check("ml top-1 risk is the Valmora coater L_OSD_001_EQ_01 with p >= 0.6",
          bool(top) and top[0][0] == "L_OSD_001_EQ_01" and float(top[0][1]) >= 0.6, str(top))
    rng = sql(f"SELECT min(failure_prob_30d), max(failure_prob_30d), count(*) FROM {FQ}.equipment_risk_drivers")[0]
    check("ml all machines scored with p in [0,1]", float(rng[0]) >= 0 and float(rng[1]) <= 1 and rng[2] == "20", str(rng))
    from helivara.dbx import api
    a = api("GET", f"/api/2.1/unity-catalog/models/{FQ}.equipment_failure_model/aliases/champion")
    check("ml UC model alias @champion exists", "version" in a, str(a.get("version", a))[:80])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for f in ["contract", "hero", "quarantine", "ml", "value", "lakebase"]:
        ap.add_argument(f"--{f}", action="store_true")
    a = ap.parse_args()
    for f in ["contract", "hero", "quarantine", "ml", "value", "lakebase"]:
        if getattr(a, f):
            globals()[f]()
    print(f"\n{sum(RESULTS)}/{len(RESULTS)} checks passed")
    sys.exit(0 if all(RESULTS) else 1)
