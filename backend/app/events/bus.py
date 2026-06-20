"""EventBus: in-process async pub/sub keyed by query_id (router.md §2.4).

Responsibility: a tiny in-process async pub/sub so dispatch()/the orchestrator can
emit without holding a WebSocket reference. The WSManager subscribes per query_id and
forwards frames to sockets. emit() is non-blocking per subscriber (put_nowait,
drop-never-block). This is a SKELETON — no logic.
"""
from __future__ import annotations

import asyncio


class EventBus:
    """In-process pub/sub: query_id -> set of subscriber queues."""

    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = {}

    def subscribe(self, query_id: str) -> asyncio.Queue:
        """Register and return a queue of event dicts for this query_id."""
        raise NotImplementedError("EventBus.subscribe is a skeleton stub")

    def unsubscribe(self, query_id: str, q: asyncio.Queue) -> None:
        """Drop a subscriber queue for this query_id."""
        raise NotImplementedError("EventBus.unsubscribe is a skeleton stub")

    async def emit(self, query_id: str, event: dict) -> None:
        """Push one event dict to every subscriber for this query_id (non-blocking,
        put_nowait — a full queue drops the frame rather than blocking dispatch)."""
        raise NotImplementedError("EventBus.emit is a skeleton stub")
