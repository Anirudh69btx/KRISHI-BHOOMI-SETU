-- ============================================================
-- FLIP v3.0 — Development Seed Data (Production Schema)
-- Idempotent (ON CONFLICT DO NOTHING)
-- ============================================================

-- 1. District & Orgs
INSERT INTO orgs (id, name, type, district_code) VALUES
    ('11111111-1111-1111-1111-111111111111', 'Krishi Vikas FPO', 'FPO', 'MH-501'),
    ('22222222-2222-2222-2222-222222222222', 'Maharashtra Agri Dept', 'GOVT', 'MH-501')
ON CONFLICT (id) DO NOTHING;

-- 2. Profiles (keycloak_sub mapped to deterministic UUIDs)
INSERT INTO profiles (id, org_id, role, language, keycloak_sub) VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', 'farmer', 'hi', 'fc000001-0000-0000-0000-000000000001'),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '11111111-1111-1111-1111-111111111111', 'fpo_admin', 'hi', 'fc000002-0000-0000-0000-000000000001'),
    ('cccccccc-cccc-cccc-cccc-cccccccccccc', '22222222-2222-2222-2222-222222222222', 'agronomist', 'en', 'fc000003-0000-0000-0000-000000000001'),
    ('dddddddd-dddd-dddd-dddd-dddddddddddd', '22222222-2222-2222-2222-222222222222', 'gov_officer', 'mr', 'fc000004-0000-0000-0000-000000000001'),
    ('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', '11111111-1111-1111-1111-111111111111', 'buyer', 'en', 'fc000005-0000-0000-0000-000000000001')
ON CONFLICT (id) DO NOTHING;

-- 3. Farm & Fields
INSERT INTO farms (id, org_id, farmer_id, name, geometry, soil_type, irrigation_type) VALUES
    ('f0000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 
     'Ramesh Farm - East Plot', 
     ST_GeomFromText('POLYGON((76.123 18.456, 76.124 18.456, 76.124 18.457, 76.123 18.457, 76.123 18.456))', 4326),
     'CLAY_LOAM', 'DRIP')
ON CONFLICT (id) DO NOTHING;

INSERT INTO fields (id, farm_id, geometry, crop_variety, sowing_date, stage, expected_harvest) VALUES
    ('f1000000-0000-0000-0000-000000000001', 'f0000000-0000-0000-0000-000000000001',
     ST_GeomFromText('POLYGON((76.123 18.456, 76.1235 18.456, 76.1235 18.4565, 76.123 18.4565, 76.123 18.456))', 4326),
     'TOMATO_HYBRID_1', '2026-06-15', 'FLOWERING', '2026-10-15'),
    ('f1000000-0000-0000-0000-000000000002', 'f0000000-0000-0000-0000-000000000001',
     ST_GeomFromText('POLYGON((76.1235 18.456, 76.124 18.456, 76.124 18.457, 76.1235 18.457, 76.1235 18.456))', 4326),
     'TOMATO_HYBRID_1', '2026-06-15', 'FLOWERING', '2026-10-15')
ON CONFLICT (id) DO NOTHING;

-- 4. Devices & Sensors
INSERT INTO devices (id, farm_id, field_id, device_type, hardware_rev, firmware_ver, cert_serial) VALUES
    ('d0000000-0000-0000-0000-000000000001', 'f0000000-0000-0000-0000-000000000001', NULL, 'GATEWAY', 'PI_ZERO_2W_v1', '1.0.0', 'CERT-GW-001'),
    ('d0000000-0000-0000-0000-000000000002', 'f0000000-0000-0000-0000-000000000001', 'f1000000-0000-0000-0000-000000000001', 'SENSOR_NODE', 'ESP32C3_v1', '1.0.0', 'CERT-SN-001'),
    ('d0000000-0000-0000-0000-000000000003', 'f0000000-0000-0000-0000-000000000001', 'f1000000-0000-0000-0000-000000000001', 'SENSOR_NODE', 'ESP32C3_v1', '1.0.0', 'CERT-SN-002'),
    ('d0000000-0000-0000-0000-000000000004', 'f0000000-0000-0000-0000-000000000001', 'f1000000-0000-0000-0000-000000000002', 'SENSOR_NODE', 'ESP32C3_v1', '1.0.0', 'CERT-SN-003')
ON CONFLICT (id) DO NOTHING;

INSERT INTO sensor_types (code, unit, description) VALUES
    ('VWC', '%', 'Volumetric Water Content'),
    ('EC', 'dS/m', 'Electrical Conductivity'),
    ('TEMP_SOIL', '°C', 'Soil Temperature'),
    ('TEMP_AIR', '°C', 'Air Temperature'),
    ('RH', '%', 'Relative Humidity'),
    ('RAIN', 'mm', 'Rainfall'),
    ('LEAF_WETNESS', '0-1', 'Leaf Wetness Duration'),
    ('PAR', 'µmol/m²/s', 'Photosynthetically Active Radiation'),
    ('WIND_SPEED', 'm/s', 'Wind Speed'),
    ('WIND_DIR', '°', 'Wind Direction'),
    ('CO2', 'ppm', 'Carbon Dioxide')
ON CONFLICT (code) DO NOTHING;

-- Gateway sensors (air + env)
INSERT INTO device_sensors (device_id, sensor_type_id, position, calibration) 
SELECT 'd0000000-0000-0000-0000-000000000001', id, '{"height_cm": 200}', '{"offset": 0, "slope": 1}'
FROM sensor_types WHERE code IN ('TEMP_AIR', 'RH', 'RAIN', 'PAR', 'WIND_SPEED', 'WIND_DIR', 'CO2')
ON CONFLICT (device_id, sensor_type_id) DO NOTHING;

-- Sensor nodes (soil + leaf)
INSERT INTO device_sensors (device_id, sensor_type_id, position, calibration)
SELECT d.id, st.id, '{"depth_cm": 30}', '{"offset": 0, "slope": 1}'
FROM devices d
CROSS JOIN sensor_types st
WHERE d.device_type = 'SENSOR_NODE' AND st.code IN ('VWC', 'EC', 'TEMP_SOIL', 'LEAF_WETNESS')
ON CONFLICT (device_id, sensor_type_id) DO NOTHING;

-- 5. Crop Cycles
INSERT INTO crop_cycles (id, field_id, crop_variety, sowing_date, stage, expected_harvest, genotype_profile) VALUES
    ('c0000000-0000-0000-0000-000000000001', 'f1000000-0000-0000-0000-000000000001', 'TOMATO_HYBRID_1', '2026-06-15', 'FLOWERING', '2026-10-15', '{"k_crop": 1.15, "root_depth_cm": 60}'),
    ('c0000000-0000-0000-0000-000000000002', 'f1000000-0000-0000-0000-000000000002', 'TOMATO_HYBRID_1', '2026-06-15', 'FLOWERING', '2026-10-15', '{"k_crop": 1.15, "root_depth_cm": 60}')
ON CONFLICT (id) DO NOTHING;

-- 6. Sample Sensor Readings for Digital Twin
INSERT INTO sensor_readings (time, farm_id, field_id, device_id, sensor_type_id, value, quality_flag)
SELECT 
    now() - INTERVAL '30 minutes',
    'f0000000-0000-0000-0000-000000000001',
    'f1000000-0000-0000-0000-000000000001',
    'd0000000-0000-0000-0000-000000000002',
    id,
    CASE 
        WHEN code = 'VWC' THEN 42.5
        WHEN code = 'TEMP_SOIL' THEN 24.8
        WHEN code = 'TEMP_AIR' THEN 27.2
        WHEN code = 'RH' THEN 88.0
        WHEN code = 'LEAF_WETNESS' THEN 0.8
        ELSE 10.0
    END,
    'RAW'
FROM sensor_types
WHERE code IN ('VWC', 'TEMP_SOIL', 'TEMP_AIR', 'RH', 'LEAF_WETNESS')
ON CONFLICT (time, farm_id, device_id, sensor_type_id) DO NOTHING;

-- 7. Sample Advisory
INSERT INTO advisories (id, farm_id, field_id, cycle_id, now_text, next_text, why_text, confidence_set, coverage, risk_factors, expires_at, verification_due, status, model_version) VALUES
    ('ad000000-0000-0000-0000-000000000001', 'f0000000-0000-0000-0000-000000000001', 'f1000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001',
     'Early Blight risk high due to humidity + leaf wetness',
     'Spray Mancozeb 2g/L today 6-8 PM',
     'Leaf wetness 7.2h + RH 92% + Temp 27°C + Blight history 2023',
     ARRAY['EARLY_BLIGHT'], 0.95,
     '{"humidity": 92, "leaf_wetness_hrs": 7.2, "temp": 27, "crop_stage": "FLOWERING"}'::jsonb,
     now() + INTERVAL '12 hours', now() + INTERVAL '7 days', 'ACTIVE', 'fusion_v3.2.1')
ON CONFLICT (id) DO NOTHING;

-- 8. Active Disaster Alert
INSERT INTO disaster_alerts (id, event_type, severity, geometry, issued_at, expires_at, message_template, source) VALUES
    ('de000000-0000-0000-0000-000000000001', 'HEATWAVE', 'WARNING',
     ST_GeomFromText('POLYGON((76.10 18.40, 76.15 18.40, 76.15 18.50, 76.10 18.50, 76.10 18.40))', 4326),
     now() - INTERVAL '1 hour', now() + INTERVAL '24 hours',
     '{"hi": "अगले 24 घंटे लू की चेतावनी। सिंचाई शाम को करें।", "mr": "पुढील 24 तास लू चेतावनी। सिंचाई संध्याकाळी करा.", "en": "Heatwave alert next 24h. Irrigate evening only."}'::jsonb,
     'IMD')
ON CONFLICT (id) DO NOTHING;

-- 9. Training Samples
INSERT INTO training_samples (farm_id, field_id, cycle_id, input_modalities, target_label, prediction_set, is_verified, source) VALUES
    ('f0000000-0000-0000-0000-000000000001', 'f1000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001',
     '{"sensor_vec": [42.5, 24.8, 27.2, 88.0], "stage": "FLOWERING"}'::jsonb,
     'EARLY_BLIGHT', ARRAY['EARLY_BLIGHT'], TRUE, 'EXPERT'),
    ('f0000000-0000-0000-0000-000000000001', 'f1000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001',
     '{"sensor_vec": [35.0, 26.0, 31.0, 65.0], "stage": "FLOWERING"}'::jsonb,
     'SPIDER_MITE', ARRAY['SPIDER_MITE'], TRUE, 'EXPERT');

-- 10. Farmer-Farm Binding
INSERT INTO farmer_farms (farmer_id, farm_id, role) VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'f0000000-0000-0000-0000-000000000001', 'OWNER')
ON CONFLICT (farmer_id, farm_id) DO NOTHING;

-- 11. Refresh Farm Digital Twin Materialized View
REFRESH MATERIALIZED VIEW farm_digital_twin;
