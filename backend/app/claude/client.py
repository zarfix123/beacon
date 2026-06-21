"""Shared AsyncAnthropic client + model ids + helpers (redaction.md §2.1,
provenance-verification.md §2.5, BUILD_INDEX.md §2.1).

ONE AsyncAnthropic client, the model-id constants, and the call helpers reused by
redaction / verification / synthesis so model id, refusal handling, and prompt caching
live in exactly one place.

Structured output note: installed `anthropic 0.64.0` has NO `messages.parse` /
`output_config`. Structured output is done via FORCED TOOL USE (`call_tool`).
"""
from __future__ import annotations

import os
import pathlib
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import anthropic

# Model selection (OQ-6). Verification runs on the live request path, so it uses Haiku
# (a yes/no grounding judgment doesn't need Opus and Haiku is much faster/cheaper).
REDACT_MODEL: str = "claude-opus-4-8"
VERIFY_MODEL: str = "claude-haiku-4-5"   # OQ-6 downgrade: latency on the live path
SYNTH_MODEL: str = "claude-opus-4-8"

_client: Optional["anthropic.AsyncAnthropic"] = None


def _load_env_file() -> None:
    """Populate ANTHROPIC_API_KEY from backend/.env if it isn't already in the env.
    Avoids a hard dependency on python-dotenv (not installed on this machine)."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    env_path = pathlib.Path(__file__).resolve().parents[2] / ".env"   # backend/.env
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip())


def get_client() -> "anthropic.AsyncAnthropic":
    """Process-wide AsyncAnthropic singleton. Reads ANTHROPIC_API_KEY from env/.env."""
    global _client
    if _client is None:
        import anthropic
        _load_env_file()
        _client = anthropic.AsyncAnthropic()
    return _client


def cached_system_block(text: str) -> list[dict]:
    """A system block with an ephemeral cache breakpoint, so a byte-stable system
    prompt is written once and read ~0.1x thereafter (no-op below the cache minimum)."""
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


def _first_block(content, block_type: str):
    for block in content:
        if getattr(block, "type", None) == block_type:
            return block
    return None


async def complete_text(
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 128,
    cache_system: bool = True,
) -> Optional[str]:
    """One-shot text completion. Returns the first text block, or None on refusal/empty.

    No sampling params / no `thinking` (Opus 4.8 rejects sampling params; these are
    mechanical calls). System is cached when cache_system is True.
    """
    client = get_client()
    system_arg = cached_system_block(system) if cache_system else system
    resp = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_arg,
        messages=[{"role": "user", "content": user}],
    )
    if resp.stop_reason == "refusal":
        return None
    block = _first_block(resp.content, "text")
    return block.text if block is not None else None


async def call_tool(
    *,
    model: str,
    system: str,
    user: str,
    tool: dict,
    max_tokens: int = 128,
    cache_system: bool = True,
) -> Optional[dict]:
    """Forced single-tool call -> the tool_use block's `input` dict, or None.

    The structured-output mechanism for anthropic 0.64.0 (no messages.parse). Forces
    exactly one tool call matching `tool`'s input_schema and returns its parsed input.
    """
    client = get_client()
    system_arg = cached_system_block(system) if cache_system else system
    resp = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_arg,
        messages=[{"role": "user", "content": user}],
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
    )
    if resp.stop_reason == "refusal":
        return None
    block = _first_block(resp.content, "tool_use")
    return dict(block.input) if block is not None else None


async def stream_text(
    *,
    model: str,
    system: str,
    user: str,
    on_delta,
    max_tokens: int = 320,
    cache_system: bool = True,
) -> Optional[str]:
    """Streaming one-shot completion: awaits `on_delta(text)` for each text delta as it
    arrives, and returns the full accumulated text (or None on refusal/empty).

    Same call rules as complete_text (no sampling params / no thinking). Used by synthesis so
    the user-facing answer streams to the UI token-by-token instead of landing after a
    multi-second wait — the hero beat reads as alive, not hung.
    """
    client = get_client()
    system_arg = cached_system_block(system) if cache_system else system
    parts: list[str] = []
    async with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system_arg,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        async for text in stream.text_stream:
            parts.append(text)
            await on_delta(text)
        final = await stream.get_final_message()
    if final.stop_reason == "refusal":
        return None
    return "".join(parts) if parts else None
