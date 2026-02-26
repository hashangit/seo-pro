"""
Analysis Service

Handles individual and batch analysis execution via worker proxy.
"""


import httpx
from fastapi import HTTPException

from api.services.credits import (
    calculate_individual_report_credits,
    calculate_page_audit_credits,
)
from api.services.supabase import get_supabase_client
from config import get_settings

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


def get_worker_url(analysis_type: str = "http") -> str | None:
    """Get the SDK Worker URL (unified worker for all analysis types)."""
    settings = get_settings()
    if settings.SDK_WORKER_URL:
        return settings.SDK_WORKER_URL
    return None  # Will trigger 503 error in endpoint


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
            return {
                "error": f"Worker error: {e.response.status_code}",
                "category": endpoint.replace("/analyze/", ""),
            }
        except httpx.RequestError as e:
            return {
                "error": f"Worker unavailable: {str(e)}",
                "category": endpoint.replace("/analyze/", ""),
            }


async def run_individual_analysis(url: str, analysis_type: str, user: dict) -> dict:
    """
    Run an individual analysis with credit deduction.

    1. Check/validate worker is available
    2. Deduct 1 credit (unless DEV_MODE)
    3. Run analysis
    4. Return results (refund on failure - P0 FIX)
    """
    worker_url = get_worker_url()
    if not worker_url:
        raise HTTPException(status_code=503, detail="Worker not configured")

    # Deduct credit for individual report
    supabase = get_supabase_client()
    credits_to_deduct = calculate_individual_report_credits()

    await deduct_analysis_credits_for_service(
        user_id=user["id"],
        credits=credits_to_deduct,
        analysis_type=analysis_type,
        url=url,
        supabase=supabase,
    )

    # Run analysis with refund on failure (P0 FIX)
    try:
        result = await proxy_to_worker(worker_url, f"/analyze/{analysis_type}", url)

        # Check for worker errors
        if "error" in result:
            # Refund credits on worker failure
            try:
                supabase.rpc(
                    "refund_credits",
                    {
                        "p_user_id": user["id"],
                        "p_amount": credits_to_deduct,
                        "p_reference_type": "individual_analysis_refund",
                        "p_description": f"Analysis failed: {result['error']}",
                    },
                ).execute()
                print(
                    f"Refunded {credits_to_deduct} credits to user {user['id']} due to analysis failure"
                )
            except Exception as refund_error:
                print(f"CRITICAL: Failed to refund credits after analysis failure: {refund_error}")

            # Still return the error to the user
            return result

        return result

    except Exception as e:
        # Refund credits on unexpected failure
        try:
            supabase.rpc(
                "refund_credits",
                {
                    "p_user_id": user["id"],
                    "p_amount": credits_to_deduct,
                    "p_reference_type": "individual_analysis_refund",
                    "p_description": f"Analysis exception: {str(e)}",
                },
            ).execute()
            print(f"Refunded {credits_to_deduct} credits to user {user['id']} due to exception")
        except Exception as refund_error:
            print(f"CRITICAL: Failed to refund credits after exception: {refund_error}")

        raise HTTPException(
            status_code=503,
            detail=f"Analysis failed. Your credits have been refunded. Error: {str(e)}",
        )


async def run_page_audit_analysis(url: str, user: dict) -> dict:
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
    await deduct_analysis_credits_for_service(
        user_id=user["id"],
        credits=calculate_page_audit_credits(),
        analysis_type="page_audit",
        url=url,
        supabase=supabase,
    )

    # Run analysis
    result = await proxy_to_worker(worker_url, "/analyze/page", url)
    return result


async def deduct_analysis_credits_for_service(
    user_id: str, credits: int, analysis_type: str, url: str, supabase
) -> bool:
    """
    Deduct credits for analysis. Returns True if successful.

    DEV MODE: Skips deduction entirely.
    """
    from api.services.credits import deduct_analysis_credits

    return await deduct_analysis_credits(user_id, credits, analysis_type, url, supabase)
