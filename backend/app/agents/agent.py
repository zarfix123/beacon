"""RuntimeAgent: identity + own AgentIndex + the gate seam (agents-corpus-index.md §2.4).

Responsibility: the runtime Agent object — identity (`id`, `party_name`,
`scope_policy`) plus a handle to ITS OWN AgentIndex and nothing else. Provides
`.search()` (delegates to retrieval over its own index) and the `.respond(gate_fn)`
seam the gate plugs into, so enforcement runs INSIDE the owning agent before content
crosses the boundary (spec §3/§6). This file contains NO visibility->decision logic.
This is a SKELETON — no logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.agents.index import AgentIndex
from app.models import Chunk, ResponseItem


@dataclass
class RuntimeAgent:
    """One party agent: identity + its own isolated index only."""
    id: str
    party_name: str
    scope_policy: str            # "three_tier"
    index: AgentIndex            # THIS agent's index only

    def search(self, query: str, top_k: int = 5) -> list[Chunk]:
        """Retrieve over OWN index only. Delegates to search.search(query, self.id,
        top_k). Returns ALL tiers, ungated, with score (retrieve-first)."""
        raise NotImplementedError("RuntimeAgent.search is a skeleton stub")

    def respond(
        self,
        query: str,
        top_k: int,
        gate_fn: Callable[[Chunk, "RuntimeAgent"], ResponseItem],
    ) -> list[ResponseItem]:
        """Seam for the GATE subsystem. retrieve-first, gate-second, IN this agent
        before anything crosses outward. This subsystem provides the seam + ordering;
        it does NOT implement gate_fn."""
        raise NotImplementedError("RuntimeAgent.respond is a skeleton stub")
