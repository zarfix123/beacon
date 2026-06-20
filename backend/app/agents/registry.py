"""AgentRegistry: the single agent_id -> Agent resolution point (agents-corpus-index.md §2.5).

Responsibility (BUILD_INDEX.md §2.1): ONE registry. Constructs the 3 isolated agents
once at startup, resolves by id, and exposes party_name / all_ids / find_chunk. The
router/API import it; no second registry under router/ or core/. KeyError on unknown
id (mirrors the search() contract).
"""
from __future__ import annotations

from app.agents.agent import RuntimeAgent
from app.models import Chunk

# The 3 locked agents (data-model.md §1; ids frozen at hour 0).
# Mapping to real accounts (BUILD_INDEX §8.2): northwind<-dennis, helios<-hao, quanta<-other.
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
        return self._agents[agent_id]

    def all_ids(self) -> list[str]:
        """Every registered agent id, in stable (AGENT_DEFS) order."""
        return list(self._agents.keys())

    def party_name(self, agent_id: str) -> str:
        """Resolve party_name (for agent-activated / ResponseItem.source_party)."""
        return self._agents[agent_id].party_name

    def find_chunk(self, chunk_id: str) -> tuple[RuntimeAgent, Chunk]:
        """Resolve (owning agent, chunk) by globally-unique chunk_id (grant_access)."""
        for agent in self._agents.values():
            for chunk in agent.index.chunks:
                if chunk["chunk_id"] == chunk_id:
                    return agent, chunk
        raise KeyError(chunk_id)


def build_registry(*, with_embeddings: bool) -> AgentRegistry:
    """Build 3 isolated RuntimeAgents from AGENT_DEFS + seed files. Called once at
    FastAPI startup. Each agent gets a SEPARATE AgentIndex (no shared lists)."""
    from app.agents.index import load_agent_index

    agents: dict[str, RuntimeAgent] = {}
    for agent_id, party_name, scope_policy in AGENT_DEFS:
        index = load_agent_index(agent_id, with_embeddings=with_embeddings)
        agents[agent_id] = RuntimeAgent(
            id=agent_id, party_name=party_name, scope_policy=scope_policy, index=index
        )
    return AgentRegistry(agents)
