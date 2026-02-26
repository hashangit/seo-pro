"""
Analysis-related Pydantic Models

Request and response models for individual and batch analysis operations.
"""


from pydantic import BaseModel

try:
    from pydantic import field_validator
except ImportError:
    from pydantic import validator as field_validator


class AnalyzeRequest(BaseModel):
    """Request model for individual analysis endpoints."""

    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v, **kwargs):
        if not v.startswith(("http://", "https://")):
            raise ValueError("Invalid URL - must start with http:// or https://")
        return v


class AnalyzeResponse(BaseModel):
    """Response model for individual analysis endpoints."""

    category: str
    score: int | None = None
    issues: list = []
    warnings: list = []
    passes: list = []
    recommendations: list = []
    error: str | None = None


class AnalysisEstimateRequest(BaseModel):
    """Analysis estimate request for any analysis type."""

    url: str
    analysis_mode: str = "individual"  # individual, page_audit, site_audit
    analysis_types: list[str] | None = None  # For individual mode, which types to run
    max_pages: int | None = None  # For site_audit mode (deprecated, use selected_urls)
    selected_urls: list[str] | None = None  # For site_audit mode, pre-selected URLs

    @field_validator("url")
    @classmethod
    def validate_url(cls, v, **kwargs):
        if not v.startswith(("http://", "https://")):
            raise ValueError("Invalid URL - must start with http:// or https://")
        return v

    @field_validator("analysis_mode")
    @classmethod
    def validate_analysis_mode(cls, v, **kwargs):
        if v not in ["individual", "page_audit", "site_audit"]:
            raise ValueError("analysis_mode must be 'individual', 'page_audit', or 'site_audit'")
        return v


class AnalysisEstimateResponse(BaseModel):
    """Analysis estimate response."""

    url: str
    analysis_mode: str
    analysis_types: list[str]
    credits_required: int
    cost_usd: float
    breakdown: str
    estimated_pages: int | None = None  # For site_audit mode
    quote_id: str | None = None  # For site_audit mode (30 min expiry)


class AnalysisListResponse(BaseModel):
    """Response model for listing analyses."""

    analyses: list
    total: int
    limit: int
    offset: int
    has_more: bool


class AnalysisStatusResponse(BaseModel):
    """Response model for a single analysis status."""

    id: str
    url: str
    analysis_type: str
    analysis_mode: str
    credits_used: int
    status: str
    created_at: str
    completed_at: str | None
    results: dict | None
    error_message: str | None
