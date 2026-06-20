"""Grant-access-live subsystem: the hero beat (grant-access.md).

Toggle one chunk's visibility (restricted -> public), then replay the original query
on the SAME query_id so the card flips amber -> green on stage. A mutation + a replay;
everything else is reuse. Re-exports the service + route.
"""
from __future__ import annotations

from app.grant_access.service import GrantAccessService  # noqa: F401
from app.grant_access.routes import router  # noqa: F401

__all__ = ["GrantAccessService", "router"]
