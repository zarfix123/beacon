"""Router.dispatch: fan-out + event timing (router.md §2.3).

Responsibility: resolve the target party set (asker excluded), emit ALL
`agent-activated` events BEFORE awaiting any responder (so the graph lights up at
once), then run responders concurrently, emitting one `response-item` per resolved
item. Returns the flat item list for the orchestrator to verify/synthesize. The
orchestrator emits `done`. This is a SKELETON — no logic.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Optional, TYPE_CHECKING

from app.events.bus import EventBus
from app.models import ResponseItem
# Event builders live in router/events.py (their canonical home); re-exported here so
# `from app.router.router import agent_activated_event` keeps working.
from app.router.events import agent_activated_event, response_item_event

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
        *,
        only_agents: Optional[list[str]] = None,
    ) -> list[ResponseItem]:
        """Fan a cross-agent request out to the discovered party set.

        Targets = every registered agent except the asker, narrowed to `only_agents`
        when given (targeted grant-access replay re-pulses just the granted party).
        Phase 1: emit `agent-activated` for ALL targets before any responder is awaited
        (the graph lights up at once). Phase 2: run responders concurrently; emit one
        `response-item` per returned item. Returns the flat list of all items.
        """
        targets = [
            (agent_id, self._registry.party_name(agent_id))
            for agent_id in self._registry.all_ids()
            if agent_id != from_agent and (only_agents is None or agent_id in only_agents)
        ]

        # Phase 1: light up every node immediately, before any responder latency.
        for agent_id, party_name in targets:
            await self._bus.emit(query_id, agent_activated_event(query_id, agent_id, party_name))

        # Phase 2: run each responder concurrently; stream response-items as they resolve.
        async def run_one(agent_id: str) -> list[ResponseItem]:
            items = await self._responder(agent_id, query)   # the wedge runs INSIDE here
            for item in items:
                await self._bus.emit(query_id, response_item_event(query_id, item))
            return items

        results = await asyncio.gather(*(run_one(agent_id) for agent_id, _ in targets))
        return [item for sub in results for item in sub]
