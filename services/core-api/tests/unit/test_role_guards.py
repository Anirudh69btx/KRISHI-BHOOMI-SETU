"""
FLIP Core API — Unit Tests for Role Guards & Dependencies (Segment 01)
Tests: require_farmer, require_expert, require_fpo_admin, platform_admin bypass.
"""

import pytest
from fastapi import HTTPException

from flip_api.auth.dependencies import (
    require_expert,
    require_farmer,
    require_fpo_admin,
    require_roles,
)
from flip_api.models.auth import TokenData


def make_token_data(roles: list[str]) -> TokenData:
    return TokenData(
        sub="550e8400-e29b-41d4-a716-446655440000",
        roles=roles,
        phone="+919876543210",
        name="Test User",
    )


@pytest.mark.asyncio
async def test_require_farmer_allows_farmer():
    """Farmer role satisfies require_farmer guard."""
    data = make_token_data(["farmer"])
    guard = require_farmer
    res = await guard(data)
    assert res.sub == data.sub
    assert "farmer" in res.roles


@pytest.mark.asyncio
async def test_require_farmer_rejects_agronomist():
    """Agronomist lacking farmer role is blocked with 403 Forbidden."""
    data = make_token_data(["agronomist"])
    guard = require_farmer

    with pytest.raises(HTTPException) as exc_info:
        await guard(data)

    assert exc_info.value.status_code == 403
    assert "insufficient permissions" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_require_expert_allows_agronomist():
    """Agronomist satisfies require_expert guard."""
    data = make_token_data(["agronomist"])
    res = await require_expert(data)
    assert "agronomist" in res.roles


@pytest.mark.asyncio
async def test_platform_admin_bypasses_all_guards():
    """Platform superadmin can access any role-restricted resource."""
    admin_data = make_token_data(["platform_admin"])

    # Test against multiple restrictive guards
    farmer_res = await require_farmer(admin_data)
    expert_res = await require_expert(admin_data)
    fpo_res = await require_fpo_admin(admin_data)

    assert "platform_admin" in farmer_res.roles
    assert "platform_admin" in expert_res.roles
    assert "platform_admin" in fpo_res.roles


@pytest.mark.asyncio
async def test_multi_role_custom_guard():
    """Custom require_roles guard checks intersection of allowed roles."""
    custom_guard = require_roles("gov_officer", "buyer")

    user_gov = make_token_data(["gov_officer"])
    res = await custom_guard(user_gov)
    assert "gov_officer" in res.roles

    user_unauthorized = make_token_data(["farmer"])
    with pytest.raises(HTTPException) as exc:
        await custom_guard(user_unauthorized)
    assert exc.value.status_code == 403
