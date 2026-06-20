"""Shared AsyncAnthropic client + model ids + helpers (redaction.md §2.1,
provenance-verification.md §2.5, BUILD_INDEX.md §2.1).

Responsibility (BUILD_INDEX.md §2.1): ONE AsyncAnthropic client, the model-id
constants, `complete_text()` / `parse` helpers, and `cached_system_block()`. Reused
by redaction, verification, and synthesis so model id, timeouts, retries, and refusal
handling live in exactly one place. This is a SKELETON — no logic.

Model ids (BUILD_INDEX.md §2.1 / OQ-6): all three default to claude-opus-4-8;
VERIFY_MODEL is the single sanctioned downgrade to claude-haiku-4-5 if latency-bound.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import anthropic
    from pydantic import BaseModel

# Model selection (BUILD_INDEX.md §2.1 model-id note / OQ-6).
REDACT_MODEL: str = "claude-opus-4-8"
VERIFY_MODEL: str = "claude-opus-4-8"   # sanctioned downgrade: "claude-haiku-4-5"
SYNTH_MODEL: str = "claude-opus-4-8"

_client: Optional["anthropic.AsyncAnthropic"] = None


def get_client() -> "anthropic.AsyncAnthropic":
    """Process-wide AsyncAnthropic singleton. Reads ANTHROPIC_API_KEY from env."""
    raise NotImplementedError("get_client is a skeleton stub")


def cached_system_block(text: str) -> list[dict]:
    """Return a system block with an ephemeral cache breakpoint, so a byte-stable
    system prompt is written once and read ~0.1x thereafter."""
    raise NotImplementedError("cached_system_block is a skeleton stub")


async def complete_text(
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 128,
    cache_system: bool = True,
) -> Optional[str]:
    """One-shot text completion. Returns the first text block, or None on refusal.

    Keeps call args minimal (no sampling params on Opus 4.8; no thinking/effort on
    Haiku 4.5 — OQ-6). System is cached when cache_system is True.
    """
    raise NotImplementedError("complete_text is a skeleton stub")


async def parse(
    *,
    model: str,
    system: list[dict],
    user: str,
    output_format: type["BaseModel"],
    max_tokens: int = 128,
) -> Optional["BaseModel"]:
    """Structured-output completion via messages.parse(). Returns the parsed model,
    or None on parse failure / refusal (caller fails closed)."""
    raise NotImplementedError("parse is a skeleton stub")
