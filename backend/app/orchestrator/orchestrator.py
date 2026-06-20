"""Orchestrator.run: plan -> fan out -> collect -> verify -> synthesize (orchestrator.md §2.2,
api-websocket.md §2.10, grant-access.md §2.5).

Responsibility: the coordination core that lives in the asking agent. Resolves the
asker, allocates (or reuses, on grant_access replay) the query_id, fans out via the
Router (emitting agent-activated per party), collects gated items, drives verification
of full items (bounded concurrency), emits one response-item per item, synthesizes,
and emits exactly one done. Never touches raw restricted/private text — it only sees
already-gated items. This is a SKELETON — no logic.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.registry import AgentRegistry
    from app.router.router import Router

# An event sink the API/WS layer (or a test collector) provides.
EventSink = Callable[[dict], Awaitable[None]]


class Orchestrator:
    """Drives one query run end-to-end. Transport-agnostic via an injected sink."""

    def __init__(
        self,
        registry: "AgentRegistry",
        router: "Router",
        emit: EventSink,
        *,
        top_k: int = 5,
        verify_concurrency: int = 3,
    ) -> None:
        self._registry = registry
        self._router = router
        self._emit = emit
        self._top_k = top_k
        self._sem = asyncio.Semaphore(verify_concurrency)

    async def run(
        self,
        query: str,
        from_agent: str,
        query_id: Optional[str] = None,
    ) -> None:
        """Plan -> fan out -> collect -> verify -> synthesize.

        Resolve asker, allocate query_id (reuse if given — grant_access replay), fan
        out via the router (emits agent-activated per party), collect gated items,
        verify full items, emit one response-item per item, synthesize, emit one done.
        Emits agent-activated*, then N response-item, then exactly one done.
        """
        raise NotImplementedError("Orchestrator.run is a skeleton stub")

    def start_run(self, query_id: str, from_agent: str, query: str) -> None:
        """Schedule run() as a fire-and-forget asyncio task and return immediately
        (so POST /query / the WS ack can respond fast). Errors are caught inside the
        task and surfaced as a terminal done with a fallback answer (OQ-5)."""
        raise NotImplementedError("Orchestrator.start_run is a skeleton stub")
