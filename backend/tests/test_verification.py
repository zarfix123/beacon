"""Tests for app/claude/verification.py (mock-driven, fail-closed)."""
from __future__ import annotations

import pytest

from app.claude.verification import verify_answer


async def test_supported_pair_verified_true(patch_claude):
    patch_claude(tool_input={"verified": True, "reason": "supported"})
    vr = await verify_answer("The fix is to clamp the integral term.",
                             "Clamp the integral term to fix it.")
    assert vr.verified is True


async def test_contradicting_pair_verified_false(patch_claude):
    patch_claude(tool_input={"verified": False, "reason": "not supported"})
    vr = await verify_answer("The capital is Mars.", "The fix is to clamp the integral term.")
    assert vr.verified is False


async def test_api_error_fails_closed(patch_claude):
    patch_claude(raises=RuntimeError("network down"))
    assert (await verify_answer("a", "b")).verified is False


async def test_refusal_fails_closed(patch_claude):
    patch_claude(tool_input=None, stop_reason="refusal")
    assert (await verify_answer("a", "b")).verified is False


async def test_missing_field_fails_closed(patch_claude):
    patch_claude(tool_input={"reason": "no verified key present"})
    assert (await verify_answer("a", "b")).verified is False
