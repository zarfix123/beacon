"""Tests for app/grant_access/ — toggle on the right row only, validation, replay wiring."""
from __future__ import annotations

import pytest

from app.agents.index import ChunkNotFoundError
from app.grant_access.service import GrantAccessService, UnknownQueryError
from app.run_registry import RunContext, RunRegistry


class FakeOrchestrator:
    def __init__(self) -> None:
        self.calls: list = []

    async def run_guarded(self, query, from_agent, query_id, *, changed_chunk_id=None):
        self.calls.append((query, from_agent, query_id, changed_chunk_id))


def _svc(fixture_registry, run_registry=None):
    return GrantAccessService(
        registry=fixture_registry,
        orchestrator=FakeOrchestrator(),
        run_registry=run_registry or RunRegistry(),
    )


def test_toggle_flips_only_the_right_row(fixture_registry):
    svc = _svc(fixture_registry)
    a = fixture_registry.get("fix_a")
    assert a.index.chunks[1]["chunk_id"] == "fix_a_c001" and a.index.chunks[1]["visibility"] == "restricted"

    assert svc.toggle_visibility("fix_a_c001") == "public"
    assert a.index.chunks[1]["visibility"] == "public"           # flipped
    assert a.index.chunks[0]["visibility"] == "public"           # untouched (already public)
    assert a.index.chunks[2]["visibility"] == "private"          # untouched (other row)


def test_toggle_is_idempotent(fixture_registry):
    svc = _svc(fixture_registry)
    assert svc.toggle_visibility("fix_a_c001") == "public"
    assert svc.toggle_visibility("fix_a_c001") == "public"       # double-click is a no-op


def test_toggle_unknown_chunk_raises(fixture_registry):
    with pytest.raises(ChunkNotFoundError):
        _svc(fixture_registry).toggle_visibility("does_not_exist")


async def test_grant_and_rerun_unknown_query_404s_without_mutating(fixture_registry):
    svc = _svc(fixture_registry)                                  # empty run registry
    with pytest.raises(UnknownQueryError):
        await svc.grant_and_rerun("fix_a_c001", "missing")
    assert fixture_registry.get("fix_a").index.chunks[1]["visibility"] == "restricted"  # not toggled


async def test_grant_and_rerun_toggles_and_acks(fixture_registry):
    rr = RunRegistry()
    rr.put(RunContext("qid", "servo jitter", "fix_b"))
    svc = _svc(fixture_registry, rr)
    result = await svc.grant_and_rerun("fix_a_c001", "qid")
    assert result.new_visibility == "public" and result.rerunning is True
    assert fixture_registry.get("fix_a").index.chunks[1]["visibility"] == "public"


async def test_replay_targets_changed_party(fixture_registry):
    rr = RunRegistry()
    rr.put(RunContext("qid", "servo jitter", "fix_b"))
    orch = FakeOrchestrator()
    svc = GrantAccessService(registry=fixture_registry, orchestrator=orch, run_registry=rr)
    await svc.replay("qid", "fix_a_c001")
    assert orch.calls == [("servo jitter", "fix_b", "qid", "fix_a_c001")]


async def test_replay_unknown_query_raises(fixture_registry):
    with pytest.raises(UnknownQueryError):
        await _svc(fixture_registry).replay("missing")
