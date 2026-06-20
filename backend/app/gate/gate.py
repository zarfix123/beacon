"""Gate orchestration: the single entry point evaluate() (permission-gate.md §2.5).

Responsibility: tie policy + capability + redaction into the one entry the responding
agent calls per chunk. Honors retrieve-first-gate-second: receives an already-retrieved
chunk dict and constructs a content-free GatedResult. Never returns chunk["text"] for
non-FULL decisions; never returns chunk["embedding"]. The redaction call is delegated
to app/claude/redaction.py (BUILD_INDEX.md §2.1). This is a SKELETON — no logic.
"""
from __future__ import annotations

from typing import Protocol

from app.gate.capability import CapabilityGrant
from app.models import GatedResult


class PartyNameResolver(Protocol):
    """Injected lookup: Agent.id -> party_name. Owned by the agents subsystem; kept
    as a Protocol so the gate has no hard import of the agent registry."""

    def __call__(self, agent_id: str) -> str: ...


class GateError(Exception):
    """Raised on an unrecognized tier or a malformed chunk. Fail-closed."""


def evaluate(
    chunk: dict,
    *,
    query: str,
    grant: CapabilityGrant,
    resolve_party_name: PartyNameResolver,
) -> GatedResult:
    """Gate ONE retrieved chunk into a boundary-safe GatedResult.

    Steps (spec §9): 1) decision = policy.decide(chunk["visibility"]); 2) if not
    allows(grant, decision): decision = DENIED (capability down-rank); 3) build the
    GatedResult per decision — FULL keeps chunk["text"]; REDACTED gets the Claude
    gist via app.claude.redaction (text stays); DENIED gets answer=None; 4) verified
    defaults False (orchestrator flips it for FULL after the verify pass).
    """
    raise NotImplementedError("gate.evaluate is a skeleton stub")
