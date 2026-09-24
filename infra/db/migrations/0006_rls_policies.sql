-- ============================================================
-- FLIP v3.0 — Migration 0006: Row-Level Security (RLS) Policies
-- Multi-tenancy via current_setting('app.current_org_id', true)
-- User isolation via current_setting('app.current_user_id', true)
-- Role bypass via current_setting('app.current_role', true)
-- ============================================================

-- ============================================================
-- PRE-REQUISITE: Disable compression on hypertables that need RLS
-- TimescaleDB CANNOT have compression + RLS on the same hypertable.
-- sensor_readings and twin_events require RLS for multi-tenancy.
-- images access is controlled at API layer → keeps compression.
--
-- Order matters (idempotent — safe to re-run):
--   1. Disable RLS temporarily (so compress can be toggled)
--   2. Remove compression policies
--   3. Disable columnstore compression
--   4. Re-enable RLS on ALL required tables
-- ============================================================

-- Step 1: Temporarily disable RLS on hypertables (needed to alter compress)
ALTER TABLE sensor_readings DISABLE ROW LEVEL SECURITY;
ALTER TABLE twin_events     DISABLE ROW LEVEL SECURITY;

-- Step 2: Remove compression policies (if_exists=TRUE → no error if absent)
SELECT remove_compression_policy('sensor_readings', TRUE);
SELECT remove_compression_policy('twin_events',     TRUE);

-- Step 3: Disable columnstore compression
ALTER TABLE sensor_readings SET (timescaledb.compress = false);
ALTER TABLE twin_events     SET (timescaledb.compress = false);

-- Retention policies remain intact (no conflict with RLS)

-- ============================================================
-- Step 4: Enable RLS on all required tables
ALTER TABLE profiles        ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms           ENABLE ROW LEVEL SECURITY;
ALTER TABLE fields          ENABLE ROW LEVEL SECURITY;
ALTER TABLE devices         ENABLE ROW LEVEL SECURITY;
ALTER TABLE crop_cycles     ENABLE ROW LEVEL SECURITY;
ALTER TABLE sensor_readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE advisories      ENABLE ROW LEVEL SECURITY;
ALTER TABLE farmer_actions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE training_samples ENABLE ROW LEVEL SECURITY;
ALTER TABLE disaster_alerts ENABLE ROW LEVEL SECURITY;

-- 1. Profiles
DROP POLICY IF EXISTS profiles_org_isolation ON profiles;
CREATE POLICY profiles_org_isolation ON profiles
    USING (
        id = NULLIF(current_setting('app.current_user_id', true), '')::UUID
        OR org_id = NULLIF(current_setting('app.current_org_id', true), '')::UUID
        OR current_setting('app.current_role', true) IN ('platform_admin', 'gov_officer')
    );

-- 2. Farms
DROP POLICY IF EXISTS farms_access ON farms;
CREATE POLICY farms_access ON farms
    USING (
        farmer_id = NULLIF(current_setting('app.current_user_id', true), '')::UUID
        OR org_id = NULLIF(current_setting('app.current_org_id', true), '')::UUID
        OR current_setting('app.current_role', true) IN ('gov_officer','platform_admin')
    );

-- 3. Fields
DROP POLICY IF EXISTS fields_access ON fields;
CREATE POLICY fields_access ON fields
    USING (
        farm_id IN (
            SELECT id FROM farms WHERE 
                farmer_id = NULLIF(current_setting('app.current_user_id', true), '')::UUID
                OR org_id = NULLIF(current_setting('app.current_org_id', true), '')::UUID
                OR current_setting('app.current_role', true) IN ('gov_officer','platform_admin')
        )
    );

-- 4. Devices
DROP POLICY IF EXISTS devices_access ON devices;
CREATE POLICY devices_access ON devices
    USING (
        farm_id IN (
            SELECT id FROM farms WHERE 
                farmer_id = NULLIF(current_setting('app.current_user_id', true), '')::UUID
                OR org_id = NULLIF(current_setting('app.current_org_id', true), '')::UUID
                OR current_setting('app.current_role', true) IN ('gov_officer','platform_admin')
        )
    );

-- 5. Crop Cycles
DROP POLICY IF EXISTS crop_cycles_access ON crop_cycles;
CREATE POLICY crop_cycles_access ON crop_cycles
    USING (
        field_id IN (
            SELECT fld.id FROM fields fld
            JOIN farms f ON f.id = fld.farm_id
            WHERE f.farmer_id = NULLIF(current_setting('app.current_user_id', true), '')::UUID
               OR f.org_id = NULLIF(current_setting('app.current_org_id', true), '')::UUID
               OR current_setting('app.current_role', true) IN ('gov_officer','platform_admin','agronomist')
        )
    );

-- 6. Sensor Readings (high volume - optimized)
DROP POLICY IF EXISTS sensor_readings_access ON sensor_readings;
CREATE POLICY sensor_readings_access ON sensor_readings
    USING (
        farm_id IN (
            SELECT id FROM farms WHERE 
                farmer_id = NULLIF(current_setting('app.current_user_id', true), '')::UUID
                OR org_id = NULLIF(current_setting('app.current_org_id', true), '')::UUID
                OR current_setting('app.current_role', true) IN ('gov_officer','platform_admin')
        )
    );

-- 7. Advisories
DROP POLICY IF EXISTS advisories_access ON advisories;
CREATE POLICY advisories_access ON advisories
    USING (
        farm_id IN (
            SELECT id FROM farms WHERE 
                farmer_id = NULLIF(current_setting('app.current_user_id', true), '')::UUID
                OR org_id = NULLIF(current_setting('app.current_org_id', true), '')::UUID
        )
        OR current_setting('app.current_role', true) IN ('agronomist','platform_admin','gov_officer')
    );

-- 8. Farmer Actions
DROP POLICY IF EXISTS farmer_actions_access ON farmer_actions;
CREATE POLICY farmer_actions_access ON farmer_actions
    USING (
        farm_id IN (
            SELECT id FROM farms WHERE farmer_id = NULLIF(current_setting('app.current_user_id', true), '')::UUID
        )
        OR current_setting('app.current_role', true) IN ('agronomist','platform_admin')
    );

-- 9. Training Samples (Experts & Admin only)
DROP POLICY IF EXISTS training_samples_access ON training_samples;
CREATE POLICY training_samples_access ON training_samples
    USING (current_setting('app.current_role', true) IN ('agronomist','platform_admin'));

-- 10. Disaster Alerts (Public read, geo-filtered in API)
DROP POLICY IF EXISTS disaster_alerts_read ON disaster_alerts;
CREATE POLICY disaster_alerts_read ON disaster_alerts FOR SELECT
    USING (true);
