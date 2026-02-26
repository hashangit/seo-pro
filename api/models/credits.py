"""
Credit-related Pydantic Models

Request and response models for credit operations.
"""

from pydantic import BaseModel


class CreditBalanceResponse(BaseModel):
    """Credit balance response."""
    balance: int
    formatted: str


class CreditHistoryResponse(BaseModel):
    """Credit history response."""
    transactions: list
    total_purchased: int
    total_spent: int
