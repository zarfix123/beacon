"""Tests for app/gate/policy.py + capability + the gate down-rank (Phase 2)."""
from __future__ import annotations

import pytest

from app.gate.capability import Capability, CapabilityGrant, allows, issue_grant
from app.gate.gate import GateError, evaluate
from app.gate.policy import decide
from app.models import GateDecision


def test_tiers_map_correctly():
    assert decide("public") is GateDecision.FULL
    assert decide("restricted") is GateDecision.REDACTED
    assert decide("private") is GateDecision.DENIED


def test_unknown_tier_fails_closed():
    with pytest.raises(GateError):
        decide("totally-bogus-tier")


def test_issue_grant_never_private():
    g = issue_grant("agent_helios")
    assert not (g.capabilities & Capability.PRIVATE_READ)
    assert allows(g, GateDecision.FULL)
    assert allows(g, GateDecision.REDACTED)
    assert allows(g, GateDecision.DENIED)


def test_missing_capability_blocks_payload_tiers():
    g = CapabilityGrant("x", Capability.NONE)
    assert allows(g, GateDecision.FULL) is False
    assert allows(g, GateDecision.REDACTED) is False
    assert allows(g, GateDecision.DENIED) is True   # denied carries no payload


async def test_gate_downranks_full_without_capability():
    chunk = {"chunk_id": "c1", "parent_doc_id": "d", "doc_title": "T",
             "owner": "a", "visibility": "public", "text": "public body"}
    gr = await evaluate(chunk, query="q", grant=CapabilityGrant("x", Capability.NONE),
                        resolve_party_name=lambda o: "Party")
    assert gr.decision is GateDecision.DENIED   # public, but no PUBLIC_READ -> down-ranked
    assert gr.answer is None
