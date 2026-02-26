"""
Audit Routes

Handles audit discovery, estimation, execution, and status checking.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from api.core.dependencies import get_current_user
from api.models.audits import (
    AuditEstimateRequest,
    AuditEstimateResponse,
    AuditRunRequest,
    AuditRunResponse,
    AuditStatusResponse,
    URLDiscoveryRequest,
    URLDiscoveryResponse,
)
from api.services.audits import create_pending_quote, run_audit_with_quote
from api.services.credits import calculate_credits, format_cost_breakdown
from api.services.supabase import get_supabase_client
from config import get_settings

router = APIRouter(prefix="/api/v1/audit", tags=["Audits"])
settings = get_settings()


@router.post("/discover", response_model=URLDiscoveryResponse)
async def discover_site_urls(request: URLDiscoveryRequest, user: dict = Depends(get_current_user)):
    """
    Discover all URLs for a site.

    This endpoint returns the full list of URLs found, allowing the user to
    select which ones to include in the audit.

    Discovery order:
    1. If sitemap_url provided, use it directly
    2. Try to find sitemap from robots.txt or common locations
    3. Fall back to extracting internal links from homepage

    Returns:
    - urls: List of discovered URLs
    - source: Where URLs came from (sitemap, homepage, manual_sitemap)
    - confidence: How accurate the discovery is (1.0 for sitemap, 0.6 for homepage)
    - sitemap_found: Whether a sitemap was found
    - sitemap_url: URL of the sitemap if found
    - warning: Any warnings about the discovery
    - error: Any errors that occurred
    """
    from api.scanner.site import SiteScanner

    scanner = SiteScanner()
    try:
        result = await scanner.discover_urls(request.url, request.sitemap_url)
    finally:
        await scanner.close()

    return URLDiscoveryResponse(
        urls=result.get("urls", []),
        source=result.get("source", "error"),
        confidence=result.get("confidence", 0.0),
        sitemap_found=result.get("sitemap_found", False),
        sitemap_url=result.get("sitemap_url"),
        warning=result.get("warning"),
        error=result.get("error"),
    )


@router.post("/estimate", response_model=AuditEstimateResponse)
async def estimate_audit_cost(
    request: AuditEstimateRequest, user: dict = Depends(get_current_user)
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
    quote_id = await create_pending_quote(
        user_id=user["id"],
        url=request.url,
        page_count=page_count,
        credits_required=credits,
        metadata={"original_page_count": page_info.get("page_count")},
    )

    return AuditEstimateResponse(
        url=request.url,
        estimated_pages=page_count,
        credits_required=credits,
        cost_lkr=round(cost_lkr, 2),
        cost_usd=cost_usd,
        breakdown=format_cost_breakdown(page_count, credits),
        quote_id=quote_id,
        expires_at=(datetime.utcnow() + timedelta(minutes=30)).isoformat(),
    )


@router.post("/run", response_model=AuditRunResponse)
async def run_audit(request: AuditRunRequest, http_user: dict = Depends(get_current_user)):
    """
    Run audit after user confirms quote.
    Deducts credits atomically and starts analysis.

    DEV MODE: When enabled, skips credit deduction for development.
    """
    result = await run_audit_with_quote(
        quote_id=request.quote_id, user_id=http_user["id"], selected_urls=request.selected_urls
    )

    return AuditRunResponse(audit_id=result["audit_id"], status=result["status"])


@router.get("/{audit_id}", response_model=AuditStatusResponse)
async def get_audit_status(audit_id: str, user: dict = Depends(get_current_user)):
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
        error_message=audit.get("error_message"),
    )


@router.get("")
async def list_audits(user: dict = Depends(get_current_user), limit: int = 100, offset: int = 0):
    """List user's audits with pagination."""
    supabase = get_supabase_client()

    result = (
        supabase.table("audits")
        .select("*")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .range(offset, limit)
        .execute()
    )

    audits = result.data if result.data else []
    total_count = len(audits)

    return {
        "audits": audits,
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total_count,
    }
