"""
Credit Service

Handles credit calculations, deductions, and formatting.
"""

import logging

from fastapi import HTTPException

from api.config import get_settings

logger = logging.getLogger(__name__)

# Credit pricing constants
CREDITS_PER_DOLLAR = 8  # $1 = 8 credits


def calculate_site_audit_credits(page_count: int) -> int:
    """
    Calculate credits required for a full site audit.

    Pricing: 7 credits × number of pages
    Includes all 12 analysis types per page.
    """
    return page_count * 7


def calculate_page_audit_credits() -> int:
    """
    Calculate credits required for a full page audit.

    Pricing: 8 credits (fixed)
    Includes all 12 analysis types on a single page.
    This is a bundle discount (12 individual would cost 12 credits).
    """
    return 8


def calculate_individual_report_credits() -> int:
    """
    Calculate credits required for a single analysis type.

    Pricing: 1 credit (fixed)
    Single analysis type on one URL.
    """
    return 1


def calculate_credits(page_count: int) -> int:
    """
    Legacy function - now calculates site audit credits.
    Kept for backward compatibility with existing audit endpoints.
    """
    return calculate_site_audit_credits(page_count)


def format_cost_breakdown(page_count: int, credits: int) -> str:
    """Generate human-readable cost explanation for site audits."""
    settings = get_settings()
    if settings.DEV_MODE:
        logger.warning(
            "credit_bypass_dev_mode",
            extra={"event": "cost_breakdown_bypass", "page_count": page_count, "credits": credits}
        )
        return f"FREE in Dev Mode - {page_count} pages will be analyzed"

    cost_usd = credits / CREDITS_PER_DOLLAR
    if page_count == 1:
        return f"1 page site audit: {credits} credits (${cost_usd:.2f})"
    else:
        return (
            f"Full site audit: {page_count} pages × 7 credits\n"
            f"Total: {credits} credits (${cost_usd:.2f})"
        )


def format_page_audit_cost() -> str:
    """Generate cost explanation for full page audit."""
    settings = get_settings()
    if settings.DEV_MODE:
        logger.warning(
            "credit_bypass_dev_mode",
            extra={"event": "page_audit_cost_bypass"}
        )
        return "FREE in Dev Mode - Full page audit (all 12 analysis types)"
    return "Full page audit (all 12 analysis types): 8 credits ($1.00)"


def format_individual_report_cost(count: int = 1) -> str:
    """Generate cost explanation for individual reports."""
    settings = get_settings()
    if settings.DEV_MODE:
        logger.warning(
            "credit_bypass_dev_mode",
            extra={"event": "individual_report_cost_bypass", "count": count}
        )
        return f"FREE in Dev Mode - {count} individual report{'s' if count != 1 else ''}"
    cost_usd = count / CREDITS_PER_DOLLAR
    return f"{count} individual report{'s' if count != 1 else ''}: {count} credit{'s' if count != 1 else ''} (${cost_usd:.2f})"


async def deduct_analysis_credits(
    user_id: str, credits: int, analysis_type: str, url: str, supabase
) -> bool:
    """
    Deduct credits for analysis. Returns True if successful.

    DEV MODE: Skips deduction entirely.
    """
    settings = get_settings()
    if settings.DEV_MODE:
        logger.warning(
            "credit_bypass_dev_mode",
            extra={
                "event": "deduct_bypass",
                "user_id": user_id,
                "credits": credits,
                "analysis_type": analysis_type,
                "url": url
            }
        )
        return True

    try:
        deduct_result = supabase.rpc(
            "deduct_credits",
            {
                "p_user_id": user_id,
                "p_amount": credits,
                "p_reference_id": None,
                "p_reference_type": "analysis",
                "p_description": f"{analysis_type} analysis: {url}",
            },
        ).execute()

        return deduct_result.data is not None and deduct_result.data
    except Exception as e:
        if "Insufficient credits" in str(e):
            raise HTTPException(
                status_code=402, detail=f"Insufficient credits. Need {credits}, please top up."
            )
        raise
