"""WSManager: bridge EventBus -> live sockets (api-websocket.md §2.6).

Responsibility: track live WS connections keyed by query_id and forward bus frames to
the right sockets. Best-effort emit: a send failure removes that socket, never aborts
the run. The orchestrator/router emit into the EventBus; the WSManager subscribes per
query_id and forwards. This is a SKELETON — no logic.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fastapi import WebSocket

if TYPE_CHECKING:
    from app.events.bus import EventBus


class WSManager:
    """query_id -> set[WebSocket]; bridges EventBus frames to live sockets."""

    def __init__(self, bus: "EventBus") -> None:
        self._bus = bus
        self._subs: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, query_id: str, ws: WebSocket) -> None:
        """Bind a socket to a query_id and start forwarding bus frames to it."""
        raise NotImplementedError("WSManager.subscribe is a skeleton stub")

    async def unsubscribe_socket(self, ws: WebSocket) -> None:
        """Drop a socket from every query_id on disconnect."""
        raise NotImplementedError("WSManager.unsubscribe_socket is a skeleton stub")

    async def emit(self, query_id: str, event: dict) -> None:
        """Send one event dict to all subscribers of query_id. Best-effort: a failed
        send removes that socket; never aborts the run."""
        raise NotImplementedError("WSManager.emit is a skeleton stub")
