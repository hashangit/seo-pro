"""
Test configuration and fixtures.
"""

import os
import uuid
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from pydantic import BaseModel

from api.config import Settings


# Override settings for testing
@pytest.fixture(autouse=True)
def override_settings(monkeypatch):
    """Override settings for testing."""
    def mock_getenv(key, default=None):
        if key == "SUPABASE_URL":
            return "https://test.supabase.co"
        elif key == "SUPABASE_SERVICE_KEY":
            return "test-service-key"
        elif key == "WORKOS_AUDIENCE" or key == "WORKOS_ISSUER":
            return "api.workos.com"
        elif key == "HTTP_WORKER_URL":
            return "http://localhost:8001"
        elif key == "BROWSER_WORKER_URL":
            return "http://localhost:8002"
        elif key == "ORCHESTRATOR_URL":
            return "http://localhost:8003"
        elif key == "FRONTEND_URL":
            return "http://localhost:3000"
        return os.environ.get(key, default)

    monkeypatch.setattr(os, "getenv", mock_getenv)


@pytest_asyncio.fixture
async def httpx_client():
    """Create HTTP client for testing."""
    return httpx.AsyncClient(base_url="http://localhost:8080", timeout=30.0, follow_redirects=True)


@pytest_asyncio.fixture
async def supabase_client():
    """Create Supabase client for testing."""
    from supabase import create_client

    return create_client("https://test.supabase.co", "test-service-key")


@pytest_asyncio.fixture
async def test_user():
    """Create a test user for authentication."""

    return {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "credits_balance": 100,
        "plan_tier": "free",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "last_sync": "2024-01-01T00:00:00Z",
    }


@pytest_asyncio.fixture
async def auth_token(test_user):
    """Create a test JWT token."""
    from jose import jwt

    return jwt.encode(
        {
            "sub": str(test_user["id"]),
            "email": test_user["email"],
            "given_name": test_user["first_name"],
            "aud": "api.workos.com",
            "iss": "api.workos.com",
            "exp": 9999999999,  # Far future
        },
        key="test-secret",
    )


@pytest_asyncio.fixture
async def app_client(monkeypatch, test_user):
    """Create a test FastAPI app client."""
    from api.config import Settings
    from api.main import app

    # Override settings for testing
    monkeypatch.setattr(
        "api.config.get_settings",
        lambda: Settings(
            ENVIRONMENT="development",
            SUPABASE_URL="https://test.supabase.co",
            SUPABASE_SERVICE_KEY="test-service-key",
            WORKOS_AUDIENCE="api.workos.com",
            WORKOS_ISSUER="api.workos.com",
            HTTP_WORKER_URL="http://localhost:8001",
            BROWSER_WORKER_URL="http://localhost:8002",
            SDK_WORKER_URL="http://localhost:8003",
        ),
    )

    # Mock verify_token to return test user data without calling WorkOS
    async def mock_verify_token(token: str) -> dict:
        """Mock token verification that returns test user data."""
        return {
            "sub": str(test_user["id"]),
            "email": test_user["email"],
            "given_name": test_user["first_name"],
            "family_name": test_user["last_name"],
            "aud": "api.workos.com",
            "iss": "api.workos.com",
        }

    monkeypatch.setattr("api.services.auth.verify_token", mock_verify_token)

    async with httpx.AsyncClient(app=app, base_url="http://localhost:8080") as client:
        yield client


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        ENVIRONMENT="development",
        SUPABASE_URL="https://test.supabase.co",
        SUPABASE_SERVICE_KEY="test-service-key",
        WORKOS_AUDIENCE="api.workos.com",
        WORKOS_ISSUER="api.workos.com",
        HTTP_WORKER_URL="http://localhost:8001",
        BROWSER_WORKER_URL="http://localhost:8002",
        SDK_WORKER_URL="http://localhost:8003",
    )


# Test data models
class EstimateRequest(BaseModel):
    url: str


class AuditRunRequest(BaseModel):
    quote_id: str


class CreditPurchaseRequest(BaseModel):
    amount: int = 5


class QuoteResponse(BaseModel):
    quote_id: str


class AuditStatusResponse(BaseModel):
    id: str
    status: str
    results: dict | None = None
