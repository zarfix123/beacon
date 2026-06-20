"""Redaction Claude call: restricted text -> safe one-line gist (redaction.md §2.2).

Responsibility: turn a `restricted` chunk's text into a one-line gist that conveys
THAT a solution exists without leaking it. The raw `chunk["text"]` is read ONLY here;
the returned gist is the only thing that leaves. Includes a deterministic leak-guard
and a static safe fallback (fail-closed on Claude error/refusal/leak). The gate calls
this; it does not own it. This is a SKELETON — no logic.
"""
from __future__ import annotations

from app.models import Chunk

# Static fallback used on Claude failure or a leak-guard rejection (always safe).
SAFE_FALLBACK_GIST: str = (
    "This party has a relevant restricted result. Request access to view it."
)


async def redact(chunk: Chunk) -> str:
    """Return a safe one-line gist for a RESTRICTED chunk. Never returns chunk text.

    Calls Claude (REDACT_MODEL, max_tokens~80). On refusal/error or a leak-guard
    failure, returns a deterministic content-free fallback.
    """
    raise NotImplementedError("redact is a skeleton stub")


def _safe_fallback(chunk: Chunk) -> str:
    """Deterministic content-free gist from owner-published doc_title only."""
    raise NotImplementedError("_safe_fallback is a skeleton stub")


def _passes_leak_guard(gist: str, chunk: Chunk) -> bool:
    """Cheap deterministic backstop: reject if the gist shares a >=6-word verbatim
    run with the restricted text, or is suspiciously long (>240 chars)."""
    raise NotImplementedError("_passes_leak_guard is a skeleton stub")
