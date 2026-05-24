"""
Authentication Service

Handles JWKS caching, token verification, and user synchronization.
"""

import asyncio
import logging
from datetime import datetime, timedelta

import httpx
from fastapi import HTTPException, status
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from api.config import get_settings

logger = logging.getLogger(__name__)

# Global state with thread-safe locking
_jwks_cache: dict | None = None
_jwks_cache_time: datetime | None = None
_JWKS_CACHE_TTL = timedelta(minutes=15)
_jwks_lock = asyncio.Lock()


async def get_jwks() -> dict:
    """Fetch JWKS from WorkOS with caching and thread-safe update."""
    global _jwks_cache, _jwks_cache_time

    settings = get_settings()
    now = datetime.utcnow()
    if _jwks_cache and _jwks_cache_time:
        if now - _jwks_cache_time < _JWKS_CACHE_TTL:
            return _jwks_cache

    async with _jwks_lock:
        # Double-check after acquiring lock
        now = datetime.utcnow()
        if _jwks_cache and _jwks_cache_time:
            if now - _jwks_cache_time < _JWKS_CACHE_TTL:
                return _jwks_cache

        jwks_url = settings.WORKOS_JWKS_URL.format(client_id=settings.WORKOS_CLIENT_ID)
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, timeout=10.0)
            response.raise_for_status()
            _jwks_cache = response.json()
            _jwks_cache_time = now

    return _jwks_cache


async def invalidate_jwks_cache() -> None:
    """
    Invalidate the JWKS cache.

    This should be called when:
    - WorkOS rotates signing keys
    - A token fails validation due to unknown key ID
    - Manual cache invalidation is needed

    P0 FIX: Provides mechanism to respond to key rotation events.
    """
    global _jwks_cache, _jwks_cache_time

    async with _jwks_lock:
        _jwks_cache = None
        _jwks_cache_time = None
        logger.info("jwks_cache_invalidated", extra={"event": "cache_invalidation"})


def _find_rsa_key(jwks: dict, kid: str) -> dict | None:
    """Find the RSA signing key for a token kid in a JWKS response."""
    for key in jwks["keys"]:
        if key["kid"] == kid:
            return {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
    return None


async def verify_token(token: str) -> dict:
    """Verify WorkOS JWT token."""
    settings = get_settings()

    try:
        headers = jwt.get_unverified_headers(token)
        jwks = await get_jwks()

        rsa_key = _find_rsa_key(jwks, headers["kid"])

        if rsa_key is None:
            await invalidate_jwks_cache()
            jwks = await get_jwks()
            rsa_key = _find_rsa_key(jwks, headers["kid"])

        if rsa_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find a valid signing key",
            )

        decode_options = {}
        audience = settings.workos_audience
        if audience is None:
            decode_options["verify_aud"] = False

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=audience,
            options=decode_options,
        )

        return payload

    except ExpiredSignatureError:
        logger.warning("jwt_expired", extra={"event": "auth_failure", "reason": "token_expired"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except JWTError as e:
        # Log detailed error server-side, return generic message to client
        logger.error(
            "jwt_validation_error",
            extra={"event": "auth_failure", "reason": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token"
        )


async def _fetch_workos_user(user_id: str) -> dict | None:
    """Fetch full user profile from WorkOS API (includes email, name from IdP).

    Returns a dict with keys: email, first_name, last_name (or None on failure).
    """
    from api.config import get_settings
    settings = get_settings()
    if not settings.WORKOS_API_KEY:
        logger.warning("no_workos_api_key_for_user_lookup")
        return None

    from workos import AsyncWorkOSClient
    try:
        client = AsyncWorkOSClient(
            api_key=settings.WORKOS_API_KEY,
            client_id=settings.WORKOS_CLIENT_ID,
        )
        profile = await client.user_management.get_user(user_id)
        return {
            "email": profile.email,
            "first_name": profile.first_name or "",
            "last_name": profile.last_name or "",
        }
    except Exception as e:
        logger.warning("workos_user_lookup_failed", extra={"error": str(e)})
        return None


async def sync_user_to_supabase(workos_user: dict, supabase) -> dict:
    """Sync WorkOS user to Supabase on first login (lazy sync).

    AuthKit JWTs only carry sub/sid/org_id/role. For email and name we fetch the
    full profile from WorkOS API, which has the identity provider's real data
    (e.g. Google OAuth returns email, given_name, family_name).
    """
    user_id = workos_user.get("sub")

    # Try to get existing user
    result = supabase.table("users").select("*").eq("id", user_id).execute()

    if result.data:
        # Update last_sync and refresh profile data from WorkOS
        workos_profile = await _fetch_workos_user(user_id)
        update_fields: dict = {"last_sync": datetime.utcnow().isoformat()}
        if workos_profile:
            if workos_profile.get("email"):
                update_fields["email"] = workos_profile["email"]
            if workos_profile.get("first_name"):
                update_fields["first_name"] = workos_profile["first_name"]
            if workos_profile.get("last_name"):
                update_fields["last_name"] = workos_profile["last_name"]
        supabase.table("users").update(update_fields).eq("id", user_id).execute()
        return result.data[0]

    # New user — fetch full profile from WorkOS API
    workos_profile = await _fetch_workos_user(user_id)
    email = (
        (workos_profile.get("email") if workos_profile else None)
        or workos_user.get("email")
        or f"{user_id}@placeholder.local"
    )
    new_user = {
        "id": user_id,
        "email": email,
        "first_name": (workos_profile.get("first_name") if workos_profile else None) or workos_user.get("given_name") or "",
        "last_name": (workos_profile.get("last_name") if workos_profile else None) or workos_user.get("family_name") or "",
        "credits_balance": 0,
        "last_sync": datetime.utcnow().isoformat(),
    }

    # Sync organization if present
    org_id = workos_user.get("org_id")
    if org_id:
        org_result = supabase.table("organizations").select("*").eq("id", org_id).execute()
        if not org_result.data:
            supabase.table("organizations").insert(
                {"id": org_id, "name": workos_user.get("org_name", "Unknown Organization")}
            ).execute()
        new_user["organization_id"] = org_id

    try:
        supabase.table("users").insert(new_user).execute()
    except Exception:
        result = supabase.table("users").select("*").eq("id", user_id).execute()
        if result.data:
            return result.data[0]

    return new_user
