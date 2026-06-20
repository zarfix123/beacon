"""GrantAccessService: toggle + replay (grant-access.md §2.1).

Responsibility: the only real logic in the hero beat — (a) toggle one chunk's
visibility via AgentIndex.set_visibility, (b) trigger a replay of the stored query
through the Orchestrator on the SAME query_id. Holds NO gate logic and NO
orchestration logic — it calls into both. This is a SKELETON — no logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

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
        raise NotImplementedError("toggle_visibility is a skeleton stub")

    async def grant_and_rerun(self, chunk_id: str, query_id: str) -> GrantResult:
        """Validate the query_id, toggle the chunk, and build the ACK. The replay is
        scheduled by the route (BackgroundTasks) so the HTTP ACK is not blocked."""
        raise NotImplementedError("grant_and_rerun is a skeleton stub")

    async def replay(self, query_id: str) -> None:
        """Re-invoke the orchestrator for the stored query on the SAME query_id,
        streaming a fresh agent-activated -> response-item -> done cycle. Raises
        UnknownQueryError if the run context is missing."""
        raise NotImplementedError("replay is a skeleton stub")
