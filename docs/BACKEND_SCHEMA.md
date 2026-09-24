# FLIP v3.0 — Backend Database Schema Reference

> **Database Engines**: PostgreSQL 16 + TimescaleDB 2.14 + PostGIS 3.4 + pgvector 0.7  
> **Source of Truth**: `infra/db/migrations/0001_initial_schema.sql` through `0008_auth_enhancements.sql`  

---

## 1. Core Relational Tables

### 1.1 Organizations & Profiles
```sql
CREATE TABLE orgs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('FPO', 'GOVT', 'BUYER', 'EXPERT', 'PARTNER', 'PLATFORM')),
    district_code TEXT,
    state_code TEXT,
    contact_person TEXT,
    contact_phone TEXT,
    contact_email TEXT,
    gst_number TEXT,
    fpo_registration_number TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id UUID,
    keycloak_sub UUID UNIQUE,                     -- Segment 01: OIDC Subject ID
    org_id UUID REFERENCES orgs(id) ON DELETE SET NULL,
    role TEXT NOT NULL CHECK (role IN ('farmer', 'fpo_admin', 'fpo_member', 'agronomist', 'gov_officer', 'buyer', 'logistics', 'platform_admin', 'device')),
    full_name TEXT,
    phone TEXT,
    language TEXT DEFAULT 'hi' CHECK (language IN ('hi', 'en', 'mr', 'te', 'kn', 'gu', 'pa', 'bn', 'or', 'as', 'ta', 'ml')),
    preferred_channels TEXT[] DEFAULT ARRAY['PUSH'] CHECK (preferred_channels <@ ARRAY['PUSH', 'SMS', 'WHATSAPP', 'IVR', 'EMAIL']),
    avatar_url TEXT,
    mfa_enabled BOOLEAN DEFAULT FALSE,            -- Segment 01: WebAuthn flag
    last_trusted_login_at TIMESTAMPTZ,
    device_fingerprint_hash TEXT,                 -- Segment 01: Device binding
    webauthn_credential_id TEXT,                  -- Segment 01: Passkey ID
    last_synced_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 1.2 Farms & Fields (PostGIS Spatial Core)
```sql
CREATE TABLE farms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE RESTRICT,
    farmer_id UUID NOT NULL REFERENCES profiles(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,
    centroid GEOGRAPHY(POINT, 4326) GENERATED ALWAYS AS (ST_Centroid(geometry)::geography) STORED,
    area_hectares NUMERIC(10,4) GENERATED ALWAYS AS (ST_Area(geometry::geography) / 10000) STORED,
    soil_type TEXT,
    soil_ph NUMERIC(3,1),
    soil_organic_carbon NUMERIC(5,2),
    irrigation_type TEXT CHECK (irrigation_type IN ('DRIP', 'SPRINKLER', 'FLOOD', 'CANAL', 'BOREWELL', 'RAINFED', 'NONE')),
    water_source TEXT,
    elevation_m NUMERIC(8,2),
    slope_degrees NUMERIC(5,2),
    aspect_degrees NUMERIC(5,2),
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE fields (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,
    centroid GEOGRAPHY(POINT, 4326) GENERATED ALWAYS AS (ST_Centroid(geometry)::geography) STORED,
    area_hectares NUMERIC(10,4) GENERATED ALWAYS AS (ST_Area(geometry::geography) / 10000) STORED,
    crop_variety TEXT,
    crop_type TEXT,
    sowing_date DATE,
    stage TEXT,
    soil_type TEXT,
    soil_ph NUMERIC(3,1),
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 1.3 Devices & Sensor Mappings
```sql
CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE RESTRICT,
    farm_id UUID REFERENCES farms(id) ON DELETE SET NULL,
    field_id UUID REFERENCES fields(id) ON DELETE SET NULL,
    device_type TEXT NOT NULL CHECK (device_type IN ('GATEWAY', 'SENSOR_NODE', 'CAMERA_NODE', 'WEATHER_STATION', 'ACTUATOR', 'TRAP_CAMERA')),
    hardware_model TEXT,
    firmware_version TEXT,
    serial_number TEXT UNIQUE,
    mac_address MACADDR,
    lorawan_dev_eui TEXT UNIQUE,
    location GEOGRAPHY(POINT, 4326),
    status TEXT DEFAULT 'PROVISIONED' CHECK (status IN ('PROVISIONED', 'ACTIVE', 'OFFLINE', 'MAINTENANCE', 'DECOMMISSIONED', 'ERROR')),
    config JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sensor_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT UNIQUE NOT NULL,                   -- e.g. VWC, SOIL_TEMP, LEAF_WETNESS, PAR
    name TEXT NOT NULL,
    unit TEXT NOT NULL,                           -- e.g. %, °C, lux, mm
    category TEXT NOT NULL CHECK (category IN ('SOIL', 'ENVIRONMENT', 'CROP', 'WEATHER', 'STORAGE')),
    min_value NUMERIC,
    max_value NUMERIC,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE device_sensors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    sensor_type_id UUID NOT NULL REFERENCES sensor_types(id) ON DELETE RESTRICT,
    port TEXT,
    depth_cm NUMERIC(5,2),
    height_cm NUMERIC(5,2),
    calibration_offset NUMERIC DEFAULT 0,
    calibration_multiplier NUMERIC DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE (device_id, sensor_type_id, port)
);
```

### 1.4 Crop Cycles
```sql
CREATE TABLE crop_cycles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    field_id UUID NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE RESTRICT,
    farmer_id UUID NOT NULL REFERENCES profiles(id) ON DELETE RESTRICT,
    crop_variety TEXT NOT NULL,
    crop_type TEXT NOT NULL,
    season TEXT NOT NULL CHECK (season IN ('KHARIF', 'RABI', 'ZAID', 'PERENNIAL')),
    year INT NOT NULL,
    sowing_date DATE,
    flowering_date DATE,
    harvest_start_date DATE,
    stage TEXT DEFAULT 'PLANNED' CHECK (stage IN ('PLANNED', 'SOWN', 'GERMINATED', 'VEGETATIVE', 'FLOWERING', 'FRUITING', 'MATURING', 'HARVESTING', 'HARVESTED', 'FAILED', 'FALLOW')),
    status TEXT DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'COMPLETED', 'ABANDONED', 'FAILED')),
    target_yield_t_ha NUMERIC(6,2),
    actual_yield_t_ha NUMERIC(6,2),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (field_id, season, year)
);
```

---

## 2. TimescaleDB Hypertables

### 2.1 `sensor_readings` (Telemetry Series)
```sql
CREATE TABLE sensor_readings (
    time TIMESTAMPTZ NOT NULL,
    farm_id UUID NOT NULL,
    field_id UUID,
    device_id UUID NOT NULL,
    sensor_type TEXT NOT NULL,
    value NUMERIC(10,4) NOT NULL,
    raw_value NUMERIC(10,4),
    quality_flag TEXT DEFAULT 'VALID' CHECK (quality_flag IN ('VALID', 'SUSPECT', 'OUT_OF_BOUNDS', 'CALIBRATED', 'INTERPOLATED', 'RAW')),
    metadata JSONB DEFAULT '{}'
);

SELECT create_hypertable('sensor_readings', 'time', if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 day');

ALTER TABLE sensor_readings SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'farm_id, device_id, sensor_type',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('sensor_readings', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('sensor_readings', INTERVAL '365 days', if_not_exists => TRUE);
```

### 2.2 `images` (Canopy & Pest Imagery with pgvector Embeddings)
```sql
CREATE TABLE images (
    captured_at TIMESTAMPTZ NOT NULL,
    id UUID DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL,
    field_id UUID,
    device_id UUID,
    camera_type TEXT DEFAULT 'RGB' CHECK (camera_type IN ('RGB', 'MULTISPECTRAL', 'THERMAL', 'TRAP')),
    image_url TEXT NOT NULL,
    thumbnail_url TEXT,
    s3_bucket TEXT NOT NULL DEFAULT 'flip-images',
    s3_key TEXT NOT NULL,
    bboxes JSONB DEFAULT '[]',
    detected_diseases TEXT[] DEFAULT ARRAY[]::TEXT[],
    embedding VECTOR(384),                        -- pgvector MiniLM / MobileNet embedding
    metadata JSONB DEFAULT '{}'
);

SELECT create_hypertable('images', 'captured_at', if_not_exists => TRUE, chunk_time_interval => INTERVAL '7 days');

ALTER TABLE images SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'farm_id, field_id',
    timescaledb.compress_orderby = 'captured_at DESC'
);

SELECT add_compression_policy('images', INTERVAL '14 days', if_not_exists => TRUE);
```

### 2.3 `farm_twin_events` (Event Sourcing & CRDT Log)
```sql
CREATE TABLE farm_twin_events (
    event_time TIMESTAMPTZ NOT NULL,
    id UUID DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL,
    field_id UUID,
    event_type TEXT NOT NULL,
    actor_id UUID,
    prev_state JSONB,
    next_state JSONB,
    crdt_clock BIGINT DEFAULT 0,
    yjs_update BYTEA,
    metadata JSONB DEFAULT '{}'
);

SELECT create_hypertable('farm_twin_events', 'event_time', if_not_exists => TRUE, chunk_time_interval => INTERVAL '7 days');

ALTER TABLE farm_twin_events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'farm_id',
    timescaledb.compress_orderby = 'event_time DESC'
);

SELECT add_compression_policy('farm_twin_events', INTERVAL '14 days', if_not_exists => TRUE);
```

---

## 3. Advisory & Closed-Loop Action Tables

### 3.1 `advisories` (Decision Records with Conformal Sets)
```sql
CREATE TABLE advisories (
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    id TEXT NOT NULL,
    farm_id UUID NOT NULL,
    field_id UUID,
    cycle_id UUID,
    now_text TEXT NOT NULL,
    next_text TEXT NOT NULL,
    why_text TEXT NOT NULL,
    confidence_set TEXT[] DEFAULT ARRAY[]::TEXT[], -- Conformal prediction set
    coverage NUMERIC(4,3) DEFAULT 0.950,           -- Guaranteed coverage (e.g. 95%)
    risk_factors JSONB DEFAULT '{}',               -- Causal sensor evidence
    expires_at TIMESTAMPTZ NOT NULL,
    verification_due TIMESTAMPTZ,
    status TEXT DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'ACKNOWLEDGED', 'ACTIONED', 'EXPIRED', 'DISMISSED', 'VERIFIED')),
    model_version TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    PRIMARY KEY (issued_at, id)
);

SELECT create_hypertable('advisories', 'issued_at', if_not_exists => TRUE, chunk_time_interval => INTERVAL '30 days');
```

### 3.2 `farmer_actions` (Closed-Loop Action Tracking)
```sql
CREATE TABLE farmer_actions (
    action_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    id UUID DEFAULT gen_random_uuid(),
    advisory_id TEXT,
    farm_id UUID NOT NULL,
    field_id UUID,
    farmer_id UUID NOT NULL,
    action_type TEXT NOT NULL CHECK (action_type IN ('SPRAY', 'IRRIGATE', 'FERTILIZE', 'HARVEST', 'SCOUT', 'PRUNE', 'SOW', 'OTHER')),
    inputs_applied JSONB DEFAULT '{}',             -- e.g. {chemical: "Copper Oxychloride", rate_g_ha: 2500}
    notes TEXT,
    geo_point GEOGRAPHY(POINT, 4326),
    status TEXT DEFAULT 'COMPLETED' CHECK (status IN ('PLANNED', 'COMPLETED', 'VERIFIED', 'DISPUTED')),
    verified_at TIMESTAMPTZ,
    outcome_delta JSONB DEFAULT '{}',              -- Post-action sensor delta
    metadata JSONB DEFAULT '{}',
    PRIMARY KEY (action_time, id)
);

SELECT create_hypertable('farmer_actions', 'action_time', if_not_exists => TRUE, chunk_time_interval => INTERVAL '30 days');
```

### 3.3 `training_samples` (Continuous Learning Store)
```sql
CREATE TABLE training_samples (
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    id UUID DEFAULT gen_random_uuid(),
    advisory_id TEXT,
    action_id UUID,
    farm_id UUID NOT NULL,
    field_id UUID,
    features JSONB NOT NULL,                       -- Multimodal input vector snapshot
    ground_truth JSONB NOT NULL,                   -- Expert or verified label
    model_version TEXT NOT NULL,
    split TEXT DEFAULT 'TRAIN' CHECK (split IN ('TRAIN', 'VAL', 'TEST', 'CALIBRATION')),
    PRIMARY KEY (collected_at, id)
);

SELECT create_hypertable('training_samples', 'collected_at', if_not_exists => TRUE, chunk_time_interval => INTERVAL '30 days');
```

---

## 4. Disaster & Emergency Alert Tables

### 4.1 `disaster_alerts`
```sql
CREATE TABLE disaster_alerts (
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('HEATWAVE', 'FLASH_FLOOD', 'HAILSTORM', 'LOCUST_SWARM', 'PEST_OUTBREAK', 'CYCLONE', 'DROUGHT', 'FROST')),
    severity TEXT NOT NULL CHECK (severity IN ('ADVISORY', 'WATCH', 'WARNING', 'EMERGENCY')),
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,      -- Affected geo-fence polygon
    expires_at TIMESTAMPTZ NOT NULL,
    message_template JSONB NOT NULL,               -- Multilingual template dictionary
    source TEXT NOT NULL CHECK (source IN ('IMD', 'NDMA', 'SATELLITE', 'LOCAL_SENSOR', 'COMMUNITY', 'AI_EARLY_WARNING')),
    status TEXT DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'CANCELLED', 'EXPIRED')),
    sirens_triggered BOOLEAN DEFAULT FALSE,
    ivr_dispatched BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    PRIMARY KEY (issued_at, id)
);

SELECT create_hypertable('disaster_alerts', 'issued_at', if_not_exists => TRUE, chunk_time_interval => INTERVAL '30 days');
```

---

## 5. Auth Enhancement Tables (Segment 01)

### 5.1 `farmer_farms` (Many-to-Many Binding Table)
```sql
CREATE TABLE farmer_farms (
    farmer_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    farm_id UUID NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'OWNER' CHECK (role IN ('OWNER', 'MANAGER', 'WORKER')),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (farmer_id, farm_id)
);
```

### 5.2 `trusted_devices` (30-Day Remember Me)
```sql
CREATE TABLE trusted_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    device_fingerprint_hash TEXT NOT NULL,
    user_agent TEXT,
    ip_subnet TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 6. Materialized Views & Indexes

### 6.1 `farm_digital_twin` (Materialized View)
```sql
CREATE MATERIALIZED VIEW farm_digital_twin AS
SELECT 
    f.id AS farm_id,
    f.name AS farm_name,
    f.org_id,
    f.farmer_id,
    f.geometry AS farm_geometry,
    f.centroid AS farm_centroid,
    f.area_hectares,
    f.soil_type,
    f.irrigation_type,
    jsonb_agg(DISTINCT jsonb_build_object(
        'field_id', fld.id,
        'name', fld.name,
        'crop_type', fld.crop_type,
        'stage', fld.stage,
        'area_hectares', fld.area_hectares
    )) FILTER (WHERE fld.id IS NOT NULL) AS fields,
    (SELECT jsonb_object_agg(sensor_type, value) FROM (
        SELECT DISTINCT ON (sensor_type) sensor_type, value
        FROM sensor_readings
        WHERE farm_id = f.id
        ORDER BY sensor_type, time DESC
    ) latest_readings) AS current_telemetry,
    (SELECT jsonb_agg(jsonb_build_object('id', id, 'now', now_text, 'risk', risk_factors))
     FROM advisories
     WHERE farm_id = f.id AND status = 'ACTIVE' AND expires_at > NOW()
    ) AS active_advisories,
    (SELECT jsonb_agg(jsonb_build_object('id', id, 'severity', severity, 'event', event_type))
     FROM disaster_alerts
     WHERE ST_Intersects(geometry, f.geometry) AND status = 'ACTIVE' AND expires_at > NOW()
    ) AS active_disasters,
    NOW() AS last_refreshed_at
FROM farms f
LEFT JOIN fields fld ON fld.farm_id = f.id
WHERE f.is_active = TRUE
GROUP BY f.id, f.name, f.org_id, f.farmer_id, f.geometry, f.centroid, f.area_hectares, f.soil_type, f.irrigation_type
WITH DATA;

CREATE UNIQUE INDEX idx_farm_digital_twin_id ON farm_digital_twin (farm_id);
```

### 6.2 Spatial & Vector Indexes
- **Spatial GIST**: `idx_farms_geo` ON `farms USING GIST (geometry)`
- **Spatial GIST**: `idx_disaster_alerts_geo` ON `disaster_alerts USING GIST (geometry)`
- **Vector HNSW**: `idx_images_embedding` ON `images USING hnsw (embedding vector_cosine_ops)`

---

## 7. Row-Level Security (RLS) Policies

All multi-tenant queries enforce strict isolation through PostgreSQL Row-Level Security:

```sql
-- Profiles table RLS
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY profiles_user_isolation ON profiles
    FOR ALL
    USING (
        id = NULLIF(current_setting('app.current_user_id', true), '')::UUID
        OR NULLIF(current_setting('app.current_role', true), '') = 'platform_admin'
        OR org_id = NULLIF(current_setting('app.current_org_id', true), '')::UUID
    );

-- Farmer-Farms binding RLS
ALTER TABLE farmer_farms ENABLE ROW LEVEL SECURITY;
CREATE POLICY farmer_farms_isolation ON farmer_farms
    FOR ALL
    USING (
        farmer_id = NULLIF(current_setting('app.current_user_id', true), '')::UUID
        OR NULLIF(current_setting('app.current_role', true), '') IN ('platform_admin', 'fpo_admin')
    );

-- Farms table RLS
ALTER TABLE farms ENABLE ROW LEVEL SECURITY;
CREATE POLICY farms_tenant_isolation ON farms
    FOR ALL
    USING (
        farmer_id = NULLIF(current_setting('app.current_user_id', true), '')::UUID
        OR org_id = NULLIF(current_setting('app.current_org_id', true), '')::UUID
        OR NULLIF(current_setting('app.current_role', true), '') = 'platform_admin'
    );
```

---

## 8. Database Functions & Triggers

### 8.1 Auto Timestamp Update
```sql
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### 8.2 Refresh Digital Twin Trigger
```sql
CREATE OR REPLACE FUNCTION refresh_farm_digital_twin()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY farm_digital_twin;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
```

### 8.3 Spatial Radius Query Helper
```sql
CREATE OR REPLACE FUNCTION farms_within_radius(
    center_point GEOGRAPHY,
    radius_meters FLOAT
)
RETURNS TABLE (farm_id UUID, farm_name TEXT, distance_meters FLOAT) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        id AS farm_id,
        name AS farm_name,
        ST_Distance(centroid, center_point) AS distance_meters
    FROM farms
    WHERE ST_DWithin(centroid, center_point, radius_meters)
    ORDER BY distance_meters ASC;
END;
$$ LANGUAGE plpgsql;
```

---

## 9. Development Seed Reference

The default development seed (`infra/db/migrations/seed_dev.sql`) populates:
- **1 District**: Pune District (`IN-MH-PU`), Maharashtra.
- **2 Organizations**: `Sahyadri Kisan Producer Co.` (FPO) and `Maharashtra Agritech Extension` (GOVT).
- **5 Profiles**:
  - `Ramesh Patil` (`farmer@test.com` / `+919876543210`) — Farmer
  - `Dr. Priya Sharma` (`expert@test.com`) — Agronomist
  - `Suresh Deshmukh` (`fpo@test.com`) — FPO Admin
  - `Vikram Singh` (`gov@test.com`) — Agriculture Officer
  - `Admin User` (`admin@test.com`) — Platform Admin
- **1 Farm & 2 Fields**: "Patil Vadi" (1.8 hectares, Drip irrigated, Tomato & Onion plots).
- **4 Devices**: 1 Gateway, 2 LoRa Sensor Nodes (Soil & Environment), 1 Trap Camera.
- **1 Active Crop Cycle**: Tomato (Flowering stage, target yield 35 t/ha).
- **1 Sample Urgent Advisory**: Tomato Early Blight (Conformal set: `["TOMATO_EARLY_BLIGHT"]`, coverage 0.95).
- **1 Active Disaster Alert**: Severe Heatwave Warning issued by IMD Pune.
