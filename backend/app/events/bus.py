"""EventBus: in-process async pub/sub keyed by query_id (router.md §2.4).

A tiny in-process async pub/sub so dispatch()/the orchestrator can emit without holding
a WebSocket reference. The WSManager subscribes per query_id and forwards frames to
sockets. emit() is non-blocking per subscriber (put_nowait, drop-never-block).

History replay: the bus keeps a small bounded history per query_id and pre-loads it into
a NEW subscriber's queue. This closes two gaps with one mechanism — a socket that
subscribes a beat after the run starts still gets the earlier frames (no subscribe race),
and a grant-access replay streams onto the still-open socket with no special handling.
"""
from __future__ import annotations

import asyncio
from collections import deque
from typing import Deque

# Per-subscriber queue depth and per-query_id history depth. Both are generous for the
# single-client demo; a full queue drops the frame rather than blocking the run.
_QUEUE_MAXSIZE = 256
_HISTORY_MAXLEN = 128


class EventBus:
    """In-process pub/sub: query_id -> set of subscriber queues (+ bounded history)."""

    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = {}
        self._history: dict[str, Deque[dict]] = {}

    def subscribe(self, query_id: str) -> asyncio.Queue:
        """Register and return a queue of event dicts for this query_id.

        The queue is pre-loaded with any history already emitted for this query_id, so a
        late subscriber never misses earlier frames.
        """
        q: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        for event in self._history.get(query_id, ()):  # replay what already happened
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                break
        self._subs.setdefault(query_id, set()).add(q)
        return q

    def unsubscribe(self, query_id: str, q: asyncio.Queue) -> None:
        """Drop a subscriber queue for this query_id."""
        subs = self._subs.get(query_id)
        if subs is not None:
            subs.discard(q)
            if not subs:
                del self._subs[query_id]

    async def emit(self, query_id: str, event: dict) -> None:
        """Push one event dict to every subscriber for this query_id and record it in
        history. Non-blocking per subscriber (put_nowait — a full queue drops the frame
        rather than blocking dispatch)."""
        self._history.setdefault(query_id, deque(maxlen=_HISTORY_MAXLEN)).append(event)
        for q in tuple(self._subs.get(query_id, ())):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # drop-never-block (Risks: slow/dead subscriber must not stall the run)
