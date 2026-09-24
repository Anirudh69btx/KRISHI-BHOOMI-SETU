-- ============================================================
-- FLIP v3.0 — Migration 0003: Advisories, Actions & Training Samples
-- ============================================================

-- 1. Advisories
CREATE TABLE IF NOT EXISTS advisories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID REFERENCES farms(id),
    field_id UUID REFERENCES fields(id),
    cycle_id UUID REFERENCES crop_cycles(id),
    now_text TEXT NOT NULL,
    next_text TEXT NOT NULL,
    why_text TEXT NOT NULL,
    confidence_set TEXT[] NOT NULL,
    coverage FLOAT DEFAULT 0.95,
    risk_factors JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    verification_due TIMESTAMPTZ,
    status TEXT DEFAULT 'ACTIVE',
    model_version TEXT,
    input_snapshot JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_advisories_farm_status ON advisories (farm_id, status, expires_at DESC);

-- 2. Farmer Actions
CREATE TABLE IF NOT EXISTS farmer_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    advisory_id UUID REFERENCES advisories(id),
    farm_id UUID REFERENCES farms(id),
    action_type TEXT NOT NULL CHECK (action_type IN ('IRRIGATE','SPRAY','FERTILIZE','HARVEST','NONE','CUSTOM')),
    executed_at TIMESTAMPTZ NOT NULL,
    details JSONB,
    verified BOOLEAN DEFAULT FALSE,
    verification_method TEXT,
    outcome_label TEXT,
    synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_farmer_actions_farm_time ON farmer_actions (farm_id, executed_at DESC);

-- 3. Training Samples
CREATE TABLE IF NOT EXISTS training_samples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID REFERENCES farms(id),
    field_id UUID REFERENCES fields(id),
    cycle_id UUID REFERENCES crop_cycles(id),
    input_modalities JSONB NOT NULL,
    target_label TEXT NOT NULL,
    prediction_set TEXT[],
    is_verified BOOLEAN DEFAULT FALSE,
    source TEXT CHECK (source IN ('EXPERT','FARMER_VERIFIED','AUTO_VERIFIED','SYNTHETIC')),
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_training_samples_label ON training_samples (target_label, is_verified);
