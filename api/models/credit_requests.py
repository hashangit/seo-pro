"""
Credit Request Models

Pydantic models for the manual payment flow.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class CreditRequestCreate(BaseModel):
    """Request to purchase credits."""
    credits: int = Field(..., gt=0, description="Number of credits to purchase")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes")


class CreditRequestResponse(BaseModel):
    """Response for a credit request."""
    id: str
    user_id: str
    credits_requested: int
    amount: Decimal
    currency: str
    status: str
    invoice_number: Optional[str] = None
    invoice_url: Optional[str] = None
    payment_proof_url: Optional[str] = None
    payment_notes: Optional[str] = None
    admin_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class CreditRequestListResponse(BaseModel):
    """List of credit requests."""
    requests: list[CreditRequestResponse]
    total: int


class PaymentProofUpload(BaseModel):
    """Upload payment proof for a credit request."""
    proof_url: str = Field(..., description="URL to the payment proof file")
    notes: Optional[str] = Field(None, max_length=500, description="Payment notes")


class AdminApproval(BaseModel):
    """Admin approval for credit request."""
    admin_notes: Optional[str] = Field(None, max_length=500, description="Admin notes")


class AdminRejection(BaseModel):
    """Admin rejection for credit request."""
    reason: str = Field(..., max_length=500, description="Rejection reason")
