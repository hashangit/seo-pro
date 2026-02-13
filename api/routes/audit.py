"""
Audit Routes

Handles audit estimation, execution, and status checking.
"""

from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/v1/audit", tags=["audits"])


@router.get("/{audit_id}")
async def get_audit_by_id(audit_id: str):
    """Get audit details by ID."""
    # TODO: Implement audit retrieval
    # This endpoint is currently implemented in main.py
    # This route is kept for future modularization
    return {"id": audit_id, "status": "not_implemented"}
