"""
Audit Service

Handles audit estimation, execution, and orchestration.
"""

import logging
from datetime import datetime, timedelta

from fastapi import HTTPException

from api.services.cloud_tasks import submit_audit_to_orchestrator
from api.services.supabase import get_supabase_client
from api.config import get_settings

logger = logging.getLogger(__name__)


async def create_pending_quote(
    user_id: str, url: str, page_count: int, credits_required: int, metadata: dict | None = None
) -> str:
    """Create a pending audit quote with 30 min expiry."""
    supabase = get_supabase_client()

    quote_result = (
        supabase.table("pending_audits")
        .insert(
            {
                "user_id": user_id,
                "url": url,
                "page_count": page_count,
                "credits_required": credits_required,
                "status": "pending",
                "metadata": metadata or {},
                "expires_at": (datetime.utcnow() + timedelta(minutes=30)).isoformat(),
            }
        )
        .execute()
    )

    return quote_result.data[0]["id"] if quote_result.data else None


async def validate_and_claim_quote(quote_id: str, user_id: str) -> dict:
    """
    Validate and claim a quote atomically.

    Returns the quote data if valid.
    Raises HTTPException if invalid/expired/not owned.
    """
    supabase = get_supabase_client()

    quote_result = supabase.table("pending_audits").select("*").eq("id", quote_id).execute()

    if not quote_result.data:
        raise HTTPException(status_code=404, detail="Quote not found")

    quote = quote_result.data[0]

    if quote["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not your quote")

    # Check expiry
    expires_at = datetime.fromisoformat(quote["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.utcnow():
        supabase.table("pending_audits").update({"status": "expired"}).eq("id", quote_id).execute()
        raise HTTPException(status_code=400, detail="Quote expired. Please request a new estimate.")

    # Atomically claim the quote
    update_result = (
        supabase.table("pending_audits")
        .update({"status": "processing"})
        .eq("id", quote_id)
        .eq("status", "pending")
        .execute()
    )

    if not update_result.data:
        raise HTTPException(status_code=400, detail="Quote already used or expired")

    return quote


async def deduct_credits_atomic(
    user_id: str, amount: int, quote_id: str, url: str, page_count: int
) -> bool:
    """
    Deduct credits atomically using RPC function.

    Raises HTTPException on insufficient credits.
    """
    supabase = get_supabase_client()

    try:
        deduct_result = supabase.rpc(
            "deduct_credits",
            {
                "p_user_id": user_id,
                "p_amount": amount,
                "p_reference_id": quote_id,
                "p_reference_type": "audit",
                "p_description": f"Site audit: {url} ({page_count} pages)",
            },
        ).execute()

        if not deduct_result.data:
            raise HTTPException(
                status_code=402, detail=f"Insufficient credits. Need {amount}, please top up."
            )
        return True
    except Exception as e:
        if "Insufficient credits" in str(e):
            raise HTTPException(
                status_code=402, detail=f"Insufficient credits. Need {amount}, please top up."
            )
        raise


async def refund_credits(user_id: str, amount: int, reference_id: str, reason: str) -> bool:
    """Refund credits to user."""
    supabase = get_supabase_client()

    try:
        supabase.rpc(
            "refund_credits",
            {
                "p_user_id": user_id,
                "p_amount": amount,
                "p_reference_id": reference_id,
                "p_reference_type": "audit_refund",
                "p_description": reason,
            },
        ).execute()
        logger.info("credits_refunded", extra={"user_id": user_id, "amount": amount, "reference_id": reference_id})
        return True
    except Exception as refund_error:
        logger.error("refund_failed", extra={"user_id": user_id, "amount": amount, "error": str(refund_error)})
        return False


async def create_audit_record(user_id: str, url: str, page_count: int, credits_used: int) -> str:
    """Create an audit record and return the audit_id."""
    supabase = get_supabase_client()

    audit_result = (
        supabase.table("audits")
        .insert(
            {
                "user_id": user_id,
                "url": url,
                "status": "queued",
                "page_count": page_count,
                "credits_used": credits_used,
            }
        )
        .execute()
    )

    return audit_result.data[0]["id"] if audit_result.data else None


async def update_audit_status(audit_id: str, status: str, error_message: str | None = None):
    """Update audit status."""
    supabase = get_supabase_client()

    update_data = {"status": status}
    if error_message:
        update_data["error_message"] = error_message

    supabase.table("audits").update(update_data).eq("id", audit_id).execute()


async def run_audit_with_quote(
    quote_id: str, user_id: str, selected_urls: list[str] | None = None
) -> dict:
    """
    Execute audit from a validated quote.

    This handles:
    1. Credit deduction
    2. Audit record creation
    3. Task submission
    4. Error handling with refunds

    Returns {"audit_id": str, "status": str}
    """
    settings = get_settings()
    supabase = get_supabase_client()

    # DEV MODE: Skip payment and credit checks
    if settings.DEV_MODE:
        logger.warning(
            "credit_bypass_dev_mode",
            extra={
                "event": "audit_bypass",
                "user_id": user_id,
                "quote_id": quote_id
            }
        )
        return await _run_audit_dev_mode(quote_id, user_id, selected_urls)

    # PRODUCTION MODE: Normal credit flow
    quote = await validate_and_claim_quote(quote_id, user_id)

    # Deduct credits
    try:
        await deduct_credits_atomic(
            user_id=user_id,
            amount=quote["credits_required"],
            quote_id=quote_id,
            url=quote["url"],
            page_count=quote["page_count"],
        )
    except Exception:
        # Rollback quote status on credit deduction failure
        supabase.table("pending_audits").update({"status": "pending"}).eq("id", quote_id).execute()
        raise

    # Mark quote as approved
    supabase.table("pending_audits").update({"status": "approved"}).eq("id", quote_id).execute()

    # Get selected URLs from request or quote metadata
    page_urls = selected_urls or quote.get("metadata", {}).get("selected_urls")

    # Update page count based on selected URLs if provided
    page_count = len(page_urls) if page_urls else quote["page_count"]

    # Create audit job
    audit_id = await create_audit_record(
        user_id=user_id,
        url=quote["url"],
        page_count=page_count,
        credits_used=quote["credits_required"],
    )

    # Submit to Cloud Tasks for processing
    try:
        await submit_audit_to_orchestrator(
            audit_id=audit_id,
            url=quote["url"],
            page_count=page_count,
            user_id=user_id,
            page_urls=page_urls,
        )
    except Exception as e:
        # CRITICAL: Refund credits when task submission fails
        logger.error("task_submission_failed", extra={"audit_id": audit_id, "error": str(e)})

        # Attempt to refund credits
        await refund_credits(
            user_id=user_id,
            amount=quote["credits_required"],
            reference_id=audit_id,
            reason=f"Task submission failed: {str(e)}",
        )

        # Update audit status to failed
        await update_audit_status(
            audit_id=audit_id,
            status="failed",
            error_message="Failed to submit analysis to worker queue. Credits refunded.",
        )

        # Update quote status
        supabase.table("pending_audits").update({"status": "failed"}).eq("id", quote_id).execute()

        raise HTTPException(
            status_code=503,
            detail="Unable to queue analysis. Your credits have been refunded. Please try again.",
        )

    return {"audit_id": audit_id, "status": "processing"}


async def _run_audit_dev_mode(
    quote_id: str, user_id: str, selected_urls: list[str] | None = None
) -> dict:
    """Run audit in dev mode (no credit checks)."""
    supabase = get_supabase_client()

    quote_result = supabase.table("pending_audits").select("*").eq("id", quote_id).execute()
    if not quote_result.data:
        raise HTTPException(status_code=404, detail="Quote not found")
    quote = quote_result.data[0]

    if quote["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not your quote")

    # Get selected URLs from request or quote metadata
    page_urls = selected_urls or quote.get("metadata", {}).get("selected_urls")

    # Update page count based on selected URLs if provided
    page_count = len(page_urls) if page_urls else quote["page_count"]

    # Create audit job directly
    audit_id = await create_audit_record(
        user_id=user_id,
        url=quote["url"],
        page_count=page_count,
        credits_used=0,  # Free in dev mode
    )

    # Submit to Cloud Tasks for processing
    try:
        await submit_audit_to_orchestrator(
            audit_id=audit_id,
            url=quote["url"],
            page_count=page_count,
            user_id=user_id,
            page_urls=page_urls,
        )
    except Exception as e:
        logger.warning("dev_mode_task_submission_failed", extra={"audit_id": audit_id, "error": str(e)})

    # Mark quote as completed
    supabase.table("pending_audits").update({"status": "completed"}).eq("id", quote_id).execute()

    return {"audit_id": audit_id, "status": "processing"}
