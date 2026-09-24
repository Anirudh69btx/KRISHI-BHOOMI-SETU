"""
FLIP Core API — Integration Tests for OTP & Rate Limiting Flow (Segment 01)
Tests: OTP dispatch, verification, error states, and 429 rate limit enforcement.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from flip_api.main import app
from flip_api.auth.rate_limit import otp_rate_limiter


@pytest.mark.asyncio
async def test_otp_send_and_verify_mock_mode():
    """Test OTP flow in mock/dev mode (OTP=123456)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Send OTP
        send_resp = await ac.post(
            "/api/v1/auth/otp/send",
            json={"phone": "+919876543210"},
        )
        assert send_resp.status_code == 200
        send_data = send_resp.json()
        assert send_data["status"] == "sent"
        assert send_data["phone"] == "+919876543210"

        # 2. Verify with wrong OTP
        wrong_verify_resp = await ac.post(
            "/api/v1/auth/otp/verify",
            json={"phone": "+919876543210", "otp": "999999"},
        )
        assert wrong_verify_resp.status_code == 400

        # 3. Verify with correct OTP
        valid_verify_resp = await ac.post(
            "/api/v1/auth/otp/verify",
            json={"phone": "+919876543210", "otp": "123456"},
        )
        assert valid_verify_resp.status_code == 200
        assert valid_verify_resp.json()["verified"] is True


@pytest.mark.asyncio
async def test_otp_rate_limiting():
    """Verify that exceeding rate limits returns 429 Too Many Requests."""
    test_phone = "+919999999999"
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Send up to limit
        limit = otp_rate_limiter.max_requests
        for _ in range(limit):
            resp = await ac.post("/api/v1/auth/otp/send", json={"phone": test_phone})
            assert resp.status_code == 200

        # Next request must trigger 429 Too Many Requests
        exceeded_resp = await ac.post("/api/v1/auth/otp/send", json={"phone": test_phone})
        assert exceeded_resp.status_code == 429
        assert "rate limit exceeded" in exceeded_resp.json()["detail"].lower()
        assert "retry-after" in exceeded_resp.headers
