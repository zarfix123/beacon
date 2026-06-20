"""AgentRegistry: the single agent_id -> Agent resolution point (agents-corpus-index.md §2.5).

Responsibility (BUILD_INDEX.md §2.1): ONE registry. Constructs the 3 isolated agents
once at startup, resolves by id, and exposes party_name / all_ids / find_chunk. The
router/API import it; no second registry under router/ or core/. KeyError on unknown
id (mirrors the search() contract). This is a SKELETON — no logic.
"""
from __future__ import annotations

from typing import Optional

from app.agents.agent import RuntimeAgent
from app.models import Chunk

# The 3 locked agents (data-model.md §1; ids frozen at hour 0).
AGENT_DEFS: list[tuple[str, str, str]] = [
    ("agent_northwind", "Northwind Robotics", "three_tier"),
    ("agent_helios", "Helios Dynamics", "three_tier"),
    ("agent_quanta", "Quanta Systems", "three_tier"),
]


class AgentRegistry:
    """Holds the 3 RuntimeAgents; the only place agent_id -> Agent resolution lives."""

    def __init__(self, agents: dict[str, RuntimeAgent]) -> None:
        self._agents = agents

    def get(self, agent_id: str) -> RuntimeAgent:
        """Resolve an agent by id. Raises KeyError on unknown id (search() contract)."""
        raise NotImplementedError("AgentRegistry.get is a skeleton stub")

    def all_ids(self) -> list[str]:
        """Every registered agent id, in stable order."""
        raise NotImplementedError("AgentRegistry.all_ids is a skeleton stub")

    def party_name(self, agent_id: str) -> str:
        """Resolve party_name (for agent-activated / ResponseItem.source_party)."""
        raise NotImplementedError("AgentRegistry.party_name is a skeleton stub")

    def find_chunk(self, chunk_id: str) -> tuple[RuntimeAgent, Chunk]:
        """Resolve (owning agent, chunk) by globally-unique chunk_id (grant_access)."""
        raise NotImplementedError("AgentRegistry.find_chunk is a skeleton stub")


def build_registry(*, with_embeddings: bool) -> AgentRegistry:
    """Build 3 isolated RuntimeAgents from AGENT_DEFS + seed files. Called once at
    FastAPI startup. Each agent gets a SEPARATE AgentIndex (no shared lists)."""
    raise NotImplementedError("build_registry is a skeleton stub")
