"""Tests for agent isolation — the security claim (BUILD_INDEX.md §2 / step 8).

Searching A returns zero chunks owned by B/C; each AgentIndex holds a separate chunk
list (no shared references); set_visibility touches exactly one row.
"""
from __future__ import annotations

import pytest

from app.agents.index import ChunkNotFoundError
from app.retrieval import search as S


def test_search_returns_only_own_chunks(real_registry):
    # Run a broad query against the REAL corpora; every hit must be owned by the
    # searched agent — no cross-party leakage through retrieval.
    for agent_id in real_registry.all_ids():
        for c in S.search("security authentication error fix code app", agent_id, 10):
            assert c["owner"] == agent_id, f"{agent_id} returned a chunk owned by {c['owner']}"


def test_indexes_are_distinct_objects(real_registry):
    ids = real_registry.all_ids()
    chunk_lists = [real_registry.get(a).index.chunks for a in ids]
    for i in range(len(chunk_lists)):
        for j in range(i + 1, len(chunk_lists)):
            assert chunk_lists[i] is not chunk_lists[j], "agents share a chunk list"


def test_set_visibility_touches_one_row(fixture_registry):
    a = fixture_registry.get("fix_a")
    b = fixture_registry.get("fix_b")
    before_a = {c["chunk_id"]: c["visibility"] for c in a.index.chunks}
    before_b = [c["visibility"] for c in b.index.chunks]

    a.index.set_visibility("fix_a_c001", "public")

    after_a = {c["chunk_id"]: c["visibility"] for c in a.index.chunks}
    changed = [cid for cid in after_a if after_a[cid] != before_a[cid]]
    assert changed == ["fix_a_c001"]
    assert after_a["fix_a_c001"] == "public"
    # the other agent's index is untouched
    assert [c["visibility"] for c in b.index.chunks] == before_b


def test_set_visibility_unknown_chunk_raises(fixture_registry):
    with pytest.raises(ChunkNotFoundError):
        fixture_registry.get("fix_a").index.set_visibility("nope_c999", "public")
