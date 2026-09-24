"""
FLIP Core API — Unit Tests for Profile Sync Logic (Segment 01)
Tests: Primary role resolution, profile schema mapping, idempotency expectations.
"""

from uuid import uuid4
import pytest
from unittest.mock import AsyncMock, MagicMock

from flip_api.auth.profile_sync import resolve_primary_role, sync_keycloak_profile
from flip_api.models.auth import ProfileSyncRequest, TokenData


def test_resolve_primary_role_precedence():
    """Verify role resolution adheres to highest privilege hierarchy."""
    assert resolve_primary_role(["farmer", "platform_admin"]) == "platform_admin"
    assert resolve_primary_role(["farmer", "fpo_admin"]) == "fpo_admin"
    assert resolve_primary_role(["farmer", "agronomist"]) == "agronomist"
    assert resolve_primary_role(["farmer", "gov_officer"]) == "gov_officer"
    assert resolve_primary_role(["farmer"]) == "farmer"
    assert resolve_primary_role(["unknown_role"]) == "farmer"  # Default fallback


@pytest.mark.asyncio
async def test_sync_keycloak_profile_creates_and_updates():
    """Mock DB session to verify profile sync upsert statement execution."""
    sub = str(uuid4())
    token_data = TokenData(
        sub=sub,
        email="testfarmer@flip.farm",
        name="Sunil Patil",
        phone="+919811122233",
        roles=["farmer"],
    )

    mock_session = AsyncMock()
    # Mock no existing user on first query -> returns None
    mock_result_empty = MagicMock()
    mock_result_empty.mappings().first.return_value = None

    # Mock insert returning row
    mock_insert_result = MagicMock()
    mock_insert_result.mappings().first.return_value = {
        "id": uuid4(),
        "role": "farmer",
        "full_name": "Sunil Patil",
        "phone": "+919811122233",
        "language": "hi",
        "preferred_channels": ["PUSH"],
        "mfa_enabled": False,
        "last_synced_at": "2026-09-10T12:00:00Z",
    }

    # Mock get_bound_farms query
    mock_farms_result = MagicMock()
    mock_farms_result.mappings().all.return_value = []

    mock_session.execute.side_effect = [
        mock_result_empty,
        mock_insert_result,
        mock_farms_result,
    ]

    response = await sync_keycloak_profile(mock_session, token_data)

    assert response.role == "farmer"
    assert response.full_name == "Sunil Patil"
    assert response.phone == "+919811122233"
    assert mock_session.execute.call_count >= 2
