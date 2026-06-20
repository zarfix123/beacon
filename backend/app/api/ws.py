"""/ws/query WebSocket endpoint (api-websocket.md §2.8).

Responsibility: support BOTH transport options on one endpoint — WS-driven
(type:query -> ack, then stream events on this socket) and POST+WS (type:subscribe to
an existing query_id). Cleans up the socket on disconnect. This is a SKELETON — no
logic.
"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket

router = APIRouter()


@router.websocket("/ws/query")
async def ws_query(ws: WebSocket) -> None:
    """Accept the socket, then loop on frames: `type:query` mints a run + acks +
    streams; `type:subscribe` binds the socket to an existing query_id; unknown
    frames are ignored. Unsubscribe on disconnect. SKELETON — no logic."""
    raise NotImplementedError("ws_query is a skeleton stub")
