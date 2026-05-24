"""
Authentication service tests.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt
from jose.utils import base64url_encode


def _b64_uint(value: int) -> str:
    return base64url_encode(
        value.to_bytes((value.bit_length() + 7) // 8, "big")
    ).decode("ascii")


def _rsa_keypair_as_jwk(kid: str) -> tuple[rsa.RSAPrivateKey, dict]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    return private_key, {
        "kty": "RSA",
        "kid": kid,
        "use": "sig",
        "alg": "RS256",
        "n": _b64_uint(public_numbers.n),
        "e": _b64_uint(public_numbers.e),
    }


def _workos_token(private_key: rsa.RSAPrivateKey, kid: str, issuer: str) -> str:
    issued_at = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": "user_123",
            "sid": "session_123",
            "iss": issuer,
            "exp": issued_at + timedelta(minutes=30),
            "iat": issued_at,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )


async def _mock_workos_verifier(monkeypatch, public_jwk: dict):
    from api.services import auth

    async def mock_get_jwks():
        return {"keys": [public_jwk]}

    monkeypatch.setattr(auth, "get_jwks", mock_get_jwks)
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: SimpleNamespace(
            WORKOS_CLIENT_ID="client_123",
            WORKOS_AUDIENCE="api.workos.com",
            workos_audience=None,
        ),
    )

    return auth


@pytest.mark.asyncio
async def test_verify_token_accepts_workos_authkit_session_token_with_legacy_env_values(monkeypatch):
    """Legacy env defaults should not reject WorkOS' documented AuthKit token claims."""
    kid = "sso_oidc_key_pair_test"
    private_key, public_jwk = _rsa_keypair_as_jwk(kid)
    token = _workos_token(private_key, kid, "https://api.workos.com/")
    auth = await _mock_workos_verifier(monkeypatch, public_jwk)

    payload = await auth.verify_token(token)

    assert payload["sub"] == "user_123"
    assert payload["sid"] == "session_123"


@pytest.mark.asyncio
async def test_verify_token_does_not_impose_legacy_issuer_on_workos_signed_token(monkeypatch):
    """AuthKit validates the token by WorkOS JWKS, not by app-local issuer guesses."""
    kid = "sso_oidc_key_pair_test"
    private_key, public_jwk = _rsa_keypair_as_jwk(kid)
    token = _workos_token(private_key, kid, "https://api.workos.com/user_management/client_123")
    auth = await _mock_workos_verifier(monkeypatch, public_jwk)

    payload = await auth.verify_token(token)

    assert payload["sub"] == "user_123"
    assert payload["sid"] == "session_123"


@pytest.mark.asyncio
async def test_verify_token_refreshes_jwks_once_when_cached_key_is_unknown(monkeypatch):
    """A valid WorkOS token should survive local JWKS cache staleness after key rotation."""
    kid = "sso_oidc_key_pair_rotated"
    private_key, public_jwk = _rsa_keypair_as_jwk(kid)
    token = _workos_token(private_key, kid, "https://api.workos.com/")
    _, stale_public_jwk = _rsa_keypair_as_jwk("sso_oidc_key_pair_stale")

    from api.services import auth

    jwks_responses = [
        {"keys": [stale_public_jwk]},
        {"keys": [public_jwk]},
    ]
    invalidated = False

    async def mock_get_jwks():
        return jwks_responses.pop(0)

    async def mock_invalidate_jwks_cache():
        nonlocal invalidated
        invalidated = True

    monkeypatch.setattr(auth, "get_jwks", mock_get_jwks)
    monkeypatch.setattr(auth, "invalidate_jwks_cache", mock_invalidate_jwks_cache)
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: SimpleNamespace(
            WORKOS_CLIENT_ID="client_123",
            WORKOS_AUDIENCE=None,
            workos_audience=None,
        ),
    )

    payload = await auth.verify_token(token)

    assert payload["sub"] == "user_123"
    assert invalidated is True
    assert len(jwks_responses) == 0
