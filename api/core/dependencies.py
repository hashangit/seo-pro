"""
FastAPI Dependencies for SEO Pro API

Reusable dependencies for authentication and authorization.
"""

import os

from fastapi import HTTPException, Request, status

from api.services.auth import sync_user_to_supabase, verify_token
from api.services.supabase import get_supabase_client


async def get_current_user(request: Request) -> dict:
    """Get current authenticated user from JWT token."""
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header format"
        )

    token = authorization.replace("Bearer ", "")
    payload = await verify_token(token)

    supabase = get_supabase_client()
    user = await sync_user_to_supabase(payload, supabase)

    return user


async def get_internal_secret(request: Request) -> str:
    """Get and validate internal API secret for protected endpoints."""
    internal_secret = request.headers.get("X-Internal-Secret")
    expected_secret = os.getenv("INTERNAL_API_SECRET")

    if expected_secret and internal_secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid secret")

    return internal_secret
