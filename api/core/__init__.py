"""
Core Infrastructure for SEO Pro API

FastAPI app factory, middleware, and dependencies.
"""

from .app import create_app
from .middleware import add_security_headers
from .dependencies import get_current_user

__all__ = [
    "create_app",
    "add_security_headers",
    "get_current_user",
]
