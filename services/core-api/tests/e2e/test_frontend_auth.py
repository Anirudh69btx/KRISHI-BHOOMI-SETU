"""
FLIP v3.0 — Playwright End-to-End Auth Test (Segment 01)
Simulates: Farmer enters phone -> OTP verification -> Lands on Dashboard with role badge -> Navigates to Profile.
"""

import pytest

# Marks the test for Playwright execution in CI
pytestmark = pytest.mark.e2e


def test_farmer_otp_login_flow(page=None):
    """
    E2E Test Scenario (Playwright):
    1. Navigate to http://localhost:5173/login
    2. Select 'Farmer Login' tab
    3. Enter test phone '+91 9876543210'
    4. Click 'Get Login OTP'
    5. Enter 6-digit OTP '123456'
    6. Verify redirect to '/dashboard'
    7. Verify '🌾 Farmer' badge is visible in Header
    8. Click Profile avatar and verify '/profile' shows linked farmer attributes
    """
    if page is None:
        pytest.skip("Playwright page fixture not available (run with pytest --browser chromium)")

    # 1. Open Login
    page.goto("http://localhost:5173/login")
    page.wait_for_selector("text=KRISHI BHOOMI SETU")

    # 2. Enter mobile number
    phone_input = page.locator("input[type='tel']")
    phone_input.fill("9876543210")
    page.click("button:has-text('Get Login OTP')")

    # 3. Enter 6-digit OTP
    page.wait_for_selector("text=Enter Verification Code")
    otp_inputs = page.locator(".flip-otp-digit")
    assert otp_inputs.count() == 6

    # Type 123456
    for idx, digit in enumerate("123456"):
        otp_inputs.nth(idx).fill(digit)

    # 4. Verify landing on Dashboard
    page.wait_for_url("**/dashboard", timeout=10000)
    assert page.is_visible("text=Dashboard")

    # 5. Check role badge in header
    badge = page.locator(".flip-role-badge")
    assert "Farmer" in badge.inner_text()

    # 6. Navigate to profile
    page.click("button[title*='View Profile']")
    page.wait_for_url("**/profile")
    assert page.is_visible("text=Farmer Profile & Settings")
    assert page.is_visible("text=Keycloak Identity Provider")
