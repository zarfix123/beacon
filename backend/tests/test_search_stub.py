"""Tests for app/retrieval/search.py keyword stub (BUILD_INDEX.md §2 / step 8).

Frozen behaviors (search-interface.md): own-agent only, ALL tiers (ungated),
descending score, <= top_k, KeyError on unknown agent, [] on no overlap.
"""
from __future__ import annotations

import pytest

from app.retrieval import search as S


def test_own_agent_only(fixture_registry):
    for c in S.search("servo database query", "fix_a", 5):
        assert c["owner"] == "fix_a"


def test_all_tiers_unfiltered(fixture_registry):
    # Query overlaps all three fix_a chunks; the stub must return every tier
    # (retrieve-first, gate-second — search NEVER filters by visibility).
    res = S.search("servo resolution salary data", "fix_a", 5)
    assert {c["visibility"] for c in res} == {"public", "restricted", "private"}


def test_scores_descending_and_bounded(fixture_registry):
    res = S.search("servo resolution salary data", "fix_a", 5)
    scores = [c["score"] for c in res]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= s <= 1.0 for s in scores)


def test_top_k_cap(fixture_registry):
    assert len(S.search("servo resolution salary data", "fix_a", top_k=2)) <= 2


def test_unknown_agent_raises_keyerror(fixture_registry):
    with pytest.raises(KeyError):
        S.search("servo", "agent_bogus", 5)


def test_no_overlap_returns_empty(fixture_registry):
    assert S.search("zzqq nonexistent token", "fix_b", 5) == []
