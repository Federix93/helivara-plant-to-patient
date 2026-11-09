import pandas as pd
import pytest

from helivara.features import FEATURES, make_features, make_labels
from helivara.generate import build_tables


def _tel(days=40, eq="E1"):
    d = pd.date_range("2026-01-01", periods=days)
    return pd.DataFrame({"date": d, "equipment": eq, "vibration": range(days), "temperature": 50.0,
                         "motor_current": 20.0, "pressure": 50.0, "anomaly_score": 0.1})


def _maint(*rows):
    return pd.DataFrame(rows, columns=["equipment", "start_date", "maintenance_type"])


def test_rolling_features_no_lookahead():
    tel = _tel()
    m = _maint(("E1", pd.Timestamp("2025-12-20"), "planned"))
    full = make_features(tel, m).set_index(["equipment", "date"])
    cut = make_features(tel[tel.date <= "2026-01-25"], m).set_index(["equipment", "date"])
    pd.testing.assert_frame_equal(full.loc[cut.index, FEATURES], cut[FEATURES])


def test_feature_columns_present():
    f = make_features(_tel(), _maint())
    assert list(f.columns[:2]) == ["equipment", "date"] and set(FEATURES) <= set(f.columns)


def test_days_since_maintenance():
    f = make_features(_tel(), _maint(("E1", pd.Timestamp("2026-01-05 10:00"), "planned"))).set_index("date")
    assert f.loc["2026-01-10", "days_since_maint"] == 5
    assert f.loc["2026-01-02", "days_since_maint"] == 999  # no maintenance yet


def test_labels_horizon():
    f = make_features(_tel(days=60), _maint())
    m = _maint(("E1", pd.Timestamp("2026-02-10 08:00"), "unplanned"),
               ("E1", pd.Timestamp("2026-01-03"), "planned"))
    y = pd.Series(make_labels(f, m).values, index=f.date)
    assert y[pd.Timestamp("2026-01-11")] == 1      # failure on d+30
    assert y[pd.Timestamp("2026-01-10")] == 0      # failure on d+31
    assert y[pd.Timestamp("2026-02-10")] == 0      # failure on the same day is not "future"
    assert y[pd.Timestamp("2026-01-02")] == 0      # planned maintenance is not a failure


@pytest.fixture(scope="module")
def gen():
    t = build_tables()
    f = make_features(t["fact_equipment_telemetry"], t["fact_maintenance"])
    return f, make_labels(f, t["fact_maintenance"], horizon_days=14)


def test_features_on_generated_data_separate_classes(gen):
    f, y = gen
    assert f.loc[y == 1, "vib_slope_14"].mean() > f.loc[y == 0, "vib_slope_14"].mean()
    assert f.loc[y == 1, "vib_ratio_7_60"].mean() > 1.1 * f.loc[y == 0, "vib_ratio_7_60"].mean()


def test_time_split_embargo_prevents_label_leakage():
    from helivara.features import time_split
    d = pd.Series(pd.date_range("2026-01-01", "2026-09-22"))
    tr, te = time_split(d, test_start="2026-06-01", test_end="2026-08-22", horizon_days=30)
    # a training row's label window (date, date+30] must end before the test window starts
    assert (d[tr] + pd.Timedelta(days=30)).max() < pd.Timestamp("2026-06-01")
    assert d[te].min() == pd.Timestamp("2026-06-01") and d[te].max() == pd.Timestamp("2026-08-22")
    assert not (tr & te).any()
