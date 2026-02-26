"""
SEO Pro API Gateway

FastAPI service for request routing, authentication, and orchestration.
Deployed on Cloud Run with scale-to-zero (min_instances=0).

This is the main entry point that assembles all modular components.
"""

import uvicorn

# Import centralized configuration
from config import get_settings, validate_required_settings

# Import app factory
from api.core.app import create_app

# Import services for startup
from api.services.supabase import get_supabase_client, reset_supabase_client
from api.services.auth import get_jwks

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

from api.routes import health, credits, audits, analyses

app.include_router(health.router)
app.include_router(credits.router)
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
        print("=" * 70)
        print("⚠️  WARNING: DEV_MODE is enabled in {} environment!".format(settings.ENVIRONMENT.upper()))
        print("⚠️  All credit checks are BYPASSED - users have unlimited access!")
        print("⚠️  Set DEV_MODE=false before production deployment!")
        print("=" * 70)

    # Prefetch JWKS to avoid cold-start delay
    try:
        await get_jwks()
        print("JWKS fetched successfully at startup")
    except Exception as e:
        print(f"Warning: Failed to prefetch JWKS: {e}")

    # Validate Supabase connection
    try:
        supabase = get_supabase_client()
        supabase.table("users").select("*").limit(1).execute()
        print("Supabase connection validated")
    except Exception as e:
        print(f"Error: Failed to connect to Supabase: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    reset_supabase_client()


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )
