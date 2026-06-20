"""Gate orchestration: the single entry point evaluate() (permission-gate.md §2.5).

Ties policy + capability + redaction into the one entry the responding agent calls per
chunk. Honors retrieve-first-gate-second: receives an already-retrieved chunk dict and
constructs a content-free GatedResult. Never returns chunk["text"] for non-FULL
decisions; never returns chunk["embedding"]. Redaction is delegated to
app.claude.redaction (injected as redact_fn so policy/leakage tests need no Claude).
"""
from __future__ import annotations

from typing import Awaitable, Callable, Protocol

from app.claude.redaction import redact as _default_redact
from app.gate import policy
from app.gate.capability import CapabilityGrant, allows
from app.models import Chunk, GateDecision, GatedResult


class PartyNameResolver(Protocol):
    """Injected lookup: Agent.id -> party_name. Owned by the agents subsystem; kept
    as a Protocol so the gate has no hard import of the agent registry."""

    def __call__(self, agent_id: str) -> str: ...


class GateError(Exception):
    """Raised on an unrecognized tier or a malformed chunk. Fail-closed."""


RedactFn = Callable[[Chunk], Awaitable[str]]


async def evaluate(
    chunk: dict,
    *,
    query: str,
    grant: CapabilityGrant,
    resolve_party_name: PartyNameResolver,
    redact_fn: RedactFn = _default_redact,
) -> GatedResult:
    """Gate ONE retrieved chunk into a boundary-safe GatedResult.

    1) decision = policy.decide(chunk["visibility"]) (GateError on unknown tier);
    2) if not allows(grant, decision): decision = DENIED (capability down-rank);
    3) build the GatedResult per decision — FULL keeps chunk["text"]; REDACTED gets the
       gist from redact_fn (the raw text is read only inside redaction, never returned);
       DENIED gets answer=None; 4) verified defaults False (the verify pass flips it for
       FULL items afterward). The raw text/embedding are never copied onto a non-FULL
       result, and GatedResult has no field for them — leakage is structural.
    """
    decision = policy.decide(chunk["visibility"])
    if not allows(grant, decision):
        decision = GateDecision.DENIED

    common = dict(
        decision=decision,
        source_party=resolve_party_name(chunk["owner"]),
        chunk_id=chunk["chunk_id"],
        source_agent_id=chunk["owner"],
        verified=False,
    )

    if decision is GateDecision.FULL:
        return GatedResult(
            answer=chunk["text"],
            source_doc_title=chunk["doc_title"],
            access_requestable=False,
            **common,
        )
    if decision is GateDecision.REDACTED:
        gist = await redact_fn(chunk)                 # raw text consumed inside; only gist returns
        return GatedResult(
            answer=gist,
            source_doc_title=chunk["doc_title"],
            access_requestable=True,
            **common,
        )
    # DENIED — answer hidden; title shown only if policy allows existence-only.
    return GatedResult(
        answer=None,
        source_doc_title=(chunk["doc_title"] if policy.SHOW_EXISTENCE_FOR_PRIVATE else None),
        access_requestable=False,
        **common,
    )
