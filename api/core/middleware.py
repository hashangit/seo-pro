"""
Middleware for SEO Pro API

Security headers and other HTTP middleware.
"""

from fastapi import Request

from api.config import get_settings


async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    settings = get_settings()
    response = await call_next(request)

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # Prevent MIME-type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Enable XSS protection
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # HSTS for production
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response
