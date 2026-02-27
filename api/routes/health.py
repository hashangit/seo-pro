"""
Health Check Routes

System health and readiness endpoints.
"""

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from api.core.dependencies import get_internal_secret
from api.models.common import HealthResponse
from api.services.auth import get_jwks, invalidate_jwks_cache
from api.services.supabase import get_supabase_client
from api.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["System"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@router.get("/health/ready")
async def readiness_check():
    """Readiness check - verifies all dependencies are accessible."""
    checks = {}

    # Check Supabase
    try:
        supabase = get_supabase_client()
        supabase.table("users").select("*").limit(1).execute()
        checks["supabase"] = "ok"
    except Exception as e:
        checks["supabase"] = f"error: {str(e)}"

    # Check JWKS endpoint
    try:
        await get_jwks()
        checks["jwks"] = "ok"
    except Exception as e:
        checks["jwks"] = f"error: {str(e)}"

    # Check SDK Worker (unified analysis worker)
    if settings.SDK_WORKER_URL:
        try:
            async with httpx.AsyncClient() as client:
                await client.get(f"{settings.SDK_WORKER_URL}/health", timeout=5.0)
                checks["sdk_worker"] = "ok"
        except Exception as e:
            checks["sdk_worker"] = f"error: {str(e)}"
    else:
        checks["sdk_worker"] = "not configured"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        content={"status": "ready" if all_ok else "not_ready", "checks": checks},
        status_code=status_code,
    )


@router.post("/internal/invalidate-jwks")
async def invalidate_jwks_cache_endpoint(request: Request):
    """
    Invalidate the JWKS cache.

    P0 FIX: This endpoint allows external systems (e.g., WorkOS webhooks)
    to trigger JWKS cache invalidation when signing keys are rotated.

    Security: This endpoint should be protected by a shared secret.
    """
    await get_internal_secret(request)
    await invalidate_jwks_cache()

    return {"status": "ok", "message": "JWKS cache invalidated"}


@router.post("/internal/cleanup/expired-quotes")
async def cleanup_expired_quotes_endpoint(request: Request):
    """
    Clean up expired pending audit quotes.

    This endpoint is designed to be called by Cloud Scheduler or similar
    cron systems. It removes all pending_audits that have expired.

    Security: This endpoint is protected by internal secret.

    Recommended schedule: Every hour (0 * * * *)
    """
    await get_internal_secret(request)

    supabase = get_supabase_client()

    try:
        result = supabase.rpc(
            "cleanup_expired_quotes_with_stats",
            {}
        ).execute()

        if result.data:
            return {
                "status": "ok",
                "deleted_count": result.data.get("deleted_count", 0),
                "cleaned_at": result.data.get("cleaned_at"),
            }

        return {"status": "ok", "deleted_count": 0, "message": "No expired quotes found"}

    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500,
        )
