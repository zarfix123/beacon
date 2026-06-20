"""Verification Claude call: grounding check (provenance-verification.md §2.3).

Given an answer that crossed the boundary and its cited source, decide whether the
answer is grounded in that source -> VerifyResult(verified=bool). Called ONLY for full
items. Fail-closed: any API error / refusal / parse failure -> verified=False (surface
unverifiable, never a false checkmark).

Structured output uses FORCED TOOL USE (anthropic 0.64.0 has no messages.parse).
"""
from __future__ import annotations

from app.claude.client import VERIFY_MODEL, call_tool
from app.claude.prompts import VERIFICATION_SYSTEM, verification_user
from app.models import VerifyResult

# The structured-output schema the model is forced to fill (single tool).
_VERIFY_TOOL: dict = {
    "name": "record_verification",
    "description": "Record whether the ANSWER is fully supported by the SOURCE.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "verified": {
                "type": "boolean",
                "description": "true iff every claim in the answer is supported by the source",
            },
            "reason": {"type": "string", "description": "one short clause; internal only"},
        },
        "required": ["verified"],
    },
}


async def verify_answer(answer: str, source_text: str) -> VerifyResult:
    """Ask Claude whether `answer` is supported by `source_text`. Fail-closed."""
    try:
        out = await call_tool(
            model=VERIFY_MODEL,
            system=VERIFICATION_SYSTEM,
            user=verification_user(answer=answer, source_text=source_text),
            tool=_VERIFY_TOOL,
            max_tokens=128,
        )
    except Exception as exc:  # any API/network error -> unverifiable, never a false ✓
        return VerifyResult(verified=False, reason=f"verify_error:{type(exc).__name__}")
    if out is None or "verified" not in out:
        return VerifyResult(verified=False, reason="refused_or_parse_failed")
    return VerifyResult(verified=bool(out["verified"]), reason=out.get("reason"))
