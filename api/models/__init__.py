"""
Pydantic Models for SEO Pro API

Request and response models organized by domain.
"""

from .common import HealthResponse
from .credits import CreditBalanceResponse, CreditHistoryResponse
from .audits import (
    AuditEstimateRequest,
    AuditEstimateResponse,
    AuditRunRequest,
    AuditRunResponse,
    AuditStatusResponse,
    URLDiscoveryRequest,
    URLDiscoveryResponse,
)
from .analyses import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalysisEstimateRequest,
    AnalysisEstimateResponse,
    AnalysisListResponse,
    AnalysisStatusResponse,
)

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
