#!/usr/bin/env python3
"""Create/patch all Discover domains + subdomains with OWNERS + bilingual descriptions,
re-assert asset assignments, and retry until the (currently 500-ing) domains service recovers.
Prints links + owner + assignment status at the end."""
import json, subprocess, time
P="fr-stable"; OWNER="5011370254861067"; WSID="7474648220918581"
HOST="https://fevm-fr-stable.cloud.databricks.com"; S="fr_stable_catalog.supply_chain"
def api(m,path,body=None):
    cmd=["databricks","api",m.lower(),path,"--profile",P]
    if body is not None: cmd+=["--json",json.dumps(body)]
    r=subprocess.run(cmd,capture_output=True,text=True)
    try: return json.loads(r.stdout)
    except: return {"_err":(r.stdout or r.stderr)[:120]}
def ex(): return {d.get("tag_key"):d for d in api("GET","/api/2.0/domains").get("domains",[])}

DESC={
 "Demand and Sales Operations":"Demand planning and Sales & Operations Planning across clusters and BUs. Governs forecast accuracy, consensus planning and launch readiness.\n\nPianificazione della domanda e S&OP per tutti i cluster e BU. Governa accuratezza delle previsioni, pianificazione consensuale e prontezza al lancio.",
 "Demand and Sales Operations/Forecast":"Statistical and consensus demand forecasts by SKU, market and month; accuracy, bias and phase-in/phase-out.\n\nPrevisioni statistiche e consensuali per SKU, mercato e mese; accuratezza, bias e fase-in/fase-out.",
 "Demand and Sales Operations/Consensus SOP":"Collaborative S&OP decisions and master-data governance (material master, serialization, artwork) for launch readiness.\n\nDecisioni S&OP collaborative e governance dei dati master (anagrafica, serializzazione, artwork) per la prontezza al lancio.",
 "Supply and Inventory":"Supply chain operations, production planning and inventory management. Governs OTIF, days of inventory, stockouts and expiry-at-risk.\n\nOperazioni della supply chain, pianificazione della produzione e gestione delle scorte. Governa OTIF, giorni di copertura, rotture di stock e rischio scadenza.",
 "Supply and Inventory/Production Planning":"Production scheduling, batch planning and schedule adherence; links predicted downtime to plan impact.\n\nProgrammazione della produzione, pianificazione lotti e aderenza al piano; collega i fermi previsti all'impatto sul piano.",
 "Supply and Inventory/Inventory and Service":"Inventory positioning, days of inventory, service-level targets and expiry risk by SKU and DC.\n\nPosizionamento scorte, giorni di copertura, livelli di servizio e rischio scadenza per SKU e centro di distribuzione.",
 "Manufacturing and Quality":"Manufacturing execution, OEE and GMP quality. Governs batch genealogy, right-first-time, QC release, deviations and CAPA.\n\nEsecuzione produttiva, OEE e qualità GMP. Governa genealogia lotti, buona-alla-prima, rilascio QC, deviazioni e CAPA.",
 "Manufacturing and Quality/Batch Execution and OEE":"OEE (availability, performance, quality), yield, right-first-time and schedule adherence by line and shift.\n\nOEE (disponibilità, prestazione, qualità), resa, buona-alla-prima e aderenza al piano per linea e turno.",
 "Manufacturing and Quality/Quality and Deviations":"QC release, deviation management and CAPA tracking by severity and root cause.\n\nRilascio QC, gestione deviazioni e CAPA per gravità e causa radice.",
 "Reliability and Maintenance":"Equipment reliability, predictive and planned maintenance and asset telemetry. Governs downtime, MTBF/MTTR, predicted failures and RUL.\n\nAffidabilità delle apparecchiature, manutenzione predittiva e pianificata e telemetria. Governa fermi, MTBF/MTTR, guasti previsti e RUL.",
 "Reliability and Maintenance/Asset Telemetry":"Equipment telemetry and anomaly detection (vibration, temperature, pressure) feeding failure prediction and RUL.\n\nTelemetria e rilevamento anomalie (vibrazione, temperatura, pressione) per previsione guasti e RUL.",
 "Reliability and Maintenance/Maintenance and Downtime":"Planned vs unplanned maintenance, downtime hours, MTTR and maintenance cost by equipment and line.\n\nManutenzione pianificata vs non pianificata, ore di fermo, MTTR e costi per apparecchiatura e linea.",
}
SUBTITLE={k:(k.split("/")[-1] if "/" in k else k) for k in DESC}
STRUCT={"Demand and Sales Operations":["Forecast","Consensus SOP"],
        "Supply and Inventory":["Production Planning","Inventory and Service"],
        "Manufacturing and Quality":["Batch Execution and OEE","Quality and Deviations"],
        "Reliability and Maintenance":["Asset Telemetry","Maintenance and Downtime"]}
ASSETS={
 "Demand and Sales Operations":["mv_demand","mv_launch_readiness","fact_demand_forecast","dim_launch","dim_product"],
 "Supply and Inventory":["mv_service","mv_inventory","fact_service","fact_inventory","dim_dc"],
 "Manufacturing and Quality":["mv_manufacturing","mv_production","mv_quality","fact_oee","fact_batch","fact_batch_genealogy","fact_qc_release","fact_deviation","dim_line"],
 "Reliability and Maintenance":["mv_reliability","fact_maintenance","fact_predicted_failure","fact_equipment_telemetry","dim_equipment"]}

def ensure_pol(k): api("POST","/api/2.1/tag-policies",{"tag_key":k,"description":f"Domain {k}","values":[{"name":k}]})
def create(key,parent=None):
    b={"tag_key":key,"subtitle":SUBTITLE[key][:280],"description":DESC[key][:4096],
       "technical_owner_ids":[OWNER],"business_owner_ids":[OWNER]}
    if parent: b["parent_domain_id"]=parent
    return api("POST","/api/2.0/domains",b).get("domain_id")
def patch(did,key):
    api("PATCH",f"/api/2.0/domains/{did}?update_mask=technical_owner_ids,business_owner_ids,description,subtitle",
        {"technical_owner_ids":[OWNER],"business_owner_ids":[OWNER],"subtitle":SUBTITLE[key][:280],"description":DESC[key][:4096]})

patched=set()
# re-assert all asset assignments once (works even while domain-create 500s)
for name,assets in ASSETS.items():
    for a in assets:
        api("POST","/api/2.1/unity-catalog/entity-tag-assignments",
            {"entity_name":f"{S}.{a}","entity_type":"tables","tag_key":name,"tag_value":name})

for attempt in range(30):
    e=ex()
    for name,subs in STRUCT.items():
        ensure_pol(name)
        if name in e:
            if name not in patched: patch(e[name]["domain_id"],name); patched.add(name)
            did=e[name]["domain_id"]
        else:
            did=create(name)
        e=ex()
        for sub in subs:
            sk=f"{name}/{sub}"
            if sk in e:
                if sk not in patched: patch(e[sk]["domain_id"],sk); patched.add(sk)
            elif did:
                ensure_pol(sk); create(sk,did)
        e=ex()
    done=sum(1 for k in DESC if k in e)
    if done>=12: print("ALL 12 DOMAINS DONE (attempt",attempt+1,")"); break
    time.sleep(150)

e=ex()
print(f"=== DOMAINS {sum(1 for k in DESC if k in e)}/12 (owner={OWNER} tech+biz) ===")
for name,subs in STRUCT.items():
    d=e.get(name)
    own = "owners OK" if d and d.get("technical_owner_ids") and d.get("business_owner_ids") else "NO OWNERS"
    print(f"{name}: {HOST+'/explore/domains/'+d['domain_id']+'?o='+WSID if d else 'MISSING(500)'}  [{own if d else ''}]")
    for sub in subs:
        sd=e.get(f"{name}/{sub}")
        print(f"   - {sub}: {HOST+'/explore/domains/'+sd['domain_id']+'?o='+WSID if sd else 'MISSING(500)'}")
