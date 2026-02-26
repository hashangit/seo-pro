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
    url: str
    max_pages: Optional[int] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v, **kwargs):
        if not v.startswith(("http://", "https://")):
            raise ValueError("Invalid URL")
        return v


class AnalysisEstimateRequest(BaseModel):
    """Analysis estimate request for any analysis type."""
    url: str
    analysis_mode: str = "individual"  # individual, page_audit, site_audit
    analysis_types: Optional[list[str]] = None  # For individual mode, which types to run
    max_pages: Optional[int] = None  # For site_audit mode

    @field_validator("url")
    @classmethod
    def validate_url(cls, v, **kwargs):
        if not v.startswith(("http://", "https://")):
            raise ValueError("Invalid URL - must start with http:// or https://")
        return v

    @field_validator("analysis_mode")
    @classmethod
    def validate_analysis_mode(cls, v, **kwargs):
        if v not in ["individual", "page_audit", "site_audit"]:
            raise ValueError("analysis_mode must be 'individual', 'page_audit', or 'site_audit'")
        return v


class AnalysisEstimateResponse(BaseModel):
    """Analysis estimate response."""
    url: str
    analysis_mode: str
    analysis_types: list[str]
    credits_required: int
    cost_usd: float
    breakdown: str


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

async def submit_audit_to_orchestrator(audit_id: str, url: str, page_count: int, user_id: str):
    """Submit audit job to SDK Worker for unified analysis."""
    sdk_worker_url = settings.SDK_WORKER_URL

    if not sdk_worker_url:
        raise HTTPException(
            status_code=503,
            detail="SDK Worker not configured. Please contact support."
        )

    # Submit single task to SDK Worker with full analysis
    await submit_sdk_task(audit_id, url, sdk_worker_url)


async def submit_sdk_task(audit_id: str, url: str, worker_url: str) -> str:
    """Submit audit task to SDK Worker."""
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
                "url": url,
                "analysis_type": "full"
            }).encode(),
        },
        "name": f"{settings.queue_path}/tasks/audit-{audit_id}-{uuid.uuid4().hex[:8]}",
    }

    response = client.create_task(request={"parent": settings.queue_path, "task": task})
    return response.name.split("/")[-1]


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

    # Check SDK Worker (required for all analysis)
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
# Analysis Estimate Endpoint
# ============================================================================

@app.post("/api/v1/analyze/estimate", response_model=AnalysisEstimateResponse, tags=["Analysis"])
async def estimate_analysis(
    request: AnalysisEstimateRequest,
    user: dict = Depends(get_current_user)
):
    """
    Estimate credits required for any analysis type.

    Modes:
    - individual: Select specific analysis types (1 credit each)
    - page_audit: All 12 analysis types on one page (8 credits)
    - site_audit: All 12 analysis types per page, site-wide (7 credits × pages)
    """
    credits = 0
    analysis_types = []
    breakdown_parts = []

    if request.analysis_mode == "individual":
        # Individual reports - 1 credit each
        if request.analysis_types:
            # Validate analysis types
            invalid_types = [t for t in request.analysis_types if t not in INDIVIDUAL_ANALYSIS_TYPES]
            if invalid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid analysis types: {invalid_types}. Valid types: {INDIVIDUAL_ANALYSIS_TYPES}"
                )
            analysis_types = request.analysis_types
        else:
            # Default to all if none specified
            analysis_types = INDIVIDUAL_ANALYSIS_TYPES

        credits = len(analysis_types) * calculate_individual_report_credits()
        breakdown_parts.append(format_individual_report_cost(len(analysis_types)))
        breakdown_parts.append(f"Types: {', '.join(analysis_types)}")

    elif request.analysis_mode == "page_audit":
        # Full page audit - 8 credits for all 12 types
        analysis_types = INDIVIDUAL_ANALYSIS_TYPES
        credits = calculate_page_audit_credits()
        breakdown_parts.append(format_page_audit_cost())
        breakdown_parts.append("(Bundle discount: 12 types → 8 credits)")

    elif request.analysis_mode == "site_audit":
        # Full site audit - 7 credits × pages
        from api.scanner.site import SiteScanner

        scanner = SiteScanner()
        try:
            page_info = await scanner.estimate_pages(request.url)
        finally:
            await scanner.close()

        page_count = page_info.get("page_count", 1)
        if request.max_pages and page_count > request.max_pages:
            page_count = request.max_pages

        analysis_types = INDIVIDUAL_ANALYSIS_TYPES
        credits = calculate_site_audit_credits(page_count)
        breakdown_parts.append(format_cost_breakdown(page_count, credits))
        breakdown_parts.append("(Volume discount: 7 credits/page vs 8 for single page)")

    cost_usd = credits / CREDITS_PER_DOLLAR

    return AnalysisEstimateResponse(
        url=request.url,
        analysis_mode=request.analysis_mode,
        analysis_types=analysis_types,
        credits_required=credits,
        cost_usd=round(cost_usd, 2),
        breakdown="\n".join(breakdown_parts)
    )


# ============================================================================
# Analyses List Endpoint
# ============================================================================

class AnalysisListResponse(BaseModel):
    """Response model for listing analyses."""
    analyses: list
    total: int
    limit: int
    offset: int
    has_more: bool


class AnalysisStatusResponse(BaseModel):
    """Response model for a single analysis status."""
    id: str
    url: str
    analysis_type: str
    analysis_mode: str
    credits_used: int
    status: str
    created_at: str
    completed_at: Optional[str]
    results: Optional[dict]
    error_message: Optional[str]


@app.get("/api/v1/analyses", response_model=AnalysisListResponse, tags=["Analysis"])
async def list_analyses(
    user: dict = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0,
    analysis_type: Optional[str] = None,
    analysis_mode: Optional[str] = None,
    status: Optional[str] = None
):
    """
    List user's analyses with optional filtering.

    Query params:
    - limit: Max results (default 100)
    - offset: Pagination offset
    - analysis_type: Filter by type (technical, content, schema, etc.)
    - analysis_mode: Filter by mode (individual, page_audit, site_audit)
    - status: Filter by status (pending, processing, completed, failed)
    """
    supabase = get_supabase_client()

    # Build query
    query = supabase.table("analyses").select("*").eq("user_id", user["id"])

    # Apply filters
    if analysis_type:
        query = query.eq("analysis_type", analysis_type)
    if analysis_mode:
        query = query.eq("analysis_mode", analysis_mode)
    if status:
        query = query.eq("status", status)

    # Execute with pagination
    result = query.order("created_at", desc=True).range(offset, offset + limit).execute()

    analyses = result.data if result.data else []

    # Get total count (separate query for accuracy)
    count_query = supabase.table("analyses").select("id", count="exact").eq("user_id", user["id"])
    if analysis_type:
        count_query = count_query.eq("analysis_type", analysis_type)
    if analysis_mode:
        count_query = count_query.eq("analysis_mode", analysis_mode)
    if status:
        count_query = count_query.eq("status", status)

    count_result = count_query.execute()
    total_count = count_result.count if hasattr(count_result, 'count') else len(analyses)

    return AnalysisListResponse(
        analyses=analyses,
        total=total_count,
        limit=limit,
        offset=offset,
        has_more=offset + limit < total_count
    )


@app.get("/api/v1/analyses/{analysis_id}", response_model=AnalysisStatusResponse, tags=["Analysis"])
async def get_analysis_status(
    analysis_id: str,
    user: dict = Depends(get_current_user)
):
    """Get status and results of a specific analysis."""
    supabase = get_supabase_client()

    result = supabase.table("analyses").select("*").eq("id", analysis_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Analysis not found")

    analysis = result.data[0]

    if analysis["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your analysis")

    return AnalysisStatusResponse(
        id=analysis["id"],
        url=analysis["url"],
        analysis_type=analysis["analysis_type"],
        analysis_mode=analysis["analysis_mode"],
        credits_used=analysis["credits_used"],
        status=analysis["status"],
        created_at=analysis["created_at"],
        completed_at=analysis.get("completed_at"),
        results=analysis.get("results_json"),
        error_message=analysis.get("error_message")
    )


# ============================================================================
# Individual Analysis Endpoints
# ============================================================================

class AnalyzeRequest(BaseModel):
    """Request model for individual analysis endpoints."""
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v, **kwargs):
        if not v.startswith(("http://", "https://")):
            raise ValueError("Invalid URL - must start with http:// or https://")
        return v


class AnalyzeResponse(BaseModel):
    """Response model for individual analysis endpoints."""
    category: str
    score: Optional[int] = None
    issues: list = []
    warnings: list = []
    passes: list = []
    recommendations: list = []
    error: Optional[str] = None


async def proxy_to_worker(worker_url: str, endpoint: str, url: str) -> dict:
    """Proxy analysis request to a worker service."""
    async with httpx.AsyncClient(timeout=120.0) as client:  # Increased timeout for SDK analysis
        try:
            response = await client.post(
                f"{worker_url}{endpoint}",
                json={"url": url},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"Worker error: {e.response.status_code}", "category": endpoint.replace("/analyze/", "")}
        except httpx.RequestError as e:
            return {"error": f"Worker unavailable: {str(e)}", "category": endpoint.replace("/analyze/", "")}


async def run_individual_analysis(
    url: str,
    analysis_type: str,
    user: dict
) -> dict:
    """
    Run an individual analysis with credit deduction.

    1. Check/validate worker is available
    2. Deduct 1 credit (unless DEV_MODE)
    3. Run analysis
    4. Return results
    """
    worker_url = get_worker_url()
    if not worker_url:
        raise HTTPException(status_code=503, detail="Worker not configured")

    # Deduct credit for individual report
    supabase = get_supabase_client()
    await deduct_analysis_credits(
        user_id=user["id"],
        credits=calculate_individual_report_credits(),
        analysis_type=analysis_type,
        url=url,
        supabase=supabase
    )

    # Run analysis
    result = await proxy_to_worker(worker_url, f"/analyze/{analysis_type}", url)
    return result


async def run_page_audit_analysis(
    url: str,
    user: dict
) -> dict:
    """
    Run a full page audit with credit deduction.

    1. Check/validate worker is available
    2. Deduct 8 credits (unless DEV_MODE)
    3. Run comprehensive analysis
    4. Return results
    """
    worker_url = get_worker_url()
    if not worker_url:
        raise HTTPException(status_code=503, detail="Worker not configured")

    # Deduct credits for page audit
    supabase = get_supabase_client()
    await deduct_analysis_credits(
        user_id=user["id"],
        credits=calculate_page_audit_credits(),
        analysis_type="page_audit",
        url=url,
        supabase=supabase
    )

    # Run analysis
    result = await proxy_to_worker(worker_url, "/analyze/page", url)
    return result


def get_worker_url(analysis_type: str = "http") -> str:
    """Get the SDK Worker URL (unified worker for all analysis types)."""
    if settings.SDK_WORKER_URL:
        return settings.SDK_WORKER_URL
    return None  # Will trigger 503 error in endpoint


@app.post("/api/v1/analyze/technical", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_technical(
    request: AnalyzeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Run technical SEO analysis only. (1 credit)

    Analyzes: title tags, meta descriptions, canonicals, heading structure,
    robots.txt, sitemap.xml, HTTPS, and Core Web Vitals indicators.
    """
    result = await run_individual_analysis(request.url, "technical", user)
    return AnalyzeResponse(**result) if "category" in result else AnalyzeResponse(category="technical", error=result.get("error"))


@app.post("/api/v1/analyze/content", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_content(
    request: AnalyzeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Run content quality (E-E-A-T) analysis only. (1 credit)

    Evaluates: Experience, Expertise, Authoritativeness, Trustworthiness,
    content depth, readability, and topical authority.
    """
    result = await run_individual_analysis(request.url, "content", user)
    return AnalyzeResponse(**result) if "category" in result else AnalyzeResponse(category="content", error=result.get("error"))


@app.post("/api/v1/analyze/schema", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_schema(
    request: AnalyzeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Run schema markup analysis only. (1 credit)

    Detects: JSON-LD, Microdata, RDFa. Validates against Google requirements.
    Identifies missing opportunities and deprecated types.
    """
    result = await run_individual_analysis(request.url, "schema", user)
    return AnalyzeResponse(**result) if "category" in result else AnalyzeResponse(category="schema", error=result.get("error"))


@app.post("/api/v1/analyze/geo", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_geo(
    request: AnalyzeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Run GEO (Generative Engine Optimization) analysis only. (1 credit)

    Analyzes: AI Overview optimization, ChatGPT/Perplexity visibility,
    llms.txt compliance, citability scoring, and AI crawler accessibility.
    """
    result = await run_individual_analysis(request.url, "geo", user)
    return AnalyzeResponse(**result) if "category" in result else AnalyzeResponse(category="geo", error=result.get("error"))


@app.post("/api/v1/analyze/sitemap", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_sitemap(
    request: AnalyzeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Run sitemap analysis only. (1 credit)

    Validates: XML format, URL count, lastmod accuracy, coverage vs crawled pages.
    """
    result = await run_individual_analysis(request.url, "sitemap", user)
    return AnalyzeResponse(**result) if "category" in result else AnalyzeResponse(category="sitemap", error=result.get("error"))


@app.post("/api/v1/analyze/hreflang", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_hreflang(
    request: AnalyzeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Run hreflang/international SEO analysis only. (1 credit)

    Validates: self-referencing tags, return tag reciprocity, x-default,
    ISO language/region codes, canonical alignment.
    """
    result = await run_individual_analysis(request.url, "hreflang", user)
    return AnalyzeResponse(**result) if "category" in result else AnalyzeResponse(category="hreflang", error=result.get("error"))


@app.post("/api/v1/analyze/images", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_images(
    request: AnalyzeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Run image SEO analysis only. (1 credit)

    Checks: alt text presence/quality, file sizes, formats (WebP/AVIF),
    responsive images, lazy loading, CLS prevention.
    """
    result = await run_individual_analysis(request.url, "images", user)
    return AnalyzeResponse(**result) if "category" in result else AnalyzeResponse(category="images", error=result.get("error"))


@app.post("/api/v1/analyze/visual", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_visual(
    request: AnalyzeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Run visual SEO analysis only (requires Playwright). (1 credit)

    Analyzes: above-the-fold elements, H1 visibility, CTA visibility,
    mobile rendering, responsive design, visual hierarchy.
    """
    result = await run_individual_analysis(request.url, "visual", user)
    return AnalyzeResponse(**result) if "category" in result else AnalyzeResponse(category="visual", error=result.get("error"))


@app.post("/api/v1/analyze/performance", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_performance(
    request: AnalyzeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Run performance/Core Web Vitals analysis only (requires Playwright). (1 credit)

    Measures: LCP (Largest Contentful Paint), INP (Interaction to Next Paint),
    CLS (Cumulative Layout Shift), resource optimization, caching headers.
    """
    result = await run_individual_analysis(request.url, "performance", user)
    return AnalyzeResponse(**result) if "category" in result else AnalyzeResponse(category="performance", error=result.get("error"))


@app.post("/api/v1/analyze/page", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_page(
    request: AnalyzeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Deep single-page SEO analysis (comprehensive, all-in-one). (8 credits)

    Comprehensive analysis of a single page covering:
    - On-page SEO (title, meta, headings, URL structure)
    - Content quality (word count, readability, E-E-A-T signals)
    - Technical elements (canonical, robots, OG tags)
    - Schema markup detection and validation
    - Image optimization
    - Core Web Vitals indicators

    This is equivalent to the CLI command `/seo page <url>`.
    Bundle discount: 12 individual reports would cost 12 credits, bundled at 8 credits.
    """
    result = await run_page_audit_analysis(request.url, user)
    return AnalyzeResponse(**result) if "category" in result else AnalyzeResponse(category="page", error=result.get("error"))


@app.post("/api/v1/analyze/plan", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_plan(
    request: AnalyzeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Run strategic SEO planning analysis. (1 credit)

    Creates industry-specific SEO strategy with templates for:
    - SaaS companies
    - E-commerce sites
    - Local service businesses
    - Publishers
    - Agencies

    Includes competitive analysis, content strategy, and implementation roadmap.
    """
    result = await run_individual_analysis(request.url, "plan", user)
    return AnalyzeResponse(**result) if "category" in result else AnalyzeResponse(category="plan", error=result.get("error"))


@app.post("/api/v1/analyze/programmatic", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_programmatic(
    request: AnalyzeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Run programmatic SEO analysis and planning. (1 credit)

    Analyzes scale SEO opportunities:
    - Template page patterns
    - Keyword clustering
    - Content automation potential
    - Implementation strategies
    """
    result = await run_individual_analysis(request.url, "programmatic", user)
    return AnalyzeResponse(**result) if "category" in result else AnalyzeResponse(category="programmatic", error=result.get("error"))


@app.post("/api/v1/analyze/competitor-pages", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_competitor_pages(
    request: AnalyzeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Analyze competitor comparison pages for SEO, GEO, and AEO. (1 credit)

    Analyzes existing "X vs Y" and "Alternatives to X" pages on your site for:
    - SEO optimization (title, meta, headings, schema)
    - GEO (Generative Engine Optimization) for AI search
    - AEO (Answer Engine Optimization) for voice/answer engines
    - Content quality and E-E-A-T signals
    - Feature matrix schema opportunities
    """
    result = await run_individual_analysis(request.url, "competitor-pages", user)
    return AnalyzeResponse(**result) if "category" in result else AnalyzeResponse(category="competitor-pages", error=result.get("error"))


# ============================================================================
# Credit calculation utilities (New Pricing Model)
# ============================================================================

# Credit pricing constants
CREDITS_PER_DOLLAR = 8  # $1 = 8 credits


def calculate_site_audit_credits(page_count: int) -> int:
    """
    Calculate credits required for a full site audit.

    Pricing: 7 credits × number of pages
    Includes all 12 analysis types per page.
    """
    return page_count * 7


def calculate_page_audit_credits() -> int:
    """
    Calculate credits required for a full page audit.

    Pricing: 8 credits (fixed)
    Includes all 12 analysis types on a single page.
    This is a bundle discount (12 individual would cost 12 credits).
    """
    return 8


def calculate_individual_report_credits() -> int:
    """
    Calculate credits required for a single analysis type.

    Pricing: 1 credit (fixed)
    Single analysis type on one URL.
    """
    return 1


def calculate_credits(page_count: int) -> int:
    """
    Legacy function - now calculates site audit credits.
    Kept for backward compatibility with existing audit endpoints.
    """
    return calculate_site_audit_credits(page_count)


def format_cost_breakdown(page_count: int, credits: int) -> str:
    """Generate human-readable cost explanation for site audits."""
    if settings.DEV_MODE:
        return f"FREE in Dev Mode - {page_count} pages will be analyzed"

    cost_usd = credits / CREDITS_PER_DOLLAR
    if page_count == 1:
        return f"1 page site audit: {credits} credits (${cost_usd:.2f})"
    else:
        return (
            f"Full site audit: {page_count} pages × 7 credits\n"
            f"Total: {credits} credits (${cost_usd:.2f})"
        )


def format_page_audit_cost() -> str:
    """Generate cost explanation for full page audit."""
    if settings.DEV_MODE:
        return "FREE in Dev Mode - Full page audit (all 12 analysis types)"
    return "Full page audit (all 12 analysis types): 8 credits ($1.00)"


def format_individual_report_cost(count: int = 1) -> str:
    """Generate cost explanation for individual reports."""
    if settings.DEV_MODE:
        return f"FREE in Dev Mode - {count} individual report{'s' if count != 1 else ''}"
    cost_usd = count / CREDITS_PER_DOLLAR
    return f"{count} individual report{'s' if count != 1 else ''}: {count} credit{'s' if count != 1 else ''} (${cost_usd:.2f})"


async def deduct_analysis_credits(
    user_id: str,
    credits: int,
    analysis_type: str,
    url: str,
    supabase
) -> bool:
    """
    Deduct credits for analysis. Returns True if successful.

    DEV MODE: Skips deduction entirely.
    """
    if settings.DEV_MODE:
        return True

    try:
        deduct_result = supabase.rpc("deduct_credits", {
            "p_user_id": user_id,
            "p_amount": credits,
            "p_reference_id": None,
            "p_reference_type": "analysis",
            "p_description": f"{analysis_type} analysis: {url}"
        }).execute()

        return deduct_result.data is not None and deduct_result.data
    except Exception as e:
        if "Insufficient credits" in str(e):
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Need {credits}, please top up."
            )
        raise


# Analysis type to endpoint mapping for individual reports
INDIVIDUAL_ANALYSIS_TYPES = [
    "technical",
    "content",
    "schema",
    "geo",
    "sitemap",
    "hreflang",
    "images",
    "visual",
    "performance",
    "plan",
    "programmatic",
    "competitor-pages",
]


# ============================================================================
# Startup and shutdown events
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
