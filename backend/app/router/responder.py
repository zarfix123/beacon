"""respond_for_agent: the boundary pipeline inside the responding agent (router.md,
BUILD_INDEX.md step 18).

For one agent: search -> gate.evaluate (with issue_grant + registry.party_name) ->
build_response_item. The gate (and the redaction/verification it triggers) runs INSIDE
the responding agent, before any item is handed back. The per-chunk work is fanned out
concurrently so the boundary Claude calls fire in PARALLEL, not serially, on the live
request path. Returns already-gated ResponseItems.
"""
from __future__ import annotations

import asyncio
import os
from typing import Optional, TYPE_CHECKING

from app.gate import evaluate
from app.gate.capability import issue_grant
from app.models import ResponseItem
from app.provenance.assembler import build_response_item
from app.retrieval.search import search

if TYPE_CHECKING:
    from app.agents.registry import AgentRegistry

# Injected at startup (mirrors retrieval.search.set_registry) so the responder can
# resolve party names without a hard import of the registry.
_REGISTRY: Optional["AgentRegistry"] = None

# Self-sourced so Phase 2 doesn't depend on config.get_settings (a Phase-3 concern).
_TOP_K = int(os.getenv("BEACON_TOP_K", "5"))
_DEFAULT_ASKER = os.getenv("BEACON_DEFAULT_ASKER", "agent_helios")  # OQ-1


def set_registry(registry: "AgentRegistry") -> None:
    """Inject the AgentRegistry at startup so the responder resolves party names."""
    global _REGISTRY
    _REGISTRY = registry


async def respond_for_agent(
    agent_id: str, query: str, *, from_agent: Optional[str] = None
) -> list[ResponseItem]:
    """Run the boundary pipeline for one agent and return already-gated items.

    Per-chunk: gate.evaluate -> build_response_item. All chunks are processed
    concurrently via asyncio.gather, so the redaction (restricted) and verification
    (full) Claude calls fan out in parallel instead of stacking serially behind the
    spinner. Order is preserved (gather returns in input order = search rank order).
    """
    if _REGISTRY is None:
        raise RuntimeError("responder registry not set — call set_registry() at startup")
    grant = issue_grant(from_agent or _DEFAULT_ASKER)
    chunks = search(query, agent_id, _TOP_K)

    async def _process(chunk: dict) -> ResponseItem:
        gated = await evaluate(
            chunk, query=query, grant=grant, resolve_party_name=_REGISTRY.party_name
        )
        return await build_response_item(chunk, gated)

    return list(await asyncio.gather(*(_process(chunk) for chunk in chunks)))
