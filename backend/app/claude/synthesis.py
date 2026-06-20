"""Synthesis Claude call: final cited answer (orchestrator.md §3.1, BUILD_INDEX §2.1).

Responsibility: compose the user-facing `done.synthesized_answer` from verified-full
items with inline [Party] citations; surface restricted items as existence-only
access asks WITHOUT inventing their content (leakage guard). Empty-input guard returns
a graceful string with no Claude call. This is a SKELETON — no logic.
"""
from __future__ import annotations

from app.models import ResponseItem


async def synthesize(
    query: str,
    items: list[ResponseItem],       # verified == True, decision == full
    redacted: list[ResponseItem],    # restricted gists, surfaced as access asks
) -> str:
    """Compose the final cited answer from verified full items (SYNTH_MODEL,
    max_tokens~300). Redacted items appear as existence-only. Empty-input guard
    returns 'No party returned a verified answer to this question.'"""
    raise NotImplementedError("synthesize is a skeleton stub")
