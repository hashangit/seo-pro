"""
Cloud Tasks Service

Handles submission of tasks to Google Cloud Tasks queue.
"""

import json
import uuid

from fastapi import HTTPException

from config import get_settings


async def submit_audit_to_orchestrator(
    audit_id: str, url: str, page_count: int, user_id: str, page_urls: list[str] | None = None
):
    """Submit audit job to SDK Worker for unified analysis."""
    settings = get_settings()
    sdk_worker_url = settings.SDK_WORKER_URL

    if not sdk_worker_url:
        raise HTTPException(
            status_code=503, detail="SDK Worker not configured. Please contact support."
        )

    # Submit single task to SDK Worker with full analysis
    await submit_sdk_task(audit_id, url, sdk_worker_url, page_urls)


async def submit_sdk_task(
    audit_id: str, url: str, worker_url: str, page_urls: list[str] | None = None
) -> str:
    """Submit audit task to SDK Worker."""
    from google.cloud import tasks_v2

    settings = get_settings()
    client = tasks_v2.CloudTasksClient()

    payload = {"audit_id": audit_id, "url": url, "analysis_type": "full"}

    # Include page URLs if provided (for site audits with user-selected pages)
    if page_urls:
        payload["page_urls"] = page_urls

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": f"{worker_url}/analyze",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload).encode(),
        },
        "name": f"{settings.queue_path}/tasks/audit-{audit_id}-{uuid.uuid4().hex[:8]}",
    }

    response = client.create_task(request={"parent": settings.queue_path, "task": task})
    return response.name.split("/")[-1]
