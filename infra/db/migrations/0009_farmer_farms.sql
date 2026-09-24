-- ============================================================
-- FLIP v3.0 — Migration 0009: Farmer-Farm Binding
-- ============================================================

CREATE TABLE IF NOT EXISTS farmer_farms (
    farmer_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    farm_id UUID REFERENCES farms(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'OWNER' CHECK (role IN ('OWNER','MANAGER','WORKER')),
    assigned_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (farmer_id, farm_id)
);

ALTER TABLE farmer_farms ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS farmer_farms_isolation ON farmer_farms;
CREATE POLICY farmer_farms_isolation ON farmer_farms
    USING (
        farmer_id = NULLIF(current_setting('app.current_user_id', true), '')::UUID
        OR current_setting('app.current_role', true) IN ('platform_admin', 'gov_officer')
    );
