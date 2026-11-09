-- Lakebase (Postgres) schema for the Control Tower app. Idempotent.
CREATE SCHEMA IF NOT EXISTS control_tower;

-- serving tables (refreshed from gold by the helivara_daily job; upsert by primary key)
CREATE TABLE IF NOT EXISTS control_tower.launch_risk_board (
  launch_id TEXT PRIMARY KEY, sku TEXT, brand TEXT, therapeutic_area TEXT, phase TEXT,
  readiness DOUBLE PRECISION, master_data_ready DOUBLE PRECISION, artwork_ready DOUBLE PRECISION,
  serialization_ready DOUBLE PRECISION, blocking_gates TEXT, revenue_at_risk_eur DOUBLE PRECISION,
  brief_en TEXT, brief_it TEXT, primary_line TEXT, plant TEXT, linked_equipment TEXT,
  linked_failure_prob DOUBLE PRECISION, refreshed_at TIMESTAMPTZ);

CREATE TABLE IF NOT EXISTS control_tower.equipment_risk (
  equipment TEXT PRIMARY KEY, plant TEXT, line TEXT, equipment_class TEXT, criticality TEXT,
  failure_prob_30d DOUBLE PRECISION, rul_days INTEGER, top_driver TEXT, impacted_brands TEXT,
  refreshed_at TIMESTAMPTZ);

-- operational table written by the app (system of record for decisions; copied back to Delta)
CREATE TABLE IF NOT EXISTS control_tower.actions (
  action_id BIGSERIAL PRIMARY KEY,
  launch_id TEXT NOT NULL,
  action_type TEXT NOT NULL CHECK (action_type IN ('escalate_master_data', 'escalate_artwork', 'book_maintenance')),
  equipment TEXT,
  owner TEXT NOT NULL,
  due_date DATE NOT NULL,
  note TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'done', 'cancelled')),
  created_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now());

-- one OPEN action per (launch, action type): a double click cannot create duplicates
CREATE UNIQUE INDEX IF NOT EXISTS actions_one_open_per_type
  ON control_tower.actions (launch_id, action_type) WHERE status = 'open';
