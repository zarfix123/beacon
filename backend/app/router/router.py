"""Router.dispatch: fan-out + event timing (router.md §2.3).

Responsibility: resolve the target party set (asker excluded), emit ALL
`agent-activated` events BEFORE awaiting any responder (so the graph lights up at
once), then run responders concurrently, emitting one `response-item` per resolved
item. Returns the flat item list for the orchestrator to verify/synthesize. The
orchestrator emits `done`. This is a SKELETON — no logic.
"""
from __future__ import annotations

from typing import Awaitable, Callable, TYPE_CHECKING

from app.events.bus import EventBus
from app.models import ResponseItem

if TYPE_CHECKING:
    from app.agents.registry import AgentRegistry

# Injected responder: (agent_id, query) -> already-gated ResponseItems.
ResponderFn = Callable[[str, str], Awaitable[list[ResponseItem]]]


class Router:
    """In-process fan-out engine + event clock."""

    def __init__(
        self,
        registry: "AgentRegistry",
        bus: EventBus,
        responder: ResponderFn,
        max_concurrency: int = 3,
    ) -> None:
        self._registry = registry
        self._bus = bus
        self._responder = responder
        self._max_concurrency = max_concurrency

    async def dispatch(
        self,
        query_id: str,
        from_agent: str,
        query: str,
    ) -> list[ResponseItem]:
        """Fan a cross-agent request out to every discovered party.

        Phase 1: emit `agent-activated` for ALL targets (asker excluded) before any
        responder is awaited. Phase 2: run responders concurrently; emit one
        `response-item` per returned item. Returns the flat list of all items.
        """
        raise NotImplementedError("Router.dispatch is a skeleton stub")
