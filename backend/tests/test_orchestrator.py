"""Tests for app/orchestrator/orchestrator.py — done shape, targeted replay, never-hang.

The orchestrator's job (post-reconciliation) is coordination + synthesis + the single
`done` event; the router emits agent-activated/response-item, so the fake router here does
not. Synthesis is monkeypatched to stay deterministic and key-free.
"""
from __future__ import annotations

import pytest

from app.orchestrator.orchestrator import Orchestrator
from app.run_registry import RunRegistry


class FakeRouter:
    def __init__(self, items_for) -> None:
        self._items_for = items_for          # callable(only_agents) -> list[item]
        self.calls: list = []

    async def dispatch(self, query_id, from_agent, query, *, only_agents=None):
        self.calls.append(only_agents)
        return self._items_for(only_agents)


class FakeRegistry:
    def __init__(self, owner_of: dict[str, str]) -> None:
        self._owner_of = owner_of

    def find_chunk(self, chunk_id):
        owner = self._owner_of[chunk_id]
        return (type("A", (), {"id": owner})(), {"chunk_id": chunk_id})


def _it(aid, decision, verified=True, cid=None):
    return {"answer": ("a" if decision != "denied" else None), "source_party": aid,
            "source_doc_title": "T", "decision": decision, "verified": verified,
            "chunk_id": cid or f"{aid}_c", "source_agent_id": aid}


@pytest.fixture
def collector_sink():
    events: list[dict] = []

    async def sink(e):
        events.append(e)

    return events, sink


@pytest.fixture(autouse=True)
def _stub_synth(monkeypatch):
    async def fake_synth(query, items, redacted, on_delta=None):
        return "ANSWER [1]"
    monkeypatch.setattr("app.orchestrator.orchestrator.synthesize", fake_synth)


async def test_run_emits_one_done_provenance_excludes_denied(collector_sink):
    events, sink = collector_sink
    items = [_it("p1", "full"), _it("p2", "redacted", verified=False), _it("p1", "denied", verified=False)]
    orch = Orchestrator(registry=None, router=FakeRouter(lambda only: items), emit=sink,
                        run_registry=RunRegistry())
    await orch.run("q", "asker", query_id="qid")

    done_events = [e for e in events if e["type"] == "done"]
    assert len(done_events) == 1                          # exactly one done
    assert "synthesizing" in [e["type"] for e in events]  # streamed-answer marker emitted
    done = done_events[0]
    assert done["query_id"] == "qid"
    assert done["item_count"] == 3                        # all items (incl denied)
    assert [p["decision"] for p in done["provenance"]] == ["full", "redacted"]  # denied excluded; order = full,redacted
    assert done["synthesized_answer"] == "ANSWER [1]"


async def test_targeted_replay_reuses_cache(collector_sink):
    events, sink = collector_sink
    first = [_it("p1", "full", cid="p1_c"), _it("p2", "redacted", verified=False, cid="p2_c")]
    replay_fresh = [_it("p2", "full", cid="p2_c")]

    def items_for(only):
        return replay_fresh if only == ["p2"] else first

    router = FakeRouter(items_for)
    orch = Orchestrator(registry=FakeRegistry({"p2_c": "p2"}), router=router, emit=sink,
                        run_registry=RunRegistry())
    await orch.run("q", "asker", query_id="qid")                       # fresh
    await orch.run("q", "asker", query_id="qid", changed_chunk_id="p2_c")  # targeted replay

    assert router.calls == [None, ["p2"]]                 # only p2 re-dispatched on replay
    done2 = events[-1]
    assert done2["item_count"] == 2                       # p1 (cached) + p2 (fresh)
    pairs = {(p["source_agent_id"], p["decision"]) for p in done2["provenance"]}
    assert pairs == {("p1", "full"), ("p2", "full")}      # the granted chunk is now full


async def test_run_streams_answer_deltas(collector_sink, monkeypatch):
    events, sink = collector_sink

    async def streaming_synth(query, items, redacted, on_delta=None):
        for tok in ["The ", "answer", "."]:
            if on_delta:
                await on_delta(tok)
        return "The answer."

    monkeypatch.setattr("app.orchestrator.orchestrator.synthesize", streaming_synth)
    orch = Orchestrator(registry=None, router=FakeRouter(lambda only: [_it("p1", "full")]),
                        emit=sink, run_registry=RunRegistry())
    await orch.run("q", "asker", query_id="qid")

    types = [e["type"] for e in events]
    deltas = [e["delta"] for e in events if e["type"] == "answer-delta"]
    assert "".join(deltas) == "The answer."                       # tokens streamed in order
    assert types.index("synthesizing") < types.index("answer-delta") < types.index("done")
    assert events[-1]["type"] == "done" and events[-1]["synthesized_answer"] == "The answer."


async def test_run_guarded_emits_done_on_error(collector_sink):
    events, sink = collector_sink

    class BoomRouter:
        async def dispatch(self, *a, **k):
            raise RuntimeError("boom")

    orch = Orchestrator(registry=None, router=BoomRouter(), emit=sink, run_registry=RunRegistry())
    await orch.run_guarded("q", "asker", "qid")           # must not raise
    assert events and events[-1]["type"] == "done"        # never-hang: terminal done emitted
