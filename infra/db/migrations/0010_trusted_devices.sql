-- ============================================================
-- FLIP v3.0 — Migration 0010: Trusted Devices (HMAC & Fingerprint)
-- ============================================================

CREATE TABLE IF NOT EXISTS trusted_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farmer_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    device_fingerprint_hash TEXT NOT NULL,
    user_agent TEXT,
    ip_subnet CIDR,
    hmac_signature TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_trusted_devices_farmer ON trusted_devices (farmer_id, expires_at);

ALTER TABLE trusted_devices ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS trusted_devices_isolation ON trusted_devices;
CREATE POLICY trusted_devices_isolation ON trusted_devices
    USING (
        farmer_id = NULLIF(current_setting('app.current_user_id', true), '')::UUID
        OR current_setting('app.current_role', true) = 'platform_admin'
    );
