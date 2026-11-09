#!/usr/bin/env python3
"""Apply rich, bilingual table + column comments to every gold table.
These feed Genie's ontology/OntoRank, so they carry business meaning, units,
allowed values, and Italian synonyms. Run after each (re)load — CTAS drops comments.

Parameterized for Terraform. Reads from environment variables:
  DBX_PROFILE, WAREHOUSE_ID, CATALOG, SCHEMA
"""
import json, subprocess, sys, os

DBX_PROFILE = os.getenv("DBX_PROFILE", "fr-stable")
WAREHOUSE_ID = os.getenv("WAREHOUSE_ID", "797d1d487d654063")
CATALOG = os.getenv("CATALOG", "fr_stable_catalog")
SCHEMA = os.getenv("SCHEMA", "supply_chain")
CAT = f"{CATALOG}.{SCHEMA}"

def run(stmt):
    r=subprocess.run(['databricks','api','post','/api/2.0/sql/statements','--profile',DBX_PROFILE,
        '--json',json.dumps({'warehouse_id':WAREHOUSE_ID,'statement':stmt,'wait_timeout':'50s','on_wait_timeout':'CONTINUE'})],
        capture_output=True,text=True)
    try: d=json.loads(r.stdout)
    except Exception: return "ERR", r.stdout[:200]
    st=d.get('status',{}).get('state')
    if st!='SUCCEEDED': return st, d.get('status',{}).get('error',{}).get('message',str(d)[:200])
    return "OK", d.get('result',{}).get('data_array')

def esc(s): return s.replace("'","''")

# {table: (table_comment, {col: comment})}
M = {
"demo_config": ("Demo control table: the fixed 'today' anchor date and generation window for this synthetic Helivara dataset. One row.", {
  "demo_date":"The demo 'today' / as-of date. All 'this quarter', 'next 30 days', 'last month' questions are relative to this date.",
  "history_start":"First date covered by historical data.",
  "forecast_end":"Last month covered by the forward demand forecast.",
  "predicted_failure_end":"End of the forward predictive-maintenance window.",
  "rng_seed":"Random seed used to generate the synthetic data (reproducibility)."}),
"dim_date": ("Calendar dimension (one row per day) used to roll facts up to month/quarter.", {
  "date":"Calendar day.","month":"Month key (YYYY-MM).","quarter":"Fiscal quarter (e.g. 2026-Q3).",
  "day_of_week":"Day of week.","is_weekend":"True if Saturday/Sunday."}),
"dim_dc": ("Distribution centres / wholesaler nodes that hold finished-goods inventory, by market. Nodo di distribuzione.", {
  "dc":"Distribution centre name/code.","market":"Market/country this DC serves."}),
"dim_equipment": ("Production equipment master: presses, coaters, blister/packaging lines, granulators, HVAC. Anagrafica macchine.", {
  "plant":"Plant where the equipment is installed.","line":"Production line the equipment belongs to.",
  "equipment":"Equipment name/tag.","equipment_class":"Type: tablet_press, coater, blister_line, granulator, HVAC.",
  "criticality":"Business criticality: high / medium / low (drives maintenance priority)."}),
"dim_launch": ("Product launch & renovation register (launch governance): readiness of master data, serialization and artwork for launching/renovating SKUs. Lancio/rinnovo prodotto.", {
  "launch_id":"Launch identifier.","sku":"SKU being launched or renovated.","cluster_bu":"Commercial cluster / Business Unit owning the launch.",
  "planned_launch_date":"Planned go-live date.","actual_launch_date":"Actual go-live date (null if not yet launched).",
  "phase":"Launch phase: launch / renovation / phase-out.",
  "master_data_ready_flag":"Material master data readiness (0-1); low = incomplete master data blocking launch. Dati anagrafici materiale.",
  "artwork_ready_flag":"Packaging artwork readiness (0-1). Artwork/grafica di confezionamento.",
  "serialization_ready_flag":"Serialization / track-and-trace readiness (0-1), EU FMD unique identifier. Serializzazione.",
  "launch_readiness_score":"Overall launch readiness (0-1), driven by master-data/artwork/serialization; low = at-risk launch. Indice di prontezza al lancio."}),
"dim_line": ("Production line master with process step and criticality. Linea di produzione.", {
  "plant":"Plant the line is in.","line":"Line name/code.",
  "process_step":"Process step: granulation, compression, coating, packaging.","criticality":"Line criticality: high/medium/low."}),
"dim_market": ("Market/country dimension grouped into regions. Mercato.", {
  "market":"Market/country (e.g. Italy, Spain, US, EU, RoW).","region":"Region grouping."}),
"dim_plant": ("Manufacturing site master. Stabilimento.", {
  "plant":"Plant name (Valmora OSD hub, Castelverde/Castelverde Chem API, Roccalba, Riberal, Ashbury Ridge).",
  "site_type":"Site type: OSD (oral solid dose), API, packaging.","city":"City.","country":"Country."}),
"dim_product": ("Product / SKU master incl. therapeutic area, launch phase, and material-master governance status (serialization, artwork). Anagrafica prodotto.", {
  "sku":"Stock-keeping unit code.","brand":"Commercial brand (e.g. Zyvanta, Oribex, Gastrelle, Venoria).",
  "therapeutic_area":"Therapeutic area: gastroenterology, immunology, vascular, consumer_health. Area terapeutica.",
  "form":"Pharmaceutical form: tablet, capsule, sachet, lozenge, liquid.","pack_size":"Units per pack.",
  "shelf_life_months":"Shelf life in months (short shelf life drives expiry risk). Durata di conservazione.",
  "is_cold_chain":"True if the product requires cold-chain handling. Catena del freddo.",
  "launch_phase":"Lifecycle phase: pre-launch, launch, growth, mature, renovation, phase-out. Fase di ciclo di vita.",
  "launch_date":"Market launch date of the SKU.","cluster_bu":"Commercial cluster / Business Unit.",
  "material_master_status":"Material master data completeness: complete / incomplete. Stato dati anagrafici.",
  "serialization_status":"Serialization status: serialized / pending / exempt. Stato serializzazione.",
  "artwork_version":"Current packaging artwork version.","artwork_status":"Artwork approval status: approved / in-review / pending."}),
"dim_supplier": ("Supplier master for API and excipients; Castelverde Chem/Castelverde is the internal API supplier. Fornitore.", {
  "supplier":"Supplier name.","material_type":"What they supply: API or excipient.","is_internal":"True if an internal Helivara site (e.g. Castelverde Chem)."}),
"fact_batch": ("Manufactured batches/lots (GMP). Grain: one row per batch. Links planned vs actual quantity, yield and right-first-time. Lotto di produzione.", {
  "batch_id":"Unique batch/lot identifier.","sku":"SKU produced.","line":"Production line used.","plant":"Plant.",
  "start_date":"Batch start date.","end_date":"Batch end date.","planned_qty":"Planned quantity (units).",
  "actual_qty":"Actual produced quantity; below plan when yield loss or line downtime occurs. Schedule miss = actual < planned.",
  "status":"Batch status: released / on-hold / rejected.","yield":"Batch yield fraction (actual/theoretical), 0-1. Resa.",
  "rft_flag":"Right-First-Time: true if the batch met quality with no rework/deviation. RFT / buona alla prima."}),
"fact_batch_genealogy": ("Lot traceability chain: API lot -> intermediate lot -> finished lot, with quantities and yields that reconcile across tiers. Genealogia del lotto.", {
  "finished_lot":"Finished-goods lot.","intermediate_lot":"Intermediate/bulk lot consumed.","api_lot":"Active ingredient (API) lot consumed.",
  "api_supplier":"API supplier (e.g. Castelverde Chem/Castelverde).","api_qty":"API quantity (kg).","intermediate_qty":"Intermediate quantity.",
  "finished_qty":"Finished quantity.","api_yield":"Yield from API to intermediate (0-1).","intermediate_yield":"Yield from intermediate to finished (0-1)."}),
"fact_demand_forecast": ("Monthly demand: statistical baseline vs consensus S&OP forecast vs actual sales, by SKU and market. Basis for forecast accuracy and S&OP. Previsione della domanda.", {
  "sku":"SKU.","brand":"Brand.","market":"Market/country.","month":"Month (YYYY-MM).",
  "statistical_forecast":"Statistical baseline forecast (units). Previsione statistica.",
  "consensus_forecast":"Consensus S&OP forecast after review (units). Previsione consensuale S&OP.",
  "actual_sales":"Actual sales (units). Vendite effettive. Forecast accuracy = 1 - |actual-consensus|/actual (MAPE)."}),
"fact_deviation": ("GMP quality deviations raised against batches, with CAPA lifecycle. Deviazione qualita.", {
  "deviation_id":"Deviation identifier.","batch_id":"Batch the deviation was raised on.",
  "severity":"Severity: minor / major / critical. Gravita.","root_cause_category":"Root-cause category (e.g. equipment, human error, material, process).",
  "capa_status":"CAPA status: open / closed / overdue. Azione correttiva/preventiva.",
  "capa_due_date":"CAPA due date.","capa_closed_date":"CAPA closure date (null if open)."}),
"fact_equipment_telemetry": ("Daily-aggregated equipment sensor telemetry; anomaly_score rises before predicted failures. Telemetria macchina.", {
  "date":"Day.","equipment":"Equipment tag.","vibration":"Vibration level.","temperature":"Temperature (C).",
  "motor_current":"Motor current (A).","pressure":"Process pressure.","anomaly_score":"Anomaly score 0-1; higher = closer to failure. Punteggio di anomalia."}),
"fact_inventory": ("Monthly finished-goods inventory position by SKU and DC, incl. days of inventory and expiry-at-risk. Giacenza/scorte.", {
  "date":"Month (first-of-month).","sku":"SKU.","dc":"Distribution centre.","on_hand_qty":"Units on hand. Giacenza.",
  "in_transit_qty":"Units in transit.","safety_stock_qty":"Safety stock target; stockout risk when on_hand < safety_stock. Scorta di sicurezza.",
  "days_of_inventory":"Days of inventory on hand (DIO/DOH). Giorni di copertura.",
  "expiry_at_risk_qty":"Units at risk of expiring before sale (short shelf life). A rischio scadenza."}),
"fact_maintenance": ("Maintenance work orders (planned vs unplanned); unplanned WOs follow predicted failures and cause downtime. Ordine di manutenzione.", {
  "wo_id":"Work order id.","equipment":"Equipment maintained.","start_date":"WO start.","end_date":"WO end.",
  "downtime_min":"Downtime caused (minutes). Fermo macchina.","maintenance_type":"planned / unplanned. Manutenzione programmata/non programmata.",
  "failure_mode":"Failure mode addressed.","cost":"Maintenance cost (EUR)."}),
"fact_oee": ("Line performance by day and shift. OEE = Availability x Performance x Quality; downtime lowers availability. Efficienza generale dell'impianto (OEE).", {
  "date":"Day.","shift":"Shift (1/2/3).","line":"Production line.","planned_runtime_min":"Planned run time (minutes).",
  "downtime_min":"Downtime in the shift (minutes). Fermo macchina.","availability":"Availability component (0-1) = uptime/planned. Disponibilita.",
  "performance":"Performance component (0-1) = speed vs ideal. Prestazione.","quality":"Quality component (0-1) = good units/total. Qualita.",
  "oee":"Overall Equipment Effectiveness (0-1) = availability x performance x quality."}),
"fact_predicted_failure": ("Forward-looking predictive-maintenance alerts: equipment predicted to fail, with remaining useful life and risk. Guasto previsto.", {
  "predicted_failure_id":"Prediction id.","equipment":"Equipment at risk.","predicted_failure_date":"Predicted failure date.",
  "rul_days":"Remaining Useful Life in days. Vita utile residua (RUL).","risk_score":"Failure risk 0-1.","failure_mode":"Predicted failure mode."}),
"fact_qc_release": ("QC batch release records (QP release): potency/stability results, release status and cycle time. Rilascio lotto (QC).", {
  "batch_id":"Batch released.","sku":"SKU.","plant":"Plant.","release_date":"Release date.",
  "release_cycle_days":"Days from batch end to release (cycle time). Tempo di rilascio.",
  "potency_pass":"True if potency within spec.","stability_pass":"True if stability within spec.",
  "release_status":"released / on-hold / rejected. Stato di rilascio."}),
"fact_service": ("Monthly customer service level by SKU and market: OTIF, stockouts and backorders; degrades when inventory falls short from production misses. Livello di servizio.", {
  "month":"Month (YYYY-MM).","sku":"SKU.","market":"Market/country.","orders":"Order lines in the month.",
  "otif":"On-Time-In-Full: fraction of order lines delivered on time and complete (0-1). Puntualita e completezza consegne.",
  "stockout_days":"Days out of stock in the month. Giorni di rottura di stock.",
  "backorder_qty":"Units on backorder. Ordini inevasi."}),
}

def main():
    tables=run(f"SELECT table_name FROM {CATALOG}.information_schema.tables WHERE table_schema='{SCHEMA}'")[1]
    tset={t[0] for t in tables}
    fails=[]
    for t,(tc,cols) in M.items():
        if t not in tset: print("MISSING TABLE",t); fails.append(t); continue
        s,info=run(f"COMMENT ON TABLE {CAT}.{t} IS '{esc(tc)}'")
        if s!="OK": print(f"  table {t}: {s} {info}"); fails.append(t)
        for c,cc in cols.items():
            s,info=run(f"ALTER TABLE {CAT}.{t} ALTER COLUMN {c} COMMENT '{esc(cc)}'")
            if s!="OK": print(f"  col {t}.{c}: {s} {info}"); fails.append(f"{t}.{c}")
        print(f"{t}: table + {len(cols)} columns commented")
    # coverage check
    cov=run(f"SELECT COUNT(*) total, SUM(CASE WHEN comment IS NULL OR comment='' THEN 1 ELSE 0 END) missing FROM {CATALOG}.information_schema.columns WHERE table_schema='{SCHEMA}' AND column_name<>'_rescued_data'")[1]
    tcov=run(f"SELECT COUNT(*) total, SUM(CASE WHEN comment IS NULL OR comment='' THEN 1 ELSE 0 END) missing FROM {CATALOG}.information_schema.tables WHERE table_schema='{SCHEMA}'")[1]
    print(f"\nCOLUMN coverage: {int(cov[0][0])-int(cov[0][1])}/{cov[0][0]} commented ({cov[0][1]} missing)")
    print(f"TABLE coverage:  {int(tcov[0][0])-int(tcov[0][1])}/{tcov[0][0]} commented ({tcov[0][1]} missing)")
    if fails: print("FAILURES:",fails); sys.exit(1)

if __name__=="__main__": main()
