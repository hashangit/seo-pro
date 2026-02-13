"""
Credit System Routes

Handles credit balance, transaction history.
NOTE: Payment gateway integration removed pending IPG setup.
DEV MODE: Credits are unlimited for development.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

# Import parent modules using absolute imports to avoid circular dependency
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import get_settings

settings = get_settings()


# ============================================================================
# Routes
# ============================================================================

router = APIRouter(prefix="/api/v1/credits", tags=["credits"])


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
                "In dev mode, all users have unlimited access."
    }
