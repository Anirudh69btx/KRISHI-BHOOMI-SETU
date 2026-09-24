# ADR-016: WebAuthn / FIDO2 Passkeys for Expert & Admin Phishing-Resistant MFA

## Status
Accepted (Segment 01)

## Context
While smallholder farmers use phone-based SMS OTPs with 30-day trusted device remember-me cookies for optimal low-friction accessibility, platform administrators, agronomists, and FPO managers hold elevated privileges. These privileged roles have the ability to annotate AI advisories, view regional outbreak analytics, and manage multi-tenant farm boundaries.

SMS OTPs are vulnerable to SIM swapping and phishing attacks. To prevent compromise of high-privilege accounts, FLIP requires mandatory, phishing-resistant Multi-Factor Authentication (MFA).

## Decision
1. **Mandatory WebAuthn / Passkeys**:
   - Experts, agronomists, FPO admins, and platform admins must authenticate using FIDO2 / WebAuthn platform authenticators (Windows Hello, Touch ID, Face ID, Android Biometrics, YubiKeys).
2. **Keycloak `expert-admin` Flow**:
   - The Keycloak realm defines a dedicated `expert-admin` authentication flow chaining password/username with WebAuthn registration and verification.
3. **Backend Authorization Guard**:
   - The `require_expert` dependency in FastAPI checks that `webauthn_credential_id` is registered on the profile or that `amr` (Authentication Methods References) in the JWT includes `webauthn` / `mfa`.
4. **Frontend Passkey Integration**:
   - `ExpertLoginTab.tsx` detects platform authenticator capabilities using `PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable()` and directly invokes `navigator.credentials.get()` / `navigator.credentials.create()`.

## Consequences
### Positive
- Cryptographically protects privileged agricultural operations against phishing, credential stuffing, and SIM swap attacks.
- Provides biometric passwordless convenience for agronomists in the field using mobile devices.

### Negative
- Requires devices with WebAuthn hardware security support (fallback to TOTP / Authenticator App is supported if platform authenticator is unavailable).
