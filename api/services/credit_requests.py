"""
Credit Request Service

Handles the manual payment flow for credit purchases.
"""

import logging
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException

from api.config import get_settings
from api.services.supabase import get_supabase_client
from api.services.email import get_email_service

logger = logging.getLogger(__name__)

# Credit pricing: $1 = 8 credits
CREDITS_PER_DOLLAR = 8


def calculate_credit_cost(credits: int) -> Decimal:
    """Calculate the cost in USD for a given number of credits."""
    return Decimal(credits) / Decimal(CREDITS_PER_DOLLAR)


def generate_invoice_number() -> str:
    """Generate a unique invoice number."""
    import uuid
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    unique_id = uuid.uuid4().hex[:6].upper()
    return f"INV-{timestamp}-{unique_id}"


async def create_credit_request(
    user_id: str,
    user_email: str,
    credits: int,
    notes: str | None = None
) -> dict:
    """
    Create a new credit request.

    Returns the created request with invoice details.
    Sends confirmation email to user.
    """
    supabase = get_supabase_client()
    settings = get_settings()

    # Calculate amount
    amount = calculate_credit_cost(credits)

    # Generate invoice number
    invoice_number = generate_invoice_number()

    # Create the request
    request_data = {
        "user_id": user_id,
        "credits_requested": credits,
        "amount": float(amount),
        "currency": "USD",
        "status": "pending",
        "invoice_number": invoice_number,
        "payment_notes": notes,
    }

    result = supabase.table("credit_requests").insert(request_data).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create credit request")

    request = result.data[0]

    logger.info(
        "credit_request_created",
        extra={
            "user_id": user_id,
            "credits": credits,
            "amount": float(amount),
            "invoice_number": invoice_number
        }
    )

    # Send confirmation email to user
    email_service = get_email_service()
    email_service.send_credit_request_confirmation(
        user_email=user_email,
        invoice_number=invoice_number,
        credits=credits,
        amount=float(amount),
        currency="USD"
    )

    return request


async def get_user_credit_requests(
    user_id: str,
    limit: int = 50,
    offset: int = 0
) -> dict:
    """Get all credit requests for a user."""
    supabase = get_supabase_client()

    # Get requests
    result = (
        supabase.table("credit_requests")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    # Get total count
    count_result = (
        supabase.table("credit_requests")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )

    return {
        "requests": result.data or [],
        "total": count_result.count or 0
    }


async def upload_payment_proof(
    user_id: str,
    user_email: str,
    request_id: str,
    proof_url: str,
    notes: str | None = None
) -> dict:
    """Upload payment proof for a credit request. Notifies admins."""
    supabase = get_supabase_client()
    settings = get_settings()

    # Verify ownership
    request_result = (
        supabase.table("credit_requests")
        .select("*")
        .eq("id", request_id)
        .eq("user_id", user_id)
        .execute()
    )

    if not request_result.data:
        raise HTTPException(status_code=404, detail="Credit request not found")

    request = request_result.data[0]

    if request["status"] not in ["pending", "invoice_sent"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot upload proof for request in status: {request['status']}"
        )

    # Update the request
    update_data = {
        "payment_proof_url": proof_url,
        "status": "proof_uploaded",
    }
    if notes:
        update_data["payment_notes"] = notes

    result = (
        supabase.table("credit_requests")
        .update(update_data)
        .eq("id", request_id)
        .execute()
    )

    logger.info(
        "payment_proof_uploaded",
        extra={"user_id": user_id, "request_id": request_id}
    )

    # Notify admins
    email_service = get_email_service()
    admin_emails = [e.strip() for e in settings.ADMIN_EMAILS.split(",") if e.strip()]

    for admin_email in admin_emails:
        email_service.send_payment_proof_notification(
            admin_email=admin_email,
            user_email=user_email,
            invoice_number=request["invoice_number"],
            credits=request["credits_requested"],
            amount=request["amount"],
            proof_url=proof_url,
            request_id=request_id
        )

    return result.data[0]


async def get_all_credit_requests(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0
) -> dict:
    """Get all credit requests (admin only)."""
    supabase = get_supabase_client()

    query = supabase.table("credit_requests").select("*, users(email, first_name, last_name)")

    if status:
        query = query.eq("status", status)

    result = (
        query
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    # Get total count
    count_query = supabase.table("credit_requests").select("id", count="exact")
    if status:
        count_query = count_query.eq("status", status)
    count_result = count_query.execute()

    return {
        "requests": result.data or [],
        "total": count_result.count or 0
    }


async def approve_credit_request(
    request_id: str,
    admin_user_id: str,
    admin_notes: str | None = None
) -> dict:
    """Approve a credit request and add credits to user. Sends email to user."""
    supabase = get_supabase_client()

    # Get the request with user info
    request_result = (
        supabase.table("credit_requests")
        .select("*, users(email)")
        .eq("id", request_id)
        .execute()
    )

    if not request_result.data:
        raise HTTPException(status_code=404, detail="Credit request not found")

    request = request_result.data[0]

    if request["status"] != "proof_uploaded":
        raise HTTPException(
            status_code=400,
            detail="Request must have payment proof uploaded before approval"
        )

    # Add credits to user
    add_result = supabase.rpc(
        "add_credits",
        {
            "p_user_id": request["user_id"],
            "p_amount": request["credits_requested"],
            "p_description": f"Credit purchase - Invoice {request['invoice_number']}"
        }
    ).execute()

    if not add_result.data:
        raise HTTPException(status_code=500, detail="Failed to add credits")

    new_balance = add_result.data.get("new_balance", 0)

    # Update request status
    update_data = {
        "status": "approved",
        "reviewed_by": admin_user_id,
        "reviewed_at": datetime.utcnow().isoformat(),
    }
    if admin_notes:
        update_data["admin_notes"] = admin_notes

    result = (
        supabase.table("credit_requests")
        .update(update_data)
        .eq("id", request_id)
        .execute()
    )

    logger.info(
        "credit_request_approved",
        extra={
            "request_id": request_id,
            "user_id": request["user_id"],
            "credits": request["credits_requested"],
            "admin_user_id": admin_user_id
        }
    )

    # Send approval email to user
    user_email = request.get("users", {}).get("email") if request.get("users") else None
    if user_email:
        email_service = get_email_service()
        email_service.send_credit_approval_notification(
            user_email=user_email,
            invoice_number=request["invoice_number"],
            credits=request["credits_requested"],
            new_balance=new_balance
        )

    return result.data[0]


async def reject_credit_request(
    request_id: str,
    admin_user_id: str,
    reason: str
) -> dict:
    """Reject a credit request. Sends email to user."""
    supabase = get_supabase_client()

    # Get the request with user info
    request_result = (
        supabase.table("credit_requests")
        .select("*, users(email)")
        .eq("id", request_id)
        .execute()
    )

    if not request_result.data:
        raise HTTPException(status_code=404, detail="Credit request not found")

    request = request_result.data[0]

    if request["status"] == "approved":
        raise HTTPException(status_code=400, detail="Cannot reject an approved request")

    # Update request status
    update_data = {
        "status": "rejected",
        "reviewed_by": admin_user_id,
        "reviewed_at": datetime.utcnow().isoformat(),
        "admin_notes": reason,
    }

    result = (
        supabase.table("credit_requests")
        .update(update_data)
        .eq("id", request_id)
        .execute()
    )

    logger.info(
        "credit_request_rejected",
        extra={
            "request_id": request_id,
            "user_id": request["user_id"],
            "reason": reason,
            "admin_user_id": admin_user_id
        }
    )

    # Send rejection email to user
    user_email = request.get("users", {}).get("email") if request.get("users") else None
    if user_email:
        email_service = get_email_service()
        email_service.send_credit_rejection_notification(
            user_email=user_email,
            invoice_number=request["invoice_number"],
            reason=reason
        )

    return result.data[0]
