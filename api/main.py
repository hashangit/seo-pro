"""
SEO Pro API Gateway

FastAPI service for request routing, authentication, and orchestration.
Deployed on Cloud Run with scale-to-zero (min_instances=0).

This is the main entry point that assembles all modular components.
"""

import logging
import sys

import uvicorn

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Import app factory
from api.core.app import create_app
from api.routes import analyses, audits, credits, credit_requests, health
from api.routes.admin import credits as admin_credits
from api.services.auth import get_jwks

# Import services for startup
from api.services.supabase import get_supabase_client, reset_supabase_client

# Import centralized configuration
from api.config import get_settings, validate_required_settings

# ============================================================================
# Environment Variable Validation
# ============================================================================


def validate_environment():
    """Validate required environment variables at startup."""
    validate_required_settings()


validate_environment()

# Get settings instance
settings = get_settings()

# ============================================================================
# Create FastAPI Application
# ============================================================================

app = create_app()

# ============================================================================
# Include Routers
# ============================================================================

app.include_router(health.router)
app.include_router(credits.router)
app.include_router(credit_requests.router)
app.include_router(admin_credits.router)
app.include_router(audits.router)
app.include_router(analyses.router)

# ============================================================================
# Startup and Shutdown Events
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    # DEV MODE warning for production/staging
    if settings.DEV_MODE and settings.ENVIRONMENT in ["production", "staging"]:
        logger.critical(
            "dev_mode_enabled_in_production",
            extra={"environment": settings.ENVIRONMENT}
        )

    # Prefetch JWKS to avoid cold-start delay
    try:
        await get_jwks()
        logger.info("jwks_prefetched", extra={"event": "startup"})
    except Exception as e:
        logger.warning("jwks_prefetch_failed", extra={"error": str(e)})

    # Validate Supabase connection
    try:
        supabase = get_supabase_client()
        supabase.table("users").select("*").limit(1).execute()
        logger.info("supabase_connection_validated", extra={"event": "startup"})
    except Exception as e:
        logger.error("supabase_connection_failed", extra={"error": str(e)})


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    reset_supabase_client()


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app", host="0.0.0.0", port=settings.PORT, reload=settings.ENVIRONMENT == "development"
    )
