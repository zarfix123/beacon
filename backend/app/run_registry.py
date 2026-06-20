"""Per-query_id run context for grant-access replay (grant-access.md §2.3, OQ-8).

Responsibility: remember enough about each `query_id` run (the original `query` +
`from_agent`) to replay it. The frozen POST /grant_access body carries only
`{chunk_id, query_id}`, so server-side run state is REQUIRED to replay. Written by
the /query handler at mint time, read by GrantAccessService.replay. This is a
SKELETON — no logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Optional


@dataclass(frozen=True)
class RunContext:
    """The original request behind one query_id (grant-access.md §2.3)."""
    query_id: str
    query: str
    from_agent: str


class RunRegistry:
    """In-memory map query_id -> RunContext. Single source of truth for
    'what was the original question for this query_id'."""

    def __init__(self) -> None:
        self._runs: dict[str, RunContext] = {}
        self._lock = Lock()

    def put(self, ctx: RunContext) -> None:
        """Store run context at query mint time (/query happy path)."""
        raise NotImplementedError("RunRegistry.put is a skeleton stub")

    def get(self, query_id: str) -> Optional[RunContext]:
        """Look up the original request for a query_id; None if unknown."""
        raise NotImplementedError("RunRegistry.get is a skeleton stub")
