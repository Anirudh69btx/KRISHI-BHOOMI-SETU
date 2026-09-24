-- ============================================================
-- FLIP v3.0 — Migration 0002: TimescaleDB Hypertables & Compression
-- ============================================================

-- 1. Sensor Readings (Core Hypertable)
CREATE TABLE IF NOT EXISTS sensor_readings (
    time TIMESTAMPTZ NOT NULL,
    farm_id UUID NOT NULL REFERENCES farms(id),
    field_id UUID REFERENCES fields(id),
    device_id UUID NOT NULL REFERENCES devices(id),
    sensor_type_id UUID NOT NULL REFERENCES sensor_types(id),
    value DOUBLE PRECISION NOT NULL,
    quality_flag TEXT DEFAULT 'RAW',
    metadata JSONB DEFAULT '{}',
    PRIMARY KEY (time, farm_id, device_id, sensor_type_id)
);

SELECT create_hypertable('sensor_readings', 'time', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

ALTER TABLE sensor_readings SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'farm_id, field_id, device_id, sensor_type_id'
);

SELECT add_compression_policy('sensor_readings', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('sensor_readings', INTERVAL '2 years', if_not_exists => TRUE);

-- 2. Images (with pgvector HNSW)
CREATE TABLE IF NOT EXISTS images (
    id UUID DEFAULT gen_random_uuid(),
    farm_id UUID REFERENCES farms(id),
    field_id UUID REFERENCES fields(id),
    device_id UUID REFERENCES devices(id),
    captured_at TIMESTAMPTZ NOT NULL,
    minio_bucket TEXT NOT NULL,
    minio_key TEXT NOT NULL,
    mime_type TEXT,
    size_bytes INT,
    inference_result JSONB,
    processing_time_ms INT,
    embedding VECTOR(512),
    PRIMARY KEY (captured_at, id)
);

CREATE INDEX IF NOT EXISTS idx_images_farm_time ON images (farm_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_images_embedding ON images USING hnsw (embedding vector_cosine_ops);

SELECT create_hypertable('images', 'captured_at', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);

ALTER TABLE images SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'farm_id, field_id'
);

SELECT add_compression_policy('images', INTERVAL '14 days', if_not_exists => TRUE);

-- 3. Twin Events (Event Sourcing)
CREATE TABLE IF NOT EXISTS twin_events (
    id UUID DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL REFERENCES farms(id),
    field_id UUID REFERENCES fields(id),
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    synced_at TIMESTAMPTZ,
    source TEXT CHECK (source IN ('EDGE','CLOUD','FARMER','EXPERT','WEATHER_API','SATELLITE')),
    version INT DEFAULT 1,
    PRIMARY KEY (occurred_at, id)
);

CREATE INDEX IF NOT EXISTS idx_twin_events_farm_time ON twin_events (farm_id, occurred_at DESC);

SELECT create_hypertable('twin_events', 'occurred_at', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);

ALTER TABLE twin_events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'farm_id'
);

SELECT add_compression_policy('twin_events', INTERVAL '14 days', if_not_exists => TRUE);
