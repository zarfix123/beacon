"""Frozen search() interface + keyword stub + real cosine (agents-corpus-index.md §2.6).

Responsibility: the FROZEN `search(query, agent_id, top_k)` entry point
(shared/contracts/search-interface.md). Single dispatch point: `_keyword_stub` until
H8, `_cosine_search` behind BEACON_SEARCH=cosine. Returns ALL visibility tiers,
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

# "stub" (keyword overlap, default), "cosine" (pure dense), or "hybrid"
# (BM25 + dense fused with RRF — the Phase-1.5 engine). All share the frozen shape.
SEARCH_BACKEND = os.getenv("BEACON_SEARCH", "stub")

# Relevance floor: drop any result whose absolute dense cosine sim is below this, so a
# genuinely off-topic query returns [] (no-hit) and a one-party query only surfaces the
# relevant party (single-hit). 0.0 = off (default; preserves the frozen "return top_k"
# behavior for the stub + existing tests). The demo sets BEACON_MIN_SIM in run.sh.
RELEVANCE_FLOOR = float(os.getenv("BEACON_MIN_SIM", "0.0"))

_TOKEN_RE = re.compile(r"\w+")

# Per-agent BM25 index cache for the hybrid path: agent_id -> (chunks_ref, BM25Okapi).
# `chunks_ref` identity-guards against a rebuilt registry; cleared in set_registry().
_BM25_CACHE: dict = {}

_RRF_K = 60  # Reciprocal Rank Fusion constant (standard).


def set_registry(registry: "AgentRegistry") -> None:
    """Inject the AgentRegistry at startup so search() resolves the per-agent index."""
    global _REGISTRY
    _REGISTRY = registry
    _BM25_CACHE.clear()


def search(query: str, agent_id: str, top_k: int = 5) -> list[Chunk]:
    """FROZEN signature (search-interface.md). Single dispatch point.

    Returns ALL visibility tiers, ungated, ordered by descending score, <= top_k,
    [] on no hit. Raises KeyError on unknown agent_id. NEVER gates/filters.
    """
    if _REGISTRY is None:
        raise RuntimeError("search registry not set — call set_registry() at startup")
    agent = _REGISTRY.get(agent_id)          # KeyError on unknown id (contract)
    if SEARCH_BACKEND == "hybrid":
        return _hybrid_search(query, agent, top_k)
    if SEARCH_BACKEND == "cosine":
        return _cosine_search(query, agent, top_k)
    return _keyword_stub(query, agent, top_k)


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t}


def _token_list(text: str) -> list[str]:
    """Ordered tokens WITH duplicates — BM25 needs term frequencies, not a set."""
    return _TOKEN_RE.findall(text.lower())


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
    -> argsort desc -> attach score in [0,1] -> top_k. Same Chunk shape, all tiers.
    Drops results below RELEVANCE_FLOOR (absolute cosine) when the floor is enabled."""
    import numpy as np

    sims = _dense_sims(query, agent)
    if sims is None:
        return []
    order = np.argsort(-sims)[:top_k]
    floor = max(RELEVANCE_FLOOR, 0.0)
    return [
        {**agent.index.chunks[i], "score": float((sims[i] + 1.0) / 2.0)}
        for i in order
        if sims[i] > 0 and sims[i] >= floor
    ]


# --------------------------------------------------------------------------- #
# Hybrid retrieval: BM25 (lexical) + dense (static embeddings), fused with RRF #
# --------------------------------------------------------------------------- #

def _get_bm25(agent: "RuntimeAgent"):
    """Lazily build + cache a BM25Okapi index over the agent's OWN chunks only.

    Tokenized on text + doc_title (with term frequencies). Returns None for an empty
    index. Isolation: each agent's BM25 sees only its own corpus.
    """
    cached = _BM25_CACHE.get(agent.id)
    if cached is not None and cached[0] is agent.index.chunks:
        return cached[1]
    from rank_bm25 import BM25Okapi

    corpus = [_token_list(c["text"] + " " + c["doc_title"]) for c in agent.index.chunks]
    bm = BM25Okapi(corpus) if corpus else None
    _BM25_CACHE[agent.id] = (agent.index.chunks, bm)
    return bm


def _lexical_order(query: str, agent: "RuntimeAgent") -> Optional[list[int]]:
    """Chunk indices ranked by BM25 score (best first), or None if unavailable."""
    bm = _get_bm25(agent)
    if bm is None:
        return None
    import numpy as np

    scores = np.asarray(bm.get_scores(_token_list(query)), dtype="float64")
    return list(np.argsort(-scores))


def _dense_sims(query: str, agent: "RuntimeAgent"):
    """Absolute cosine sims (in [-1, 1]) of the query vs the agent's matrix, or None if
    the matrix wasn't built (stub-mode registry). Shared by cosine search, dense-order,
    and the relevance floor so the query is embedded only once."""
    matrix = agent.index.matrix
    if matrix is None or matrix.shape[0] == 0:
        return None
    import numpy as np

    from app.agents.embeddings import embed_query

    qv = embed_query(query)
    denom = (np.linalg.norm(matrix, axis=1) * np.linalg.norm(qv)) + 1e-9
    return (matrix @ qv) / denom


def _hybrid_search(query: str, agent: "RuntimeAgent", top_k: int) -> list[Chunk]:
    """BM25 + dense, fused with Reciprocal Rank Fusion. Returns all tiers, ungated,
    descending fused score (max-normalized to (0,1]), <= top_k. Falls back to whichever
    channel is available; [] on empty query or empty index."""
    if not _tokens(query):
        return []
    chunks = agent.index.chunks
    n = len(chunks)
    if n == 0:
        return []

    import numpy as np

    sims = _dense_sims(query, agent)                                  # computed once
    dense_order = list(np.argsort(-sims)) if sims is not None else None
    orders = [o for o in (_lexical_order(query, agent), dense_order) if o is not None]
    if not orders:
        return []

    fused = [0.0] * n
    for order in orders:
        for rank, idx in enumerate(order):
            fused[idx] += 1.0 / (_RRF_K + rank + 1)  # rank is 0-based

    ranked = sorted(range(n), key=lambda i: fused[i], reverse=True)[:top_k]
    top = fused[ranked[0]] if ranked else 1.0
    top = top or 1.0
    floor = max(RELEVANCE_FLOOR, 0.0)
    out: list[Chunk] = []
    for i in ranked:
        if fused[i] <= 0:
            continue
        if floor > 0.0 and sims is not None and sims[i] < floor:      # relevance floor
            continue
        out.append({**chunks[i], "score": round(fused[i] / top, 4)})
    return out
