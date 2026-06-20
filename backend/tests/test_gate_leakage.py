"""Cardinal no-leak test: restricted/private content never crosses the boundary."""
from __future__ import annotations

import pytest

from app.gate.capability import issue_grant
from app.gate.gate import evaluate
from app.models import GateDecision

_RESOLVE = lambda owner: "Northwind Robotics"   # noqa: E731
_GRANT = issue_grant("agent_helios")

_RESTRICTED = {
    "chunk_id": "r1", "parent_doc_id": "d", "doc_title": "Servo Postmortem",
    "owner": "agent_northwind", "visibility": "restricted",
    "text": "the secret root cause was integral windup; clamp the term and add a feedforward path",
    "embedding": [0.1, 0.2, 0.3],
}
_PRIVATE = {
    "chunk_id": "p1", "parent_doc_id": "d", "doc_title": "HR Comp",
    "owner": "agent_northwind", "visibility": "private",
    "text": "internal salary compensation figures, strictly confidential",
    "embedding": [0.4, 0.5],
}
_PUBLIC = {
    "chunk_id": "u1", "parent_doc_id": "d", "doc_title": "Servo Overview",
    "owner": "agent_northwind", "visibility": "public",
    "text": "public servo tuning overview for the docs site",
    "embedding": [0.6],
}


async def _fake_redact(chunk):
    return "The owner has a documented resolution on this topic; request access to view it."


async def test_restricted_answer_carries_no_secret_token():
    gr = await evaluate(_RESTRICTED, query="servo jitter", grant=_GRANT,
                        resolve_party_name=_RESOLVE, redact_fn=_fake_redact)
    assert gr.decision is GateDecision.REDACTED
    assert gr.answer != _RESTRICTED["text"]
    low = (gr.answer or "").lower()
    for token in ("secret", "windup", "feedforward", "clamp"):
        assert token not in low
    w = gr.to_wire()
    assert "text" not in w and "embedding" not in w


async def test_private_denied_has_no_answer():
    gr = await evaluate(_PRIVATE, query="salary", grant=_GRANT,
                        resolve_party_name=_RESOLVE, redact_fn=_fake_redact)
    assert gr.decision is GateDecision.DENIED
    assert gr.answer is None
    w = gr.to_wire()
    assert w["answer"] is None and "text" not in w and "embedding" not in w


async def test_full_wire_has_no_raw_fields():
    gr = await evaluate(_PUBLIC, query="servo", grant=_GRANT,
                        resolve_party_name=_RESOLVE, redact_fn=_fake_redact)
    assert gr.decision is GateDecision.FULL
    assert gr.answer == _PUBLIC["text"]                 # full payload allowed
    w = gr.to_wire()
    assert "text" not in w and "embedding" not in w     # text only as `answer`, never a raw field


async def test_real_redact_leak_guard_forces_fallback(patch_claude):
    # The model tries to echo the restricted source verbatim -> leak-guard rejects -> fallback.
    patch_claude(text=_RESTRICTED["text"])
    from app.claude.redaction import SAFE_FALLBACK_GIST, redact
    gist = await redact(_RESTRICTED)
    assert gist == SAFE_FALLBACK_GIST
    assert "windup" not in gist.lower() and "secret" not in gist.lower()
