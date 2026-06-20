"""Frozen search() interface + keyword stub + real cosine (agents-corpus-index.md §2.6).

Responsibility: the FROZEN `search(query, agent_id, top_k)` entry point
(shared/contracts/search-interface.md). Single dispatch point: `_keyword_stub` until
H8, `_cosine_search` behind RELAY_SEARCH=cosine. Returns ALL visibility tiers,
UNGATED, ordered by descending score, <= top_k, [] on no hit. Raises KeyError on
unknown agent_id. NEVER gates/filters by visibility (retrieve-first, gate-second).
"""
from __future__ import annotations

import os
import re
from typing import Optional, TYPE_CHECKING

from app.models import Chunk

if TYPE_CHECKING:
    from app.agents.registry import AgentRegistry
    from app.agents.agent import RuntimeAgent

# Set at startup by the lifespan wiring (main.py) so search() can resolve agents.
_REGISTRY: Optional["AgentRegistry"] = None

# "stub" until H8, then "cosine" (drop-in identical shape).
SEARCH_BACKEND = os.getenv("RELAY_SEARCH", "stub")

_TOKEN_RE = re.compile(r"\w+")


def set_registry(registry: "AgentRegistry") -> None:
    """Inject the AgentRegistry at startup so search() resolves the per-agent index."""
    global _REGISTRY
    _REGISTRY = registry


def search(query: str, agent_id: str, top_k: int = 5) -> list[Chunk]:
    """FROZEN signature (search-interface.md). Single dispatch point.

    Returns ALL visibility tiers, ungated, ordered by descending score, <= top_k,
    [] on no hit. Raises KeyError on unknown agent_id. NEVER gates/filters.
    """
    if _REGISTRY is None:
        raise RuntimeError("search registry not set — call set_registry() at startup")
    agent = _REGISTRY.get(agent_id)          # KeyError on unknown id (contract)
    if SEARCH_BACKEND == "cosine":
        return _cosine_search(query, agent, top_k)
    return _keyword_stub(query, agent, top_k)


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t}


def _keyword_stub(query: str, agent: "RuntimeAgent", top_k: int) -> list[Chunk]:
    """Deterministic keyword-overlap stub: score = |distinct query tokens present in
    chunk text+title| / |distinct query tokens|, drop score==0, sort desc, take
    top_k. No embeddings read; carries all tiers with score."""
    q = _tokens(query)
    if not q:
        return []
    scored: list[Chunk] = []
    for c in agent.index.chunks:
        toks = _tokens(c["text"] + " " + c["doc_title"])
        overlap = len(q & toks)
        if overlap == 0:
            continue
        scored.append({**c, "score": round(overlap / len(q), 4)})
    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored[:top_k]


def _cosine_search(query: str, agent: "RuntimeAgent", top_k: int) -> list[Chunk]:
    """Real retrieval: embed query -> cosine vs agent.index.matrix (own index only)
    -> argsort desc -> attach score in [0,1] -> top_k. Same Chunk shape, all tiers."""
    import numpy as np

    from app.agents.embeddings import embed_query

    matrix = agent.index.matrix
    if matrix is None or matrix.shape[0] == 0:
        return []
    qv = embed_query(query)
    denom = (np.linalg.norm(matrix, axis=1) * np.linalg.norm(qv)) + 1e-9
    sims = (matrix @ qv) / denom
    order = np.argsort(-sims)[:top_k]
    return [
        {**agent.index.chunks[i], "score": float((sims[i] + 1.0) / 2.0)}
        for i in order
        if sims[i] > 0
    ]
