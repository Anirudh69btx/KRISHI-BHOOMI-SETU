-- ============================================================
-- FLIP v3.0 — Migration 0004: Disaster Alerts & Delivery Logs
-- ============================================================

-- 1. Disaster Alerts
CREATE TABLE IF NOT EXISTS disaster_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL CHECK (event_type IN (
        'FLASH_FLOOD','HEATWAVE','HAIL','CYCLONE','DROUGHT',
        'DISEASE_OUTBREAK','PEST_OUTBREAK','FROST','LIGHTNING','FIRE'
    )),
    severity TEXT CHECK (severity IN ('WATCH','WARNING','EMERGENCY')),
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    message_template JSONB NOT NULL,
    source TEXT,
    metadata JSONB DEFAULT '{}',
    acknowledged_by UUID[] DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_disaster_geo_time ON disaster_alerts USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_disaster_active ON disaster_alerts (expires_at, issued_at);

-- 2. Alert Delivery Logs
CREATE TABLE IF NOT EXISTS alert_delivery_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID REFERENCES disaster_alerts(id) ON DELETE CASCADE,
    channel TEXT CHECK (channel IN ('PUSH','SMS','WHATSAPP','IVR','SIREN','EMAIL')),
    recipient TEXT,
    status TEXT CHECK (status IN ('SENT','DELIVERED','FAILED','READ')),
    sent_at TIMESTAMPTZ DEFAULT now(),
    delivered_at TIMESTAMPTZ,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_alert_delivery_alert ON alert_delivery_logs (alert_id, status);
