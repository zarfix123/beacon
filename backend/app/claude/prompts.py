"""Frozen, byte-stable system/user prompt templates (cache-friendly).

Responsibility (BUILD_INDEX.md §2.1): one place to hold the frozen prompt templates
for redaction, verification, and synthesis. Kept byte-stable (no timestamps/ids) so
the Anthropic prompt cache keys on the system prefix. This is a SKELETON — templates
are placeholders to be tuned against the locked demo query.
"""
from __future__ import annotations

# ---- Redaction (redaction.md §3) --------------------------------------------
# System prompt: produce a one-line gist that signals a solution EXISTS without
# leaking any specifics. TODO: finalize against the seeded restricted servo chunk.
REDACTION_SYSTEM: str = (
    "TODO: frozen redaction system prompt — one safe sentence, no specifics, "
    "invite an access request (see backend/docs/redaction.md §3)."
)


def redaction_user(*, doc_title: str, chunk_text: str, query: str) -> str:
    """Build the per-call redaction user message. SKELETON — no logic."""
    raise NotImplementedError("redaction_user is a skeleton stub")


# ---- Verification (provenance-verification.md §3) ---------------------------
VERIFICATION_SYSTEM: str = (
    "TODO: frozen grounding-verifier system prompt — judge ONLY against SOURCE, "
    "verified=true iff fully supported (see backend/docs/provenance-verification.md §3)."
)


def verification_user(*, answer: str, source_text: str) -> str:
    """Build the per-call verification user message (delimited tags). SKELETON."""
    raise NotImplementedError("verification_user is a skeleton stub")


# ---- Synthesis (orchestrator.md §3.1) ---------------------------------------
SYNTHESIS_SYSTEM: str = (
    "TODO: frozen synthesis system prompt — answer from VERIFIED FACTS only, inline "
    "[Party] citations, restricted items as existence-only (see backend/docs/orchestrator.md §3.1)."
)


def synthesis_user(*, query: str, verified_facts: list[dict], redacted: list[dict]) -> str:
    """Build the per-call synthesis user message. Must contain NO restricted
    payloads (leakage guard). SKELETON — no logic."""
    raise NotImplementedError("synthesis_user is a skeleton stub")
