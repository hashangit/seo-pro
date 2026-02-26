"""
Test endpoints for critical API functionality.

Note: Tests requiring database access are marked to skip in CI.
They can be run locally with a real Supabase connection.
"""

import os

import pytest

from api.conftest import EstimateRequest, get_test_settings

# Skip database tests in CI (where no real Supabase is available)
SKIP_DB_TESTS = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"


# =============================================================================
# Health Check Tests - No database required
# =============================================================================


@pytest.mark.asyncio
async def test_health_check(app_client):
    """Test health check endpoint."""
    response = await app_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


# =============================================================================
# Authentication Tests - These test that the auth middleware works
# NOTE: These will return 401 if the dependency override is NOT applied
# =============================================================================


@pytest.mark.asyncio
async def test_unauthenticated_request_no_token(app_client):
    """Test that requests without token are rejected."""
    # Since app_client has dependency override, we test with a fresh client
    # We need to clear the dependency overrides to test auth properly
    from api.main import app
    from api.core.dependencies import get_current_user
    import httpx

    # Save and clear dependency overrides temporarily
    saved_overrides = app.dependency_overrides.copy()
    app.dependency_overrides.clear()

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8080") as client:
            response = await client.get("/api/v1/credits/balance")
            assert response.status_code == 401
    finally:
        # Restore the overrides
        app.dependency_overrides.update(saved_overrides)


@pytest.mark.asyncio
async def test_unauthenticated_request_invalid_token(app_client):
    """Test that requests with invalid token are rejected."""
    from api.main import app
    import httpx

    # Save and clear dependency overrides temporarily
    saved_overrides = app.dependency_overrides.copy()
    app.dependency_overrides.clear()

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8080") as client:
            response = await client.get(
                "/api/v1/credits/balance", headers={"Authorization": "Bearer invalid_token"}
            )
            assert response.status_code == 401
    finally:
        # Restore the overrides
        app.dependency_overrides.update(saved_overrides)


# =============================================================================
# Webhook Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.skip(reason="Webhook endpoint not implemented yet")
async def test_invalid_signature_webhook(app_client):
    """Test that invalid webhook signatures are rejected."""
    test_settings = get_test_settings()

    # Prepare webhook payload
    payload = {
        "merchant_id": test_settings.PAYHERE_MERCHANT_ID,
        "order_id": "test-order",
        "payhere_amount": "350.00",
        "payhere_currency": "LKR",
        "status_code": "2",  # Success
        "md5sig": "INVALID_SIGNATURE",
    }

    response = await app_client.post(
        "/api/v1/webhooks/payhere",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 400
    assert "signature" in response.json()["detail"]


# =============================================================================
# Database-Dependent Tests (skip in CI)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.skipif(SKIP_DB_TESTS, reason="Requires database connection")
async def test_estimate_without_url(app_client, auth_token):
    """Test estimate without URL returns 422 (validation error)."""
    response = await app_client.post(
        "/api/v1/audit/estimate", json={}, headers={"Authorization": f"Bearer {auth_token}"}
    )
    # FastAPI returns 422 for validation errors when required fields are missing
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.skipif(SKIP_DB_TESTS, reason="Requires database connection")
async def test_get_credit_balance(app_client, auth_token):
    """Test getting credit balance."""
    response = await app_client.get(
        "/api/v1/credits/balance", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["balance"] == 100
    assert data["formatted"] == "100 credits"


@pytest.mark.asyncio
@pytest.mark.skipif(SKIP_DB_TESTS, reason="Requires database connection")
async def test_estimate_audit_cost(app_client, auth_token):
    """Test audit cost estimation."""
    request = EstimateRequest(url="https://example.com")
    response = await app_client.post(
        "/api/v1/audit/estimate", json=request.model_dump(), headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "credits_required" in data
    assert data["estimated_pages"] > 0
    assert data["cost_usd"] == data["credits_required"]


@pytest.mark.asyncio
@pytest.mark.skipif(SKIP_DB_TESTS, reason="Requires database connection")
async def test_get_quote(app_client, auth_token):
    """Test getting a pending quote."""
    # First create an estimate
    estimate_response = await app_client.post(
        "/api/v1/audit/estimate",
        json=EstimateRequest(url="https://example.com").model_dump(),
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    quote_id = estimate_response.json()["quote_id"]

    # Fetch the quote
    response = await app_client.get(f"/api/v1/audits?quote_id={quote_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == quote_id
    assert data["status"] == "pending"
    assert data["expires_at"]


@pytest.mark.asyncio
@pytest.mark.skipif(SKIP_DB_TESTS, reason="Requires database connection")
async def test_run_audit(app_client, auth_token):
    """Test running an audit."""
    from api.conftest import AuditRunRequest

    # First create an estimate
    estimate_response = await app_client.post(
        "/api/v1/audit/estimate",
        json=EstimateRequest(url="https://example.com").model_dump(),
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    quote_id = estimate_response.json()["quote_id"]

    # Run the audit (should fail if credits insufficient, but test user has 100)
    run_response = await app_client.post(
        "/api/v1/audit/run",
        json=AuditRunRequest(quote_id=quote_id).model_dump(),
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert run_response.status_code in [200, 402]  # 200 if success, 402 if insufficient credits

    if run_response.status_code == 200:
        data = run_response.json()
        assert "audit_id" in data
