"""Tests for app/claude/redaction.py (mock-driven)."""
from __future__ import annotations

import pytest

from app.claude.redaction import SAFE_FALLBACK_GIST, _passes_leak_guard, redact

_CHUNK = {
    "chunk_id": "r1", "parent_doc_id": "d", "doc_title": "Servo Postmortem",
    "owner": "a", "visibility": "restricted",
    "text": "the secret root cause was integral windup clamp the term and add a feedforward path",
}


async def test_clean_gist_passes(patch_claude):
    patch_claude(text="The owner has a documented resolution; request access to view it.")
    gist = await redact(_CHUNK)
    assert gist and "\n" not in gist and len(gist) <= 240
    assert _passes_leak_guard(gist, _CHUNK)


async def test_refusal_falls_back(patch_claude):
    patch_claude(text=None, stop_reason="refusal")
    assert await redact(_CHUNK) == SAFE_FALLBACK_GIST


async def test_api_error_falls_back(patch_claude):
    patch_claude(raises=RuntimeError("network down"))
    assert await redact(_CHUNK) == SAFE_FALLBACK_GIST


async def test_deterministic_with_same_mock(patch_claude):
    patch_claude(text="The owner has a documented resolution; request access to view it.")
    first = await redact(_CHUNK)
    second = await redact(_CHUNK)
    assert first == second


def test_leak_guard_rejects_verbatim_run():
    leaky = "the secret root cause was integral windup clamp the term"   # >=6-word run from source
    assert _passes_leak_guard(leaky, _CHUNK) is False


def test_leak_guard_allows_safe_gist():
    assert _passes_leak_guard("Owner has a documented fix; request access.", _CHUNK) is True


def test_leak_guard_rejects_overlong():
    assert _passes_leak_guard("padding " * 50, _CHUNK) is False   # > 240 chars
