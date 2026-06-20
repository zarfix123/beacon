"""Hybrid retrieval (BM25 + static dense, RRF) — Phase 1.5.

Self-contained: builds a small controlled registry WITH an embedding matrix so the two
channels are exercised deterministically. Skips cleanly if model2vec / rank-bm25 aren't
installed (keeps the 15 fast stub tests torch-free / dep-free).
"""
from __future__ import annotations

import pytest

pytest.importorskip("model2vec")
pytest.importorskip("rank_bm25")

from app.agents.agent import RuntimeAgent
from app.agents.embeddings import embed_texts
from app.agents.index import AgentIndex
from app.agents.registry import AgentRegistry
from app.retrieval import search as search_module


def _chunk(owner: str, n: int, text: str, title: str):
    return {
        "chunk_id": f"{owner}_c{n:03d}",
        "parent_doc_id": f"{owner}_d00",
        "doc_title": title,
        "owner": owner,
        "visibility": "public",
        "text": text,
    }


# Controlled corpora: known content so exact-term vs paraphrase behavior is assertable.
_ALPHA = [
    _chunk("alpha", 0, "rate limiting throttle gateway requests per minute under load", "Throttle config"),
    _chunk("alpha", 1, "RetryPolicy exponential backoff with jitter on failed calls", "Retry policy"),
    _chunk("alpha", 2, "database index optimization speeds up the slow query plan", "DB tuning"),
    _chunk("alpha", 3, "kubernetes pod autoscaling and rolling deployment strategy", "K8s"),
]
_BETA = [
    _chunk("beta", 0, "monthly billing invoice and payment reconciliation report", "Billing"),
]


def _agent(owner, party, chunks):
    matrix = embed_texts([c["text"] for c in chunks])  # dense = text only (matches build_embeddings)
    return RuntimeAgent(
        id=owner, party_name=party, scope_policy="three_tier",
        index=AgentIndex(agent_id=owner, chunks=chunks, matrix=matrix),
    )


@pytest.fixture
def hybrid_registry(monkeypatch):
    reg = AgentRegistry({"alpha": _agent("alpha", "Alpha", _ALPHA), "beta": _agent("beta", "Beta", _BETA)})
    search_module.set_registry(reg)
    monkeypatch.setattr(search_module, "SEARCH_BACKEND", "hybrid")
    return reg


def test_scores_bounded_descending_and_capped(hybrid_registry):
    hits = search_module.search("throttle requests", "alpha", top_k=3)
    assert 0 < len(hits) <= 3
    scores = [h["score"] for h in hits]
    assert all(0.0 < s <= 1.0 for s in scores)
    assert scores == sorted(scores, reverse=True)


def test_exact_term_ranks_first_via_bm25(hybrid_registry):
    # "RetryPolicy" is a rare exact identifier present in exactly one chunk -> BM25 pins it #1.
    hits = search_module.search("RetryPolicy", "alpha", top_k=3)
    assert hits[0]["chunk_id"] == "alpha_c001"


def test_paraphrase_retrieved_via_dense_channel(hybrid_registry):
    # Few literal tokens overlap with "rate limiting throttle gateway"; the dense channel
    # still recalls it — the semantic win a pure keyword stub would miss.
    hits = search_module.search("how do we stop the service from getting overloaded", "alpha", top_k=3)
    assert "alpha_c000" in [h["chunk_id"] for h in hits]


def test_isolation_only_own_chunks(hybrid_registry):
    # A billing-flavoured query against alpha must never surface beta's chunk.
    hits = search_module.search("billing invoice payment", "alpha", top_k=5)
    assert all(h["owner"] == "alpha" for h in hits)
    beta_hits = search_module.search("billing invoice payment", "beta", top_k=5)
    assert all(h["owner"] == "beta" for h in beta_hits)


def test_unknown_agent_raises_keyerror(hybrid_registry):
    with pytest.raises(KeyError):
        search_module.search("anything", "nope", top_k=3)


def test_empty_query_returns_empty(hybrid_registry):
    assert search_module.search("   ", "alpha", top_k=3) == []
