"""
Pydantic Models for SEO Pro API

Request and response models organized by domain.
"""

from .analyses import (
    AnalysisEstimateRequest,
    AnalysisEstimateResponse,
    AnalysisListResponse,
    AnalysisStatusResponse,
    AnalyzeRequest,
    AnalyzeResponse,
)
from .audits import (
    AuditEstimateRequest,
    AuditEstimateResponse,
    AuditRunRequest,
    AuditRunResponse,
    AuditStatusResponse,
    URLDiscoveryRequest,
    URLDiscoveryResponse,
)
from .common import HealthResponse
from .credits import CreditBalanceResponse, CreditHistoryResponse

__all__ = [
    # Common
    "HealthResponse",
    # Credits
    "CreditBalanceResponse",
    "CreditHistoryResponse",
    # Audits
    "AuditEstimateRequest",
    "AuditEstimateResponse",
    "AuditRunRequest",
    "AuditRunResponse",
    "AuditStatusResponse",
    "URLDiscoveryRequest",
    "URLDiscoveryResponse",
    # Analyses
    "AnalyzeRequest",
    "AnalyzeResponse",
    "AnalysisEstimateRequest",
    "AnalysisEstimateResponse",
    "AnalysisListResponse",
    "AnalysisStatusResponse",
]
