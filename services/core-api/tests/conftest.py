"""
FLIP Core API — Test Fixtures & Cryptographic Key Helpers (Segment 01)
Generates RSA keypairs to simulate Keycloak JWKS and issue mock test JWTs.
"""

import time
from uuid import uuid4
import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt


@pytest.fixture(scope="session")
def rsa_keypair():
    """Generate a test RSA 2048-bit keypair for signing and verifying test JWTs."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    kid = "flip-test-key-id-1"

    # Minimal JWK representation for public key
    public_numbers = public_key.public_numbers()
    import base64

    def int_to_b64(val: int) -> str:
        b = val.to_bytes((val.bit_length() + 7) // 8, byteorder="big")
        return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")

    jwk_dict = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": int_to_b64(public_numbers.n),
        "e": int_to_b64(public_numbers.e),
    }

    return {
        "kid": kid,
        "private_pem": private_pem,
        "public_pem": public_pem,
        "jwk": jwk_dict,
        "jwks": {"keys": [jwk_dict]},
    }


def make_test_jwt(
    rsa_keypair: dict,
    sub: str | None = None,
    roles: list[str] | None = None,
    email: str = "farmer@test.com",
    name: str = "Ramesh Kumar",
    phone: str = "+919876543210",
    exp_delta: int = 3600,
    kid: str | None = None,
) -> str:
    """Helper to generate a signed RS256 Keycloak access token."""
    now = int(time.time())
    payload = {
        "sub": sub or str(uuid4()),
        "iss": "http://localhost:8080/realms/flip",
        "aud": "flip-web",
        "exp": now + exp_delta,
        "iat": now,
        "email": email,
        "name": name,
        "phone": phone,
        "realm_access": {"roles": roles or ["farmer"]},
        "flip_role": (roles or ["farmer"])[0],
    }

    headers = {"kid": kid or rsa_keypair["kid"], "alg": "RS256"}
    token = jwt.encode(payload, rsa_keypair["private_pem"], algorithm="RS256", headers=headers)
    return token
