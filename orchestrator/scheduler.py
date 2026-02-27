"""
Orchestrator - Cloud Tasks Integration

Coordinates parallel execution of audit tasks across workers.
"""

import asyncio
import json
import os

# Import URL validator for SSRF protection
import sys
import uuid
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from google.cloud import tasks_v2
from pydantic import BaseModel, Field

from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.utils.url_validator import validate_url_safe

# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(title="SEO Pro Orchestrator")

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("CLOUD_RUN_LOCATION", "us-central1")
QUEUE_PATH = (
    os.getenv("QUEUE_PATH") or f"projects/{PROJECT_ID}/locations/{LOCATION}/queues/seo-audit-queue"
)
HTTP_WORKER_URL = os.getenv("HTTP_WORKER_URL")
BROWSER_WORKER_URL = os.getenv("BROWSER_WORKER_URL")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

# Task timeout configuration
TASK_TIMEOUT_SECONDS = int(os.getenv("TASK_TIMEOUT_SECONDS", "300"))
AUDIT_COMPLETION_TIMEOUT_SECONDS = int(
    os.getenv("AUDIT_COMPLETION_TIMEOUT_SECONDS", "3600")
)  # 1 hour


# ============================================================================
# Request/Response Models
# ============================================================================


class SubmitAuditRequest(BaseModel):
    """Request model for audit submission with idempotency."""

    user_id: str
    url: str
    page_count: int
    idempotency_key: str | None = Field(
        None, description="Unique key to prevent duplicate submissions"
    )


class TaskStatusUpdate(BaseModel):
    """Task status update from worker."""

    task_id: str
    audit_id: str
    status: str
    results_json: dict[str, Any] | None = None
    error_message: str | None = None


# ============================================================================
# Audit State Management
# ============================================================================

_audit_state: dict[str, dict[str, Any]] = {}


def get_audit_state(audit_id: str) -> dict[str, Any]:
    """Get current audit state."""
    return _audit_state.get(audit_id, {})


def set_audit_state(audit_id: str, state: dict[str, Any]) -> None:
    """Set audit state."""
    _audit_state[audit_id] = state


async def check_audit_completion(audit_id: str) -> bool:
    """Check if all tasks are completed."""
    state = get_audit_state(audit_id)
    if not state:
        return False

    total_tasks = state.get("total_tasks", 0)
    completed_tasks = state.get("completed_tasks", 0)

    return total_tasks > 0 and completed_tasks >= total_tasks


async def update_audit_status(audit_id: str) -> None:
    """Update audit status based on task completion."""
    state = get_audit_state(audit_id)

    if not state:
        return

    # Count completed tasks
    completed_tasks = sum(1 for v in state.values() if v.get("status") == "completed")
    total_tasks = state.get("total_tasks", 0)

    # Check if all tasks done
    if completed_tasks >= total_tasks and total_tasks > 0:
        # All tasks completed - update audit
        supabase.table("audits").update({"status": "completed", "completed_at": "now()"}).eq(
            "id", audit_id
        ).execute()

        # Clean up state
        _audit_state.pop(audit_id, None)


# ============================================================================
# Health Check Enhancement
# ============================================================================


@app.get("/health")
async def health():
    """Health check with dependency verification."""
    checks = {"status": "healthy", "service": "orchestrator"}

    # Check Supabase connectivity
    try:
        supabase.table("users").select("*").limit(1).execute()
        checks["supabase"] = "ok"
    except Exception as e:
        checks["supabase"] = f"error: {str(e)}"

    # Check Cloud Tasks client
    try:
        client = get_task_client()
        checks["cloud_tasks"] = "ok"
    except Exception as e:
        checks["cloud_tasks"] = f"error: {str(e)}"

    # Check worker URLs
    if HTTP_WORKER_URL:
        checks["http_worker_url"] = "configured"
    else:
        checks["http_worker_url"] = "not configured"

    if BROWSER_WORKER_URL:
        checks["browser_worker_url"] = "configured"
    else:
        checks["browser_worker_url"] = "not configured"

    all_ok = all(v == "ok" for v in checks.values() if v.endswith("_ok"))
    status_code = 200 if all_ok else 503
    checks["overall"] = "ready" if all_ok else "not_ready"

    return checks


# ============================================================================
# Task Status Update Endpoint (for workers)
# ============================================================================


@app.post("/task-update")
async def update_task_status(update: TaskStatusUpdate):
    """Receive task status updates from workers."""
    task_id = update.task_id
    audit_id = update.audit_id
    status = update.status

    # Validate task belongs to audit
    audit_result = supabase.table("audit_tasks").select("*").eq("id", task_id).execute()
    if not audit_result.data:
        raise HTTPException(status_code=404, detail="Task not found")

    task = audit_result.data[0]
    if task["audit_id"] != audit_id:
        raise HTTPException(status_code=403, detail="Task does not belong to this audit")

    # Update task status
    update_data: dict[str, Any] = {"status": status}

    if status in ["completed", "failed"]:
        update_data["completed_at"] = "now()"

    if update.results_json:
        update_data["results_json"] = update.results_json

    if update.error_message:
        update_data["error_message"] = update.error_message

    supabase.table("audit_tasks").update(update_data).eq("id", task_id).execute()

    # Update audit state
    await update_audit_state_on_task_completion(audit_id, task_id, status)

    return {"status": "ok"}


async def update_audit_state_on_task_completion(audit_id: str, task_id: str, status: str) -> None:
    """Update audit state when a task completes."""
    state = get_audit_state(audit_id)

    if not state:
        state = {"total_tasks": 0, "completed_tasks": 0, "tasks": {}}
        set_audit_state(audit_id, state)

    # Update task completion
    if "total_tasks" not in state:
        state["total_tasks"] = 1  # Will be incremented when creating tasks
    else:
        state["total_tasks"] += 1

    state["completed_tasks"] = state.get("completed_tasks", 0)
    if status in ["completed", "failed"]:
        state["completed_tasks"] += 1

    # Check for audit completion
    await update_audit_status(audit_id)


def get_task_client():
    """Get Cloud Tasks client."""
    return tasks_v2.CloudTasksClient()


async def create_http_task(url: str, payload: dict[str, Any], task_name: str) -> str:
    """Create a Cloud Task for HTTP execution."""
    client = get_task_client()

    parent = client.queue_path(PROJECT_ID, LOCATION, "seo-audit-queue")
    task_id = str(uuid.uuid4())

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": url,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload).encode(),
        },
        "name": f"{parent}/tasks/{task_id}",
    }

    response = client.create_task(request={"parent": parent, "task": task})

    return task_id


async def submit_audit_job(
    user_id: str, url: str, page_count: int, idempotency_key: str | None = None
) -> dict[str, Any]:
    """
    Submit audit job to Cloud Tasks queue with idempotency support.

    Args:
        user_id: User ID
        url: URL to audit
        page_count: Number of pages
        idempotency_key: Optional unique key to prevent duplicate submissions

    Returns:
        Dict with audit_id and status
    """
    # Validate URL
    is_valid, error_msg = validate_url_safe(url)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {error_msg}")

    # Check for duplicate submission (idempotency)
    if idempotency_key:
        # Check if audit with this key already exists
        existing = (
            supabase.table("audits").select("*").eq("idempotency_key", idempotency_key).execute()
        )
        if existing.data:
            raise HTTPException(
                status_code=409,
                detail="This request has already been processed. Please refresh to see results.",
            )

    # Create audit record
    audit_id = str(uuid.uuid4())

    # Initialize audit state
    set_audit_state(
        audit_id,
        {
            "total_tasks": 6,  # 5 tasks + 1 completion check
            "completed_tasks": 0,
            "tasks": {},
            "user_id": user_id,
            "url": url,
            "created_at": datetime.utcnow().isoformat(),
        },
    )

    try:
        audit_result = (
            supabase.table("audits")
            .insert(
                {
                    "id": audit_id,
                    "idempotency_key": idempotency_key,
                    "user_id": user_id,
                    "url": url,
                    "status": "queued",
                    "page_count": page_count,
                    "credits_used": 0,  # Already deducted
                }
            )
            .execute()
        )

    except Exception as e:
        # Clean up state on error
        _audit_state.pop(audit_id, None)
        raise HTTPException(status_code=500, detail=f"Failed to create audit: {str(e)}")

    # Determine task distribution
    # 5 tasks to HTTP worker, 1 to Playwright worker
    tasks_to_create = [
        {"type": "technical", "worker": "http", "url": HTTP_WORKER_URL + "/analyze"},
        {"type": "content", "worker": "http", "url": HTTP_WORKER_URL + "/analyze"},
        {"type": "schema", "worker": "http", "url": HTTP_WORKER_URL + "/analyze"},
        {"type": "sitemap", "worker": "http", "url": HTTP_WORKER_URL + "/analyze"},
        {"type": "programmatic", "worker": "http", "url": HTTP_WORKER_URL + "/analyze"},
        {"type": "visual", "worker": "browser", "url": BROWSER_WORKER_URL + "/analyze"},
    ]

    # Create tasks with error handling
    task_ids = []
    for task_def in tasks_to_create:
        try:
            # Create task record
            task_result = (
                supabase.table("audit_tasks")
                .insert(
                    {
                        "audit_id": audit_id,
                        "task_type": task_def["type"],
                        "worker_type": task_def["worker"],
                        "status": "queued",
                    }
                )
                .execute()
            )

            # Submit to Cloud Tasks with retry
            task_id = await create_http_task_with_retry(
                url=task_def["url"],
                payload={
                    "audit_id": audit_id,
                    "task_id": task_result.data[0]["id"] if task_result.data else None,
                    "url": url,
                    "type": task_def["type"],
                },
                task_name=f"{audit_id}-{task_def['type']}",
            )

            task_ids.append(task_id)

            # Update state
            state = get_audit_state(audit_id)
            state["tasks"][task_id] = {
                "type": task_def["type"],
                "worker": task_def["worker"],
                "status": "queued",
            }

        except Exception as e:
            # Log error but continue with other tasks
            print(f"Error creating task {task_def['type']}: {e}")

    return {"id": audit_id, "status": "queued", "tasks_created": len(task_ids)}


async def create_http_task_with_retry(
    url: str, payload: dict[str, Any], task_name: str, max_retries: int = 3
) -> str:
    """Create Cloud Task with retry logic for transient failures."""
    import json

    from google.cloud import tasks_v2

    client = get_task_client()
    parent = client.queue_path(PROJECT_ID, LOCATION, "seo-audit-queue")
    task_id = str(uuid.uuid4())

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": url,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload).encode(),
        },
        "name": f"{parent}/tasks/{task_id}",
        "schedule_time": {
            "seconds": 5  # Delay task by 5 seconds
        },
    }

    for attempt in range(max_retries):
        try:
            response = client.create_task(request={"parent": parent, "task": task})
            return response.name.split("/")[-1]
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(1 * (2**attempt))  # Exponential backoff
            else:
                raise HTTPException(
                    status_code=503,
                    detail=f"Failed to submit task after {max_retries} attempts: {str(e)}",
                )


# Endpoints
@app.post("/submit")
async def submit_audit(data: dict[str, Any]):
    """
    Submit audit for processing with idempotency support.

    Request body should include:
    - user_id: Required user ID
    - url: URL to audit
    - page_count: Number of pages (optional)
    - idempotency_key: Optional unique key to prevent duplicates
    """
    return await submit_audit_job(
        user_id=data.get("user_id"),
        url=data.get("url"),
        page_count=data.get("page_count", 1),
        idempotency_key=data.get("idempotency_key"),
    )


if __name__ == "__main__":
    # Run with proper signal handling for graceful shutdown
    import signal

    import uvicorn

    class UvicornServer(uvicorn.Server):
        """Custom server with signal handling."""

        def handle_exit(self, sig):
            print(f"Received signal {sig.name}, shutting down gracefully...")
            # Cancel any pending tasks
            _audit_state.clear()

    server = UvicornServer(app=app, host="0.0.0.0", port=8080, timeout_keep_alive=5)

    # Set signal handlers
    signal.signal(signal.SIGINT, lambda s, f: server.handle_exit(s))
    signal.signal(signal.SIGTERM, lambda s, f: server.handle_exit(s))

    uvicorn.run(server)
