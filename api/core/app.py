"""
FastAPI App Factory for SEO Pro API

Creates and configures the FastAPI application instance.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.core.middleware import add_security_headers
from api.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="SEO Pro API",
        description="SEO analysis platform with credit-based pricing",
        version="1.0.0",
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Internal-Secret", "X-Request-ID"],
    )

    # Security headers middleware
    app.middleware("http")(add_security_headers)

    return app
