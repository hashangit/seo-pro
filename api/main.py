"""
SEO Pro API Gateway
FastAPI service for request routing, authentication, and orchestration.
Deployed on Cloud Run with scale-to-zero (min_instances=0).
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import jwt
from pydantic import BaseModel, Field

try:
    from pydantic import field_validator
except ImportError:
    # Older pydantic doesn't have field_validator, use validator instead
    from pydantic import validator as field_validator

# Import centralized configuration
from config import get_settings, validate_required_settings, get_supabase_client

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
# Initialize FastAPI
# ============================================================================

app = FastAPI(
    title="SEO Pro API",
    description="SEO analysis platform with credit-based pricing",
    version="1.0.0",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None
)

# CORS middleware - validate origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Global State (with thread-safe locking)
# ============================================================================

_jwks_cache: Optional[dict] = None
_jwks_cache_time: Optional[datetime] = None
_JWKS_CACHE_TTL = timedelta(minutes=15)
_jwks_lock = asyncio.Lock()

# Shared Supabase client (connection pooling)
_supabase_client = None


# ============================================================================
# JWKS Cache with Thread Safety
# ============================================================================

async def get_jwks() -> dict:
    """Fetch JWKS from WorkOS with caching and thread-safe update."""
    global _jwks_cache, _jwks_cache_time

    now = datetime.utcnow()
    if _jwks_cache and _jwks_cache_time:
        if now - _jwks_cache_time < _JWKS_CACHE_TTL:
            return _jwks_cache

    async with _jwks_lock:
        # Double-check after acquiring lock
        now = datetime.utcnow()
        if _jwks_cache and _jwks_cache_time:
            if now - _jwks_cache_time < _JWKS_CACHE_TTL:
                return _jwks_cache

        async with httpx.AsyncClient() as client:
            response = await client.get(settings.WORKOS_JWKS_URL, timeout=10.0)
            response.raise_for_status()
            _jwks_cache = response.json()
            _jwks_cache_time = now

    return _jwks_cache


async def verify_token(token: str) -> dict:
    """Verify WorkOS JWT token."""
    from jose.exceptions import JWTError, ExpiredSignatureError

    try:
        headers = jwt.get_unverified_headers(token)
        jwks = await get_jwks()

        # Get signing key
        rsa_key = None
        for key in jwks["keys"]:
            if key["kid"] == headers["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break

        if rsa_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find a valid signing key"
            )

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.WORKOS_AUDIENCE,
            issuer=settings.WORKOS_ISSUER
        )

        return payload

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


# ============================================================================
# Supabase Client with Connection Pooling
# ============================================================================

def get_supabase_client():
    """Get Supabase client singleton for database operations."""
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    return _supabase_client


async def get_current_user(request: Request) -> dict:
    """Get current authenticated user from JWT token."""
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )

    token = authorization.replace("Bearer ", "")
    payload = await verify_token(token)

    supabase = get_supabase_client()
    user = await sync_user_to_supabase(payload, supabase)

    return user


async def sync_user_to_supabase(workos_user: dict, supabase) -> dict:
    """Sync WorkOS user to Supabase on first login (lazy sync) with upsert."""
    user_id = workos_user.get("sub")

    # Try to get existing user
    result = supabase.table("users").select("*").eq("id", user_id).execute()

    if result.data:
        # Update last_sync
        supabase.table("users").update({
            "last_sync": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        return result.data[0]

    # Create new user with UPSERT to handle race conditions
    new_user = {
        "id": user_id,
        "email": workos_user.get("email"),
        "first_name": workos_user.get("given_name"),
        "last_name": workos_user.get("family_name"),
        "credits_balance": 0,
        "plan_tier": "free",
        "last_sync": datetime.utcnow().isoformat()
    }

    # Sync organization if present
    org_id = workos_user.get("org_id")
    if org_id:
        # Check if organization exists
        org_result = supabase.table("organizations").select("*").eq("id", org_id).execute()
        if not org_result.data:
            # Create organization
            supabase.table("organizations").insert({
                "id": org_id,
                "name": workos_user.get("org_name", "Unknown Organization")
            }).execute()
        new_user["organization_id"] = org_id

    # Use upsert via RPC to handle race conditions
    try:
        supabase.table("users").insert(new_user).execute()
    except Exception:
        # If insert failed (race condition), just fetch user
        result = supabase.table("users").select("*").eq("id", user_id).execute()
        if result.data:
            return result.data[0]

    return new_user


# ============================================================================
# Request/Response Models
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CreditBalanceResponse(BaseModel):
    """Credit balance response."""
    balance: int
    formatted: str


class CreditHistoryResponse(BaseModel):
    """Credit history response."""
    transactions: list
    total_purchased: int
    total_spent: int


class AuditEstimateRequest(BaseModel):
    """Audit estimate request."""
class AuditEstimateRequest(BaseModel):
    """Audit estimate request."""
    url: str
    max_pages: Optional[int] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v, **kwargs):
        if not v.startswith(("http://", "https://")):
            raise ValueError("Invalid URL")
        return v


class AuditEstimateResponse(BaseModel):
    """Audit estimate response."""
    url: str
    estimated_pages: int
    credits_required: int
    cost_lkr: float
    cost_usd: float
    breakdown: str
    quote_id: str
    expires_at: str


class AuditRunRequest(BaseModel):
    """Run audit request."""
    quote_id: str


class AuditRunResponse(BaseModel):
    """Run audit response."""
    audit_id: str
    status: str


class AuditStatusResponse(BaseModel):
    """Audit status response."""
    id: str
    url: str
    status: str
    page_count: int
    credits_used: int
    created_at: str
    completed_at: Optional[str]
    results: Optional[dict]
    error_message: Optional[str]


# ============================================================================
# Cloud Tasks Integration
# ============================================================================

async def submit_audit_task(audit_id: str, task_type: str, worker_url: str) -> str:
    """Submit audit task to Cloud Tasks queue."""
    from google.cloud import tasks_v2
    import uuid
    import json

    client = tasks_v2.CloudTasksClient()

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": f"{worker_url}/analyze",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "audit_id": audit_id,
                "task_type": task_type
            }).encode(),
        },
        "name": f"{settings.queue_path}/tasks/audit-{audit_id}-{task_type}-{uuid.uuid4().hex[:8]}",
    }

    response = client.create_task(request={"parent": settings.queue_path, "task": task})
    return response.name.split("/")[-1]


async def submit_audit_to_orchestrator(audit_id: str, url: str, page_count: int, user_id: str):
    """Submit audit job to orchestrator for distributed processing."""
    orchestrator_url = settings.ORCHESTRATOR_URL
    if not orchestrator_url:
        # Fallback: submit tasks directly
        tasks = [
            ("technical", settings.HTTP_WORKER_URL),
            ("content", settings.HTTP_WORKER_URL),
            ("schema", settings.HTTP_WORKER_URL),
            ("sitemap", settings.HTTP_WORKER_URL),
            ("programmatic", settings.HTTP_WORKER_URL),
            ("visual", settings.BROWSER_WORKER_URL),
        ]

        if not all(w for _, w in tasks):
            raise HTTPException(
                status_code=503,
                detail="Worker URLs not configured. Please contact support."
            )

        for task_type, worker_url in tasks:
            await submit_audit_task(audit_id, task_type, worker_url)
    else:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{orchestrator_url}/submit",
                json={
                    "audit_id": audit_id,
                    "user_id": user_id,
                    "url": url,
                    "page_count": page_count
                },
                timeout=30.0
            )


# ============================================================================
# Health Check
# ============================================================================

@app.get("/api/v1/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.get("/api/v1/health/ready", tags=["System"])
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

    # Check Workers
    if settings.HTTP_WORKER_URL:
        try:
            async with httpx.AsyncClient() as client:
                await client.get(f"{settings.HTTP_WORKER_URL}/health", timeout=5.0)
                checks["http_worker"] = "ok"
        except Exception as e:
            checks["http_worker"] = f"error: {str(e)}"

    if settings.BROWSER_WORKER_URL:
        try:
            async with httpx.AsyncClient() as client:
                await client.get(f"{settings.BROWSER_WORKER_URL}/health", timeout=5.0)
                checks["browser_worker"] = "ok"
        except Exception as e:
            checks["browser_worker"] = f"error: {str(e)}"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        content={"status": "ready" if all_ok else "not_ready", "checks": checks},
        status_code=status_code
    )


# ============================================================================
# Credits Endpoints
# ============================================================================

@app.get("/api/v1/credits/balance", response_model=CreditBalanceResponse, tags=["Credits"])
async def get_credit_balance(user: dict = Depends(get_current_user)):
    """
    Get user's current credit balance - fetches fresh from database.
    DEV MODE: Returns unlimited balance.
    """
    supabase = get_supabase_client()

    # DEV MODE: Return unlimited balance
    if settings.DEV_MODE:
        return CreditBalanceResponse(
            balance=999999,
            formatted="Unlimited (Dev Mode)"
        )

    # Fetch fresh balance from database
    result = supabase.table("users").select("credits_balance").eq("id", user["id"]).execute()

    if result.data:
        balance = result.data[0].get("credits_balance", 0)
    else:
        balance = 0

    return CreditBalanceResponse(
        balance=balance,
        formatted=f"{balance} credit{'s' if balance != 1 else ''}"
    )


@app.get("/api/v1/credits/history", response_model=CreditHistoryResponse, tags=["Credits"])
async def get_credit_history(user: dict = Depends(get_current_user)):
    """Get user's credit transaction history."""
    supabase = get_supabase_client()

    result = supabase.table("credit_transactions").select("*").eq(
        "user_id", user["id"]
    ).order("created_at", desc=True).limit(100).execute()

    transactions = result.data if result.data else []
    total_purchased = sum(t["amount"] for t in transactions if t["amount"] > 0)
    total_spent = abs(sum(t["amount"] for t in transactions if t["amount"] < 0))

    return CreditHistoryResponse(
        transactions=transactions,
        total_purchased=total_purchased,
        total_spent=total_spent
    )


# ============================================================================
# Audit Endpoints
# ============================================================================

@app.post("/api/v1/audit/estimate", response_model=AuditEstimateResponse, tags=["Audits"])
async def estimate_audit_cost(
    request: AuditEstimateRequest,
    user: dict = Depends(get_current_user)
):
    """
    Estimate audit cost before charging.
    Scans sitemap to determine page count.
    """
    from api.scanner.site import SiteScanner

    # Quick scan of site with proper cleanup
    scanner = SiteScanner()
    try:
        page_info = await scanner.estimate_pages(request.url)
    finally:
        await scanner.close()

    # Apply max_pages limit if provided
    page_count = page_info.get("page_count", 1)
    if request.max_pages and page_count > request.max_pages:
        page_count = request.max_pages

    # Calculate required credits
    credits = calculate_credits(page_count)
    cost_lkr = credits * 350  # Placeholder rate - will be replaced with IPG
    cost_usd = credits  # 1 credit = $1

    # Store as pending quote (30 min expiry)
    supabase = get_supabase_client()
    quote_result = supabase.table("pending_audits").insert({
        "user_id": user["id"],
        "url": request.url,
        "page_count": page_count,
        "credits_required": credits,
        "status": "pending",
        "metadata": {"original_page_count": page_info.get("page_count")},
        "expires_at": (datetime.utcnow() + timedelta(minutes=30)).isoformat()
    }).execute()

    quote_id = quote_result.data[0]["id"] if quote_result.data else None

    return AuditEstimateResponse(
        url=request.url,
        estimated_pages=page_count,
        credits_required=credits,
        cost_lkr=round(cost_lkr, 2),
        cost_usd=cost_usd,
        breakdown=format_cost_breakdown(page_count, credits),
        quote_id=quote_id,
        expires_at=(datetime.utcnow() + timedelta(minutes=30)).isoformat()
    )


@app.post("/api/v1/audit/run", response_model=AuditRunResponse, tags=["Audits"])
async def run_audit(
    request: AuditRunRequest,
    http_user: dict = Depends(get_current_user)
):
    """
    Run audit after user confirms quote.
    Deducts credits atomically and starts analysis.

    DEV MODE: When enabled, skips credit deduction for development.
    """
    supabase = get_supabase_client()

    # DEV MODE: Skip payment and credit checks
    if settings.DEV_MODE:
        # In dev mode, create audit directly without credit checks
        quote_result = supabase.table("pending_audits").select("*").eq("id", request.quote_id).execute()
        if not quote_result.data:
            raise HTTPException(status_code=404, detail="Quote not found")
        quote = quote_result.data[0]

        if quote["user_id"] != http_user["id"]:
            raise HTTPException(status_code=403, detail="Not your quote")

        # Create audit job directly
        audit_result = supabase.table("audits").insert({
            "user_id": http_user["id"],
            "url": quote["url"],
            "status": "queued",
            "page_count": quote["page_count"],
            "credits_used": 0  # Free in dev mode
        }).execute()

        audit_id = audit_result.data[0]["id"] if audit_result.data else None

        # Submit to Cloud Tasks for processing
        try:
            await submit_audit_to_orchestrator(
                audit_id=audit_id,
                url=quote["url"],
                page_count=quote["page_count"],
                user_id=http_user["id"]
            )
        except Exception as e:
            print(f"Warning: Failed to submit tasks: {e}")

        # Mark quote as completed
        supabase.table("pending_audits").update({"status": "completed"}).eq("id", request.quote_id).execute()

        return AuditRunResponse(
            audit_id=audit_id,
            status="processing"
        )

    # PRODUCTION MODE: Normal credit flow
    # Validate quote and update status atomically
    quote_result = supabase.table("pending_audits").select("*").eq("id", request.quote_id).execute()

    if not quote_result.data:
        raise HTTPException(status_code=404, detail="Quote not found")

    quote = quote_result.data[0]

    if quote["user_id"] != http_user["id"]:
        raise HTTPException(status_code=403, detail="Not your quote")

    # Check expiry first
    expires_at = datetime.fromisoformat(quote["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.utcnow():
        supabase.table("pending_audits").update({"status": "expired"}).eq("id", request.quote_id).execute()
        raise HTTPException(status_code=400, detail="Quote expired. Please request a new estimate.")

    # Atomic quote status update and credit deduction
    # First, atomically claim the quote
    update_result = supabase.table("pending_audits").update(
        {"status": "processing"}
    ).eq("id", request.quote_id).eq("status", "pending").execute()

    if not update_result.data:
        raise HTTPException(status_code=400, detail="Quote already used or expired")

    # Atomic credit deduction using RPC function
    try:
        deduct_result = supabase.rpc("deduct_credits", {
            "p_user_id": http_user["id"],
            "p_amount": quote["credits_required"],
            "p_reference_id": quote["id"],
            "p_reference_type": "audit",
            "p_description": f"Site audit: {quote['url']} ({quote['page_count']} pages)"
        }).execute()

        if not deduct_result.data:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Need {quote['credits_required']}, please top up."
            )
    except Exception as e:
        # Rollback quote status on credit deduction failure
        supabase.table("pending_audits").update({"status": "pending"}).eq("id", request.quote_id).execute()
        if "Insufficient credits" in str(e):
            raise HTTPException(status_code=402, detail=str(e))
        raise

    # Mark quote as approved
    supabase.table("pending_audits").update({"status": "approved"}).eq("id", request.quote_id).execute()

    # Create audit job
    audit_result = supabase.table("audits").insert({
        "user_id": http_user["id"],
        "url": quote["url"],
        "status": "queued",
        "page_count": quote["page_count"],
        "credits_used": quote["credits_required"]
    }).execute()

    audit_id = audit_result.data[0]["id"] if audit_result.data else None

    # Submit to Cloud Tasks for processing
    try:
        await submit_audit_to_orchestrator(
            audit_id=audit_id,
            url=quote["url"],
            page_count=quote["page_count"],
            user_id=http_user["id"]
        )
    except Exception as e:
        # Log error but don't fail - audit can be retried
        print(f"Warning: Failed to submit tasks: {e}")

    return AuditRunResponse(
        audit_id=audit_id,
        status="processing"
    )


@app.get("/api/v1/audit/{audit_id}", response_model=AuditStatusResponse, tags=["Audits"])
async def get_audit_status(
    audit_id: str,
    user: dict = Depends(get_current_user)
):
    """Get audit status and results."""
    supabase = get_supabase_client()

    result = supabase.table("audits").select("*").eq("id", audit_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit = result.data[0]

    if audit["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your audit")

    return AuditStatusResponse(
        id=audit["id"],
        url=audit["url"],
        status=audit["status"],
        page_count=audit["page_count"],
        credits_used=audit["credits_used"],
        created_at=audit["created_at"],
        completed_at=audit.get("completed_at"),
        results=audit.get("results_json"),
        error_message=audit.get("error_message")
    )


@app.get("/api/v1/audit", response_model=list, tags=["Audits"])
async def list_audits(
    user: dict = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0
):
    """List user's audits with pagination."""
    supabase = get_supabase_client()

    result = supabase.table("audits").select("*")\
        .eq("user_id", user["id"])\
        .order("created_at", desc=True)\
        .range(offset, limit)\
        .execute()

    audits = result.data if result.data else []
    total_count = len(audits)

    return {
        "audits": audits,
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total_count
    }


# ============================================================================
# Credit calculation utilities
# ============================================================================

def calculate_credits(page_count: int) -> int:
    """
    Calculate credits required based on page count.

    Pricing:
    - 1 page = 3 credits
    - 10 pages = 5 credits
    - Additional 10-page blocks = 2 credits each
    """
    if page_count == 1:
        return 3
    elif page_count <= 10:
        return 5
    else:
        additional_blocks = (page_count - 10 + 9) // 10
        return 5 + (additional_blocks * 2)


def format_cost_breakdown(page_count: int, credits: int) -> str:
    """Generate human-readable cost explanation."""
    if settings.DEV_MODE:
        return f"FREE in Dev Mode - {page_count} pages will be analyzed"

    credit_rate = 350  # Placeholder - will be replaced with IPG rate
    if page_count == 1:
        return f"1 page analysis: {credits} credits (${credits} / Rs. {credits * credit_rate})"
    elif page_count <= 10:
        return f"Up to 10 pages: {credits} credits (${credits} / Rs. {credits * credit_rate})"
    else:
        additional = page_count - 10
        blocks = (additional + 9) // 10
        return (
            f"First 10 pages: 5 credits\n"
            f"Additional {additional} pages (~{blocks} × 10): {blocks * 2} credits\n"
            f"Total: {credits} credits (${credits} / Rs. {credits * credit_rate})"
        )


# ============================================================================
# Startup and shutdown events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
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

    # Include routers
    from routes import audit  # noqa: F401
    # NOTE: PayHere integration removed - will be replaced with IPG
    # from webhooks import payhere  # noqa: F401

    app.include_router(audit.router, prefix="/api/v1/audit")
    # app.include_router(payhere.router, prefix="/api/v1/webhooks")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    global _supabase_client
    # Close any open connections if needed
    _supabase_client = None


# ============================================================================
# Main entry point
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )
