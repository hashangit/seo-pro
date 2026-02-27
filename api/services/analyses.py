"""
Analysis Service

Handles individual and batch analysis execution via worker proxy.
"""

import logging

import httpx
from fastapi import HTTPException
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from api.services.credits import (
    calculate_individual_report_credits,
    calculate_page_audit_credits,
)
from api.services.supabase import get_supabase_client
from api.config import get_settings

logger = logging.getLogger(__name__)

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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(httpx.ConnectError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def proxy_to_worker(worker_url: str, endpoint: str, url: str) -> dict:
    """Proxy analysis request to a worker service with retry on transient failures."""
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
        except httpx.ConnectError:
            # This will be retried by the @retry decorator
            logger.warning(
                "worker_connection_failed",
                extra={"worker_url": worker_url, "endpoint": endpoint}
            )
            raise
        except httpx.RequestError as e:
            return {
                "error": f"Worker unavailable: {str(e)}",
                "category": endpoint.replace("/analyze/", ""),
            }


async def _create_analysis_record(
    supabase, user_id: str, url: str, analysis_type: str, analysis_mode: str, credits_used: int
) -> str | None:
    """Create an analysis record and return the analysis_id."""
    try:
        result = supabase.rpc(
            "create_analysis_record",
            {
                "p_user_id": user_id,
                "p_url": url,
                "p_analysis_type": analysis_type,
                "p_analysis_mode": analysis_mode,
                "p_credits_used": credits_used,
                "p_status": "processing",
            },
        ).execute()
        return result.data if result.data else None
    except Exception as e:
        logger.warning(
            "analysis_record_create_failed",
            extra={"user_id": user_id, "url": url, "error": str(e)}
        )
        return None


async def _update_analysis_record(
    supabase, analysis_id: str, status: str, results: dict | None = None, error: str | None = None
) -> bool:
    """Update an analysis record with results."""
    try:
        import json
        result = supabase.rpc(
            "update_analysis_record",
            {
                "p_analysis_id": analysis_id,
                "p_status": status,
                "p_results_json": json.dumps(results) if results else None,
                "p_error_message": error,
            },
        ).execute()
        return result.data is not None
    except Exception as e:
        logger.warning(
            "analysis_record_update_failed",
            extra={"analysis_id": analysis_id, "error": str(e)}
        )
        return False


async def run_individual_analysis(url: str, analysis_type: str, user: dict) -> dict:
    """
    Run an individual analysis with credit deduction.

    1. Check/validate worker is available
    2. Deduct 1 credit (unless DEV_MODE)
    3. Create analysis record in DB
    4. Run analysis
    5. Update record with results
    6. Return results (refund on failure - P0 FIX)
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

    # Create analysis record
    analysis_id = await _create_analysis_record(
        supabase=supabase,
        user_id=user["id"],
        url=url,
        analysis_type=analysis_type,
        analysis_mode="individual",
        credits_used=credits_to_deduct,
    )

    # Run analysis with refund on failure (P0 FIX)
    try:
        result = await proxy_to_worker(worker_url, f"/analyze/{analysis_type}", url)

        # Check for worker errors
        if "error" in result:
            # Update analysis record as failed
            if analysis_id:
                await _update_analysis_record(
                    supabase, analysis_id, "failed", error=result.get("error")
                )

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
                logger.info(
                    "analysis_refund_success",
                    extra={"user_id": user["id"], "credits": credits_to_deduct, "reason": "worker_error"}
                )
            except Exception as refund_error:
                logger.error(
                    "analysis_refund_failed",
                    extra={"user_id": user["id"], "credits": credits_to_deduct, "error": str(refund_error)}
                )

            # Still return the error to the user
            return result

        # Update analysis record as completed
        if analysis_id:
            await _update_analysis_record(
                supabase, analysis_id, "completed", results=result
            )

        return result

    except Exception as e:
        # Update analysis record as failed
        if analysis_id:
            await _update_analysis_record(
                supabase, analysis_id, "failed", error=str(e)
            )

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
            logger.info(
                "analysis_refund_success",
                extra={"user_id": user["id"], "credits": credits_to_deduct, "reason": "exception"}
            )
        except Exception as refund_error:
            logger.error(
                "analysis_refund_failed",
                extra={"user_id": user["id"], "credits": credits_to_deduct, "error": str(refund_error)}
            )

        raise HTTPException(
            status_code=503,
            detail=f"Analysis failed. Your credits have been refunded. Error: {str(e)}",
        )


async def run_page_audit_analysis(url: str, user: dict) -> dict:
    """
    Run a full page audit with credit deduction.

    1. Check/validate worker is available
    2. Deduct 8 credits (unless DEV_MODE)
    3. Create analysis record in DB
    4. Run comprehensive analysis
    5. Update record with results
    6. Return results
    """
    worker_url = get_worker_url()
    if not worker_url:
        raise HTTPException(status_code=503, detail="Worker not configured")

    # Deduct credits for page audit
    supabase = get_supabase_client()
    credits_to_deduct = calculate_page_audit_credits()

    await deduct_analysis_credits_for_service(
        user_id=user["id"],
        credits=credits_to_deduct,
        analysis_type="page_audit",
        url=url,
        supabase=supabase,
    )

    # Create analysis record
    analysis_id = await _create_analysis_record(
        supabase=supabase,
        user_id=user["id"],
        url=url,
        analysis_type="page_audit",
        analysis_mode="page_audit",
        credits_used=credits_to_deduct,
    )

    # Run analysis
    try:
        result = await proxy_to_worker(worker_url, "/analyze/page", url)

        # Check for worker errors
        if "error" in result:
            # Update analysis record as failed
            if analysis_id:
                await _update_analysis_record(
                    supabase, analysis_id, "failed", error=result.get("error")
                )
            return result

        # Update analysis record as completed
        if analysis_id:
            await _update_analysis_record(
                supabase, analysis_id, "completed", results=result
            )

        return result

    except Exception as e:
        # Update analysis record as failed
        if analysis_id:
            await _update_analysis_record(
                supabase, analysis_id, "failed", error=str(e)
            )
        raise


async def deduct_analysis_credits_for_service(
    user_id: str, credits: int, analysis_type: str, url: str, supabase
) -> bool:
    """
    Deduct credits for analysis. Returns True if successful.

    DEV MODE: Skips deduction entirely.
    """
    from api.services.credits import deduct_analysis_credits

    return await deduct_analysis_credits(user_id, credits, analysis_type, url, supabase)
