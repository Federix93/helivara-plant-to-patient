"""Predictive-maintenance features and labels (shared by local tests and the Databricks notebooks).

Every feature at (equipment, date) uses only telemetry on or before that date (no look-ahead).
Label = 1 if an UNPLANNED failure starts in (date, date + horizon_days].
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SIGNALS = {"vibration": "vib", "temperature": "temp", "motor_current": "cur"}
FEATURES = (
    [f"{s}_mean_7" for s in SIGNALS.values()]
    + [f"{s}_slope_14" for s in SIGNALS.values()]
    + [f"{s}_ratio_7_60" for s in SIGNALS.values()]
    + ["anomaly_max_7", "days_since_maint"]
)


def _rolling_slope(x: pd.Series, t: pd.Series, w: int) -> pd.Series:
    r = lambda s: s.rolling(w, min_periods=3).mean()  # noqa: E731
    mt, mx, mtx, mtt = r(t), r(x), r(t * x), r(t * t)
    var = mtt - mt * mt
    return ((mtx - mt * mx) / var.replace(0, np.nan)).fillna(0.0)


def make_features(telemetry: pd.DataFrame, maintenance: pd.DataFrame) -> pd.DataFrame:
    tel = telemetry.copy()
    tel["date"] = pd.to_datetime(tel["date"]).dt.normalize()
    tel = tel.sort_values(["equipment", "date"]).reset_index(drop=True)
    out = []
    for eq, g in tel.groupby("equipment", sort=True):
        g = g.copy()
        t = pd.Series((g["date"] - g["date"].min()).dt.days.astype(float).values, index=g.index)
        for col, p in SIGNALS.items():
            x = g[col].astype(float)
            g[f"{p}_mean_7"] = x.rolling(7, min_periods=1).mean()
            g[f"{p}_slope_14"] = _rolling_slope(x, t, 14)
            base = x.rolling(60, min_periods=7).mean()
            g[f"{p}_ratio_7_60"] = (g[f"{p}_mean_7"] / base).fillna(1.0)
        g["anomaly_max_7"] = g["anomaly_score"].astype(float).rolling(7, min_periods=1).max()
        out.append(g)
    f = pd.concat(out, ignore_index=True)

    m = maintenance.copy()
    m["mdate"] = pd.to_datetime(m["start_date"]).dt.normalize().astype("datetime64[ns]")
    m = m[["equipment", "mdate"]].astype({"equipment": str}).sort_values("mdate")
    f["date"] = f["date"].astype("datetime64[ns]")
    f["equipment"] = f["equipment"].astype(str)
    f = f.sort_values("date")
    f = pd.merge_asof(f, m, left_on="date", right_on="mdate", by="equipment", direction="backward")
    f["days_since_maint"] = (f["date"] - f["mdate"]).dt.days.fillna(999).astype(int)
    f = f.sort_values(["equipment", "date"]).reset_index(drop=True)
    return f[["equipment", "date"] + FEATURES]


def make_labels(features: pd.DataFrame, maintenance: pd.DataFrame, horizon_days: int = 30) -> pd.Series:
    m = maintenance[maintenance["maintenance_type"] == "unplanned"]
    fails = {eq: np.sort(pd.to_datetime(g["start_date"]).dt.normalize().values)
             for eq, g in m.groupby("equipment")}
    y = np.zeros(len(features), dtype=int)
    dates = pd.to_datetime(features["date"]).values
    for i, (eq, d) in enumerate(zip(features["equipment"].values, dates)):
        fd = fails.get(eq)
        if fd is None:
            continue
        lo = np.searchsorted(fd, d, side="right")                       # strictly after d
        hi = np.searchsorted(fd, d + np.timedelta64(horizon_days, "D"), side="right")
        y[i] = int(hi > lo)
    return pd.Series(y, index=features.index, name="label")


def time_split(dates: pd.Series, test_start: str, test_end: str, horizon_days: int = 30):
    """Out-of-time split with an embargo: a training row's label window (date, date+horizon] must end
    before the test window starts, so no failure event is seen by both train and test labels."""
    d = pd.to_datetime(dates)
    start = pd.Timestamp(test_start)
    train = d + pd.Timedelta(days=horizon_days) < start
    test = (d >= start) & (d <= pd.Timestamp(test_end))
    return train, test
