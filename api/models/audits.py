"""
Audit-related Pydantic Models

Request and response models for audit operations.
"""

from typing import Optional
from pydantic import BaseModel, Field

try:
    from pydantic import field_validator
except ImportError:
    from pydantic import validator as field_validator


class AuditEstimateRequest(BaseModel):
    """Audit estimate request."""
    url: str
    max_pages: Optional[int] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v, **kwargs):
        if not v.startswith(("http://", "https://")):
            raise ValueError("Invalid URL")
        return v


class URLDiscoveryRequest(BaseModel):
    """Request to discover URLs for a site."""
    url: str
    sitemap_url: Optional[str] = None  # Manual sitemap URL if auto-discovery fails

    @field_validator("url")
    @classmethod
    def validate_url(cls, v, **kwargs):
        if not v.startswith(("http://", "https://")):
            raise ValueError("Invalid URL - must start with http:// or https://")
        return v

    @field_validator("sitemap_url")
    @classmethod
    def validate_sitemap_url(cls, v, **kwargs):
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("Invalid sitemap URL - must start with http:// or https://")
        return v


class URLDiscoveryResponse(BaseModel):
    """Response with discovered URLs."""
    urls: list[str]
    source: str  # "sitemap", "homepage", "manual_sitemap", "error"
    confidence: float
    sitemap_found: bool
    sitemap_url: Optional[str]
    warning: Optional[str] = None
    error: Optional[str] = None


class AuditEstimateResponse(BaseModel):
    """Audit estimate response."""
    url: str
    estimated_pages: int
    credits_required: int
    cost_lkr: float
    cost_usd: float
    breakdown: str
    quote_id: str
    expires_at: str


class AuditRunRequest(BaseModel):
    """Run audit request."""
    quote_id: str
    selected_urls: Optional[list[str]] = None  # URLs selected by user for site audit


class AuditRunResponse(BaseModel):
    """Run audit response."""
    audit_id: str
    status: str


class AuditStatusResponse(BaseModel):
    """Audit status response."""
    id: str
    url: str
    status: str
    page_count: int
    credits_used: int
    created_at: str
    completed_at: Optional[str]
    results: Optional[dict]
    error_message: Optional[str]
