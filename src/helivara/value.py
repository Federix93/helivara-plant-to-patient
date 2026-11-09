"""Business-value formulas. All inputs are ESTIMATES held in the editable `value_assumptions` table."""
from __future__ import annotations

WEEKS_PER_MONTH = 4.345

DEFAULT_ASSUMPTIONS = [
    {"key": "zyvanta_net_price_eur", "value": 450.0, "unit": "EUR/pack",
     "source": "Assumed net price of a 14-tablet specialty immunology pack (~EUR 30/day of therapy); edit to the real net price"},
    {"key": "weeks_delay_avoided", "value": 4.0, "unit": "weeks",
     "source": "Blockers surface ~4 weeks earlier with daily readiness monitoring vs the monthly S&OP review"},
    {"key": "downtime_cost_per_hour_eur", "value": 8000.0, "unit": "EUR/hour",
     "source": "Lost contribution + recovery cost per hour of unplanned downtime on an OSD line (industry rule of thumb)"},
    {"key": "downtime_reduction", "value": 0.20, "unit": "fraction",
     "source": "Typical reduction in unplanned downtime from predictive maintenance programs (20-30%)"},
    {"key": "unit_cost_eur", "value": 12.0, "unit": "EUR/unit", "source": "Assumed standard cost of a finished pack"},
    {"key": "expiry_reduction", "value": 0.25, "unit": "fraction",
     "source": "Reduction in expiry write-offs from earlier visibility (matches the 25% holding-cost benchmark)"},
    {"key": "otif_value_per_point_eur", "value": 200000.0, "unit": "EUR/OTIF point/year",
     "source": "Avoided tender penalties and lost sales per OTIF percentage point"},
    {"key": "otif_points", "value": 5.0, "unit": "points", "source": "Expected OTIF improvement (7-10% benchmark, conservative)"},
]


def _non_negative(**kw):
    for k, v in kw.items():
        if v < 0:
            raise ValueError(f"{k} must be >= 0, got {v}")


def _fraction(**kw):
    for k, v in kw.items():
        if not 0 <= v <= 1:
            raise ValueError(f"{k} must be in [0, 1], got {v}")


def weekly_units_from_monthly(monthly_units: float) -> float:
    _non_negative(monthly_units=monthly_units)
    return monthly_units / WEEKS_PER_MONTH


def launch_revenue_at_risk(weekly_units: float, net_price_eur: float, weeks_delay_avoided: float) -> float:
    _non_negative(weekly_units=weekly_units, net_price_eur=net_price_eur, weeks_delay_avoided=weeks_delay_avoided)
    return weekly_units * net_price_eur * weeks_delay_avoided


def downtime_value(unplanned_hours_per_year: float, cost_per_hour_eur: float, reduction: float) -> float:
    _non_negative(unplanned_hours_per_year=unplanned_hours_per_year, cost_per_hour_eur=cost_per_hour_eur)
    _fraction(reduction=reduction)
    return unplanned_hours_per_year * cost_per_hour_eur * reduction


def expiry_value(expiry_at_risk_units: float, unit_cost_eur: float, reduction: float) -> float:
    _non_negative(expiry_at_risk_units=expiry_at_risk_units, unit_cost_eur=unit_cost_eur)
    _fraction(reduction=reduction)
    return expiry_at_risk_units * unit_cost_eur * reduction


def otif_value(otif_points: float, value_per_point_eur: float) -> float:
    _non_negative(otif_points=otif_points, value_per_point_eur=value_per_point_eur)
    return otif_points * value_per_point_eur
