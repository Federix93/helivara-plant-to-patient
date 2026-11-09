"""Helivara synthetic data generator (seed 42). Helivara and all its brands are FICTIONAL.

build_tables()  -> the 21 gold-shaped tables (dims + facts), fictional names.
write_raw()     -> simulated source-system extracts for the Lakeflow pipeline:
                   sap/*.csv, mes/*.json, iot/*.json, cmms/*.csv, config/*.json (+ dirty rows).

The core section keeps the original random draw order so every table except telemetry and
maintenance is identical to the data the existing metric views and Genie agents were built on.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

DEMO_DATE = datetime(2026, 9, 22)
HISTORY_START = datetime(2024, 3, 1)
FORECAST_END = datetime(2026, 12, 31)
PREDICTED_FAILURE_END = datetime(2026, 11, 21)
HERO_EQUIPMENT = "L_OSD_001_EQ_01"


def _core(seed: int) -> dict[str, pd.DataFrame]:
    """Original generator logic (renamed). Do not reorder random draws."""
    np.random.seed(seed)


    # ============ Dimensions ============

    # EXACT 11 Helivara brands
    brands_data = {
        'sku': ['SKU_001', 'SKU_002', 'SKU_003', 'SKU_004', 'SKU_005',
                'SKU_006', 'SKU_007', 'SKU_008', 'SKU_009', 'SKU_010', 'SKU_011'],
        'brand': ['Zyvanta', 'Oribex', 'Gastrelle', 'Colvera', 'Florabis',
                  'Lactavio', 'Refluxa', 'Venoria', 'Faringel', 'Digestin', 'Citralux'],
        'therapeutic_area': ['immunology', 'immunology', 'gastroenterology', 'gastroenterology', 'gastroenterology',
                             'gastroenterology', 'gastroenterology', 'vascular', 'consumer_health', 'consumer_health', 'consumer_health'],
        'form': ['tablet', 'capsule', 'tablet', 'capsule', 'sachet',
                 'tablet', 'tablet', 'tablet', 'tablet', 'lozenge', 'sachet'],
        'pack_size': [14, 28, 20, 30, 14, 30, 14, 30, 20, 10, 10],
        'shelf_life_months': [36, 24, 36, 24, 12, 24, 24, 24, 12, 12, 12],
        'is_cold_chain': [False, False, False, False, False, False, False, False, False, False, False],
        'launch_phase': ['launch', 'phase-out', 'mature', 'mature', 'mature',
                         'mature', 'mature', 'mature', 'mature', 'mature', 'mature'],
        'launch_date': [datetime(2024, 6, 1), datetime(2022, 1, 1), datetime(2018, 1, 1), datetime(2017, 1, 1), datetime(2015, 1, 1),
                        datetime(2016, 1, 1), datetime(2019, 1, 1), datetime(2019, 1, 1), datetime(2014, 1, 1), datetime(2013, 1, 1), datetime(2014, 1, 1)],
        'cluster_bu': ['Immunology', 'Immunology', 'GI', 'GI', 'GI',
                       'GI', 'GI', 'Vascular', 'Consumer', 'Consumer', 'Consumer'],
        'material_master_status': ['incomplete', 'complete', 'complete', 'complete', 'complete',
                                   'complete', 'complete', 'complete', 'complete', 'complete', 'complete'],
        'serialization_status': ['pending', 'serialized', 'serialized', 'serialized', 'serialized',
                                 'serialized', 'serialized', 'serialized', 'exempt', 'exempt', 'exempt'],
        'artwork_version': ['v1.0', 'v1.8', 'v3.0', 'v2.5', 'v1.5',
                            'v2.0', 'v1.2', 'v2.5', 'v3.1', 'v2.8', 'v1.5'],
        'artwork_status': ['in-review', 'approved', 'approved', 'approved', 'approved',
                           'approved', 'approved', 'approved', 'approved', 'approved', 'approved']
    }
    dim_product = pd.DataFrame(brands_data)

    # Plants
    plants_data = {
        'plant': ['Valmora', 'Castelverde', 'Roccalba', 'Riberal', 'Ashbury Ridge'],
        'site_type': ['OSD', 'API', 'OSD', 'OSD', 'OSD'],
        'city': ['Valmora', 'Castelverde', 'Roccalba', 'Riberal', 'Ashbury Ridge'],
        'country': ['Italy', 'Italy', 'Italy', 'Spain', 'USA']
    }
    dim_plant = pd.DataFrame(plants_data)

    # Markets
    markets_data = {
        'market': ['Italy', 'Spain', 'EU', 'US', 'RoW'],
        'region': ['Europe', 'Europe', 'Europe', 'Americas', 'Global']
    }
    dim_market = pd.DataFrame(markets_data)

    # DCs
    dcs_data = {
        'dc': ['DC_Italy', 'DC_Spain', 'DC_EU', 'DC_US', 'DC_RoW'],
        'market': ['Italy', 'Spain', 'EU', 'US', 'RoW']
    }
    dim_dc = pd.DataFrame(dcs_data)

    # Lines
    lines_data = {
        'plant': ['Valmora', 'Valmora', 'Castelverde', 'Castelverde', 'Roccalba', 'Riberal', 'Ashbury Ridge', 'Ashbury Ridge'],
        'line': ['L_OSD_001', 'L_OSD_002', 'L_API_001', 'L_API_002', 'L_OSD_003', 'L_OSD_004', 'L_OSD_005', 'L_OSD_006'],
        'process_step': ['compression', 'packaging', 'granulation', 'processing', 'compression', 'compression', 'compression', 'packaging'],
        'criticality': ['high', 'high', 'high', 'medium', 'high', 'medium', 'high', 'medium']
    }
    dim_line = pd.DataFrame(lines_data)

    # Equipment
    equip_data = []
    equip_classes = ['tablet_press', 'coater', 'blister_line', 'granulator', 'HVAC']
    for _, line_row in dim_line.iterrows():
        plant = line_row['plant']
        line = line_row['line']
        n_equip = np.random.randint(2, 4)
        for i in range(n_equip):
            equip_data.append({
                'plant': plant,
                'line': line,
                'equipment': f"{line}_EQ_{i+1:02d}",
                'equipment_class': np.random.choice(equip_classes),
                'criticality': np.random.choice(['high', 'medium', 'low'], p=[0.3, 0.5, 0.2])
            })
    dim_equipment = pd.DataFrame(equip_data)

    # Suppliers
    suppliers_data = {
        'supplier': ['Castelverde Chem', 'Merck', 'BASF', 'Teva', 'Ajinomoto'],
        'material_type': ['API', 'excipient', 'excipient', 'API', 'excipient'],
        'is_internal': [True, False, False, False, False]
    }
    dim_supplier = pd.DataFrame(suppliers_data)

    # Launch register — ONLY 2 entries: Zyvanta (at-risk) and Oribex (phase-out)
    launch_data = [
        {
            'launch_id': 'ZYV-001',
            'sku': 'SKU_001',
            'cluster_bu': 'Immunology',
            'planned_launch_date': datetime(2024, 6, 1),
            'actual_launch_date': datetime(2024, 6, 1),
            'phase': 'launch',
            'master_data_ready_flag': 0.0,  # INCOMPLETE
            'artwork_ready_flag': 0.0,      # IN-REVIEW
            'serialization_ready_flag': 1.0, # PENDING but showing high on serialization
        },
        {
            'launch_id': 'ORB-001',
            'sku': 'SKU_002',
            'cluster_bu': 'Immunology',
            'planned_launch_date': datetime(2022, 1, 1),
            'actual_launch_date': datetime(2022, 1, 1),
            'phase': 'phase-out',
            'master_data_ready_flag': 0.9,
            'artwork_ready_flag': 0.9,
            'serialization_ready_flag': 0.9,
        }
    ]
    dim_launch = pd.DataFrame(launch_data)
    dim_launch['launch_readiness_score'] = (
        (dim_launch['master_data_ready_flag'] + dim_launch['artwork_ready_flag'] + dim_launch['serialization_ready_flag']) / 3
    )

    # Demo config
    demo_config = pd.DataFrame({
        'demo_date': [DEMO_DATE],
        'history_start': [HISTORY_START],
        'forecast_end': [FORECAST_END],
        'predicted_failure_end': [PREDICTED_FAILURE_END],
        'rng_seed': [42]
    })

    # Date dimension
    dates = pd.date_range(HISTORY_START, FORECAST_END + timedelta(days=1))
    dim_date = pd.DataFrame({
        'date': dates,
        'month': dates.strftime('%Y-%m'),
        'quarter': dates.strftime('%Y-Q%q'),
        'day_of_week': dates.strftime('%A'),
        'is_weekend': dates.day_of_week >= 5
    })

    # ============ Fact tables ============

    # fact_demand_forecast: monthly
    months_range = pd.date_range(HISTORY_START, FORECAST_END, freq='MS')
    demand_data = []
    for _, prod in dim_product.iterrows():
        sku = prod['sku']
        brand = prod['brand']
        for market in ['Italy', 'Spain', 'EU', 'US', 'RoW']:
            # Skip US sales for Oribex after 2025-11
            if brand == 'Oribex' and market == 'US':
                months_subset = [m for m in months_range if m < datetime(2025, 11, 1)]
            else:
                months_subset = months_range

            for month_date in months_subset:
                month = month_date.strftime('%Y-%m')
                # Zyvanta: ramp up from 2024 to 2026
                if brand == 'Zyvanta':
                    months_since_launch = (month_date - datetime(2024, 6, 1)).days / 30.44
                    base_vol = 500 + months_since_launch * 150
                elif brand == 'Oribex':
                    # Phase-out: declining
                    months_since_peak = (datetime(2024, 1, 1) - month_date).days / 30.44
                    base_vol = max(300 * (1 - 0.02 * months_since_peak), 50)
                else:
                    base_vol = np.random.uniform(800, 1500)

                # Seasonality & noise
                noise = np.random.normal(1.0, 0.12)
                seasonal = 1.0 + 0.15 * np.sin(2 * np.pi * month_date.month / 12)
                actual_sales = max(100, int(base_vol * seasonal * noise))

                # Forecast with MAPE
                mape_target = 0.25 if brand == 'Zyvanta' else 0.18
                consensus_forecast = int(actual_sales * np.random.normal(1.0, mape_target))
                statistical_forecast = int(actual_sales * np.random.normal(1.0, mape_target * 1.1))

                demand_data.append({
                    'sku': sku,
                    'brand': brand,
                    'market': market,
                    'month': month,
                    'statistical_forecast': max(10, statistical_forecast),
                    'consensus_forecast': max(10, consensus_forecast),
                    'actual_sales': actual_sales
                })
    fact_demand_forecast = pd.DataFrame(demand_data)

    # fact_service: monthly OTIF
    service_data = []
    for _, prod in dim_product.iterrows():
        sku = prod['sku']
        for market in ['Italy', 'Spain', 'EU', 'US', 'RoW']:
            if prod['brand'] == 'Oribex' and market == 'US':
                months_subset = [m for m in months_range if m < datetime(2025, 11, 1)]
            else:
                months_subset = months_range

            for month_date in months_subset:
                month = month_date.strftime('%Y-%m')
                base_otif = np.random.uniform(0.90, 0.94)
                if np.random.random() < 0.08:
                    base_otif = np.random.uniform(0.75, 0.85)
                    stockout_days = np.random.randint(3, 15)
                    backorder_qty = np.random.randint(100, 500)
                else:
                    stockout_days = 0
                    backorder_qty = 0

                orders = np.random.randint(20, 100)
                service_data.append({
                    'month': month,
                    'sku': sku,
                    'market': market,
                    'orders': orders,
                    'otif': base_otif,
                    'stockout_days': stockout_days,
                    'backorder_qty': backorder_qty
                })
    fact_service = pd.DataFrame(service_data)

    # fact_inventory: MONTHLY (bumped DIO to 50-70 range)
    inventory_data = []
    inv_dates = pd.date_range(HISTORY_START, FORECAST_END, freq='MS')
    for _, prod in dim_product.iterrows():
        sku = prod['sku']
        for _, dc_row in dim_dc.iterrows():
            dc = dc_row['dc']
            market = dc_row['market']
            for inv_date in inv_dates:
                on_hand = np.random.randint(1000, 5000)
                in_transit = np.random.randint(200, 1000)
                safety_stock = np.random.randint(600, 1200)
                # Target 50-70 DIO
                dio = np.random.uniform(50, 70)
                dio = np.clip(dio, 10, 150)
                expiry_risk = np.random.randint(0, int(on_hand * 0.1)) if prod['shelf_life_months'] < 24 else 0

                inventory_data.append({
                    'date': inv_date,
                    'sku': sku,
                    'dc': dc,
                    'on_hand_qty': on_hand,
                    'in_transit_qty': in_transit,
                    'safety_stock_qty': safety_stock,
                    'days_of_inventory': dio,
                    'expiry_at_risk_qty': expiry_risk
                })
    fact_inventory = pd.DataFrame(inventory_data)

    # fact_oee: daily/shift
    oee_data = []
    oee_dates = pd.date_range(datetime(2025, 3, 1), datetime(2026, 8, 31))
    for oee_date in oee_dates:
        for line in dim_line['line'].unique():
            for shift in [1, 2, 3]:
                planned_runtime = np.random.randint(400, 500)
                downtime = np.random.randint(0, 80) if np.random.random() < 0.25 else 0
                availability = max(0.5, (planned_runtime - downtime) / planned_runtime)
                performance = np.random.uniform(0.75, 0.95)
                quality = np.random.uniform(0.88, 0.98)
                oee = availability * performance * quality
                oee = np.clip(oee, 0.55, 0.80)

                oee_data.append({
                    'date': oee_date,
                    'shift': shift,
                    'line': line,
                    'planned_runtime_min': planned_runtime,
                    'downtime_min': downtime,
                    'availability': availability,
                    'performance': performance,
                    'quality': quality,
                    'oee': oee
                })
    fact_oee = pd.DataFrame(oee_data)

    # Normalize OEE to 0.60-0.72 range
    avg_oee = fact_oee['oee'].mean()
    if avg_oee < 0.60:
        fact_oee['oee'] = fact_oee['oee'] * (0.66 / avg_oee)
    elif avg_oee > 0.72:
        fact_oee['oee'] = fact_oee['oee'] * (0.66 / avg_oee)
    fact_oee['oee'] = np.clip(fact_oee['oee'], 0.55, 0.80)

    # fact_batch
    batch_data = []
    batch_dates = pd.date_range(datetime(2025, 3, 1), datetime(2026, 9, 30), freq='D')
    batch_id = 1
    for batch_date in batch_dates:
        n_batches_today = np.random.randint(2, 8)
        for _ in range(n_batches_today):
            sku = np.random.choice(dim_product['sku'].values)
            line = np.random.choice(dim_line['line'].values)
            plant = dim_line[dim_line['line'] == line]['plant'].iloc[0]

            planned_qty = np.random.randint(500, 5000)
            yield_rate = np.random.uniform(0.90, 0.98)
            actual_qty = int(planned_qty * yield_rate)

            if np.random.random() < 0.20:
                actual_qty = int(planned_qty * np.random.uniform(0.70, 0.95))

            rft_flag = np.random.random() < 0.92
            status = np.random.choice(['released', 'on-hold', 'rejected'], p=[0.88, 0.08, 0.04])

            batch_data.append({
                'batch_id': f"BATCH_{batch_id:06d}",
                'sku': sku,
                'line': line,
                'plant': plant,
                'start_date': batch_date,
                'end_date': batch_date + timedelta(hours=np.random.randint(4, 48)),
                'planned_qty': planned_qty,
                'actual_qty': actual_qty,
                'status': status,
                'yield': yield_rate,
                'rft_flag': rft_flag
            })
            batch_id += 1
    fact_batch = pd.DataFrame(batch_data)

    # fact_batch_genealogy
    genealogy_data = []
    for _, batch in fact_batch.head(len(fact_batch)).iterrows():
        if np.random.random() < 0.85:
            api_qty = np.random.randint(100, 1000)
            api_yield = np.random.uniform(0.95, 0.99)
            intermediate_qty = int(api_qty * api_yield)
            intermediate_yield = np.random.uniform(0.96, 0.99)
            finished_qty = int(intermediate_qty * intermediate_yield)

            genealogy_data.append({
                'finished_lot': batch['batch_id'],
                'intermediate_lot': f"INTL_{batch['batch_id']}",
                'api_lot': f"API_{batch['batch_id']}",
                'api_supplier': np.random.choice(dim_supplier[dim_supplier['material_type'] == 'API']['supplier'].values),
                'api_qty': api_qty,
                'intermediate_qty': intermediate_qty,
                'finished_qty': finished_qty,
                'api_yield': api_yield,
                'intermediate_yield': intermediate_yield
            })
    fact_batch_genealogy = pd.DataFrame(genealogy_data)

    # fact_qc_release
    qc_data = []
    for _, batch in fact_batch.iterrows():
        potency_pass = np.random.random() < 0.96
        stability_pass = np.random.random() < 0.94
        release_status = 'released' if (potency_pass and stability_pass) else ('on-hold' if np.random.random() < 0.5 else 'rejected')
        release_cycle_days = np.random.randint(3, 21)

        qc_data.append({
            'batch_id': batch['batch_id'],
            'sku': batch['sku'],
            'plant': batch['plant'],
            'release_date': batch['end_date'] + timedelta(days=release_cycle_days),
            'release_cycle_days': release_cycle_days,
            'potency_pass': potency_pass,
            'stability_pass': stability_pass,
            'release_status': release_status
        })
    fact_qc_release = pd.DataFrame(qc_data)

    # fact_maintenance
    maintenance_data = []
    maint_dates = pd.date_range(datetime(2025, 3, 1), DEMO_DATE)
    wo_id = 1
    for maint_date in maint_dates:
        if np.random.random() < 0.15:
            equipment = np.random.choice(dim_equipment['equipment'].values)
            downtime_min = np.random.randint(30, 480)
            maintenance_type = 'unplanned' if np.random.random() < 0.35 else 'planned'
            failure_mode = np.random.choice(['bearing_failure', 'motor_issue', 'seal_leak', 'calibration'])
            cost = int(downtime_min * np.random.uniform(2, 10))

            maintenance_data.append({
                'wo_id': f"WO_{wo_id:06d}",
                'equipment': equipment,
                'start_date': maint_date,
                'end_date': maint_date + timedelta(minutes=downtime_min),
                'downtime_min': downtime_min,
                'maintenance_type': maintenance_type,
                'failure_mode': failure_mode,
                'cost': cost
            })
            wo_id += 1
    fact_maintenance = pd.DataFrame(maintenance_data)

    # fact_predicted_failure
    pf_data = []
    pf_id = 1
    for _, equip in dim_equipment.iterrows():
        if np.random.random() < 0.40:
            n_preds = np.random.randint(1, 3)
            for _ in range(n_preds):
                pred_date = DEMO_DATE + timedelta(days=np.random.randint(1, 61))
                if pred_date <= PREDICTED_FAILURE_END:
                    pf_data.append({
                        'predicted_failure_id': f"PF_{pf_id:06d}",
                        'equipment': equip['equipment'],
                        'predicted_failure_date': pred_date,
                        'rul_days': (pred_date - DEMO_DATE).days,
                        'risk_score': np.random.uniform(0.5, 0.95),
                        'failure_mode': np.random.choice(['bearing', 'motor', 'seal', 'calibration'])
                    })
                    pf_id += 1
    fact_predicted_failure = pd.DataFrame(pf_data)

    # fact_equipment_telemetry
    telemetry_data = []
    telemetry_dates = pd.date_range(datetime(2025, 9, 1), DEMO_DATE)
    for tel_date in telemetry_dates:
        for _, equip in dim_equipment.iterrows():
            vibration = np.random.uniform(2.0, 8.0)
            temperature = np.random.uniform(45, 75)
            motor_current = np.random.uniform(10, 50)
            pressure = np.random.uniform(20, 100)
            anomaly_score = (vibration / 10.0 + (temperature - 50) / 50.0) / 2.0
            anomaly_score = np.clip(anomaly_score, 0, 1)

            telemetry_data.append({
                'date': tel_date,
                'equipment': equip['equipment'],
                'vibration': round(vibration, 2),
                'temperature': round(temperature, 1),
                'motor_current': round(motor_current, 1),
                'pressure': round(pressure, 1),
                'anomaly_score': round(anomaly_score, 3)
            })
    fact_equipment_telemetry = pd.DataFrame(telemetry_data)

    # fact_deviation
    deviation_data = []
    dev_id = 1
    for _, batch in fact_batch.iterrows():
        if np.random.random() < 0.12:
            n_devs = np.random.randint(1, 3)
            for _ in range(n_devs):
                severity = np.random.choice(['minor', 'major', 'critical'], p=[0.60, 0.35, 0.05])
                capa_status = np.random.choice(['open', 'closed', 'overdue'], p=[0.15, 0.80, 0.05])
                capa_due_date = batch['end_date'] + timedelta(days=np.random.randint(10, 60))
                capa_closed_date = None
                if capa_status == 'closed':
                    capa_closed_date = capa_due_date - timedelta(days=np.random.randint(0, 30))

                deviation_data.append({
                    'deviation_id': f"DEV_{dev_id:06d}",
                    'batch_id': batch['batch_id'],
                    'severity': severity,
                    'root_cause_category': np.random.choice(['equipment', 'human_error', 'material', 'process']),
                    'capa_status': capa_status,
                    'capa_due_date': capa_due_date,
                    'capa_closed_date': capa_closed_date
                })
                dev_id += 1
    fact_deviation = pd.DataFrame(deviation_data)

    return {k: v for k, v in locals().items()
            if isinstance(v, pd.DataFrame) and (k.startswith("dim_") or k.startswith("fact_")
                                                or k == "demo_config")}


def _routing(dim_product: pd.DataFrame, dim_line: pd.DataFrame) -> pd.DataFrame:
    """Deterministic primary production line per SKU (no RNG). SKU_001 → Valmora coating line."""
    osd = dim_line[dim_line.line.str.startswith("L_OSD")].reset_index(drop=True)
    rows = []
    for i, sku in enumerate(dim_product.sku):
        line = osd.loc[0] if sku == "SKU_001" else osd.loc[1 + (i % (len(osd) - 1))]
        rows.append({"sku": sku, "primary_line": line.line, "plant": line.plant,
                     "process_step": line.process_step})
    return pd.DataFrame(rows)


def _extra_failures(maint: pd.DataFrame, dim_equipment: pd.DataFrame, n: int = 75) -> pd.DataFrame:
    rng = np.random.default_rng(4242)
    eqs = [e for e in dim_equipment.equipment if e != HERO_EQUIPMENT]
    days = pd.date_range("2025-09-15", "2026-09-01")
    start_id = int(maint.wo_id.str[3:].astype(int).max()) + 1
    rows = []
    for k in range(n):
        start = pd.Timestamp(rng.choice(days))
        dt = int(rng.integers(60, 600))
        rows.append({"wo_id": f"WO_{start_id + k:06d}", "equipment": rng.choice(eqs),
                     "start_date": start, "end_date": start + timedelta(minutes=dt),
                     "downtime_min": dt, "maintenance_type": "unplanned",
                     "failure_mode": rng.choice(["bearing_failure", "motor_issue", "seal_leak", "calibration"]),
                     "cost": int(dt * rng.uniform(2, 10))})
    out = pd.concat([maint, pd.DataFrame(rows)], ignore_index=True)
    return out.sort_values(["start_date", "wo_id"]).reset_index(drop=True)


def _telemetry(dim_equipment: pd.DataFrame, maint: pd.DataFrame) -> pd.DataFrame:
    """Daily telemetry with a wear ramp over the 30 days before each unplanned failure (quadratic:
    faint a month out, strong in the last week)."""
    rng = np.random.default_rng(777)
    dates = pd.date_range("2025-09-01", DEMO_DATE)
    fails = maint[maint.maintenance_type == "unplanned"]
    frames = []
    for eq in dim_equipment.equipment:
        n = len(dates)
        # stable per-machine baseline + day-to-day sensor noise
        vib = rng.uniform(3.0, 6.0) * (1 + rng.normal(0, 0.10, n))
        temp = rng.uniform(50, 65) + rng.normal(0, 2.0, n)
        cur = rng.uniform(20, 40) * (1 + rng.normal(0, 0.08, n))
        pres = rng.uniform(40, 80) * (1 + rng.normal(0, 0.05, n))
        ramp = np.zeros(n)
        fdays = pd.to_datetime(fails[fails.equipment == eq].start_date).dt.normalize()
        for fd in fdays:
            d = (fd - dates).days.values
            win = (d > 0) & (d <= 30)
            ramp = np.maximum(ramp, np.where(win, ((31 - d) / 30.0) ** 2, 0))
        if eq == HERO_EQUIPMENT:
            d = (pd.Timestamp(DEMO_DATE) - dates).days.values
            ramp = np.maximum(ramp, np.where(d < 14, (14 - d) / 14.0, 0))
        k_v, k_t, k_c = rng.uniform(0.4, 0.8), rng.uniform(5, 10), rng.uniform(0.15, 0.30)
        vib = vib * (1 + k_v * ramp)
        temp = temp + k_t * ramp
        cur = cur * (1 + k_c * ramp)
        anomaly = np.clip((vib / 10.0 + (temp - 50) / 50.0) / 2.0, 0, 1)
        frames.append(pd.DataFrame({"date": dates, "equipment": eq, "vibration": vib.round(2),
                                    "temperature": temp.round(1), "motor_current": cur.round(1),
                                    "pressure": pres.round(1), "anomaly_score": anomaly.round(3)}))
    return pd.concat(frames, ignore_index=True)


def build_tables(seed: int = 42) -> dict[str, pd.DataFrame]:
    t = _core(seed)
    t.pop("fact_predicted_failure", None)  # now produced by the ML model
    dl = t["dim_line"]
    dl.loc[dl.line == "L_OSD_001", "process_step"] = "coating"
    de = t["dim_equipment"]
    de.loc[de.equipment == HERO_EQUIPMENT, ["equipment_class", "criticality"]] = ["coater", "high"]
    t["dim_routing"] = _routing(t["dim_product"], dl)
    t["fact_maintenance"] = _extra_failures(t["fact_maintenance"], de)
    t["fact_equipment_telemetry"] = _telemetry(de, t["fact_maintenance"])
    return t


RAW_LAYOUT = {
    "sap": ("csv", ["dim_date", "dim_dc", "dim_line", "dim_market", "dim_plant", "dim_product",
                    "dim_supplier", "dim_launch", "dim_routing", "dim_equipment",
                    "fact_demand_forecast", "fact_inventory", "fact_service"]),
    "mes": ("json", ["fact_batch", "fact_batch_genealogy", "fact_oee", "fact_qc_release", "fact_deviation"]),
    "iot": ("json", ["fact_equipment_telemetry"]),
    "cmms": ("csv", ["fact_maintenance"]),
    "config": ("json", ["demo_config"]),
}

# (column to corrupt, corruption) per fact table — mirrors the pipeline's expectations
DIRTY_RULES = {
    "fact_demand_forecast": ("actual_sales", "negative"), "fact_inventory": ("on_hand_qty", "negative"),
    "fact_service": ("sku", "null"), "fact_batch": ("batch_id", "duplicate"),
    "fact_batch_genealogy": ("finished_lot", "null"), "fact_oee": ("availability", "out_of_range"),
    "fact_qc_release": ("batch_id", "null"), "fact_deviation": ("deviation_id", "duplicate"),
    "fact_equipment_telemetry": ("vibration", "out_of_range"), "fact_maintenance": ("downtime_min", "negative"),
}


def _dirty(df: pd.DataFrame, col: str, kind: str, n: int, rng) -> pd.DataFrame:
    bad = df.sample(n=n, random_state=int(rng.integers(1e9))).copy()
    if kind == "negative":
        bad[col] = -bad[col].abs() - 1
    elif kind == "null":
        bad[col] = None
    elif kind == "out_of_range":
        bad[col] = 999.0
    # "duplicate": an exact copy of an existing business key
    return bad


def write_raw(tables: dict[str, pd.DataFrame], out_dir: Path, dirty_rate: float = 0.015) -> dict[str, Path]:
    out_dir = Path(out_dir)
    rng = np.random.default_rng(99)
    manifest, paths = {}, {}
    for system, (fmt, names_) in RAW_LAYOUT.items():
        (out_dir / system).mkdir(parents=True, exist_ok=True)
        for name in names_:
            df = tables[name]
            if name in DIRTY_RULES:
                col, kind = DIRTY_RULES[name]
                n = max(1, int(round(len(df) * dirty_rate)))
                df = pd.concat([df, _dirty(df, col, kind, n, rng)], ignore_index=True)
                manifest[name] = n
            (out_dir / system / name).mkdir(parents=True, exist_ok=True)
            p = out_dir / system / name / f"{name}.{fmt}"
            if fmt == "csv":
                df.to_csv(p, index=False)
            else:
                df.to_json(p, orient="records", lines=True, date_format="iso")
            paths[name] = p
    (out_dir / "_dirty_manifest.json").write_text(json.dumps(manifest, indent=1))
    return paths


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "raw_out")
    tabs = build_tables()
    for k, p in write_raw(tabs, target).items():
        print(f"{k:28s} {len(tabs[k]):7d} rows -> {p}")
