"""
WebSocket Authentication Helper

Validates WorkOS JWT tokens from WebSocket query parameters
and returns authenticated user data.
"""

import logging
from fastapi import WebSocket, WebSocketDisconnect
from urllib.parse import parse_qs

from api.services.auth import verify_token, sync_user_to_supabase
from api.services.supabase import get_supabase_client

logger = logging.getLogger(__name__)


async def get_user_from_ws_token(websocket: WebSocket) -> dict:
    """Extract and validate WorkOS JWT from WebSocket query params."""
    query_string = websocket.scope.get("query_string", b"").decode()
    params = parse_qs(query_string)
    token = params.get("token", [None])[0]

    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        raise WebSocketDisconnect(code=4001)

    try:
        payload = await verify_token(token)
        supabase = get_supabase_client()
        user = await sync_user_to_supabase(payload, supabase)
        return user
    except Exception:
        await websocket.close(code=4002, reason="Invalid authentication token")
        raise WebSocketDisconnect(code=4002)
