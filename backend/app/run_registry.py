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

from app.models import ResponseItem


@dataclass(frozen=True)
class RunContext:
    """The original request behind one query_id (grant-access.md §2.3)."""
    query_id: str
    query: str
    from_agent: str


class RunRegistry:
    """In-memory map query_id -> RunContext (the original question) + the last run's
    emitted items (so a grant-access replay can reuse unchanged parties' results instead
    of re-fanning-out to everyone — the targeted-replay cache)."""

    def __init__(self) -> None:
        self._runs: dict[str, RunContext] = {}
        self._items: dict[str, list[ResponseItem]] = {}
        self._lock = Lock()

    def put(self, ctx: RunContext) -> None:
        """Store run context at query mint time (/query happy path)."""
        with self._lock:
            self._runs[ctx.query_id] = ctx

    def get(self, query_id: str) -> Optional[RunContext]:
        """Look up the original request for a query_id; None if unknown."""
        with self._lock:
            return self._runs.get(query_id)

    def set_items(self, query_id: str, items: list[ResponseItem]) -> None:
        """Cache the items a run emitted, for targeted grant-access replay."""
        with self._lock:
            self._items[query_id] = list(items)

    def get_items(self, query_id: str) -> Optional[list[ResponseItem]]:
        """Return the last run's cached items for a query_id; None if unknown."""
        with self._lock:
            cached = self._items.get(query_id)
            return list(cached) if cached is not None else None
