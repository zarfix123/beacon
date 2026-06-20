"""Shared test fixtures (BUILD_INDEX.md §2 tests/conftest.py).

Phase 1 fixtures:
  - `fixture_registry`: a small hand-built registry with mixed visibility tiers and
    known token overlaps, for deterministic search / isolation / set_visibility asserts
    that don't depend on whatever the ingest happened to select.
  - `real_registry`: a registry built from the ingested real corpora (stub mode).

Both `set_registry()` the module-global so `search()` resolves against them.
(The fake EventBus / responder / gate fixtures noted in the original TODO arrive with
Phases 2-3.)
"""
from __future__ import annotations

import pytest

from app.agents.agent import RuntimeAgent
from app.agents.index import AgentIndex
from app.agents.registry import AgentRegistry, build_registry
from app.models import Chunk
from app.retrieval import search as search_module


def make_chunk(owner: str, n: int, visibility: str, text: str, title: str | None = None) -> Chunk:
    return {
        "chunk_id": f"{owner}_c{n:03d}",
        "parent_doc_id": f"{owner}_d00",
        "doc_title": title or f"{owner} doc {n}",
        "owner": owner,
        "visibility": visibility,
        "text": text,
    }


def _agent(owner: str, party: str, chunks: list[Chunk]) -> RuntimeAgent:
    return RuntimeAgent(
        id=owner, party_name=party, scope_policy="three_tier",
        index=AgentIndex(agent_id=owner, chunks=chunks),
    )


@pytest.fixture
def fixture_registry():
    """Deterministic hand-built registry: mixed tiers + known overlaps."""
    a = _agent("fix_a", "Party A", [
        make_chunk("fix_a", 0, "public", "servo jitter fix clamp the integral term", "Servo Fix"),
        make_chunk("fix_a", 1, "restricted", "servo resolution secret postmortem details", "Servo Postmortem"),
        make_chunk("fix_a", 2, "private", "internal salary compensation data", "HR Comp"),
    ])
    b = _agent("fix_b", "Party B", [
        make_chunk("fix_b", 0, "public", "database query optimization add an index", "DB Tips"),
    ])
    reg = AgentRegistry({"fix_a": a, "fix_b": b})
    search_module.set_registry(reg)
    return reg


@pytest.fixture
def real_registry():
    """Registry built from the ingested real corpora (keyword-stub mode)."""
    reg = build_registry(with_embeddings=False)
    search_module.set_registry(reg)
    return reg
