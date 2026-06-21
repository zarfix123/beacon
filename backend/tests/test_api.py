"""Integration tests for the API spine (app/main + http + ws + grant_access).

Drives the REAL wiring (lifespan builds the app; the orchestrator/router/responder run)
with Claude mocked and a deterministic fixture registry swapped in for the real corpora.
Exercises the WS-driven transport end-to-end and the grant-access targeted replay.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def client(fixture_registry, patch_claude, monkeypatch):
    # Canned Claude: redaction/synthesis read the text block; verification reads the tool.
    patch_claude(
        text="Servo jitter resolves by clamping the integral term [1].",
        tool_input={"verified": True},
    )
    # main.py did `from app.agents.registry import build_registry`, so patch the name it bound.
    monkeypatch.setattr("app.main.build_registry", lambda *, with_embeddings: fixture_registry)
    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


def _drain_until_done(ws, cap: int = 60) -> list[dict]:
    frames = []
    for _ in range(cap):
        msg = ws.receive_json()
        frames.append(msg)
        if msg.get("type") == "done":
            return frames
    raise AssertionError("no done frame within cap")


def test_post_query_returns_ids(client):
    body = client.post("/query", json={"query": "servo jitter"}).json()
    assert body["query_id"].startswith("q_")
    assert body["from_agent"] == "agent_you"              # settings.default_asker (the "You" node)
    assert set(body["agents"]) == {"fix_a", "fix_b"}       # asker is not a party -> all parties respond


def test_ws_query_streams_full_cycle(client):
    with client.websocket_connect("/ws/query") as ws:
        ws.send_json({"type": "query", "query": "servo jitter"})
        ack = ws.receive_json()
        assert ack["type"] == "ack" and ack["query_id"].startswith("q_")

        frames = _drain_until_done(ws)
        types = [f["type"] for f in frames]
        assert "agent-activated" in types and "response-item" in types
        assert types[-1] == "done"

        # no raw payload ever crosses the wire
        for f in frames:
            assert "text" not in f and "embedding" not in f

        done = frames[-1]
        assert done["synthesized_answer"]
        assert done["item_count"] == sum(1 for t in types if t == "response-item")


def test_grant_access_targeted_replay_flips_card(client):
    with client.websocket_connect("/ws/query") as ws:
        ws.send_json({"type": "query", "query": "servo jitter"})
        ack = ws.receive_json()
        first = _drain_until_done(ws)

        redacted = [f for f in first if f.get("type") == "response-item" and f["decision"] == "redacted"]
        assert redacted, "demo needs a restricted chunk to grant"
        chunk_id = redacted[0]["chunk_id"]

        resp = client.post("/grant_access", json={"chunk_id": chunk_id, "query_id": ack["query_id"]})
        assert resp.status_code == 200
        ack2 = resp.json()
        assert ack2["new_visibility"] == "public" and ack2["rerunning"] is True

        # The targeted replay re-streams on the SAME socket; the granted chunk is now full.
        second = _drain_until_done(ws)
        flipped = [f for f in second if f.get("type") == "response-item" and f["chunk_id"] == chunk_id]
        assert flipped and flipped[0]["decision"] == "full" and flipped[0]["verified"] is True


def test_grant_access_unknown_chunk_404(client):
    # need a real run first so the query_id is known (isolates the chunk 404 from the query 404)
    body = client.post("/query", json={"query": "servo jitter"}).json()
    resp = client.post("/grant_access", json={"chunk_id": "nope", "query_id": body["query_id"]})
    assert resp.status_code == 404


def test_meta_endpoints(client):
    assert client.get("/health").json() == {"status": "ok"}
    agents = client.get("/agents").json()
    # the live client builds the constellation + real party names from this
    assert {a["id"] for a in agents} == {"fix_a", "fix_b"}
    assert all(a["party_name"] for a in agents)
    # /demo/reset is a no-op no-raise when the demo chunks aren't in this (fixture) registry
    assert client.post("/demo/reset").json() == {"reset": {}}
