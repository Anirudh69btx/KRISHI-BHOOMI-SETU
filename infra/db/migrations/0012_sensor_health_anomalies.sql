-- ============================================================
-- FLIP v3.0 — Migration 0012: Sensor Health + Anomaly Detection
-- ============================================================
-- Adds:
--   1. device_sensors health columns (health_score, factors, timestamps)
--   2. sensor_anomalies hypertable   (EKF + Isolation Forest events)
--   3. maintenance_tickets table     (field service workflow)
--   4. Continuous aggregate + retention policies
--   5. pg_notify trigger for health degradation events
-- All statements are idempotent (safe to re-run).
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- 1. DEVICE_SENSORS — health score columns
-- ────────────────────────────────────────────────────────────
ALTER TABLE device_sensors
    ADD COLUMN IF NOT EXISTS health_score        INTEGER     DEFAULT 100
                                                 CHECK (health_score BETWEEN 0 AND 100),
    ADD COLUMN IF NOT EXISTS last_health_check   TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS health_factors      JSONB       DEFAULT '{}';

COMMENT ON COLUMN device_sensors.health_score IS
    'Composite 0-100 sensor health score. < 60 triggers maintenance ticket.';
COMMENT ON COLUMN device_sensors.health_factors IS
    'Breakdown: {anomaly_freq, battery_trend, rssi, calibration_age, data_completeness}';

-- ────────────────────────────────────────────────────────────
-- 2. SENSOR_ANOMALIES hypertable
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sensor_anomalies (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id             UUID            REFERENCES farms(id) ON DELETE CASCADE,
    device_id           UUID            REFERENCES devices(id) ON DELETE CASCADE,
    sensor_type_id      UUID            REFERENCES sensor_types(id),
    detected_at         TIMESTAMPTZ     NOT NULL DEFAULT now(),
    anomaly_type        TEXT            NOT NULL
                                        CHECK (anomaly_type IN (
                                            'EKF_POINT',
                                            'ISOLATION_FOREST',
                                            'MULTIVARIATE_DRIFT'
                                        )),
    severity            TEXT            NOT NULL DEFAULT 'WARNING'
                                        CHECK (severity IN ('INFO','WARNING','CRITICAL')),
    raw_value           DOUBLE PRECISION,
    expected_value      DOUBLE PRECISION,
    residual            DOUBLE PRECISION,
    anomaly_score       DOUBLE PRECISION,
    ekf_covariance      DOUBLE PRECISION,
    sensor_snapshot     JSONB,
    acknowledged        BOOLEAN         DEFAULT FALSE,
    acknowledged_by     UUID            REFERENCES profiles(id),
    acknowledged_at     TIMESTAMPTZ
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'sensor_anomalies'
    ) THEN
        PERFORM create_hypertable(
            'sensor_anomalies',
            'detected_at',
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        );
        RAISE NOTICE 'sensor_anomalies hypertable created';
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_anomalies_farm_time
    ON sensor_anomalies (farm_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomalies_device_time
    ON sensor_anomalies (device_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomalies_type_sev
    ON sensor_anomalies (anomaly_type, severity, detected_at DESC);

COMMENT ON TABLE sensor_anomalies IS
    'Anomaly events from Edge EKF (point) and Cloud Isolation Forest (batch) detectors.';

-- ────────────────────────────────────────────────────────────
-- 3. MAINTENANCE_TICKETS table
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS maintenance_tickets (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id                 UUID        REFERENCES farms(id) ON DELETE CASCADE,
    device_id               UUID        REFERENCES devices(id) ON DELETE SET NULL,
    sensor_type_id          UUID        REFERENCES sensor_types(id),
    ticket_type             TEXT        NOT NULL
                                        CHECK (ticket_type IN (
                                            'CALIBRATION',
                                            'BATTERY_REPLACE',
                                            'HARDWARE_REPAIR',
                                            'REPOSITION'
                                        )),
    priority                TEXT        NOT NULL DEFAULT 'MEDIUM'
                                        CHECK (priority IN ('LOW','MEDIUM','HIGH','URGENT')),
    description             TEXT,
    status                  TEXT        NOT NULL DEFAULT 'OPEN'
                                        CHECK (status IN (
                                            'OPEN','ASSIGNED','IN_PROGRESS','RESOLVED','CLOSED'
                                        )),
    health_score_at_creation INTEGER    CHECK (health_score_at_creation BETWEEN 0 AND 100),
    created_at              TIMESTAMPTZ DEFAULT now(),
    assigned_to             UUID        REFERENCES profiles(id),
    resolved_at             TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tickets_farm_status
    ON maintenance_tickets (farm_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_device
    ON maintenance_tickets (device_id, status);

COMMENT ON TABLE maintenance_tickets IS
    'Field service tickets auto-created when sensor health_score drops below 60.';

-- ────────────────────────────────────────────────────────────
-- 4. Continuous Aggregate — hourly anomaly counts per farm
-- ────────────────────────────────────────────────────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS anomaly_counts_1h
WITH (timescaledb.continuous) AS
    SELECT
        time_bucket('1 hour', detected_at)  AS bucket,
        farm_id,
        anomaly_type,
        severity,
        count(*)                            AS anomaly_count
    FROM sensor_anomalies
    GROUP BY bucket, farm_id, anomaly_type, severity
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'anomaly_counts_1h',
    start_offset      => INTERVAL '3 hours',
    end_offset        => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '30 minutes',
    if_not_exists     => TRUE
);

-- Retention: auto-drop anomaly events older than 90 days
SELECT add_retention_policy(
    'sensor_anomalies',
    INTERVAL '90 days',
    if_not_exists => TRUE
);

-- ────────────────────────────────────────────────────────────
-- 5. pg_notify trigger — fire when health_score drops below 60
-- ────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION notify_sensor_health_degraded()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.health_score < 60)
    AND (OLD.health_score IS NULL OR OLD.health_score >= 60) THEN
        PERFORM pg_notify(
            'nats_bridge',
            json_build_object(
                'table',      'device_sensors',
                'operation',  'HEALTH_DEGRADED',
                'record',     row_to_json(NEW),
                'old_record', row_to_json(OLD),
                'timestamp',  now()
            )::text
        );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sensor_health_degraded ON device_sensors;
CREATE TRIGGER trg_sensor_health_degraded
    AFTER UPDATE OF health_score ON device_sensors
    FOR EACH ROW
    EXECUTE FUNCTION notify_sensor_health_degraded();

DO $$
BEGIN
    RAISE NOTICE 'Migration 0012 complete: sensor health + anomaly detection schema ready';
END $$;

