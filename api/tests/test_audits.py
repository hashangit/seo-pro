"""
Test endpoints for critical API functionality.
"""

import uuid

import pytest

from api.conftest import (
    AuditRunRequest,
    EstimateRequest,
    settings,
)

# =============================================================================
# Health Check Tests
# ============================================================================


@pytest.mark.asyncio
async def test_health_check(app_client):
    """Test health check endpoint."""
    response = await app_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "checks" in data
    assert data["supabase"] == "ok"


# =============================================================================
# Credit Balance Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_credit_balance(app_client, auth_token):
    """Test getting credit balance."""
    response = await app_client.get(
        "/api/v1/credits/balance", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["balance"] == 100
    assert data["formatted"] == "100 credits"


# =============================================================================
# Audit Estimate Tests
# ============================================================================


@pytest.mark.asyncio
async def test_estimate_audit_cost(app_client, auth_token):
    """Test audit cost estimation."""
    request = EstimateRequest(url="https://example.com")
    response = await app_client.post(
        "/api/v1/audit/estimate", json=request, headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "credits_required" in data
    assert data["estimated_pages"] > 0
    assert data["cost_usd"] == data["credits_required"]


# =============================================================================
# Quote Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_quote(app_client, auth_token):
    """Test getting a pending quote."""
    # First create an estimate
    estimate_response = await app_client.post(
        "/api/v1/audit/estimate",
        json=EstimateRequest(url="https://example.com"),
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


# =============================================================================
# Audit Run Tests
# ============================================================================


@pytest.mark.asyncio
async def test_run_audit(app_client, auth_token):
    """Test running an audit."""
    # First create an estimate
    estimate_response = await app_client.post(
        "/api/v1/audit/estimate",
        json=EstimateRequest(url="https://example.com"),
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    quote_id = estimate_response.json()["quote_id"]

    # Run the audit (should fail if credits insufficient, but test user has 100)
    run_response = await app_client.post(
        "/api/v1/audit/run",
        json=AuditRunRequest(quote_id=quote_id),
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert run_response.status_code in [200, 402]  # 200 if success, 402 if insufficient credits

    if run_response.status_code == 200:
        data = run_response.json()
        assert "audit_id" in data


# =============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_estimate_without_url(app_client, auth_token):
    """Test estimate without URL returns 400."""
    response = await app_client.post(
        "/api/v1/audit/estimate", json={}, headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_unauthenticated_request(app_client):
    """Test that unauthenticated requests are rejected."""
    response = await app_client.get("/api/v1/credits/balance")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_signature_webhook(app_client):
    """Test that invalid webhook signatures are rejected."""
    from api.conftest import app_client

    # Prepare webhook payload
    payload = {
        "merchant_id": settings().PAYHERE_MERCHANT_ID,
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
# Fixtures
# ============================================================================


@pytest.fixture
async def cleanup_test_data(supabase_client):
    """Clean up test data from Supabase."""
    # Delete test users
    await supabase_client.table("users").delete().eq("email", "test@example.com").execute()

    # Delete test audits
    await supabase_client.table("audits").delete().eq("url", "https://example.com").execute()


@pytest.fixture
async def sample_quote(supabase_client):
    """Create a sample quote for testing."""

    quote_id = str(uuid.uuid4())

    # Insert quote
    await (
        supabase_client.table("pending_audits")
        .insert(
            {
                "id": quote_id,
                "user_id": "test-user-id",
                "url": "https://example.com",
                "page_count": 5,
                "credits_required": 5,
                "status": "pending",
                "expires_at": "now() + interval '30 minutes'",
            }
        )
        .execute()
    )

    return quote_id


# =============================================================================
# Test Run
# ============================================================================


@pytest.mark.asyncio
async def test_full_audit_flow(app_client, auth_token, supabase_client):
    """
    Test full audit flow: estimate -> quote approval -> run audit.
    This test requires a Supabase client with real connection.
    """
    # Create test user
    user_response = (
        await supabase_client.table("users")
        .insert(
            {
                "id": "test-user-id",
                "email": "audit-test@example.com",
                "credits_balance": 100,
                "plan_tier": "free",
                "created_at": "now()",
            }
        )
        .execute()
    )

    test_user_id = user_response.data[0]["id"]

    # Get auth token for test user
    from api.conftest import auth_token

    token = auth_token(test_user_id)

    # 1. Estimate audit cost
    estimate_request = EstimateRequest(url="https://example.com")
    estimate_response = await app_client.post(
        "/api/v1/audit/estimate",
        json=estimate_request,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert estimate_response.status_code == 200
    estimate_data = estimate_response.json()
    quote_id = estimate_data["quote_id"]

    # 2. Get and verify quote
    quote_response = await app_client.get(f"/api/v1/audits?quote_id={quote_id}")
    assert quote_response.status_code == 200
    quote_data = quote_response.json()
    assert quote_data["status"] == "pending"

    # 3. Run audit (should succeed with 100 credits)
    run_request = AuditRunRequest(quote_id=quote_id)
    run_response = await app_client.post(
        "/api/v1/audit/run", json=run_request, headers={"Authorization": f"Bearer {token}"}
    )
    assert run_response.status_code == 200
    run_data = run_response.json()

    # 4. Verify audit was created
    audit_response = await app_client.get(
        f"/api/v1/audit/{run_data['audit_id']}", headers={"Authorization": f"Bearer {token}"}
    )
    assert audit_response.status_code == 200
    audit_data = audit_response.json()

    # Cleanup
    await supabase_client.table("users").delete().eq("id", test_user_id).execute()
    await supabase_client.table("pending_audits").delete().eq("id", quote_id).execute()
    await supabase_client.table("audits").delete().eq("id", audit_data["id"]).execute()
