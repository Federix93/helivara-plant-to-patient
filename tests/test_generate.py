"""Generator invariants: hero facts, fictional names, legacy equivalence, failure signal."""
import json
import runpy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from helivara import names
from helivara.generate import build_tables, write_raw

LEGACY = Path(__file__).resolve().parents[1] / "legacy" / "generate_data_tf.py"
REAL = names.load_real_names(missing_ok=True)


@pytest.fixture(scope="module")
def t():
    return build_tables()


def test_hero_launch_facts(t):
    L = t["dim_launch"].set_index("launch_id")
    z = L.loc["ZYV-001"]
    assert abs(z.launch_readiness_score - 1 / 3) < 1e-9
    assert (z.master_data_ready_flag, z.artwork_ready_flag, z.serialization_ready_flag) == (0.0, 0.0, 1.0)
    assert abs(L.loc["ORB-001"].launch_readiness_score - 0.9) < 1e-9
    assert t["dim_product"].set_index("sku").loc["SKU_001", "brand"] == "Zyvanta"


def test_oribex_no_us_after_2025_11(t):
    for tbl in ("fact_demand_forecast", "fact_service"):
        df = t[tbl]
        bad = df[(df.sku == "SKU_002") & (df.market == "US") & (df.month >= "2025-11")]
        assert bad.empty, tbl


def test_no_forbidden_names(t):
    for name, df in t.items():
        for col in df.select_dtypes(include=["object", "str"]).columns:
            vals = " ".join(map(str, df[col].dropna().unique()))
            assert names.find_forbidden(vals) == [], f"{name}.{col}"


@pytest.mark.skipif(REAL is None or not LEGACY.exists(), reason="legacy generator not present")
def test_unchanged_tables_match_legacy(t, tmp_path, monkeypatch):
    monkeypatch.setattr("os.makedirs", lambda *a, **k: None)
    monkeypatch.setattr(pd.DataFrame, "to_parquet", lambda *a, **k: None)
    g = runpy.run_path(str(LEGACY))
    maps = REAL.all_maps
    for tbl in ("fact_demand_forecast", "fact_service", "fact_inventory", "fact_oee",
                "fact_batch", "fact_deviation", "dim_launch", "dim_product", "fact_qc_release"):
        old = g[tbl].replace(maps)
        new = t[tbl]
        pd.testing.assert_frame_equal(old.reset_index(drop=True), new[old.columns].reset_index(drop=True),
                                      check_like=True, obj=tbl)


def _unplanned(t):
    m = t["fact_maintenance"]
    return m[m.maintenance_type == "unplanned"]


def test_telemetry_has_failure_signal(t):
    tel = t["fact_equipment_telemetry"].copy()
    fails = _unplanned(t)
    pre, calm = [], []
    for eq, g in tel.groupby("equipment"):
        fdates = pd.to_datetime(fails[fails.equipment == eq].start_date).dt.normalize().values
        d = g.date.values
        if len(fdates):
            delta = (fdates[None, :] - d[:, None]).astype("timedelta64[D]").astype(int)
            near7 = ((delta > 0) & (delta <= 7)).any(axis=1)
            near30 = ((delta > 0) & (delta <= 30)).any(axis=1)
        else:
            near7 = near30 = np.zeros(len(g), bool)
        pre.append(g.vibration.values[near7])
        calm.append(g.vibration.values[~near30])
    assert np.concatenate(pre).mean() >= 1.3 * np.concatenate(calm).mean()


def test_valmora_coater_degrading(t):
    e = t["dim_equipment"].set_index("equipment").loc["L_OSD_001_EQ_01"]
    assert e.equipment_class == "coater" and e.plant == "Valmora"
    g = t["fact_equipment_telemetry"]
    g = g[g.equipment == "L_OSD_001_EQ_01"].sort_values("date")
    assert g.vibration.tail(7).mean() >= 1.3 * g.vibration.head(90).mean()
    assert g.date.max() == pd.Timestamp("2026-09-22")


def test_routing_links_zyvanta_to_valmora_coating(t):
    r = t["dim_routing"].set_index("sku")
    assert r.loc["SKU_001", "primary_line"] == "L_OSD_001"
    assert r.loc["SKU_001", "process_step"] == "coating"
    assert set(r.index) == set(t["dim_product"].sku)


def test_extra_unplanned_failures(t):
    assert len(_unplanned(t)) >= 100
    assert t["fact_maintenance"].wo_id.is_unique


def test_no_scored_or_legacy_tables(t):
    assert "fact_predicted_failure" not in t and "fact_oee_legacy" not in t


def test_write_raw_dirty_rate(t, tmp_path):
    files = write_raw(t, tmp_path)
    for sub in ("sap", "mes", "iot", "cmms", "config"):
        assert any((tmp_path / sub).iterdir()), sub
    man = json.loads((tmp_path / "_dirty_manifest.json").read_text())
    fact_rows = sum(len(df) for n, df in t.items() if n.startswith("fact_"))
    rate = sum(man.values()) / fact_rows
    assert 0.01 <= rate <= 0.02, rate
    assert set(files) == set(t)
    # one directory per entity (Auto Loader reads a directory per stream)
    assert files["fact_batch"] == tmp_path / "mes" / "fact_batch" / "fact_batch.json"
