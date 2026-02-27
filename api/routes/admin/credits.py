"""
Admin Credit Request Routes

Admin endpoints for managing credit requests.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from api.config import get_settings
from api.core.dependencies import get_current_user
from api.models.credit_requests import (
    CreditRequestResponse,
    CreditRequestListResponse,
    AdminApproval,
    AdminRejection,
)
from api.services.credit_requests import (
    get_all_credit_requests,
    approve_credit_request,
    reject_credit_request,
)
from api.services.supabase import get_supabase_client

router = APIRouter(prefix="/api/v1/admin/credits/requests", tags=["Admin - Credits"])


def verify_admin_user(user: dict) -> None:
    """
    Verify the user has admin privileges.

    For now, this checks for a specific email or org.
    TODO: Implement proper role-based access control.
    """
    settings = get_settings()

    # For MVP, we'll use a simple email check
    # In production, this should use proper RBAC
    admin_emails = [e.strip() for e in settings.ADMIN_EMAILS.split(",") if e.strip()]

    if user.get('email') not in admin_emails:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )


@router.get("", response_model=CreditRequestListResponse)
async def list_all_credit_requests(
    user: dict = Depends(get_current_user),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Get all credit requests (admin only).

    Can filter by status: pending, proof_uploaded, approved, rejected
    """
    verify_admin_user(user)

    result = await get_all_credit_requests(
        status=status,
        limit=limit,
        offset=offset
    )
    return CreditRequestListResponse(
        requests=[CreditRequestResponse(**r) for r in result["requests"]],
        total=result["total"]
    )


@router.post("/{request_id}/approve", response_model=CreditRequestResponse)
async def approve_request(
    request_id: str,
    approval: AdminApproval,
    user: dict = Depends(get_current_user)
):
    """
    Approve a credit request (admin only).

    This will add the credits to the user's balance.
    """
    verify_admin_user(user)

    result = await approve_credit_request(
        request_id=request_id,
        admin_user_id=user["id"],
        admin_notes=approval.admin_notes
    )
    return CreditRequestResponse(**result)


@router.post("/{request_id}/reject", response_model=CreditRequestResponse)
async def reject_request(
    request_id: str,
    rejection: AdminRejection,
    user: dict = Depends(get_current_user)
):
    """
    Reject a credit request (admin only).

    Provide a reason for the rejection.
    """
    verify_admin_user(user)

    result = await reject_credit_request(
        request_id=request_id,
        admin_user_id=user["id"],
        reason=rejection.reason
    )
    return CreditRequestResponse(**result)


@router.get("/{request_id}", response_model=CreditRequestResponse)
async def get_credit_request_admin(
    request_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific credit request (admin only)."""
    verify_admin_user(user)

    supabase = get_supabase_client()

    result = (
        supabase.table("credit_requests")
        .select("*, users(email, first_name, last_name)")
        .eq("id", request_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Credit request not found")

    return CreditRequestResponse(**result.data[0])


# ============================================================================
# System Maintenance Endpoints
# ============================================================================


class CleanupResponse(BaseModel):
    """Response for cleanup operations."""

    success: bool
    deleted_count: int
    message: str


@router.post("/cleanup/expired-quotes", response_model=CleanupResponse)
async def cleanup_expired_quotes(
    user: dict = Depends(get_current_user)
):
    """
    Clean up expired pending audit quotes (admin only).

    This removes all pending_audits that have expired (past their expires_at timestamp).
    Should be called periodically via cron or scheduled task.
    """
    verify_admin_user(user)

    supabase = get_supabase_client()

    try:
        result = supabase.rpc(
            "cleanup_expired_quotes_with_stats",
            {}
        ).execute()

        if result.data:
            return CleanupResponse(
                success=True,
                deleted_count=result.data.get("deleted_count", 0),
                message=f"Cleaned up {result.data.get('deleted_count', 0)} expired quotes"
            )

        return CleanupResponse(
            success=False,
            deleted_count=0,
            message="Cleanup function returned no data"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {str(e)}"
        )
