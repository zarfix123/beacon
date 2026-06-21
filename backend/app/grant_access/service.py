"""GrantAccessService: toggle + replay (grant-access.md §2.1).

Responsibility: the only real logic in the hero beat — (a) toggle one chunk's
visibility via AgentIndex.set_visibility, (b) trigger a replay of the stored query
through the Orchestrator on the SAME query_id. Holds NO gate logic and NO
orchestration logic — it calls into both. This is a SKELETON — no logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from app.agents.index import ChunkNotFoundError
from app.models import Visibility

if TYPE_CHECKING:
    from app.agents.registry import AgentRegistry
    from app.orchestrator.orchestrator import Orchestrator
    from app.run_registry import RunRegistry


@dataclass(frozen=True)
class GrantResult:
    """Internal result of grant_and_rerun, shaped into GrantAccessResponse by the route."""
    chunk_id: str
    new_visibility: Visibility
    query_id: str
    rerunning: bool


class UnknownQueryError(KeyError):
    """Raised when query_id has no stored RunContext (-> 404)."""


class GrantAccessService:
    """Owns the two new behaviors: mutate one chunk's visibility, and trigger a
    replay of the original query through the orchestrator."""

    def __init__(
        self,
        registry: "AgentRegistry",
        orchestrator: "Orchestrator",
        run_registry: "RunRegistry",
    ) -> None:
        self._registry = registry
        self._orchestrator = orchestrator
        self._run_registry = run_registry

    def toggle_visibility(self, chunk_id: str, *, target: Visibility = "public") -> Visibility:
        """Flip one chunk's stored visibility (restricted -> public for the demo).

        Resolves the owning agent from the globally-unique chunk_id and mutates ONLY
        that row (isolation preserved). Idempotent: already-public -> no-op, still
        returns "public". Raises ChunkNotFoundError on miss.
        """
        try:
            agent, _chunk = self._registry.find_chunk(chunk_id)
        except KeyError:
            raise ChunkNotFoundError(chunk_id)
        return agent.index.set_visibility(chunk_id, target)

    async def grant_and_rerun(self, chunk_id: str, query_id: str) -> GrantResult:
        """Validate the query_id, toggle the chunk, and build the ACK. The replay is
        scheduled by the route (BackgroundTasks) so the HTTP ACK is not blocked.

        Validation happens BEFORE the toggle so an unknown query_id never mutates state.
        """
        if self._run_registry.get(query_id) is None:
            raise UnknownQueryError(query_id)
        new_visibility = self.toggle_visibility(chunk_id, target="public")
        return GrantResult(
            chunk_id=chunk_id, new_visibility=new_visibility,
            query_id=query_id, rerunning=True,
        )

    async def replay(self, query_id: str, changed_chunk_id: Optional[str] = None) -> None:
        """Re-invoke the orchestrator for the stored query on the SAME query_id.

        Targeted: only the granted chunk's party re-dispatches (changed_chunk_id), the
        rest are reused from the cache. Uses run_guarded so a mid-stream error still emits
        a terminal done (the hero beat never hangs). Raises UnknownQueryError if the run
        context is missing.
        """
        ctx = self._run_registry.get(query_id)
        if ctx is None:
            raise UnknownQueryError(query_id)
        await self._orchestrator.run_guarded(
            ctx.query, ctx.from_agent, ctx.query_id, changed_chunk_id=changed_chunk_id,
        )
