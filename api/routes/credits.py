"""
Credit System Routes

Handles credit balance and transaction history.
NOTE: Payment gateway integration removed pending IPG setup.
DEV MODE: Credits are unlimited for development.
"""

from fastapi import APIRouter, Depends

from api.core.dependencies import get_current_user
from api.models.credits import CreditBalanceResponse, CreditHistoryResponse
from api.services.supabase import get_supabase_client
from api.config import get_settings

router = APIRouter(prefix="/api/v1/credits", tags=["Credits"])
settings = get_settings()


@router.get("/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(user: dict = Depends(get_current_user)):
    """
    Get user's current credit balance - fetches fresh from database.
    DEV MODE: Returns unlimited balance.
    """
    supabase = get_supabase_client()

    # DEV MODE: Return unlimited balance
    if settings.DEV_MODE:
        return CreditBalanceResponse(balance=999999, formatted="Unlimited (Dev Mode)")

    # Fetch fresh balance from database
    result = supabase.table("users").select("credits_balance").eq("id", user["id"]).execute()

    if result.data:
        balance = result.data[0].get("credits_balance", 0)
    else:
        balance = 0

    return CreditBalanceResponse(
        balance=balance, formatted=f"{balance} credit{'s' if balance != 1 else ''}"
    )


@router.get("/history", response_model=CreditHistoryResponse)
async def get_credit_history(user: dict = Depends(get_current_user)):
    """Get user's credit transaction history."""
    supabase = get_supabase_client()

    result = (
        supabase.table("credit_transactions")
        .select("*")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )

    transactions = result.data if result.data else []
    total_purchased = sum(t["amount"] for t in transactions if t["amount"] > 0)
    total_spent = abs(sum(t["amount"] for t in transactions if t["amount"] < 0))

    return CreditHistoryResponse(
        transactions=transactions, total_purchased=total_purchased, total_spent=total_spent
    )


@router.get("/purchase")
async def purchase_credits_info():
    """
    Credits purchase endpoint information.
    NOTE: Payment integration removed pending IPG setup.
    In DEV MODE, users have unlimited access.
    """
    return {
        "message": "Payment gateway integration pending",
        "dev_mode": settings.DEV_MODE,
        "note": "An IPG (International Payment Gateway) will be integrated soon. "
        "In dev mode, all users have unlimited access.",
    }
