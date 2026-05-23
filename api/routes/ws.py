"""
WebSocket Routes

Real-time audit status updates via WebSocket + Postgres LISTEN/NOTIFY.
"""

import asyncio
import json
import logging

import asyncpg
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.config import get_settings
from api.core.ws_auth import get_user_from_ws_token

logger = logging.getLogger(__name__)
router = APIRouter()

# Shared connection pool (initialized in startup)
_pg_pool: asyncpg.Pool | None = None


def get_pg_pool() -> asyncpg.Pool | None:
    return _pg_pool


async def init_pg_pool(database_url: str):
    global _pg_pool
    _pg_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
    logger.info("pg_pool_initialized")


async def shutdown_pg_pool():
    global _pg_pool
    if _pg_pool:
        await _pg_pool.close()
        _pg_pool = None
        logger.info("pg_pool_closed")


@router.websocket("/api/v1/audit/{audit_id}/stream")
async def audit_stream(websocket: WebSocket, audit_id: str):
    user = await get_user_from_ws_token(websocket)
    await websocket.accept()
    logger.info("ws_connected", extra={"audit_id": audit_id, "user_id": user["id"]})

    pool = get_pg_pool()
    if not pool:
        await websocket.close(code=1011, reason="Database connection unavailable")
        return

    try:
        async with pool.acquire() as conn:
            await conn.execute("LISTEN audit_changes")

            while True:
                try:
                    notification = await asyncio.wait_for(
                        conn.get_notify(), timeout=30
                    )
                    payload = json.loads(notification.payload)

                    if payload["user_id"] == user["id"] and payload["id"] == audit_id:
                        await websocket.send_json(payload)
                        if payload["status"] in ("completed", "failed"):
                            await websocket.close()
                            break

                except asyncio.TimeoutError:
                    try:
                        await websocket.send_json({"type": "ping"})
                    except Exception:
                        break

    except WebSocketDisconnect:
        logger.info("ws_disconnected", extra={"audit_id": audit_id})
    except Exception as e:
        logger.error("ws_error", extra={"audit_id": audit_id, "error": str(e)})
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
