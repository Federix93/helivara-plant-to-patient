# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Value model + AI launch brief
# MAGIC 1. `value_assumptions`: editable business assumptions (seeded once, never overwritten, so business edits stick).
# MAGIC 2. `launch_value`: estimated revenue at risk per launch = weekly planned units × net price × weeks of delay avoided.
# MAGIC 3. `value_summary`: annual value per lever (launch protection, downtime, expiry, OTIF) with its formula.
# MAGIC 4. `launch_action_brief`: `ai_query` turns readiness gates + machine risk + € at risk into a short brief (EN + IT).
# MAGIC All figures are **estimates on synthetic data**; formulas live in `helivara.value` (unit-tested).

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.abspath(".."))
import pandas as pd
from helivara.value import (DEFAULT_ASSUMPTIONS, downtime_value, expiry_value, launch_revenue_at_risk,
                            otif_value, weekly_units_from_monthly)

FQ = "fr_stable_catalog.supply_chain"
LLM = "databricks-claude-sonnet-5-5"

spark.sql(f"""CREATE TABLE IF NOT EXISTS {FQ}.value_assumptions (key STRING, value DOUBLE, unit STRING, source STRING)
COMMENT 'Editable business assumptions behind every value estimate (EUR). Edit a value and re-run notebook 03.'""")
if spark.table(f"{FQ}.value_assumptions").count() == 0:
    spark.createDataFrame(pd.DataFrame(DEFAULT_ASSUMPTIONS)).write.mode("append").saveAsTable(f"{FQ}.value_assumptions")
A = {r.key: r.value for r in spark.table(f"{FQ}.value_assumptions").collect()}
display(spark.table(f"{FQ}.value_assumptions"))

# COMMAND ----------

# Revenue at risk per launch (only launches in 'launch' phase carry launch-delay risk)
fc = spark.sql(f"""
  SELECT l.launch_id, l.sku, p.brand, l.launch_readiness_score,
         SUM(f.consensus_forecast) / COUNT(DISTINCT f.month) AS monthly_units
  FROM {FQ}.dim_launch l JOIN {FQ}.dim_product p USING (sku)
  JOIN {FQ}.fact_demand_forecast f ON f.sku = l.sku AND f.month BETWEEN '2026-10' AND '2026-12'
  WHERE l.phase = 'launch' GROUP BY ALL""").toPandas()
fc["weekly_units"] = fc.monthly_units.map(weekly_units_from_monthly)
fc["net_price_eur"] = A["zyvanta_net_price_eur"]
fc["weeks_delay_avoided"] = A["weeks_delay_avoided"]
fc["revenue_at_risk_eur"] = [launch_revenue_at_risk(w, p, d) for w, p, d in
                             zip(fc.weekly_units, fc.net_price_eur, fc.weeks_delay_avoided)]
spark.createDataFrame(fc).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{FQ}.launch_value")
spark.sql(f"COMMENT ON TABLE {FQ}.launch_value IS 'Estimated revenue at risk per launch (EUR) = weekly planned units "
          f"(Q4-2026 consensus forecast) x net price x weeks of delay avoided; assumptions in value_assumptions. ESTIMATE.'")
print(fc[["launch_id", "brand", "weekly_units", "revenue_at_risk_eur"]].to_string(index=False))

# COMMAND ----------

hours = spark.sql(f"""SELECT SUM(downtime_min)/60 FROM {FQ}.fact_maintenance
  WHERE maintenance_type='unplanned' AND start_date > (SELECT demo_date FROM {FQ}.demo_config) - INTERVAL 365 DAYS""").first()[0]
expiry_units = spark.sql(f"""SELECT SUM(expiry_at_risk_qty) FROM {FQ}.fact_inventory
  WHERE date > (SELECT demo_date FROM {FQ}.demo_config) - INTERVAL 365 DAYS
    AND date <= (SELECT demo_date FROM {FQ}.demo_config)""").first()[0]
rows = [
    ("Launch protection (Zyvanta)", "one-time, per protected launch", float(fc.revenue_at_risk_eur.sum()),
     f"weekly units {fc.weekly_units.sum():,.0f} x EUR {A['zyvanta_net_price_eur']:,.0f} x {A['weeks_delay_avoided']:.0f} weeks earlier"),
    ("Unplanned downtime avoided", "recurring, per year", downtime_value(float(hours), A["downtime_cost_per_hour_eur"], A["downtime_reduction"]),
     f"{float(hours):,.0f} unplanned h/yr x EUR {A['downtime_cost_per_hour_eur']:,.0f}/h x {A['downtime_reduction']:.0%}"),
    ("Expiry write-off avoided", "recurring, per year", expiry_value(float(expiry_units), A["unit_cost_eur"], A["expiry_reduction"]),
     f"{float(expiry_units):,.0f} units at risk/yr x EUR {A['unit_cost_eur']:,.0f} x {A['expiry_reduction']:.0%}"),
    ("OTIF improvement", "recurring, per year", otif_value(A["otif_points"], A["otif_value_per_point_eur"]),
     f"{A['otif_points']:.0f} pts x EUR {A['otif_value_per_point_eur']:,.0f}/pt"),
]
vs = pd.DataFrame(rows, columns=["lever", "value_type", "annual_value_eur", "formula"])
spark.createDataFrame(vs).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{FQ}.value_summary")
spark.sql(f"COMMENT ON TABLE {FQ}.value_summary IS 'Value per lever (EUR, ESTIMATES) with the formula used. value_type: "
          f"launch protection is one-time per protected launch (patent-protected sales days not lost); other levers recur yearly. "
          f"annual_value_eur = value in year one.'")
rec = vs[vs.value_type.str.startswith("recurring")].annual_value_eur.sum()
print(vs.to_string(index=False)); print(f"YEAR-ONE TOTAL EUR {vs.annual_value_eur.sum():,.0f} | recurring EUR {rec:,.0f}/yr")

# COMMAND ----------

# GenAI brief per at-risk launch, grounded on governed facts + the ML risk of the launch's primary line
ctx = spark.sql(f"""
  SELECT l.launch_id, p.brand, l.launch_readiness_score AS readiness, l.master_data_ready_flag AS md,
         l.artwork_ready_flag AS art, l.serialization_ready_flag AS ser, v.revenue_at_risk_eur,
         r.primary_line, r.plant, r.process_step,
         max_by(e.equipment, d.failure_prob_30d) AS top_equipment, max(d.failure_prob_30d) AS top_prob
  FROM {FQ}.dim_launch l JOIN {FQ}.dim_product p USING (sku) JOIN {FQ}.launch_value v USING (launch_id)
  JOIN {FQ}.dim_routing r ON r.sku = l.sku
  JOIN {FQ}.dim_equipment e ON e.line = r.primary_line
  JOIN {FQ}.equipment_risk_drivers d ON d.equipment = e.equipment
  WHERE l.launch_readiness_score < 1 GROUP BY ALL""")
ctx.createOrReplaceTempView("ctx")
facts = ("concat('Launch ', launch_id, ' (', brand, '): readiness ', round(readiness,2), '; master data ready ', md, "
         "'; artwork ready ', art, '; serialization ready ', ser, '; estimated revenue at risk EUR ', "
         "format_number(revenue_at_risk_eur,0), '; primary line ', primary_line, ' at ', plant, ' (', process_step, "
         "'); highest failure risk on that line: ', top_equipment, ' with ', round(top_prob*100), '% probability of "
         "unplanned failure within 30 days.')")
prompt = ("'You are a supply-chain advisor for a pharma launch. Using ONLY these facts, write 4 short sentences: "
          "the status, the blockers (name each gate that is 0), the manufacturing risk, and 2 concrete next actions "
          "with owners by role (no person names). Facts: ' || facts")
spark.sql(f"""
  CREATE OR REPLACE TABLE {FQ}.launch_action_brief
  COMMENT 'AI-generated action brief per at-risk launch (ai_query on {LLM}), grounded on governed facts. Advice, not a decision.'
  AS SELECT launch_id, facts,
     ai_query('{LLM}', {prompt}) AS brief_en,
     ai_query('{LLM}', {prompt} || ' Rispondi in italiano.') AS brief_it,
     '{LLM}' AS model_endpoint, current_timestamp() AS generated_at
  FROM (SELECT launch_id, {facts} AS facts FROM ctx)""")
for r in spark.table(f"{FQ}.launch_action_brief").collect():
    print(r.launch_id, "\nFACTS:", r.facts, "\nEN:", r.brief_en, "\nIT:", r.brief_it)
