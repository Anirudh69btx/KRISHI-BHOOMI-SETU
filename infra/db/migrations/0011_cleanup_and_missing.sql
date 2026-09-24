-- ============================================================
-- FLIP v3.0 — Migration 0011: Hypertable Cleanup + Missing Tables
-- ============================================================
-- A. Drop unnecessary hypertables (keep exactly 4)
--    Remaining hypertables: sensor_readings, images,
--                           twin_events, weather_observations
--
-- B. Add 3 missing tables referenced in routers + seed data:
--    advisory_templates, action_verifications, disaster_dispatches
-- ============================================================

-- ============================================================
-- A. DROP UNNECESSARY HYPERTABLES (migrate data → regular tables)
--    drop_hypertable() with migrate_data=>TRUE converts the hypertable
--    back to a regular PostgreSQL table without data loss.
--    if_exists=>TRUE makes this idempotent (safe on re-run).
-- ============================================================

-- NOTE: 'farm_twin_events' may not exist in this schema
-- (we use 'twin_events'). The call is still guarded by if_exists.
DO $$
BEGIN
    -- advisories
    IF EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'advisories'
    ) THEN
        PERFORM drop_hypertable('advisories', migrate_data => TRUE);
        RAISE NOTICE 'Converted advisories back to regular table';
    END IF;

    -- disaster_alerts
    IF EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'disaster_alerts'
    ) THEN
        PERFORM drop_hypertable('disaster_alerts', migrate_data => TRUE);
        RAISE NOTICE 'Converted disaster_alerts back to regular table';
    END IF;

    -- farm_twin_events (legacy name)
    IF EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'farm_twin_events'
    ) THEN
        PERFORM drop_hypertable('farm_twin_events', migrate_data => TRUE);
        RAISE NOTICE 'Converted farm_twin_events back to regular table';
    END IF;

    -- farmer_actions
    IF EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'farmer_actions'
    ) THEN
        PERFORM drop_hypertable('farmer_actions', migrate_data => TRUE);
        RAISE NOTICE 'Converted farmer_actions back to regular table';
    END IF;

    -- training_samples
    IF EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'training_samples'
    ) THEN
        PERFORM drop_hypertable('training_samples', migrate_data => TRUE);
        RAISE NOTICE 'Converted training_samples back to regular table';
    END IF;
END $$;

-- ============================================================
-- B. ADD MISSING TABLES
-- ============================================================

-- 1. Advisory Templates
--    Crop/condition-specific advisory templates (managed by agronomists)
CREATE TABLE IF NOT EXISTS advisory_templates (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    crop_variety   TEXT        NOT NULL,
    condition_type TEXT        NOT NULL,
    template_json  JSONB       NOT NULL,
    created_at     TIMESTAMPTZ DEFAULT now(),
    UNIQUE (crop_variety, condition_type)
);

COMMENT ON TABLE advisory_templates IS
    'Agronomist-curated advisory templates indexed by crop variety and condition type';

CREATE INDEX IF NOT EXISTS idx_advisory_templates_crop
    ON advisory_templates (crop_variety, condition_type);

-- 2. Action Verifications
--    Multi-method verification chain for farmer actions
CREATE TABLE IF NOT EXISTS action_verifications (
    id                UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    farmer_action_id  UUID    NOT NULL REFERENCES farmer_actions(id) ON DELETE CASCADE,
    verified_by       UUID    REFERENCES profiles(id),
    method            TEXT    CHECK (method IN ('SENSOR', 'IMAGE', 'EXPERT', 'SELF', 'SATELLITE')),
    outcome           TEXT    CHECK (outcome IN ('SUCCESS', 'PARTIAL', 'FAILED', 'INCONCLUSIVE')),
    notes             TEXT,
    created_at        TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE action_verifications IS
    'Multi-source verification log for farmer actions (sensor/image/expert/self/satellite)';

CREATE INDEX IF NOT EXISTS idx_action_verifications_action
    ON action_verifications (farmer_action_id);
CREATE INDEX IF NOT EXISTS idx_action_verifications_outcome
    ON action_verifications (outcome, created_at DESC);

-- 3. Disaster Dispatches
--    Per-channel delivery log for disaster alerts
CREATE TABLE IF NOT EXISTS disaster_dispatches (
    id                  UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    disaster_alert_id   UUID    NOT NULL REFERENCES disaster_alerts(id) ON DELETE CASCADE,
    channel             TEXT    CHECK (channel IN ('PUSH', 'SMS', 'WHATSAPP', 'IVR', 'SIREN', 'EMAIL')),
    recipient           TEXT,
    status              TEXT    CHECK (status IN ('PENDING', 'SENT', 'DELIVERED', 'FAILED', 'READ'))
                                DEFAULT 'PENDING',
    sent_at             TIMESTAMPTZ DEFAULT now(),
    delivered_at        TIMESTAMPTZ,
    error               TEXT
);

COMMENT ON TABLE disaster_dispatches IS
    'Delivery audit log per channel per recipient for disaster alert dispatch';

CREATE INDEX IF NOT EXISTS idx_disaster_dispatches_alert
    ON disaster_dispatches (disaster_alert_id, status);
CREATE INDEX IF NOT EXISTS idx_disaster_dispatches_sent_at
    ON disaster_dispatches (sent_at DESC);

-- ============================================================
-- C. Grant permissions to application role
--    (flip_app role is created in 0001; GRANT is idempotent)
-- ============================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flip_app') THEN
        GRANT SELECT, INSERT, UPDATE ON
            advisory_templates,
            action_verifications,
            disaster_dispatches
        TO flip_app;
        RAISE NOTICE 'Granted permissions to flip_app role';
    ELSE
        RAISE NOTICE 'flip_app role not found — skipping GRANT (dev environment)';
    END IF;
END $$;

-- ============================================================
-- D. Verification query (prints summary to psql output)
-- ============================================================
SELECT
    hypertable_name,
    compression_enabled
FROM timescaledb_information.hypertables
ORDER BY hypertable_name;
