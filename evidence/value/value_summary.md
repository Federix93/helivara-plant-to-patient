# Value model output (estimates on synthetic data)

Computed by notebook `03_value_and_brief` from gold tables × `value_assumptions` (editable).
Launch protection is **one-time per protected launch** (patent-protected sales days not lost); the other levers recur every year.

| Lever | Type | Value (EUR) | Formula |
|---|---|---:|---|
| Launch protection (Zyvanta) | one-time, per protected launch | 7,850,127 | weekly units 4,361 x EUR 450 x 4 weeks earlier |
| Unplanned downtime avoided | recurring, per year | 730,613 | 457 unplanned h/yr x EUR 8,000/h x 20% |
| Expiry write-off avoided | recurring, per year | 106,878 | 35,626 units at risk/yr x EUR 12 x 25% |
| OTIF improvement | recurring, per year | 1,000,000 | 5 pts x EUR 200,000/pt |
| **Year-one total** | | **9,687,618** | |
| of which recurring per year | | 1,837,491 | |

## Assumptions

| key | value | unit | source |
|---|---:|---|---|
| downtime_cost_per_hour_eur | 8000.0 | EUR/hour | Lost contribution + recovery cost per hour of unplanned downtime on an OSD line (industry rule of thumb) |
| downtime_reduction | 0.2 | fraction | Typical reduction in unplanned downtime from predictive maintenance programs (20-30%) |
| expiry_reduction | 0.25 | fraction | Reduction in expiry write-offs from earlier visibility (matches the 25% holding-cost benchmark) |
| otif_points | 5.0 | points | Expected OTIF improvement (7-10% benchmark, conservative) |
| otif_value_per_point_eur | 200000.0 | EUR/OTIF point/year | Avoided tender penalties and lost sales per OTIF percentage point |
| unit_cost_eur | 12.0 | EUR/unit | Assumed standard cost of a finished pack |
| weeks_delay_avoided | 4.0 | weeks | Blockers surface ~4 weeks earlier with daily readiness monitoring vs the monthly S&OP review |
| zyvanta_net_price_eur | 450.0 | EUR/pack | Assumed net price of a 14-tablet specialty immunology pack (~EUR 30/day of therapy); edit to the real net price |
