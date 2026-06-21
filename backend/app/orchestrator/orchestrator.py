"""Orchestrator.run: fan out -> collect -> synthesize -> done (orchestrator.md §2.2,
api-websocket.md §2.10, grant-access.md §2.5).

The coordination core that lives in the asking agent. It calls the Router (which emits
agent-activated + response-item and runs the wedge on each responder's side), then
synthesizes over the verified-full items and emits exactly one `done`. It NEVER sees raw
restricted/private text — only already-gated, already-verified ResponseItem dicts.

Reconciliation (Phase 3): verification already runs inside the responder
(build_response_item), on the owner's side where the raw chunk text is local and must not
cross the boundary. So the orchestrator does NOT re-verify; `verify_concurrency`/`_sem` is
vestigial, kept only for ctor compatibility.

Grant-access uses a TARGETED replay: only the granted chunk's party re-dispatches; the
other parties' items are reused from the per-query_id cache in RunRegistry, then the
answer is re-synthesized. Near-instant reveal, and only the changed card re-streams.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Optional, TYPE_CHECKING

from app.claude.synthesis import synthesize
from app.core.ids import new_query_id      # re-exported: handlers import it from here
from app.models import ResponseItem

if TYPE_CHECKING:
    from app.agents.registry import AgentRegistry
    from app.router.router import Router
    from app.run_registry import RunRegistry

# An event sink the API/WS layer (or a test collector) provides.
EventSink = Callable[[dict], Awaitable[None]]

_PROVENANCE_KEYS = (
    "source_party", "source_doc_title", "decision", "verified", "source_agent_id", "chunk_id",
)
_FALLBACK_ANSWER = "The query could not be completed. Please try again."


def _provenance_entry(item: ResponseItem) -> dict:
    """The 6-key provenance entry (data-model §4 minus `answer`)."""
    return {k: item[k] for k in _PROVENANCE_KEYS}


def _done_event(query_id: str, answer: str, provenance_items: list[ResponseItem], item_count: int) -> dict:
    """The frozen `done` WS frame (api-websocket.md)."""
    return {
        "type": "done",
        "query_id": query_id,
        "synthesized_answer": answer,
        "provenance": [_provenance_entry(i) for i in provenance_items],
        "item_count": item_count,
    }


class Orchestrator:
    """Drives one query run end-to-end. Transport-agnostic via an injected sink."""

    def __init__(
        self,
        registry: "AgentRegistry",
        router: "Router",
        emit: EventSink,
        run_registry: "RunRegistry",
        *,
        top_k: int = 5,
        verify_concurrency: int = 3,
    ) -> None:
        self._registry = registry
        self._router = router
        self._emit = emit
        self._run_registry = run_registry
        self._top_k = top_k
        self._sem = asyncio.Semaphore(verify_concurrency)  # vestigial (verify is in responder)

    async def run(
        self,
        query: str,
        from_agent: str,
        query_id: Optional[str] = None,
        *,
        changed_chunk_id: Optional[str] = None,
    ) -> None:
        """Fan out (or targeted-replay) -> collect -> synthesize -> emit one done.

        Fresh run (changed_chunk_id is None): dispatch to every party. Targeted replay:
        re-dispatch ONLY the party owning changed_chunk_id, reuse the cached items for the
        rest. Emits agent-activated* + response-item* (via the router), then exactly one done.
        """
        query_id = query_id or new_query_id()

        if changed_chunk_id is None:
            items = await self._router.dispatch(query_id, from_agent, query)
        else:
            changed_agent = self._registry.find_chunk(changed_chunk_id)[0].id
            fresh = await self._router.dispatch(
                query_id, from_agent, query, only_agents=[changed_agent]
            )
            prior = self._run_registry.get_items(query_id) or []
            items = [i for i in prior if i["source_agent_id"] != changed_agent] + fresh

        self._run_registry.set_items(query_id, items)

        verified_full = [i for i in items if i["decision"] == "full" and i["verified"]]
        redacted = [i for i in items if i["decision"] == "redacted"]
        # provenance order == [verified-full, then redacted] so synthesis's [n] citations
        # line up 1:1 with done.provenance for the answer panel.
        provenance = verified_full + redacted

        answer = await synthesize(query, verified_full, redacted)
        await self._emit(_done_event(query_id, answer, provenance, len(items)))

    async def run_guarded(
        self,
        query: str,
        from_agent: str,
        query_id: str,
        *,
        changed_chunk_id: Optional[str] = None,
    ) -> None:
        """run() wrapped so any mid-stream error still emits a terminal done — the client
        (and the grant-access hero beat) never hangs on a silent spinner."""
        try:
            await self.run(query, from_agent, query_id=query_id, changed_chunk_id=changed_chunk_id)
        except Exception:
            await self._emit_fallback_done(query_id)

    def start_run(self, query_id: str, from_agent: str, query: str) -> None:
        """Schedule a fresh run fire-and-forget so POST /query / the WS ack returns fast.
        Errors are caught inside run_guarded and surfaced as a terminal done (OQ-5)."""
        asyncio.create_task(self.run_guarded(query, from_agent, query_id))

    async def _emit_fallback_done(self, query_id: str) -> None:
        """Emit a terminal done on failure, preserving the last-known sources if any."""
        try:
            items = self._run_registry.get_items(query_id) or []
            verified_full = [i for i in items if i["decision"] == "full" and i["verified"]]
            redacted = [i for i in items if i["decision"] == "redacted"]
            await self._emit(
                _done_event(query_id, _FALLBACK_ANSWER, verified_full + redacted, len(items))
            )
        except Exception:
            pass  # last resort: nothing more we can do without making it worse
