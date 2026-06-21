"""MCP client session + fan-out dispatcher with local fallback (Phase 5, plan step 3).

Beacon is the MCP *client*: it federates a party that serves its gated knowledge over a
real MCP server. Three pieces:

  - `connect_mcp`        — open a streamable-HTTP MCP session, kept alive by an AsyncExitStack.
  - `make_mcp_responder` — a `ResponderFn` that calls the party's `respond` tool over MCP,
                           wrapped in a timeout so a *hang* falls back fast (a hang never raises).
  - `make_dispatch_responder` — route each party to its MCP responder if configured, else the
                           local responder; ANY MCP error/timeout falls back to local for that
                           party. Tags every returned item with `transport` (mcp/fallback/local)
                           so the federation beat is *visible*, not asserted.

Faithfulness is preserved structurally: the served items are already gated (the gate +
redaction + verification ran inside the party server), and `_coerce_items` keeps only the 7
canonical wire keys — no `text`/`embedding` path exists. Nothing here re-reads visibility.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import AsyncExitStack
from typing import Awaitable, Callable, Optional, TYPE_CHECKING

from app.models import ResponseItem

if TYPE_CHECKING:                         # absolute import → the installed `mcp` SDK, not app.mcp
    from mcp import ClientSession

logger = logging.getLogger(__name__)

# (agent_id, query) -> already-gated ResponseItems (the frozen Router seam).
ResponderFn = Callable[[str, str], Awaitable[list[ResponseItem]]]

# The 7 canonical wire keys an MCP-returned item may carry. A defensive whitelist: even a
# misbehaving server cannot smuggle `text`/`embedding` across the boundary — we drop everything
# else. (`transport` is added by the dispatcher AFTER coercion, never trusted from the wire.)
_WIRE_KEYS = (
    "answer", "source_party", "source_doc_title",
    "decision", "verified", "chunk_id", "source_agent_id",
)

# A hang (server alive but stalled mid-call) never raises — without a timeout it would freeze
# the whole fan-out behind one party. Wrap call_tool so a hang falls back FAST to local.
MCP_TIMEOUT = float(os.getenv("BEACON_MCP_TIMEOUT", "8.0"))


async def connect_mcp(stack: AsyncExitStack, url: str) -> "ClientSession":
    """Open an initialized streamable-HTTP MCP client session against `url`.

    The transport + session are entered into `stack`, so they stay open for the process
    lifetime and are torn down when the caller closes the stack (lifespan shutdown).
    """
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    read, write, _ = await stack.enter_async_context(streamablehttp_client(url))
    session = await stack.enter_async_context(ClientSession(read, write))
    await session.initialize()
    return session


def make_mcp_responder(session: "ClientSession", agent_id: str) -> ResponderFn:
    """A `ResponderFn` that federates one party over MCP via its `respond` tool.

    Calls `respond(query)` (timeout-guarded), reads the returned JSON text, and coerces it
    to clean 7-key ResponseItems. Raises on timeout / transport error / bad payload so the
    dispatcher can fall back to local — failing clean instead of hanging or leaking.
    """
    async def _respond(_aid: str, query: str) -> list[ResponseItem]:
        result = await asyncio.wait_for(
            session.call_tool("respond", {"query": query}), timeout=MCP_TIMEOUT
        )
        text = _first_text(result)
        if not text:
            return []
        return _coerce_items(json.loads(text))

    return _respond


def make_dispatch_responder(local: ResponderFn, mcp_map: dict[str, ResponderFn]) -> ResponderFn:
    """Route the fan-out: MCP party → its MCP responder, everyone else → `local`.

    On ANY MCP failure/timeout for a configured party, fall back to `local(agent_id, query)`
    so the demo is never at the mercy of the MCP server. Tags each item's `transport`:
    "mcp" (MCP call succeeded), "fallback" (MCP failed → served locally), "local" (never MCP).
    """
    async def _dispatch(agent_id: str, query: str) -> list[ResponseItem]:
        responder = mcp_map.get(agent_id)
        if responder is None:
            return _tag(await local(agent_id, query), "local")
        try:
            return _tag(await responder(agent_id, query), "mcp")
        except Exception as exc:          # timeout, transport drop, malformed payload — fail clean
            logger.warning(
                "MCP responder for %s failed (%s); falling back to local", agent_id, exc
            )
            return _tag(await local(agent_id, query), "fallback")

    return _dispatch


# --------------------------------------------------------------------------- #
# internals                                                                    #
# --------------------------------------------------------------------------- #

def _first_text(result) -> Optional[str]:
    """Pull the first text payload out of a CallToolResult (FastMCP returns a str tool result
    as a single TextContent block). Tolerant of block shape across SDK versions."""
    for block in (getattr(result, "content", None) or []):
        text = getattr(block, "text", None)
        if text:
            return text
    return None


def _coerce_items(raw: object) -> list[ResponseItem]:
    """Keep only the 7 canonical wire keys per item; drop non-dict/non-list junk. This is the
    structural no-leak guard at the client edge: `text`/`embedding`/any extra key never survive."""
    if not isinstance(raw, list):
        return []
    out: list[ResponseItem] = []
    for entry in raw:
        if isinstance(entry, dict):
            out.append({k: entry.get(k) for k in _WIRE_KEYS})  # type: ignore[misc]
    return out


def _tag(items: list[ResponseItem], transport: str) -> list[ResponseItem]:
    """Stamp the federation transport on each item in place (additive; the WS frame spreads it)."""
    for item in items:
        item["transport"] = transport     # type: ignore[typeddict-item]
    return items
