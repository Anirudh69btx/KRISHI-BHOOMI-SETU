-- ============================================================
-- FLIP v3.0 — Migration 0008: Auth Enhancements (Segment 01 Dependency)
-- ============================================================

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS keycloak_sub UUID UNIQUE;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS webauthn_credential_id BYTEA;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS last_trusted_login_at TIMESTAMPTZ;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS device_fingerprint_hash TEXT;

CREATE INDEX IF NOT EXISTS idx_profiles_keycloak_sub ON profiles(keycloak_sub);
