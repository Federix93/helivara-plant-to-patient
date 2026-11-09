#!/usr/bin/env python3
"""Create TRUE Unity Catalog metric views (WITH METRICS LANGUAGE YAML) for the demo.
Grain-correct: each view has ONE fact source + dimension joins (no fact-to-fact fan-out).
Replaces the plain aggregated views created earlier. Verifies table_type=METRIC_VIEW.

Parameterized for Terraform. Reads from environment variables:
  DBX_PROFILE, WAREHOUSE_ID, CATALOG, SCHEMA
"""
import json, subprocess, sys, os

DBX_PROFILE = os.getenv("DBX_PROFILE", "fr-stable")
WAREHOUSE_ID = os.getenv("WAREHOUSE_ID", "797d1d487d654063")
CATALOG = os.getenv("CATALOG", "fr_stable_catalog")
SCHEMA = os.getenv("SCHEMA", "supply_chain")
M = f"{CATALOG}.{SCHEMA}"
GOLD = f"{CATALOG}.{SCHEMA}"

def run(s):
    r=subprocess.run(['databricks','api','post','/api/2.0/sql/statements','--profile',DBX_PROFILE,
        '--json',json.dumps({'warehouse_id':WAREHOUSE_ID,'statement':s,'wait_timeout':'50s','on_wait_timeout':'CONTINUE'})],
        capture_output=True,text=True)
    try:d=json.loads(r.stdout)
    except Exception:return "ERR",r.stdout[:200]
    st=d.get('status',{}).get('state')
    if st!='SUCCEEDED':return st,d.get('status',{}).get('error',{}).get('message',str(d)[:250])
    return "OK",d.get('result',{}).get('data_array')

# name -> (yaml_body, view_comment, sample_measure_query)
VIEWS={
"mv_demand":(f"""version: 0.1
source: {GOLD}.fact_demand_forecast
joins:
  - name: p
    source: {GOLD}.dim_product
    on: source.sku = p.sku
dimensions:
  - name: month
    expr: month
  - name: brand
    expr: brand
  - name: therapeutic_area
    expr: p.therapeutic_area
  - name: market
    expr: market
  - name: cluster_bu
    expr: p.cluster_bu
  - name: launch_phase
    expr: p.launch_phase
measures:
  - name: forecast_accuracy
    expr: 1 - SUM(ABS(actual_sales - consensus_forecast)) / NULLIF(SUM(actual_sales),0)
  - name: forecast_bias
    expr: SUM(consensus_forecast - actual_sales) / NULLIF(SUM(actual_sales),0)
  - name: consensus_vs_statistical_gap
    expr: (SUM(consensus_forecast) - SUM(statistical_forecast)) / NULLIF(SUM(statistical_forecast),0)
  - name: total_actual_sales
    expr: SUM(actual_sales)
  - name: total_consensus_forecast
    expr: SUM(consensus_forecast)""",
 "Demand & S&OP metrics: forecast accuracy, bias and consensus vs statistical, by brand/area/market/BU/phase/month. IT: accuratezza previsione, bias, previsione consensuale S&OP.",
 "SELECT therapeutic_area, ROUND(MEASURE(forecast_accuracy),3) fa FROM {{v}}.mv_demand GROUP BY therapeutic_area ORDER BY 1"),

"mv_launch_readiness":(f"""version: 0.1
source: {GOLD}.dim_launch
joins:
  - name: p
    source: {GOLD}.dim_product
    on: source.sku = p.sku
dimensions:
  - name: sku
    expr: sku
  - name: brand
    expr: p.brand
  - name: therapeutic_area
    expr: p.therapeutic_area
  - name: cluster_bu
    expr: cluster_bu
  - name: phase
    expr: phase
measures:
  - name: avg_launch_readiness
    expr: AVG(launch_readiness_score)
  - name: master_data_ready_rate
    expr: AVG(master_data_ready_flag)
  - name: artwork_ready_rate
    expr: AVG(artwork_ready_flag)
  - name: serialization_ready_rate
    expr: AVG(serialization_ready_flag)
  - name: num_launches
    expr: COUNT(DISTINCT launch_id)""",
 "Launch & renovation readiness (Global Demand & S&OP): overall readiness plus material-data, artwork and serialization ready rates. IT: prontezza al lancio, dati anagrafici, artwork, serializzazione.",
 "SELECT brand, ROUND(MEASURE(avg_launch_readiness),2) r, ROUND(MEASURE(master_data_ready_rate),2) md FROM {{v}}.mv_launch_readiness GROUP BY brand ORDER BY 1"),

"mv_service":(f"""version: 0.1
source: {GOLD}.fact_service
joins:
  - name: p
    source: {GOLD}.dim_product
    on: source.sku = p.sku
dimensions:
  - name: month
    expr: month
  - name: sku
    expr: sku
  - name: brand
    expr: p.brand
  - name: therapeutic_area
    expr: p.therapeutic_area
  - name: market
    expr: market
measures:
  - name: otif
    expr: AVG(otif)
  - name: total_stockout_days
    expr: SUM(stockout_days)
  - name: total_backorder_qty
    expr: SUM(backorder_qty)
  - name: total_orders
    expr: SUM(orders)""",
 "Customer service level: OTIF, stockout days, backorders by SKU/brand/market/month. IT: livello di servizio, puntualita e completezza consegne (OTIF), rotture di stock.",
 "SELECT market, ROUND(MEASURE(otif),3) otif FROM {{v}}.mv_service GROUP BY market ORDER BY 1"),

"mv_inventory":(f"""version: 0.1
source: {GOLD}.fact_inventory
joins:
  - name: p
    source: {GOLD}.dim_product
    on: source.sku = p.sku
  - name: dcx
    source: {GOLD}.dim_dc
    on: source.dc = dcx.dc
dimensions:
  - name: month
    expr: date
  - name: sku
    expr: sku
  - name: brand
    expr: p.brand
  - name: dc
    expr: dc
  - name: market
    expr: dcx.market
measures:
  - name: avg_days_of_inventory
    expr: AVG(days_of_inventory)
  - name: total_on_hand
    expr: SUM(on_hand_qty)
  - name: total_safety_stock
    expr: SUM(safety_stock_qty)
  - name: total_expiry_at_risk
    expr: SUM(expiry_at_risk_qty)""",
 "Finished-goods inventory: days of inventory (DIO), on-hand, safety stock and expiry-at-risk by SKU/DC/market/month. IT: giacenza, giorni di copertura, scorta di sicurezza, a rischio scadenza.",
 "SELECT market, ROUND(MEASURE(avg_days_of_inventory),1) dio FROM {{v}}.mv_inventory GROUP BY market ORDER BY 1"),

"mv_manufacturing":(f"""version: 0.1
source: {GOLD}.fact_oee
joins:
  - name: ln
    source: {GOLD}.dim_line
    on: source.line = ln.line
dimensions:
  - name: date
    expr: date
  - name: shift
    expr: shift
  - name: line
    expr: line
  - name: plant
    expr: ln.plant
  - name: process_step
    expr: ln.process_step
measures:
  - name: oee
    expr: AVG(oee)
  - name: availability
    expr: AVG(availability)
  - name: performance
    expr: AVG(performance)
  - name: quality
    expr: AVG(quality)
  - name: total_downtime_min
    expr: SUM(downtime_min)""",
 "Manufacturing OEE: Overall Equipment Effectiveness = Availability x Performance x Quality, plus downtime, by plant/line/process/date/shift. IT: efficienza generale impianto (OEE), disponibilita, prestazione, qualita, fermo macchina.",
 "SELECT plant, ROUND(MEASURE(oee),3) oee FROM {{v}}.mv_manufacturing GROUP BY plant ORDER BY 1"),

"mv_production":(f"""version: 0.1
source: {GOLD}.fact_batch
joins:
  - name: p
    source: {GOLD}.dim_product
    on: source.sku = p.sku
dimensions:
  - name: sku
    expr: sku
  - name: brand
    expr: p.brand
  - name: therapeutic_area
    expr: p.therapeutic_area
  - name: plant
    expr: plant
  - name: line
    expr: line
  - name: status
    expr: status
measures:
  - name: rft_rate
    expr: AVG(CAST(rft_flag AS DOUBLE))
  - name: avg_yield
    expr: AVG(yield)
  - name: schedule_adherence
    expr: SUM(actual_qty) / NULLIF(SUM(planned_qty),0)
  - name: total_planned_qty
    expr: SUM(planned_qty)
  - name: total_actual_qty
    expr: SUM(actual_qty)
  - name: batch_count
    expr: COUNT(DISTINCT batch_id)""",
 "Production & batch performance: right-first-time (RFT), yield, schedule adherence (actual/planned), volumes by SKU/plant/line. IT: produzione, buona alla prima (RFT), resa, aderenza al piano.",
 "SELECT plant, ROUND(MEASURE(rft_rate),3) rft, ROUND(MEASURE(schedule_adherence),3) adh FROM {{v}}.mv_production GROUP BY plant ORDER BY 1"),

"mv_quality":(f"""version: 0.1
source: {GOLD}.fact_deviation
joins:
  - name: b
    source: {GOLD}.fact_batch
    on: source.batch_id = b.batch_id
dimensions:
  - name: plant
    expr: b.plant
  - name: sku
    expr: b.sku
  - name: severity
    expr: severity
  - name: root_cause_category
    expr: root_cause_category
  - name: capa_status
    expr: capa_status
measures:
  - name: deviation_count
    expr: COUNT(DISTINCT deviation_id)
  - name: major_count
    expr: COUNT(DISTINCT CASE WHEN severity = 'major' THEN deviation_id END)
  - name: critical_count
    expr: COUNT(DISTINCT CASE WHEN severity = 'critical' THEN deviation_id END)
  - name: capa_on_time_rate
    expr: AVG(CASE WHEN capa_closed_date IS NOT NULL AND capa_closed_date <= capa_due_date THEN 1.0 ELSE 0.0 END)""",
 "GMP quality: deviation counts by severity and CAPA on-time rate, by plant/SKU/root-cause. IT: qualita GMP, deviazioni, gravita, azioni correttive (CAPA) puntuali.",
 "SELECT plant, MEASURE(deviation_count) dev, MEASURE(major_count) maj FROM {{v}}.mv_quality GROUP BY plant ORDER BY 1"),

"mv_reliability":(f"""version: 0.1
source: {GOLD}.fact_maintenance
joins:
  - name: eq
    source: {GOLD}.dim_equipment
    on: source.equipment = eq.equipment
dimensions:
  - name: equipment
    expr: equipment
  - name: line
    expr: eq.line
  - name: plant
    expr: eq.plant
  - name: equipment_class
    expr: eq.equipment_class
  - name: maintenance_type
    expr: maintenance_type
measures:
  - name: unplanned_downtime_hours
    expr: SUM(CASE WHEN maintenance_type = 'unplanned' THEN downtime_min ELSE 0 END) / 60.0
  - name: total_downtime_hours
    expr: SUM(downtime_min) / 60.0
  - name: mttr_min
    expr: AVG(downtime_min)
  - name: total_maintenance_cost
    expr: SUM(cost)
  - name: wo_count
    expr: COUNT(DISTINCT wo_id)""",
 "Reliability & maintenance: unplanned downtime hours, MTTR, maintenance cost and work-order counts by plant/line/equipment. IT: affidabilita, fermo macchina non pianificato, MTTR, costo manutenzione.",
 "SELECT plant, ROUND(MEASURE(unplanned_downtime_hours),1) dt, MEASURE(wo_count) wos FROM {{v}}.mv_reliability GROUP BY plant ORDER BY 1"),
}

def main():
    # drop the old plain views first
    for v in ["mv_demand","mv_launch_readiness","mv_service_inventory","mv_service","mv_inventory",
              "mv_manufacturing","mv_production","mv_quality","mv_reliability"]:
        run(f"DROP VIEW IF EXISTS {M}.{v}")
    fails=[]
    for name,(body,vc,_) in VIEWS.items():
        ddl=f"CREATE OR REPLACE VIEW {M}.{name}\nWITH METRICS LANGUAGE YAML AS $$\n{body}\n$$"
        s,info=run(ddl)
        if s!="OK": print(f"CREATE {name}: {s} -> {info}"); fails.append(name); continue
        run(f"COMMENT ON VIEW {M}.{name} IS '{vc.replace(chr(39),chr(39)*2)}'")
        print(f"CREATE {name}: OK")
    print("\n=== VERIFY (type must be METRIC_VIEW) ===")
    types=run(f"SELECT table_name, table_type FROM {CATALOG}.information_schema.tables WHERE table_schema='{SCHEMA}' AND table_name LIKE 'mv_%' ORDER BY table_name")[1]
    for tn,tt in types:
        flag="OK" if tt=="METRIC_VIEW" else "!!NOT METRIC VIEW!!"
        print(f"  {tn:24s} {tt}  {flag}")
        if tt!="METRIC_VIEW": fails.append(tn)
    print("\n=== SAMPLE MEASURE QUERIES ===")
    for name,(_,_,q) in VIEWS.items():
        s,info=run(q.format(v=M))
        print(f"  {name}: {info if s=='OK' else s+' '+str(info)}")
        if s!="OK": fails.append(name+"_query")
    if fails: print("\nFAILURES:",fails); sys.exit(1)
    print("\nALL 8 METRIC VIEWS CREATED & VERIFIED")

if __name__=="__main__": main()
