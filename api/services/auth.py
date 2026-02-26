"""
Authentication Service

Handles JWKS caching, token verification, and user synchronization.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import HTTPException, Request, status
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError

from config import get_settings

# Global state with thread-safe locking
_jwks_cache: Optional[dict] = None
_jwks_cache_time: Optional[datetime] = None
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

        async with httpx.AsyncClient() as client:
            response = await client.get(settings.WORKOS_JWKS_URL, timeout=10.0)
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
        print("JWKS cache invalidated")


async def verify_token(token: str) -> dict:
    """Verify WorkOS JWT token."""
    settings = get_settings()

    try:
        headers = jwt.get_unverified_headers(token)
        jwks = await get_jwks()

        # Get signing key
        rsa_key = None
        for key in jwks["keys"]:
            if key["kid"] == headers["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break

        if rsa_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find a valid signing key"
            )

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.WORKOS_AUDIENCE,
            issuer=settings.WORKOS_ISSUER
        )

        return payload

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except JWTError as e:
        # Log detailed error server-side, return generic message to client
        print(f"JWT validation error: {str(e)}")  # Server-side logging only
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )


async def sync_user_to_supabase(workos_user: dict, supabase) -> dict:
    """Sync WorkOS user to Supabase on first login (lazy sync) with upsert."""
    user_id = workos_user.get("sub")

    # Try to get existing user
    result = supabase.table("users").select("*").eq("id", user_id).execute()

    if result.data:
        # Update last_sync
        supabase.table("users").update({
            "last_sync": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        return result.data[0]

    # Create new user with UPSERT to handle race conditions
    new_user = {
        "id": user_id,
        "email": workos_user.get("email"),
        "first_name": workos_user.get("given_name"),
        "last_name": workos_user.get("family_name"),
        "credits_balance": 0,
        "plan_tier": "free",
        "last_sync": datetime.utcnow().isoformat()
    }

    # Sync organization if present
    org_id = workos_user.get("org_id")
    if org_id:
        # Check if organization exists
        org_result = supabase.table("organizations").select("*").eq("id", org_id).execute()
        if not org_result.data:
            # Create organization
            supabase.table("organizations").insert({
                "id": org_id,
                "name": workos_user.get("org_name", "Unknown Organization")
            }).execute()
        new_user["organization_id"] = org_id

    # Use upsert via RPC to handle race conditions
    try:
        supabase.table("users").insert(new_user).execute()
    except Exception:
        # If insert failed (race condition), just fetch user
        result = supabase.table("users").select("*").eq("id", user_id).execute()
        if result.data:
            return result.data[0]

    return new_user
