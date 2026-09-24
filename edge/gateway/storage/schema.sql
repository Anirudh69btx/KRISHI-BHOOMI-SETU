-- FLIP Edge Gateway SQLite Local Buffer Schema
-- Resilient offline store-and-forward for sensor data, images, advisories, and CRDT sync

PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

-- Raw Sensor Telemetry Buffer
CREATE TABLE IF NOT EXISTS sensor_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    farm_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT,
    quality_flag TEXT DEFAULT 'RAW',
    metadata TEXT,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sensor_raw_farm_time 
    ON sensor_raw (farm_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_sensor_raw_synced 
    ON sensor_raw (synced_at);

-- Image Captures & Edge AI Detections
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    farm_id TEXT NOT NULL,
    field_id TEXT,
    device_id TEXT NOT NULL,
    minio_key TEXT NOT NULL,
    inference_result TEXT,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_images_farm_time 
    ON images (farm_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_images_synced 
    ON images (synced_at);

-- Local Generated Advisories
CREATE TABLE IF NOT EXISTS advisories (
    id TEXT PRIMARY KEY,
    farm_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    urgency TEXT DEFAULT 'ROUTINE',
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    spoken_at TIMESTAMP,
    synced_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_advisories_urgency 
    ON advisories (urgency, generated_at DESC);

-- Farmer Recorded Actions
CREATE TABLE IF NOT EXISTS farmer_actions (
    id TEXT PRIMARY KEY,
    advisory_id TEXT NOT NULL,
    farm_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    details TEXT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP
);

-- Store-and-Forward Outbox (Gateway -> Cloud NATS JetStream)
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    payload TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_outbox_unsent 
    ON outbox (sent_at, id ASC);

-- Store-and-Forward Inbox (Cloud NATS -> Gateway)
CREATE TABLE IF NOT EXISTS inbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    payload TEXT NOT NULL,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inbox_unprocessed 
    ON inbox (processed_at, id ASC);

-- Trusted Local Sensor Nodes & Hardware Auth
CREATE TABLE IF NOT EXISTS trusted_devices (
    id TEXT PRIMARY KEY,
    device_fingerprint TEXT NOT NULL,
    public_key TEXT,
    last_seen TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- CRDT State Journal for Multi-Master Conflict-Free Synchronization
CREATE TABLE IF NOT EXISTS crdt_state (
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_value TEXT,
    lamport_clock INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (entity_type, entity_id, field_name)
);
