"""Tests for app/provenance/ (pointer + assembler)."""
from __future__ import annotations

import pytest

from app.models import GateDecision, GatedResult, VerifyResult
from app.provenance.assembler import build_response_item
from app.provenance.pointer import assemble_provenance


def _gated(decision, answer, *, verified=False, title="T", car=False):
    return GatedResult(decision=decision, answer=answer, source_party="Party",
                       source_doc_title=title, verified=verified, chunk_id="c1",
                       source_agent_id="agent_a", access_requestable=car)


def test_assemble_never_reads_text_or_embedding():
    # chunk WITHOUT text/embedding keys -> must not KeyError
    chunk = {"chunk_id": "c1", "owner": "agent_a", "doc_title": "Title"}
    p = assemble_provenance(chunk, resolve_party_name=lambda o: "Party A")
    assert p.source_party == "Party A"
    assert p.source_doc_title == "Title"
    assert p.owner == "agent_a"


def test_payload_hidden_suppresses_title():
    chunk = {"chunk_id": "c1", "owner": "a", "doc_title": "Secret Title"}
    p = assemble_provenance(chunk, payload_hidden=True)
    assert p.source_doc_title is None


async def test_build_response_item_verifies_only_full():
    calls = []

    async def spy_verify(answer, source):
        calls.append((answer, source))
        return VerifyResult(verified=True)

    chunk = {"chunk_id": "c1", "owner": "agent_a", "doc_title": "T", "text": "the source text"}

    full = _gated(GateDecision.FULL, "the source text")
    item = await build_response_item(chunk, full, verify_fn=spy_verify)
    assert item["verified"] is True
    assert len(calls) == 1 and calls[0] == ("the source text", "the source text")

    redacted = _gated(GateDecision.REDACTED, "a gist", car=True)
    item2 = await build_response_item(chunk, redacted, verify_fn=spy_verify)
    assert item2["verified"] is False
    assert len(calls) == 1   # NOT called for redacted

    denied = _gated(GateDecision.DENIED, None, title=None)
    item3 = await build_response_item(chunk, denied, verify_fn=spy_verify)
    assert item3["verified"] is False
    assert len(calls) == 1   # NOT called for denied


def test_wire_has_exactly_seven_keys_no_internals():
    w = _gated(GateDecision.DENIED, None, title=None).to_wire()
    assert set(w) == {"answer", "source_party", "source_doc_title", "decision",
                      "verified", "chunk_id", "source_agent_id"}
    assert "timestamp" not in w and "reason" not in w and "access_requestable" not in w
