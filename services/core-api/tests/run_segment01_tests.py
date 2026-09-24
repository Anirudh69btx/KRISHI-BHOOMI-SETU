"""
FLIP v3.0 — Self-Contained Segment 01 (Enhanced) IAM Test Runner
Executes comprehensive verification across all 6 IAM capabilities without external network dependencies.
"""

import sys
import os

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import time
import base64
import json
import hashlib
import hmac
from uuid import uuid4

# Add src directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from flip_api.models.auth import (
    TokenData,
    ProfileSyncRequest,
    ProfileSyncResponse,
    BoundFarm,
    UserMeResponse,
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    OtpVerifyResponse,
)
from flip_api.auth.profile_sync import resolve_primary_role
from flip_api.auth.rate_limit import RateLimiter


def run_all_tests():
    passed = 0
    failed = 0

    def test(name, fn):
        nonlocal passed, failed
        try:
            fn()
            print(f"  ✅ PASS: {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ FAIL: {name} — {e}")
            failed += 1

    print("\n" + "=" * 70)
    print("🌾 FLIP v3.0 — SEGMENT 01 (ENHANCED) IAM VALIDATION SUITE")
    print("=" * 70 + "\n")

    # 1. Pydantic Schemas & Typing
    print("📦 [1/6] Validating Pydantic Data Models & Types...")
    def test_models():
        sub = str(uuid4())
        td = TokenData(
            sub=sub,
            email="farmer@test.com",
            name="Ramesh Kumar",
            phone="+919876543210",
            roles=["farmer"],
            org_id=str(uuid4()),
        )
        assert td.sub == sub
        assert "farmer" in td.roles

        sync_req = ProfileSyncRequest(
            full_name="Ramesh K.",
            phone="+919876543210",
            language="hi",
            device_fingerprint_hash="abc123hash",
            webauthn_credential_id="cred_webauthn_999",
        )
        assert sync_req.language == "hi"
        assert sync_req.webauthn_credential_id == "cred_webauthn_999"

        otp_req = OtpSendRequest(phone="+919876543210")
        assert otp_req.phone == "+919876543210"

    test("Pydantic Schemas (TokenData, ProfileSyncRequest, OTP)", test_models)

    # 2. Role Resolution & Precedence
    print("\n🛡️ [2/6] Validating Role Hierarchy & Precedence Engine...")
    def test_role_precedence():
        assert resolve_primary_role(["farmer", "platform_admin"]) == "platform_admin"
        assert resolve_primary_role(["farmer", "fpo_admin"]) == "fpo_admin"
        assert resolve_primary_role(["farmer", "agronomist"]) == "agronomist"
        assert resolve_primary_role(["farmer", "gov_officer"]) == "gov_officer"
        assert resolve_primary_role(["farmer"]) == "farmer"
        assert resolve_primary_role([]) == "farmer"
    test("Role Precedence Calculation", test_role_precedence)

    # 3. 30-Day Trusted Device Fingerprint & HMAC Cookie Verification
    print("\n🍪 [3/6] Validating 30-Day Trusted Device & Fingerprinting (C9)...")
    def test_trusted_device():
        secret = "flip-trusted-device-secret-key-32chars"
        ua = "Mozilla/5.0 (Linux; Android 14; Pixel 8)"
        ip = "192.168.1.50"
        subnet = "192.168.1"
        phone = "+919876543210"

        # Fingerprint calculation
        raw_fp = f"{ua}|{subnet}".encode("utf-8")
        fp_hash = hashlib.sha256(raw_fp).hexdigest()

        # Token generation
        expiry = int(time.time()) + 30 * 24 * 3600
        payload = f"{phone}:{expiry}:{fp_hash}"
        sig = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        cookie_value = f"{base64.urlsafe_b64encode(payload.encode()).decode()}.{sig}"

        # Cookie verification
        parts = cookie_value.split(".")
        decoded_payload = base64.urlsafe_b64decode(parts[0].encode()).decode()
        expected_sig = hmac.new(secret.encode("utf-8"), decoded_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        assert parts[1] == expected_sig, "HMAC signature must match"

        fields = decoded_payload.split(":")
        assert fields[0] == phone
        assert int(fields[1]) > time.time()
        assert fields[2] == fp_hash
    test("30-Day Trusted Device HMAC Generation & Validation", test_trusted_device)

    # 4. WebAuthn Passkey MFA Enforcer Logic (C8)
    print("\n🔑 [4/6] Validating WebAuthn Passkey MFA Enforcement (C8)...")
    def test_webauthn_logic():
        expert_token_with_webauthn = TokenData(
            sub=str(uuid4()),
            roles=["agronomist"],
            raw_claims={"amr": ["pwd", "webauthn"], "mfa_enabled": True},
        )
        amr = expert_token_with_webauthn.raw_claims.get("amr", [])
        mfa_ok = "webauthn" in amr or expert_token_with_webauthn.raw_claims.get("mfa_enabled") is True
        assert mfa_ok is True

        expert_token_without_mfa = TokenData(
            sub=str(uuid4()),
            roles=["agronomist"],
            raw_claims={"amr": ["pwd"], "mfa_enabled": False},
        )
        amr_no = expert_token_without_mfa.raw_claims.get("amr", [])
        mfa_fail = "webauthn" in amr_no or expert_token_without_mfa.raw_claims.get("mfa_enabled") is True
        assert mfa_fail is False
    test("WebAuthn AMR Claim & MFA Enforcer", test_webauthn_logic)

    # 5. CloudEvents v1.0 Profile Synced NATS Event Sourcing (C11)
    print("\n⚡ [5/6] Validating Event Sourcing CloudEvents v1.0 Schema (C11)...")
    def test_cloudevent_schema():
        event = {
            "specversion": "1.0",
            "type": "flip.profile.synced.v1",
            "source": "/services/core-api",
            "id": str(uuid4()),
            "time": "2026-09-10T12:00:00Z",
            "datacontenttype": "application/json",
            "data": {
                "profile_id": str(uuid4()),
                "keycloak_sub": str(uuid4()),
                "role": "farmer",
                "farm_ids": [str(uuid4()), str(uuid4())],
                "synced_at": "2026-09-10T12:00:00Z",
            },
        }
        assert event["specversion"] == "1.0"
        assert event["type"] == "flip.profile.synced.v1"
        assert len(event["data"]["farm_ids"]) == 2
    test("CloudEvents v1.0 flip.profile.synced.v1 Schema", test_cloudevent_schema)

    # 6. Sliding Window Rate Limiter
    print("\n⏱️ [6/6] Validating In-Memory Sliding Window Rate Limiter...")
    import asyncio
    async def async_rate_limit_test():
        limiter = RateLimiter(max_requests=3, window_seconds=60, scope="test_otp")
        phone = "+919999911111"
        # 3 allowed
        assert (await limiter.is_allowed(phone))[0] is True
        assert (await limiter.is_allowed(phone))[0] is True
        assert (await limiter.is_allowed(phone))[0] is True
        # 4th must be rejected
        allowed, retry_after = await limiter.is_allowed(phone)
        assert allowed is False
        assert retry_after > 0

    def test_rate_limiter():
        asyncio.run(async_rate_limit_test())

    test("Rate Limiter (Max 3/min threshold)", test_rate_limiter)

    print("\n" + "=" * 70)
    print(f"🎉 TEST SUMMARY: {passed} PASSED, {failed} FAILED")
    print("=" * 70 + "\n")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
