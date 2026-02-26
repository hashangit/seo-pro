"""
Analysis Routes

Handles individual and batch analysis operations.
"""


from fastapi import APIRouter, Depends, HTTPException

from api.core.dependencies import get_current_user
from api.models.analyses import (
    AnalysisEstimateRequest,
    AnalysisEstimateResponse,
    AnalysisListResponse,
    AnalysisStatusResponse,
    AnalyzeRequest,
    AnalyzeResponse,
)
from api.services.analyses import (
    INDIVIDUAL_ANALYSIS_TYPES,
    run_individual_analysis,
    run_page_audit_analysis,
)
from api.services.audits import create_pending_quote
from api.services.credits import (
    CREDITS_PER_DOLLAR,
    calculate_individual_report_credits,
    calculate_page_audit_credits,
    calculate_site_audit_credits,
    format_cost_breakdown,
    format_individual_report_cost,
    format_page_audit_cost,
)
from api.services.supabase import get_supabase_client
from api.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["Analysis"])
settings = get_settings()


# ============================================================================
# Analysis Estimate Endpoint
# ============================================================================


@router.post("/analyze/estimate", response_model=AnalysisEstimateResponse)
async def estimate_analysis(
    request: AnalysisEstimateRequest, user: dict = Depends(get_current_user)
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
            invalid_types = [
                t for t in request.analysis_types if t not in INDIVIDUAL_ANALYSIS_TYPES
            ]
            if invalid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid analysis types: {invalid_types}. Valid types: {INDIVIDUAL_ANALYSIS_TYPES}",
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
        # If selected_urls provided, use that count directly
        if request.selected_urls:
            page_count = len(request.selected_urls)
        else:
            # Fall back to discovery
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

        # Create pending quote for site audits (30 min expiry)
        metadata = {"analysis_mode": "site_audit"}
        if request.selected_urls:
            metadata["selected_urls"] = request.selected_urls

        quote_id = await create_pending_quote(
            user_id=user["id"],
            url=request.url,
            page_count=page_count,
            credits_required=credits,
            metadata=metadata,
        )

        cost_usd = credits / CREDITS_PER_DOLLAR

        return AnalysisEstimateResponse(
            url=request.url,
            analysis_mode=request.analysis_mode,
            analysis_types=analysis_types,
            credits_required=credits,
            cost_usd=round(cost_usd, 2),
            breakdown="\n".join(breakdown_parts),
            estimated_pages=page_count,
            quote_id=quote_id,
        )

    cost_usd = credits / CREDITS_PER_DOLLAR

    return AnalysisEstimateResponse(
        url=request.url,
        analysis_mode=request.analysis_mode,
        analysis_types=analysis_types,
        credits_required=credits,
        cost_usd=round(cost_usd, 2),
        breakdown="\n".join(breakdown_parts),
        estimated_pages=1,  # Individual and page audit are single page
    )


# ============================================================================
# Analyses List Endpoints
# ============================================================================


@router.get("/analyses", response_model=AnalysisListResponse)
async def list_analyses(
    user: dict = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0,
    analysis_type: str | None = None,
    analysis_mode: str | None = None,
    status: str | None = None,
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
    total_count = count_result.count if hasattr(count_result, "count") else len(analyses)

    return AnalysisListResponse(
        analyses=analyses,
        total=total_count,
        limit=limit,
        offset=offset,
        has_more=offset + limit < total_count,
    )


@router.get("/analyses/{analysis_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(analysis_id: str, user: dict = Depends(get_current_user)):
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
        error_message=analysis.get("error_message"),
    )


# ============================================================================
# Individual Analysis Endpoints
# ============================================================================


def create_analysis_response(result: dict, analysis_type: str) -> AnalyzeResponse:
    """Create AnalyzeResponse from worker result."""
    if "category" in result:
        return AnalyzeResponse(**result)
    return AnalyzeResponse(category=analysis_type, error=result.get("error"))


@router.post("/analyze/technical", response_model=AnalyzeResponse)
async def analyze_technical(request: AnalyzeRequest, user: dict = Depends(get_current_user)):
    """
    Run technical SEO analysis only. (1 credit)

    Analyzes: title tags, meta descriptions, canonicals, heading structure,
    robots.txt, sitemap.xml, HTTPS, and Core Web Vitals indicators.
    """
    result = await run_individual_analysis(request.url, "technical", user)
    return create_analysis_response(result, "technical")


@router.post("/analyze/content", response_model=AnalyzeResponse)
async def analyze_content(request: AnalyzeRequest, user: dict = Depends(get_current_user)):
    """
    Run content quality (E-E-A-T) analysis only. (1 credit)

    Evaluates: Experience, Expertise, Authoritativeness, Trustworthiness,
    content depth, readability, and topical authority.
    """
    result = await run_individual_analysis(request.url, "content", user)
    return create_analysis_response(result, "content")


@router.post("/analyze/schema", response_model=AnalyzeResponse)
async def analyze_schema(request: AnalyzeRequest, user: dict = Depends(get_current_user)):
    """
    Run schema markup analysis only. (1 credit)

    Detects: JSON-LD, Microdata, RDFa. Validates against Google requirements.
    Identifies missing opportunities and deprecated types.
    """
    result = await run_individual_analysis(request.url, "schema", user)
    return create_analysis_response(result, "schema")


@router.post("/analyze/geo", response_model=AnalyzeResponse)
async def analyze_geo(request: AnalyzeRequest, user: dict = Depends(get_current_user)):
    """
    Run GEO (Generative Engine Optimization) analysis only. (1 credit)

    Analyzes: AI Overview optimization, ChatGPT/Perplexity visibility,
    llms.txt compliance, citability scoring, and AI crawler accessibility.
    """
    result = await run_individual_analysis(request.url, "geo", user)
    return create_analysis_response(result, "geo")


@router.post("/analyze/sitemap", response_model=AnalyzeResponse)
async def analyze_sitemap(request: AnalyzeRequest, user: dict = Depends(get_current_user)):
    """
    Run sitemap analysis only. (1 credit)

    Validates: XML format, URL count, lastmod accuracy, coverage vs crawled pages.
    """
    result = await run_individual_analysis(request.url, "sitemap", user)
    return create_analysis_response(result, "sitemap")


@router.post("/analyze/hreflang", response_model=AnalyzeResponse)
async def analyze_hreflang(request: AnalyzeRequest, user: dict = Depends(get_current_user)):
    """
    Run hreflang/international SEO analysis only. (1 credit)

    Validates: self-referencing tags, return tag reciprocity, x-default,
    ISO language/region codes, canonical alignment.
    """
    result = await run_individual_analysis(request.url, "hreflang", user)
    return create_analysis_response(result, "hreflang")


@router.post("/analyze/images", response_model=AnalyzeResponse)
async def analyze_images(request: AnalyzeRequest, user: dict = Depends(get_current_user)):
    """
    Run image SEO analysis only. (1 credit)

    Checks: alt text presence/quality, file sizes, formats (WebP/AVIF),
    responsive images, lazy loading, CLS prevention.
    """
    result = await run_individual_analysis(request.url, "images", user)
    return create_analysis_response(result, "images")


@router.post("/analyze/visual", response_model=AnalyzeResponse)
async def analyze_visual(request: AnalyzeRequest, user: dict = Depends(get_current_user)):
    """
    Run visual SEO analysis only (requires Playwright). (1 credit)

    Analyzes: above-the-fold elements, H1 visibility, CTA visibility,
    mobile rendering, responsive design, visual hierarchy.
    """
    result = await run_individual_analysis(request.url, "visual", user)
    return create_analysis_response(result, "visual")


@router.post("/analyze/performance", response_model=AnalyzeResponse)
async def analyze_performance(request: AnalyzeRequest, user: dict = Depends(get_current_user)):
    """
    Run performance/Core Web Vitals analysis only (requires Playwright). (1 credit)

    Measures: LCP (Largest Contentful Paint), INP (Interaction to Next Paint),
    CLS (Cumulative Layout Shift), resource optimization, caching headers.
    """
    result = await run_individual_analysis(request.url, "performance", user)
    return create_analysis_response(result, "performance")


@router.post("/analyze/page", response_model=AnalyzeResponse)
async def analyze_page(request: AnalyzeRequest, user: dict = Depends(get_current_user)):
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
    return create_analysis_response(result, "page")


@router.post("/analyze/plan", response_model=AnalyzeResponse)
async def analyze_plan(request: AnalyzeRequest, user: dict = Depends(get_current_user)):
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
    return create_analysis_response(result, "plan")


@router.post("/analyze/programmatic", response_model=AnalyzeResponse)
async def analyze_programmatic(request: AnalyzeRequest, user: dict = Depends(get_current_user)):
    """
    Run programmatic SEO analysis and planning. (1 credit)

    Analyzes scale SEO opportunities:
    - Template page patterns
    - Keyword clustering
    - Content automation potential
    - Implementation strategies
    """
    result = await run_individual_analysis(request.url, "programmatic", user)
    return create_analysis_response(result, "programmatic")


@router.post("/analyze/competitor-pages", response_model=AnalyzeResponse)
async def analyze_competitor_pages(request: AnalyzeRequest, user: dict = Depends(get_current_user)):
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
    return create_analysis_response(result, "competitor-pages")
