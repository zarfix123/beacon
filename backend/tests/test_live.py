"""Live smoke tests — REAL Anthropic API. Run with `-m live` (needs ANTHROPIC_API_KEY / .env)."""
from __future__ import annotations

import os
import pathlib

import pytest

pytestmark = pytest.mark.live

_ENV = pathlib.Path(__file__).resolve().parents[1] / ".env"
_HAS_KEY = bool(os.getenv("ANTHROPIC_API_KEY")) or _ENV.exists()
requires_key = pytest.mark.skipif(not _HAS_KEY, reason="no ANTHROPIC_API_KEY / backend/.env")


@requires_key
async def test_live_redaction_no_leak():
    from app.claude.redaction import redact
    chunk = {
        "chunk_id": "r1", "parent_doc_id": "d", "doc_title": "Servo Jitter Postmortem",
        "owner": "a", "visibility": "restricted",
        "text": ("Root cause was PID integral windup under sustained load; we clamped the "
                 "integral term and added a 5ms feed-forward, which eliminated the oscillation."),
    }
    gist = await redact(chunk)
    assert gist and "\n" not in gist and len(gist) <= 240
    low = gist.lower()
    for token in ("windup", "feed-forward", "5ms", "clamped"):
        assert token not in low, f"leaked token: {token}"


@requires_key
async def test_live_verification_true_and_false():
    from app.claude.verification import verify_answer
    source = "The capital of France is Paris. The Eiffel Tower stands in Paris."
    good = await verify_answer("The capital of France is Paris.", source)
    bad = await verify_answer("The capital of France is Berlin.", source)
    assert good.verified is True
    assert bad.verified is False
