"""Integration: the per-party responder pipeline (search -> gate -> verify), Claude mocked."""
from __future__ import annotations

import pytest

from app.router import responder


async def test_responder_full_pipeline(fixture_registry, patch_claude):
    # One fake client serves both redaction (text block) and verification (tool_use block).
    patch_claude(
        text="The owner has a documented resolution; request access to view it.",
        tool_input={"verified": True},
    )
    responder.set_registry(fixture_registry)

    items = await responder.respond_for_agent("fix_a", "servo resolution salary data")
    by_decision = {i["decision"]: i for i in items}

    # query overlaps all three fix_a chunks (public servo / restricted servo-resolution / private salary)
    assert {"full", "redacted", "denied"} <= set(by_decision)

    full = by_decision["full"]
    assert full["verified"] is True and full["answer"]

    red = by_decision["redacted"]
    assert red["verified"] is False
    low = (red["answer"] or "").lower()
    assert "secret" not in low and "postmortem" not in low

    den = by_decision["denied"]
    assert den["answer"] is None and den["verified"] is False

    # isolation + no raw fields anywhere on the wire
    assert all(i["source_agent_id"] == "fix_a" for i in items)
    assert all("text" not in i and "embedding" not in i for i in items)


async def test_responder_requires_registry(monkeypatch):
    monkeypatch.setattr(responder, "_REGISTRY", None)
    with pytest.raises(RuntimeError):
        await responder.respond_for_agent("fix_a", "anything")
