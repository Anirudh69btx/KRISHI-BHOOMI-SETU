"""
FLIP Core API — Unit Tests for Keycloak JWT Validation (Segment 01)
Tests: Valid tokens, expired tokens, signature corruption, missing kid, invalid claims.
"""

import pytest
from fastapi import HTTPException
from jose import jwt

from flip_api.auth.keycloak import decode_and_validate_jwt, extract_token_data
from tests.conftest import make_test_jwt


def test_valid_jwt_decodes_successfully(rsa_keypair):
    """Valid RS256 token signed by realm key decodes with all claims intact."""
    token = make_test_jwt(rsa_keypair, sub="550e8400-e29b-41d4-a716-446655440000", roles=["farmer"])
    claims = decode_and_validate_jwt(token, jwks=rsa_keypair["jwks"])

    assert claims["sub"] == "550e8400-e29b-41d4-a716-446655440000"
    assert "farmer" in claims["realm_access"]["roles"]

    token_data = extract_token_data(claims)
    assert token_data.sub == "550e8400-e29b-41d4-a716-446655440000"
    assert "farmer" in token_data.roles
    assert token_data.phone == "+919876543210"
    assert token_data.name == "Ramesh Kumar"


def test_expired_token_raises_401(rsa_keypair):
    """Token with past exp claim must be rejected with 401 Unauthorized."""
    token = make_test_jwt(rsa_keypair, exp_delta=-300)

    with pytest.raises(HTTPException) as exc_info:
        decode_and_validate_jwt(token, jwks=rsa_keypair["jwks"])

    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


def test_invalid_signature_raises_401(rsa_keypair):
    """Token signed with wrong key or tampered payload raises 401."""
    token = make_test_jwt(rsa_keypair)
    # Corrupt token characters in payload
    parts = token.split(".")
    tampered_token = f"{parts[0]}.eyJnYXJiYWdlIjoidHJ1ZSJ9.{parts[2]}"

    with pytest.raises(HTTPException) as exc_info:
        decode_and_validate_jwt(tampered_token, jwks=rsa_keypair["jwks"])

    assert exc_info.value.status_code == 401


def test_missing_kid_raises_401(rsa_keypair):
    """Token lacking 'kid' header parameter is rejected."""
    token = jwt.encode(
        {"sub": "123", "exp": 9999999999},
        rsa_keypair["private_pem"],
        algorithm="RS256",
        headers={"alg": "RS256"},  # kid omitted
    )

    with pytest.raises(HTTPException) as exc_info:
        decode_and_validate_jwt(token, jwks=rsa_keypair["jwks"])

    assert exc_info.value.status_code == 401
    assert "missing 'kid'" in exc_info.value.detail.lower()


def test_unknown_kid_raises_401(rsa_keypair):
    """Token with kid not present in JWKS raises 401."""
    token = make_test_jwt(rsa_keypair, kid="unknown-foreign-key")

    with pytest.raises(HTTPException) as exc_info:
        decode_and_validate_jwt(token, jwks=rsa_keypair["jwks"])

    assert exc_info.value.status_code == 401
    assert "no matching public key" in exc_info.value.detail.lower()


def test_missing_sub_raises_401():
    """Claims lacking 'sub' cannot construct valid TokenData."""
    claims = {"roles": ["farmer"], "name": "No Sub"}
    with pytest.raises(HTTPException) as exc_info:
        extract_token_data(claims)

    assert exc_info.value.status_code == 401
    assert "subject" in exc_info.value.detail.lower()
