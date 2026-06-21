"""MCP federation: faithfulness across the boundary + dispatcher routing/fallback (Phase 5).

Mock-first (no live server): the MCP server's `respond` tool is literally
`json.dumps(await respond_for_agent(agent_id, query))`, so we exercise that exact
serialization against the deterministic `fixture_registry` and prove no raw restricted text
crosses. The client `_coerce_items` is the second structural guard. The dispatcher tests prove
MCP→local fallback and the transport tagging that drives the federation badge. A live
round-trip is covered separately by the smoke path in run.sh / manual verification.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from app.mcp import client
from app.mcp.client import (
    _WIRE_KEYS,
    _coerce_items,
    make_dispatch_responder,
    make_mcp_responder,
)
from app.router import responder


# --------------------------------------------------------------------------- #
# fakes                                                                        #
# --------------------------------------------------------------------------- #

class _FakeTextBlock:
    """Mimics an MCP TextContent block (FastMCP returns a str tool result as one of these)."""
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeToolResult:
    def __init__(self, text: str) -> None:
        self.content = [_FakeTextBlock(text)]


class _FakeSession:
    """Stand-in for an MCP ClientSession: call_tool returns canned JSON, sleeps, or raises."""
    def __init__(self, *, payload=None, sleep: float | None = None, raises: Exception | None = None):
        self._payload = payload
        self._sleep = sleep
        self._raises = raises

    async def call_tool(self, name: str, arguments: dict):
        assert name == "respond" and "query" in arguments
        if self._raises is not None:
            raise self._raises
        if self._sleep is not None:
            await asyncio.sleep(self._sleep)
        return _FakeToolResult(json.dumps(self._payload))


def _item(**overrides) -> dict:
    """A canonical 7-key gated item; override any field."""
    base = {
        "answer": "an answer",
        "source_party": "Helios Dynamics",
        "source_doc_title": "observability/checkout-429-dashboard.md",
        "decision": "full",
        "verified": True,
        "chunk_id": "helios_demo_dashboard",
        "source_agent_id": "agent_helios",
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# faithfulness — the cardinal test: no raw restricted text crosses the MCP boundary
# --------------------------------------------------------------------------- #

async def test_faithfulness_no_raw_restricted_text_in_mcp_payload(fixture_registry, patch_claude):
    """The server serializes `respond_for_agent(...)`; the restricted chunk's distinctive
    tokens (and the private chunk's) must NOT appear in the JSON that crosses the wire."""
    patch_claude(
        text="Access-controlled material; request access to view the details.",
        tool_input={"verified": True},
    )
    responder.set_registry(fixture_registry)

    # EXACTLY what scripts/mcp_party.respond() puts on the wire:
    items = await responder.respond_for_agent("fix_a", "servo resolution secret salary postmortem")
    payload = json.dumps(items)
    low = payload.lower()

    # The no-leak invariant covers the raw chunk TEXT BODY. Distinctive body-only tokens:
    #   restricted text "servo resolution secret postmortem details" -> "secret", "details"
    #   private   text "internal salary compensation data"          -> "salary", "compensation"
    # (The doc *title*, e.g. "Servo Postmortem", is provenance and legitimately crosses — it's
    # the handle the user clicks to "request access" — so it is NOT a leak.)
    assert "secret" not in low
    assert "salary" not in low and "compensation" not in low
    # the no-leak invariant is structural: text/embedding keys never serialize.
    assert '"text"' not in payload and '"embedding"' not in payload

    by_decision = {i["decision"]: i for i in items}
    assert {"full", "redacted", "denied"} <= set(by_decision)
    red = by_decision["redacted"]
    assert red["answer"] and "secret" not in red["answer"].lower()
    # provenance still crosses for the redacted item (so "request access" has a target).
    assert red["source_doc_title"] == "Servo Postmortem"
    assert by_decision["denied"]["answer"] is None


# --------------------------------------------------------------------------- #
# client edge — _coerce_items is the second structural guard                   #
# --------------------------------------------------------------------------- #

def test_coerce_items_strips_non_wire_keys():
    """Even a misbehaving server cannot smuggle text/embedding/extra keys across — the client
    keeps ONLY the 7 canonical wire keys."""
    raw = [{**_item(), "text": "RAW RESTRICTED SECRET", "embedding": [0.1, 0.2], "evil": True}]
    out = _coerce_items(raw)
    assert len(out) == 1
    assert set(out[0].keys()) == set(_WIRE_KEYS)
    assert "text" not in out[0] and "embedding" not in out[0] and "evil" not in out[0]


def test_coerce_items_rejects_non_list():
    assert _coerce_items({"not": "a list"}) == []
    assert _coerce_items("garbage") == []


# --------------------------------------------------------------------------- #
# make_mcp_responder — reads the tool result + enforces the timeout            #
# --------------------------------------------------------------------------- #

async def test_mcp_responder_parses_and_coerces_tool_result():
    # server returns a leaky item; the responder must coerce it to clean 7-key shape.
    session = _FakeSession(payload=[{**_item(), "text": "RAW", "embedding": [1.0]}])
    resp = make_mcp_responder(session, "agent_helios")
    items = await resp("agent_helios", "anything")
    assert len(items) == 1
    assert items[0]["chunk_id"] == "helios_demo_dashboard"
    assert "text" not in items[0] and "embedding" not in items[0]


async def test_mcp_responder_empty_payload():
    session = _FakeSession(payload=[])
    resp = make_mcp_responder(session, "agent_helios")
    assert await resp("agent_helios", "q") == []


async def test_mcp_responder_times_out_on_hang(monkeypatch):
    """A hang (server alive but stalled) must raise via the timeout — never block forever."""
    monkeypatch.setattr(client, "MCP_TIMEOUT", 0.05)
    session = _FakeSession(payload=[_item()], sleep=0.5)
    resp = make_mcp_responder(session, "agent_helios")
    with pytest.raises((asyncio.TimeoutError, TimeoutError)):
        await resp("agent_helios", "q")


# --------------------------------------------------------------------------- #
# make_dispatch_responder — routing, fallback, and transport tagging          #
# --------------------------------------------------------------------------- #

async def test_dispatcher_routes_mcp_vs_local_and_tags_transport():
    async def local(aid, q):
        return [_item(source_agent_id=aid, answer="from-local")]

    async def mcp_resp(aid, q):
        return [_item(source_agent_id=aid, answer="from-mcp")]

    dispatch = make_dispatch_responder(local, {"agent_helios": mcp_resp})

    mcp_items = await dispatch("agent_helios", "q")
    assert mcp_items[0]["answer"] == "from-mcp"
    assert mcp_items[0]["transport"] == "mcp"

    local_items = await dispatch("agent_quanta", "q")          # not in the mcp map
    assert local_items[0]["answer"] == "from-local"
    assert local_items[0]["transport"] == "local"


async def test_dispatcher_falls_back_to_local_on_mcp_error():
    """ANY MCP failure for a configured party → serve it locally, tagged 'fallback'."""
    calls = {"local": 0}

    async def local(aid, q):
        calls["local"] += 1
        return [_item(source_agent_id=aid, answer="from-local")]

    async def boom(aid, q):
        raise RuntimeError("mcp server down")

    dispatch = make_dispatch_responder(local, {"agent_helios": boom})
    items = await dispatch("agent_helios", "q")
    assert items[0]["answer"] == "from-local"
    assert items[0]["transport"] == "fallback"
    assert calls["local"] == 1


async def test_dispatcher_falls_back_on_timeout(monkeypatch):
    """A hang surfaces as a TimeoutError inside the MCP responder → dispatcher falls back."""
    monkeypatch.setattr(client, "MCP_TIMEOUT", 0.05)

    async def local(aid, q):
        return [_item(source_agent_id=aid, answer="from-local")]

    mcp_resp = make_mcp_responder(_FakeSession(payload=[_item()], sleep=0.5), "agent_helios")
    dispatch = make_dispatch_responder(local, {"agent_helios": mcp_resp})
    items = await dispatch("agent_helios", "q")
    assert items[0]["transport"] == "fallback" and items[0]["answer"] == "from-local"


# --------------------------------------------------------------------------- #
# shape parity — MCP-returned items are the exact shape the orchestrator consumes
# --------------------------------------------------------------------------- #

async def test_shape_parity_with_orchestrator_consumers():
    session = _FakeSession(payload=[_item(decision="redacted", verified=False, answer="gist")])
    resp = make_mcp_responder(session, "agent_helios")
    [it] = await resp("agent_helios", "q")

    # every key the router (response_item_event) + orchestrator (verified/decision filters,
    # provenance) read off an item is present.
    for key in _WIRE_KEYS:
        assert key in it

    from app.orchestrator.orchestrator import _provenance_entry
    from app.router.events import response_item_event

    prov = _provenance_entry(it)                # builds the 6-key provenance entry cleanly
    assert prov["decision"] == "redacted" and prov["source_agent_id"] == "agent_helios"

    frame = response_item_event("q1", it)       # serializes into the frozen response-item frame
    assert frame["type"] == "response-item" and frame["chunk_id"] == "helios_demo_dashboard"
