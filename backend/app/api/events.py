"""WSManager: bridge EventBus -> live sockets (api-websocket.md §2.6).

Tracks live WS connections keyed by query_id and forwards bus frames to the right
sockets. Best-effort emit: a send failure removes that socket, never aborts the run.

Design: the orchestrator/router emit into the EventBus (transport-agnostic). The
WSManager runs ONE pump task per query_id that drains `bus.subscribe(query_id)` and
fans each frame out to every socket bound to that query_id. Two layers so the bus stays
pure stdlib + unit-testable, and all FastAPI/socket-lifecycle concerns live here.
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
        self._pumps: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, query_id: str, ws: WebSocket) -> None:
        """Bind a socket to a query_id and ensure a pump is forwarding bus frames to it.

        Idempotent per (query_id, ws). The first socket for a query_id starts the pump;
        subsequent sockets just join the fan-out set.
        """
        async with self._lock:
            self._subs.setdefault(query_id, set()).add(ws)
            if query_id not in self._pumps:
                self._pumps[query_id] = asyncio.create_task(self._pump(query_id))

    async def _pump(self, query_id: str) -> None:
        """Drain the bus for one query_id and fan each frame out to its sockets.

        Subscribes to the bus once per query_id (history is replayed into this queue on
        subscribe). Runs until cancelled by unsubscribe_socket when the last socket goes.
        """
        q = self._bus.subscribe(query_id)
        try:
            while True:
                event = await q.get()
                await self.emit(query_id, event)
        finally:
            self._bus.unsubscribe(query_id, q)

    async def emit(self, query_id: str, event: dict) -> None:
        """Send one event dict to all subscribers of query_id. Best-effort: a failed
        send removes that socket; never aborts the run."""
        socks = self._subs.get(query_id)
        if not socks:
            return
        for ws in tuple(socks):
            try:
                await ws.send_json(event)
            except Exception:
                socks.discard(ws)  # dead socket; keep streaming to the rest

    async def unsubscribe_socket(self, ws: WebSocket) -> None:
        """Drop a socket from every query_id on disconnect; stop now-empty pumps."""
        async with self._lock:
            empty: list[str] = []
            for query_id, socks in self._subs.items():
                socks.discard(ws)
                if not socks:
                    empty.append(query_id)
            for query_id in empty:
                self._subs.pop(query_id, None)
                task = self._pumps.pop(query_id, None)
                if task is not None:
                    task.cancel()
