"""
Credit Request Routes

Handles the manual payment flow for credit purchases.
"""

from fastapi import APIRouter, Depends, Query

from api.core.dependencies import get_current_user
from api.models.credit_requests import (
    CreditRequestCreate,
    CreditRequestResponse,
    CreditRequestListResponse,
    PaymentProofUpload,
)
from api.services.credit_requests import (
    create_credit_request,
    get_user_credit_requests,
    upload_payment_proof,
)

router = APIRouter(prefix="/api/v1/credits/requests", tags=["Credit Requests"])


@router.post("", response_model=CreditRequestResponse)
async def request_credits(
    request: CreditRequestCreate,
    user: dict = Depends(get_current_user)
):
    """
    Request to purchase credits.

    Creates a credit request with an invoice number.
    User will need to make payment and upload proof.
    """
    result = await create_credit_request(
        user_id=user["id"],
        user_email=user.get("email", ""),
        credits=request.credits,
        notes=request.notes
    )
    return CreditRequestResponse(**result)


@router.get("", response_model=CreditRequestListResponse)
async def list_my_credit_requests(
    user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get all credit requests for the current user."""
    result = await get_user_credit_requests(
        user_id=user["id"],
        limit=limit,
        offset=offset
    )
    return CreditRequestListResponse(
        requests=[CreditRequestResponse(**r) for r in result["requests"]],
        total=result["total"]
    )


@router.post("/{request_id}/proof", response_model=CreditRequestResponse)
async def submit_payment_proof(
    request_id: str,
    proof: PaymentProofUpload,
    user: dict = Depends(get_current_user)
):
    """
    Submit payment proof for a credit request.

    Upload your payment receipt/confirmation and provide the URL.
    An admin will review and approve the credit addition.
    """
    result = await upload_payment_proof(
        user_id=user["id"],
        user_email=user.get("email", ""),
        request_id=request_id,
        proof_url=proof.proof_url,
        notes=proof.notes
    )
    return CreditRequestResponse(**result)


@router.get("/{request_id}", response_model=CreditRequestResponse)
async def get_credit_request(
    request_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific credit request."""
    from api.services.supabase import get_supabase_client

    supabase = get_supabase_client()
    result = (
        supabase.table("credit_requests")
        .select("*")
        .eq("id", request_id)
        .eq("user_id", user["id"])
        .execute()
    )

    if not result.data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Credit request not found")

    return CreditRequestResponse(**result.data[0])
