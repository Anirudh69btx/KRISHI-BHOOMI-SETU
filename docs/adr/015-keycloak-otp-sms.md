# ADR-015: Keycloak Custom SPI & Twilio Verify for Farmer Phone OTP Authentication

## Status
Accepted (Segment 01)

## Context
Smallholder Indian farmers cannot be expected to remember alphanumeric passwords or manage hardware security keys. At the same time, FLIP v3.0 requires an enterprise-grade identity foundation (ADR-006) with multi-tenancy, Row-Level Security, role hierarchies, and audit logging.

Building a custom authentication system with custom user tables, password hashing, and token issuance in FastAPI violates core security principles and increases vulnerability surface.

## Decision
We enforce Keycloak as the sole Identity Provider (IdP) for all user categories across FLIP:
1. **No Custom Auth Tables**: Keycloak owns all credentials and tokens. FastAPI core API only validates standard OIDC access tokens against Keycloak JWKS (`/realms/flip/protocol/openid-connect/certs`).
2. **Keycloak Java SPI (`otp-sms-provider`)**: Implements `Authenticator` and `RequiredActionProvider` deploying into Keycloak Quarkus runtime (`/opt/keycloak/providers/otp-sms-provider.jar`).
3. **Twilio Verify API Integration**: Keycloak SPI directly coordinates OTP dispatch and cryptographic verification checks with Twilio Verify API (with automated mock fallback for local dev).
4. **OIDC PKCE for Web**: The React PWA communicates strictly using OIDC Authorization Code Flow with Proof Key for Code Exchange (PKCE) via `oidc-client-ts`.
5. **Profile Synchronization**: On token receipt or renewal, frontend calls `POST /api/v1/auth/sync-profile` to idempotently upsert Keycloak `sub` to the PostgreSQL `profiles` table.

## Consequences
### Positive
- **Zero Credential Liability**: No passwords, hashed secrets, or custom JWT private keys are stored in the core application database.
- **Unified Role Gating**: Realm roles (`farmer`, `fpo_admin`, `agronomist`, `gov_officer`, `platform_admin`) are mapped directly to Postgres RLS policies (`farmer_farms`, `farms`).
- **Offline Resilience**: Keycloak issuing standard refresh tokens allows `oidc-client-ts` to renew tokens silently in the background.

### Negative
- Keycloak SPI requires Java Maven build and jar deployment into container.
- SMS delivery relies on external telecom gateways (mitigated by dev mock mode and WhatsApp fallback in future segments).
