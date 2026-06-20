"""Frozen search() interface + keyword stub + real cosine (agents-corpus-index.md §2.6).

Responsibility: the FROZEN `search(query, agent_id, top_k)` entry point
(shared/contracts/search-interface.md). Single dispatch point: `_keyword_stub` until
H8, `_cosine_search` behind RELAY_SEARCH=cosine. Returns ALL visibility tiers,
UNGATED, ordered by descending score, <= top_k, [] on no hit. Raises KeyError on
unknown agent_id. NEVER gates/filters by visibility (retrieve-first, gate-second).
This is a SKELETON — no logic.
"""
from __future__ import annotations

import os
from typing import Optional, TYPE_CHECKING

from app.models import Chunk

if TYPE_CHECKING:
    from app.agents.registry import AgentRegistry
    from app.agents.agent import RuntimeAgent

# Set at startup by the lifespan wiring (main.py) so search() can resolve agents.
_REGISTRY: Optional["AgentRegistry"] = None

# "stub" until H8, then "cosine" (drop-in identical shape).
SEARCH_BACKEND = os.getenv("RELAY_SEARCH", "stub")


def set_registry(registry: "AgentRegistry") -> None:
    """Inject the AgentRegistry at startup so search() resolves the per-agent index."""
    raise NotImplementedError("set_registry is a skeleton stub")


def search(query: str, agent_id: str, top_k: int = 5) -> list[Chunk]:
    """FROZEN signature (search-interface.md). Single dispatch point.

    Returns ALL visibility tiers, ungated, ordered by descending score, <= top_k,
    [] on no hit. Raises KeyError on unknown agent_id. NEVER gates/filters.
    """
    raise NotImplementedError("search is a skeleton stub")


def _keyword_stub(query: str, agent: "RuntimeAgent", top_k: int) -> list[Chunk]:
    """Deterministic keyword-overlap stub (search-interface.md stub algorithm):
    tokenize query + chunk text/title on \\W+, score = |distinct query tokens in
    chunk| / |distinct query tokens|, drop score==0, sort desc, take top_k. No
    embeddings read; carries all tiers with score."""
    raise NotImplementedError("_keyword_stub is a skeleton stub")


def _cosine_search(query: str, agent: "RuntimeAgent", top_k: int) -> list[Chunk]:
    """Real retrieval: embed query -> cosine vs agent.index.matrix (own index only)
    -> argsort desc -> attach score in [0,1] -> top_k. Same Chunk shape, all tiers."""
    raise NotImplementedError("_cosine_search is a skeleton stub")
