"""Synthesis Claude call: final cited answer (orchestrator.md §3.1, BUILD_INDEX §2.1).

Composes the user-facing `done.synthesized_answer` from verified-full items with inline
[n] citations, and surfaces restricted items as existence-only access asks WITHOUT
inventing their content (leakage guard: the prompt carries party + doc only for those).
Empty-input guard returns a graceful string with no Claude call; any refusal/error
fails SOFT to a deterministic string so the orchestrator's `done` event always emits.
"""
from __future__ import annotations

from typing import Awaitable, Callable, Optional

from app.claude.client import SYNTH_MODEL, complete_text, stream_text
from app.claude.prompts import SYNTHESIS_SYSTEM, synthesis_user
from app.models import ResponseItem

_EMPTY = "No party returned a verified answer to this question."


def _party_list(*groups: list[ResponseItem]) -> str:
    """Distinct party names across the given item groups, in first-seen order."""
    seen: list[str] = []
    for group in groups:
        for item in group:
            name = item.get("source_party")
            if name and name not in seen:
                seen.append(name)
    return ", ".join(seen) if seen else "the network"


async def synthesize(
    query: str,
    items: list[ResponseItem],       # verified == True, decision == full
    redacted: list[ResponseItem],    # restricted gists, surfaced as access asks
    on_delta: Optional[Callable[[str], Awaitable[None]]] = None,
) -> str:
    """Compose the final cited answer from verified full items (SYNTH_MODEL,
    max_tokens~512). Redacted items appear as existence-only. Empty-input guard
    returns a graceful string; refusal/error -> deterministic fallback.

    When `on_delta` is given, the answer STREAMS: each text delta is forwarded to on_delta
    as it generates (the orchestrator turns those into answer-delta WS events), and the full
    text is still returned. Without it, a single non-streaming call (used by tests)."""
    if not items and not redacted:
        return _EMPTY

    verified_facts = [
        {"source_party": i["source_party"], "source_doc_title": i.get("source_doc_title"),
         "answer": i.get("answer")}
        for i in items
    ]
    redacted_facts = [
        {"source_party": i["source_party"], "source_doc_title": i.get("source_doc_title")}
        for i in redacted
    ]
    user = synthesis_user(query=query, verified_facts=verified_facts, redacted=redacted_facts)

    try:
        if on_delta is not None:
            text = await stream_text(model=SYNTH_MODEL, system=SYNTHESIS_SYSTEM, user=user,
                                     on_delta=on_delta, max_tokens=512)
        else:
            text = await complete_text(model=SYNTH_MODEL, system=SYNTHESIS_SYSTEM, user=user,
                                       max_tokens=512)
    except Exception:
        text = None

    if text and text.strip():
        return text.strip()

    # Fail-soft: never block the `done` event on a refusal/empty/error.
    return (
        f"A verified answer could not be composed automatically; relevant sources were "
        f"returned by {_party_list(items, redacted)} (see the cited sources)."
    )
