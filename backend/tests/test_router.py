"""Tests for app/router/router.py — fan-out order, frozen frames, only_agents filter."""
from __future__ import annotations

from app.events.bus import EventBus
from app.router.router import Router, agent_activated_event, response_item_event


class FakeRegistry:
    def __init__(self, parties: dict[str, str]) -> None:
        self._p = parties

    def all_ids(self) -> list[str]:
        return list(self._p)

    def party_name(self, agent_id: str) -> str:
        return self._p[agent_id]


def _items(agent_id: str) -> list[dict]:
    base = {"source_party": "P", "source_doc_title": "T", "source_agent_id": agent_id}
    return [
        {**base, "answer": "full text", "decision": "full", "verified": True, "chunk_id": f"{agent_id}_c0"},
        {**base, "answer": "gist", "decision": "redacted", "verified": False, "chunk_id": f"{agent_id}_c1"},
        {**base, "answer": None, "source_doc_title": None, "decision": "denied", "verified": False, "chunk_id": f"{agent_id}_c2"},
    ]


def _drain(bus: EventBus, query_id: str) -> list[dict]:
    q = bus.subscribe(query_id)               # history replay hands back every frame, in order
    out = []
    while not q.empty():
        out.append(q.get_nowait())
    return out


async def test_event_builders_match_frozen_frames():
    assert agent_activated_event("q1", "agent_northwind", "Northwind Robotics") == {
        "type": "agent-activated", "query_id": "q1", "agent_id": "agent_northwind",
        "party_name": "Northwind Robotics", "status": "searching",
    }
    item = _items("agent_northwind")[0]
    ev = response_item_event("q1", item)
    assert ev["type"] == "response-item" and ev["query_id"] == "q1"
    assert ev["chunk_id"] == "agent_northwind_c0" and ev["decision"] == "full"
    assert "embedding" not in ev and "text" not in ev


async def test_dispatch_order_and_flat_return():
    reg = FakeRegistry({"asker": "Asker", "p1": "Party 1", "p2": "Party 2"})
    bus = EventBus()

    async def responder(agent_id, query):
        return _items(agent_id)

    router = Router(registry=reg, bus=bus, responder=responder)
    items = await router.dispatch("q1", "asker", "hello")

    frames = _drain(bus, "q1")
    types = [f["type"] for f in frames]
    first_ri = types.index("response-item")
    assert all(t == "agent-activated" for t in types[:first_ri])     # all nodes pulse first
    assert {f["agent_id"] for f in frames if f["type"] == "agent-activated"} == {"p1", "p2"}  # asker excluded
    assert types.count("response-item") == 6                          # 3 items x 2 parties
    assert len(items) == 6


async def test_only_agents_targets_one_party():
    reg = FakeRegistry({"asker": "Asker", "p1": "Party 1", "p2": "Party 2"})
    bus = EventBus()

    async def responder(agent_id, query):
        return _items(agent_id)

    router = Router(registry=reg, bus=bus, responder=responder)
    items = await router.dispatch("q1", "asker", "hi", only_agents=["p1"])
    assert {i["source_agent_id"] for i in items} == {"p1"}
    activated = {f["agent_id"] for f in _drain(bus, "q1") if f["type"] == "agent-activated"}
    assert activated == {"p1"}
