"""Outbound MCP server (scripts/mcp_beacon_server.py): formatting + a mocked query run.

The server reuses the orchestrator verbatim, so these tests focus on its OWN surface: the
`_format` markdown (restricted = exists-but-locked, no content) and `run_query` end-to-end
over a FakeRouter + stubbed synthesis (no real corpora, no Claude key). Importing the module
must be side-effect-free (env/logging are applied only in main()).
"""
from __future__ import annotations

import types

import pytest

from app.orchestrator.orchestrator import Orchestrator
from app.run_registry import RunRegistry
from scripts import mcp_beacon_server as srv


def _it(party, decision, *, verified=True, title="T", answer="content", aid=None, cid=None):
    return {
        "answer": (None if decision == "denied" else answer),
        "source_party": party,
        "source_doc_title": (None if decision == "denied" else title),
        "decision": decision,
        "verified": verified,
        "chunk_id": cid or f"{party}_c",
        "source_agent_id": aid or party,
    }


class FakeRouter:
    """Returns canned gated items; mirrors the real Router's dispatch signature."""
    def __init__(self, items):
        self._items = items

    async def dispatch(self, query_id, from_agent, query, *, only_agents=None):
        return self._items


# --------------------------------------------------------------------------- #
# _format — the server's own rendering                                        #
# --------------------------------------------------------------------------- #

def test_format_restricted_is_locked_with_no_content():
    done = {
        "synthesized_answer": "The limit is 60 req/min [1].",
        "provenance": [
            {"source_party": "Northwind Robotics", "source_doc_title": "RetryPolicy.md",
             "decision": "full", "verified": True},
            {"source_party": "Quanta Systems", "source_doc_title": "throttle.yaml",
             "decision": "redacted", "verified": False},
        ],
    }
    items = [
        _it("Northwind Robotics", "full", title="RetryPolicy.md"),
        _it("Quanta Systems", "redacted", verified=False, title="throttle.yaml",
            answer="SECRET GIST MUST NOT APPEAR"),
    ]
    out = srv._format(done, items)

    assert "The limit is 60 req/min [1]." in out
    # restricted shows as exists-but-locked + request access, with provenance but NO content
    assert "🔒 restricted" in out
    assert "request access" in out
    assert "throttle.yaml" in out
    assert "SECRET GIST MUST NOT APPEAR" not in out
    # full item rendered with its title
    assert "✅ full — RetryPolicy.md" in out
    # sources section maps the citation indices
    assert "[1] Northwind Robotics — RetryPolicy.md" in out


def test_format_denied_shows_no_title_no_content():
    items = [_it("Quanta Systems", "denied", verified=False)]
    out = srv._format({"synthesized_answer": "A.", "provenance": []}, items)
    assert "⛔ denied" in out
    assert "Quanta Systems: ⛔ denied" in out


def test_format_no_answer_fallback():
    out = srv._format(None, [])
    assert "No party returned a verified answer" in out
    assert "(no party returned a result)" in out


def test_strip_flag():
    assert srv._strip_flag("/beacon who changed the rate limit?") == "who changed the rate limit?"
    assert srv._strip_flag("  /BEACON   spaced  ") == "spaced"
    assert srv._strip_flag("no flag here") == "no flag here"       # left untouched
    assert srv._strip_flag("/beacon") == ""


# --------------------------------------------------------------------------- #
# run_query — end-to-end over the real orchestrator (FakeRouter + stub synth)  #
# --------------------------------------------------------------------------- #

async def test_run_query_end_to_end(monkeypatch):
    async def fake_synth(query, items, redacted, on_delta=None):
        return "ANSWER [1]"
    monkeypatch.setattr("app.orchestrator.orchestrator.synthesize", fake_synth)

    settings = types.SimpleNamespace(default_asker="agent_you", top_k=2, beacon_search="hybrid")
    run_registry = RunRegistry()
    done_events: dict[str, dict] = {}

    async def emit(event):
        if event.get("type") == "done":
            done_events[event["query_id"]] = event

    items = [
        _it("Northwind Robotics", "full", title="RetryPolicy.md"),
        _it("Quanta Systems", "redacted", verified=False, title="throttle.yaml",
            answer="LOCKED GIST"),
        _it("Northwind Robotics", "denied", verified=False),
    ]
    orch = Orchestrator(registry=None, router=FakeRouter(items), emit=emit,
                        run_registry=run_registry, top_k=2)

    out = await srv.run_query(settings, orch, run_registry, done_events, "who changed the rate limit?")

    assert "ANSWER [1]" in out                       # synthesized answer surfaced
    assert "✅ full — RetryPolicy.md" in out         # full party
    assert "🔒 restricted" in out and "request access" in out  # restricted = locked
    assert "LOCKED GIST" not in out                  # no restricted content
    assert "⛔ denied" in out                         # denied party listed
