-- ============================================================
-- FLIP v3.0 — Migration 0005: Materialized Views & Advanced Indexes
-- ============================================================

-- 1. Farm Digital Twin Materialized View
CREATE MATERIALIZED VIEW IF NOT EXISTS farm_digital_twin AS
SELECT 
    f.id AS farm_id,
    f.name AS farm_name,
    f.geometry,
    COALESCE(
        jsonb_agg(DISTINCT jsonb_build_object(
            'field_id', fd.id,
            'crop', fd.crop_variety,
            'stage', fd.stage,
            'sowing_date', fd.sowing_date,
            'expected_harvest', fd.expected_harvest
        )) FILTER (WHERE fd.id IS NOT NULL),
        '[]'::jsonb
    ) AS fields,
    COALESCE(
        (
            SELECT jsonb_build_object(
                'soil_moisture', avg(sr.value) FILTER (WHERE st.code = 'VWC'),
                'soil_temp', avg(sr.value) FILTER (WHERE st.code = 'TEMP_SOIL'),
                'air_temp', avg(sr.value) FILTER (WHERE st.code = 'TEMP_AIR'),
                'humidity', avg(sr.value) FILTER (WHERE st.code IN ('RH', 'HUMIDITY')),
                'leaf_wetness', avg(sr.value) FILTER (WHERE st.code = 'LEAF_WETNESS'),
                'last_update', max(sr.time)
            )
            FROM sensor_readings sr
            JOIN sensor_types st ON sr.sensor_type_id = st.id
            WHERE sr.farm_id = f.id AND sr.time > now() - INTERVAL '24 hours'
              AND sr.quality_flag IN ('RAW','EKF_CORRECTED')
        ),
        '{}'::jsonb
    ) AS current_telemetry,
    COALESCE(
        (
            SELECT jsonb_agg(DISTINCT jsonb_build_object(
                'advisory_id', a.id,
                'now', a.now_text,
                'next', a.next_text,
                'why', a.why_text,
                'confidence_set', a.confidence_set,
                'expires_at', a.expires_at,
                'status', a.status
            ))
            FROM advisories a
            WHERE a.farm_id = f.id AND a.status = 'ACTIVE' AND a.expires_at > now()
        ),
        '[]'::jsonb
    ) AS active_advisories,
    COALESCE(
        (
            SELECT jsonb_agg(DISTINCT jsonb_build_object(
                'alert_id', da.id,
                'type', da.event_type,
                'severity', da.severity,
                'expires_at', da.expires_at,
                'message', da.message_template
            ))
            FROM disaster_alerts da
            WHERE ST_Intersects(da.geometry, f.geometry)
              AND da.expires_at > now()
        ),
        '[]'::jsonb
    ) AS active_disasters,
    now() AS refreshed_at
FROM farms f
LEFT JOIN fields fd ON fd.farm_id = f.id
GROUP BY f.id, f.name, f.geometry;

CREATE UNIQUE INDEX IF NOT EXISTS idx_farm_digital_twin_pk ON farm_digital_twin (farm_id);
CREATE INDEX IF NOT EXISTS idx_farm_digital_twin_geom ON farm_digital_twin USING GIST (geometry);

-- 2. Spatial & Analytical Indexes
CREATE INDEX IF NOT EXISTS idx_sensor_readings_farm_time ON sensor_readings (farm_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_training_samples_farm ON training_samples (farm_id, created_at DESC);
