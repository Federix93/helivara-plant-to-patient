import pytest

from helivara.value import (DEFAULT_ASSUMPTIONS, downtime_value, expiry_value, launch_revenue_at_risk,
                            otif_value, weekly_units_from_monthly)


def test_launch_revenue_at_risk():
    assert launch_revenue_at_risk(1000, 950, 4) == 3_800_000


def test_downtime_value():
    assert downtime_value(500, 8000, 0.2) == 800_000


def test_expiry_value():
    assert expiry_value(10_000, 12, 0.25) == 30_000


def test_otif_value():
    assert otif_value(5, 200_000) == 1_000_000


def test_weekly_units_from_monthly():
    assert weekly_units_from_monthly(4345) == pytest.approx(1000, rel=1e-3)


@pytest.mark.parametrize("fn,args", [(launch_revenue_at_risk, (-1, 950, 4)), (downtime_value, (500, -1, 0.2)),
                                     (expiry_value, (1, 1, -0.1)), (otif_value, (-5, 1))])
def test_negative_inputs_raise(fn, args):
    with pytest.raises(ValueError):
        fn(*args)


def test_reduction_above_one_raises():
    with pytest.raises(ValueError):
        downtime_value(500, 8000, 1.5)


def test_default_assumptions_are_labelled():
    keys = {a["key"] for a in DEFAULT_ASSUMPTIONS}
    assert {"zyvanta_net_price_eur", "weeks_delay_avoided", "downtime_cost_per_hour_eur", "downtime_reduction",
            "unit_cost_eur", "expiry_reduction", "otif_value_per_point_eur", "otif_points"} <= keys
    assert all(a["source"] for a in DEFAULT_ASSUMPTIONS)
