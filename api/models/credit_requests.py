"""
Credit Request Models

Pydantic models for the manual payment flow.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CreditRequestCreate(BaseModel):
    """Request to purchase credits."""
    credits: int = Field(..., gt=0, description="Number of credits to purchase")
    notes: str | None = Field(None, max_length=500, description="Optional notes")


class CreditRequestResponse(BaseModel):
    """Response for a credit request."""
    id: str
    user_id: str
    credits_requested: int
    amount: Decimal
    currency: str
    status: str
    invoice_number: str | None = None
    invoice_url: str | None = None
    payment_proof_url: str | None = None
    payment_notes: str | None = None
    admin_notes: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class CreditRequestListResponse(BaseModel):
    """List of credit requests."""
    requests: list[CreditRequestResponse]
    total: int


class PaymentProofUpload(BaseModel):
    """Upload payment proof for a credit request."""
    proof_url: str = Field(..., description="URL to the payment proof file")
    notes: str | None = Field(None, max_length=500, description="Payment notes")


class AdminApproval(BaseModel):
    """Admin approval for credit request."""
    admin_notes: str | None = Field(None, max_length=500, description="Admin notes")


class AdminRejection(BaseModel):
    """Admin rejection for credit request."""
    reason: str = Field(..., max_length=500, description="Rejection reason")
