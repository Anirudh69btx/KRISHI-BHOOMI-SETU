-- ============================================================
-- FLIP v3.0 — Migration 0007: Functions & Triggers (NATS Bridge & Refresh)
-- ============================================================

-- 1. Updated_at trigger
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS orgs_updated_at ON orgs;
CREATE TRIGGER orgs_updated_at BEFORE UPDATE ON orgs FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS profiles_updated_at ON profiles;
CREATE TRIGGER profiles_updated_at BEFORE UPDATE ON profiles FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS farms_updated_at ON farms;
CREATE TRIGGER farms_updated_at BEFORE UPDATE ON farms FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS fields_updated_at ON fields;
CREATE TRIGGER fields_updated_at BEFORE UPDATE ON fields FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS devices_updated_at ON devices;
CREATE TRIGGER devices_updated_at BEFORE UPDATE ON devices FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS crop_cycles_updated_at ON crop_cycles;
CREATE TRIGGER crop_cycles_updated_at BEFORE UPDATE ON crop_cycles FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS advisories_updated_at ON advisories;
CREATE TRIGGER advisories_updated_at BEFORE UPDATE ON advisories FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 2. NATS Event Notifier (pg_notify → NATS bridge)
CREATE OR REPLACE FUNCTION notify_nats_event()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    payload JSONB;
BEGIN
    payload = jsonb_build_object(
        'table', TG_TABLE_NAME,
        'operation', TG_OP,
        'record', to_jsonb(NEW),
        'old_record', CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) ELSE NULL END,
        'timestamp', now()
    );
    PERFORM pg_notify('nats_bridge', payload::text);
    RETURN NEW;
END $$;

-- Apply NATS bridge triggers to key event tables
DROP TRIGGER IF EXISTS twin_events_nats ON twin_events;
CREATE TRIGGER twin_events_nats
    AFTER INSERT ON twin_events FOR EACH ROW EXECUTE FUNCTION notify_nats_event();

DROP TRIGGER IF EXISTS advisories_nats ON advisories;
CREATE TRIGGER advisories_nats
    AFTER INSERT OR UPDATE ON advisories FOR EACH ROW EXECUTE FUNCTION notify_nats_event();

DROP TRIGGER IF EXISTS farmer_actions_nats ON farmer_actions;
CREATE TRIGGER farmer_actions_nats
    AFTER INSERT ON farmer_actions FOR EACH ROW EXECUTE FUNCTION notify_nats_event();

-- NOTE: sensor_readings NATS bridge is handled at the API/ingestion layer.
-- A row-level trigger on a high-volume hypertable with RLS causes performance
-- degradation. The ingest service publishes directly to NATS JetStream instead.

-- 3. Refresh Farm Digital Twin
-- TimescaleDB hypertables do NOT support FOR EACH STATEMENT triggers.
-- Use a TimescaleDB background job (runs every 15 minutes) instead.
CREATE OR REPLACE FUNCTION refresh_farm_digital_twin_job(job_id INT, config JSONB)
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    BEGIN
        REFRESH MATERIALIZED VIEW CONCURRENTLY farm_digital_twin;
    EXCEPTION WHEN OTHERS THEN
        -- Fallback: non-concurrent refresh (locks briefly)
        REFRESH MATERIALIZED VIEW farm_digital_twin;
    END;
END $$;

-- Schedule: refresh digital twin every 15 minutes
SELECT add_job(
    'refresh_farm_digital_twin_job',
    INTERVAL '15 minutes',
    config => '{}'::JSONB
);

-- 4. Spatial helper: find farms within radius in meters
CREATE OR REPLACE FUNCTION farms_within_radius(center GEOGRAPHY, radius_m FLOAT)
RETURNS SETOF farms LANGUAGE sql AS $$
    SELECT * FROM farms WHERE ST_DWithin(geography(geometry), center, radius_m);
$$;
