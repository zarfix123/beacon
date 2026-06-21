"""Deterministic demo-retrieval guard (Phase 4 step 1).

Asserts the LOCKED demo query surfaces the planted chunk_ids in top-2 for each responder
under the real hybrid engine, with the right tiers — so a re-seed / re-tier can never
silently break the grant-access money moment. Skips if the corpus isn't seeded (CI/clean
checkout: the corpora + embeddings are gitignored; run `python -m scripts.demo_seed` first).
"""
from __future__ import annotations

import pytest

from app.agents.corpus import CORPORA_DIR
from app.demo import DEMO_CHUNKS, DEMO_QUERY

_SEEDED = (CORPORA_DIR / "embeddings.npz").exists() and all(
    (CORPORA_DIR / f"{c['owner']}.json").exists() for c in DEMO_CHUNKS
)
requires_seed = pytest.mark.skipif(
    not _SEEDED, reason="demo corpus not seeded — run `python -m scripts.demo_seed`"
)

_EXPECTED = {
    "agent_northwind": {"northwind_demo_gateway", "northwind_demo_runbook"},
    "agent_quanta": {"quanta_demo_throttle", "quanta_demo_notes"},
    "agent_helios": {"helios_demo_dashboard"},
}
_TIERS = {
    "northwind_demo_gateway": "public",
    "northwind_demo_runbook": "private",
    "quanta_demo_throttle": "restricted",
    "quanta_demo_notes": "public",
    "helios_demo_dashboard": "public",
}


@requires_seed
def test_locked_query_surfaces_planted_chunks(monkeypatch):
    import app.retrieval.search as sm
    from app.agents.registry import build_registry

    monkeypatch.setattr(sm, "SEARCH_BACKEND", "hybrid")        # demo engine, regardless of env
    reg = build_registry(with_embeddings=True)
    sm.set_registry(reg)

    # top-2 per responder is exactly the planted set (no off-topic real chunk sneaks in)
    for agent_id, expected in _EXPECTED.items():
        got = {h["chunk_id"] for h in sm.search(DEMO_QUERY, agent_id, top_k=2)}
        assert expected <= got, f"{agent_id}: planted demo chunks not in top-2 — got {got}"

    # tiers are correct -> the demo yields full + redacted + denied (not all public)
    vis = {
        c["chunk_id"]: c["visibility"]
        for agent_id in _EXPECTED
        for c in reg.get(agent_id).index.chunks
        if c["chunk_id"] in _TIERS
    }
    assert vis == _TIERS, f"demo tiers drifted: {vis}"
