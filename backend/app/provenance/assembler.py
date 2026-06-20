"""build_response_item: gate verdict + chunk -> ResponseItem (provenance-verification.md §2.4).

Responsibility: turn one gated chunk into the canonical ResponseItem. Verifies ONLY
`full` items (delegates to app.claude.verification.verify_answer); `redacted`/`denied`
stay verified=False. Delegates the redacted gist to app.claude.redaction. Trusts the
gate's `decision` and never re-reads visibility. This is a SKELETON — no logic.
"""
from __future__ import annotations

from app.models import ResponseItem


async def build_response_item(chunk: dict, decision: str) -> ResponseItem:
    """Turn one gated chunk into the canonical Response item.

    `decision` is the gate verdict (full|redacted|denied), already computed INSIDE
    the responding agent. full -> assemble pointer + verify; redacted -> pointer +
    redaction gist, verified=False; denied -> answer=None, payload hidden,
    verified=False.
    """
    raise NotImplementedError("build_response_item is a skeleton stub")
