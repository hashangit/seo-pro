"""
Business Logic Services for SEO Pro API

Services handle core business logic separated from route handlers.
"""

from .supabase import get_supabase_client
from .auth import get_jwks, invalidate_jwks_cache, verify_token, sync_user_to_supabase
from .credits import (
    calculate_site_audit_credits,
    calculate_page_audit_credits,
    calculate_individual_report_credits,
    calculate_credits,
    format_cost_breakdown,
    format_page_audit_cost,
    format_individual_report_cost,
    deduct_analysis_credits,
    CREDITS_PER_DOLLAR,
)
from .cloud_tasks import submit_audit_to_orchestrator, submit_sdk_task
from .analyses import (
    proxy_to_worker,
    run_individual_analysis,
    run_page_audit_analysis,
    get_worker_url,
    INDIVIDUAL_ANALYSIS_TYPES,
)
from .audits import (
    create_pending_quote,
    validate_and_claim_quote,
    deduct_credits_atomic,
    refund_credits,
    create_audit_record,
    update_audit_status,
    run_audit_with_quote,
)

__all__ = [
    # Supabase
    "get_supabase_client",
    # Auth
    "get_jwks",
    "invalidate_jwks_cache",
    "verify_token",
    "sync_user_to_supabase",
    # Credits
    "calculate_site_audit_credits",
    "calculate_page_audit_credits",
    "calculate_individual_report_credits",
    "calculate_credits",
    "format_cost_breakdown",
    "format_page_audit_cost",
    "format_individual_report_cost",
    "deduct_analysis_credits",
    "CREDITS_PER_DOLLAR",
    # Cloud Tasks
    "submit_audit_to_orchestrator",
    "submit_sdk_task",
    # Analyses
    "proxy_to_worker",
    "run_individual_analysis",
    "run_page_audit_analysis",
    "get_worker_url",
    "INDIVIDUAL_ANALYSIS_TYPES",
    # Audits
    "create_pending_quote",
    "validate_and_claim_quote",
    "deduct_credits_atomic",
    "refund_credits",
    "create_audit_record",
    "update_audit_status",
    "run_audit_with_quote",
]
