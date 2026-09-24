-- ============================================================
-- FLIP v3.0 — Migration 0001: Initial Core Schema & Extensions
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "postgis_topology";
CREATE EXTENSION IF NOT EXISTS "timescaledb";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Auth schema for identity integration
CREATE SCHEMA IF NOT EXISTS auth;
CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 1. Orgs & Profiles
CREATE TABLE IF NOT EXISTS orgs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    type TEXT CHECK (type IN ('FPO','GOVT','BUYER','EXPERT','PLATFORM')),
    district_code TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    org_id UUID REFERENCES orgs(id),
    role TEXT NOT NULL CHECK (role IN ('farmer','fpo_admin','agronomist','gov_officer','buyer','platform_admin')),
    language TEXT DEFAULT 'hi',
    preferred_channels TEXT[] DEFAULT '{}',
    keycloak_sub UUID UNIQUE,
    webauthn_credential_id BYTEA,
    last_synced_at TIMESTAMPTZ,
    last_trusted_login_at TIMESTAMPTZ,
    device_fingerprint_hash TEXT,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- 2. Farms & Fields (PostGIS)
CREATE TABLE IF NOT EXISTS farms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES orgs(id),
    farmer_id UUID REFERENCES profiles(id),
    name TEXT NOT NULL,
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,
    soil_type TEXT,
    irrigation_type TEXT,
    elevation_model BYTEA,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_farms_geo ON farms USING GIST (geometry);

CREATE TABLE IF NOT EXISTS fields (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID REFERENCES farms(id) ON DELETE CASCADE,
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,
    crop_variety TEXT,
    sowing_date DATE,
    stage TEXT,
    expected_harvest DATE,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_fields_geo ON fields USING GIST (geometry);

-- 3. Devices & Sensors
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID REFERENCES farms(id),
    field_id UUID REFERENCES fields(id),
    device_type TEXT CHECK (device_type IN ('GATEWAY','SENSOR_NODE','CAMERA','TRAP_CAMERA','STORAGE_NODE')),
    hardware_rev TEXT,
    firmware_ver TEXT,
    cert_serial TEXT UNIQUE,
    status TEXT DEFAULT 'ACTIVE',
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sensor_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT UNIQUE NOT NULL,
    unit TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS device_sensors (
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    sensor_type_id UUID REFERENCES sensor_types(id),
    position JSONB,
    calibration JSONB,
    PRIMARY KEY (device_id, sensor_type_id)
);

-- 4. Crop Cycles
CREATE TABLE IF NOT EXISTS crop_cycles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    field_id UUID REFERENCES fields(id),
    crop_variety TEXT NOT NULL,
    sowing_date DATE NOT NULL,
    stage TEXT DEFAULT 'GERMINATION',
    expected_harvest DATE,
    status TEXT DEFAULT 'ACTIVE',
    genotype_profile JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 5. Weather
CREATE TABLE IF NOT EXISTS weather_forecasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID REFERENCES farms(id),
    source TEXT,
    forecast_time TIMESTAMPTZ NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_weather_farm_time ON weather_forecasts (farm_id, forecast_time DESC);

CREATE TABLE IF NOT EXISTS weather_observations (
    id UUID DEFAULT gen_random_uuid(),
    farm_id UUID REFERENCES farms(id),
    observed_at TIMESTAMPTZ NOT NULL,
    data JSONB NOT NULL,
    source TEXT DEFAULT 'LOCAL_SENSORS',
    PRIMARY KEY (observed_at, id)
);
SELECT create_hypertable('weather_observations', 'observed_at', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);
