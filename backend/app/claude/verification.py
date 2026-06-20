"""Verification Claude call: grounding check (provenance-verification.md §2.3).

Responsibility: given an answer that crossed the boundary (decision == "full") and
the source it cites, decide whether the answer is grounded in that source. Output a
VerifyResult(verified=bool). Called ONLY for full items. Fail-closed: any API error
or parse failure -> verified=False (surface unverifiable, never a false checkmark).
This is a SKELETON — no logic.
"""
from __future__ import annotations

from app.models import VerifyResult


async def verify_answer(answer: str, source_text: str) -> VerifyResult:
    """Ask Claude whether `answer` is supported by `source_text`.

    Uses structured output (messages.parse), VERIFY_MODEL, max_tokens=128, frozen
    cached system block. On any exception, returns VerifyResult(verified=False).
    """
    raise NotImplementedError("verify_answer is a skeleton stub")
