"""Redaction Claude call: restricted text -> safe one-line gist (redaction.md §2.2).

The raw `chunk["text"]` is read ONLY here; the returned gist is the only thing that
leaves. A deterministic leak-guard + a static content-free fallback make the no-leak
guarantee hold even on a misbehaving model. The gate calls this; it does not own it.
"""
from __future__ import annotations

import re

from app.claude.client import REDACT_MODEL, complete_text
from app.claude.prompts import REDACTION_SYSTEM, redaction_user
from app.models import Chunk

# Static fallback used on Claude failure or a leak-guard rejection (always safe).
SAFE_FALLBACK_GIST: str = (
    "This party has a relevant restricted result. Request access to view it."
)

_MAX_GIST_CHARS = 240
_LEAK_RUN = 6                 # reject a gist sharing a >=6-word verbatim run with source
_WORD_RE = re.compile(r"\w+")


async def redact(chunk: Chunk) -> str:
    """Return a safe one-line gist for a RESTRICTED chunk. Never returns chunk text.

    Calls Claude (REDACT_MODEL, max_tokens~80). On refusal/error or a leak-guard
    failure, returns a deterministic content-free fallback.
    """
    try:
        gist = await complete_text(
            model=REDACT_MODEL,
            system=REDACTION_SYSTEM,
            user=redaction_user(doc_title=chunk["doc_title"], chunk_text=chunk["text"]),
            max_tokens=80,
        )
    except Exception:               # API/network error -> never crash the response
        return _safe_fallback(chunk)
    if gist is None:                # refusal / empty
        return _safe_fallback(chunk)
    gist = " ".join(gist.split()).strip()          # collapse to a single clean line
    if not gist or not _passes_leak_guard(gist, chunk):
        return _safe_fallback(chunk)
    return gist


def _safe_fallback(chunk: Chunk) -> str:
    """Deterministic, content-free gist (carries none of the restricted text). The
    owner-published doc_title still rides along separately as the card's citation."""
    return SAFE_FALLBACK_GIST


def _passes_leak_guard(gist: str, chunk: Chunk) -> bool:
    """Reject if the gist is suspiciously long (>240 chars) or shares a >=6-word
    verbatim run with the restricted text."""
    if len(gist) > _MAX_GIST_CHARS:
        return False
    gist_words = _WORD_RE.findall(gist.lower())
    src_words = _WORD_RE.findall(chunk["text"].lower())
    if len(gist_words) < _LEAK_RUN or len(src_words) < _LEAK_RUN:
        return True
    src_runs = {
        tuple(src_words[i:i + _LEAK_RUN]) for i in range(len(src_words) - _LEAK_RUN + 1)
    }
    return not any(
        tuple(gist_words[i:i + _LEAK_RUN]) in src_runs
        for i in range(len(gist_words) - _LEAK_RUN + 1)
    )
