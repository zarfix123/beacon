"""Finalize a GatedResult into the wire ResponseItem (provenance-verification.md §2.4).

Single job: verify FULL items (delegates to app.claude.verification.verify_answer) and
serialize. `redacted`/`denied` stay verified=False. Does NOT redact (the gate already
did) and never re-reads visibility — the no-leak invariant is structural: a non-FULL
GatedResult carries no raw text to begin with.

Reconciliation note: takes the gate's GatedResult (not a bare `decision: str`) so the
raw text is never in this function's hands for non-FULL items.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Awaitable, Callable

from app.claude.verification import verify_answer as _default_verify
from app.models import GateDecision, GatedResult, ResponseItem, VerifyResult

VerifyFn = Callable[[str, str], Awaitable[VerifyResult]]


async def build_response_item(
    chunk: dict,
    gated: GatedResult,
    *,
    verify_fn: VerifyFn = _default_verify,
) -> ResponseItem:
    """Turn one gated chunk into the canonical Response item.

    full -> verify the answer against its source (chunk text), set verified;
    redacted/denied -> unchanged (verified stays False). Returns the 7-key wire dict.
    """
    if gated.decision is GateDecision.FULL and gated.answer is not None:
        result = await verify_fn(gated.answer, chunk["text"])
        gated = replace(gated, verified=result.verified)
    return gated.to_wire()
