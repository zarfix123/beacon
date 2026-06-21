"""Request-time app.state accessors (api-websocket.md §2.9).

Responsibility: thin helpers so HTTP and WebSocket handlers read shared components
(registry, orchestrator, ws_manager, run_registry, grant_access_service) off
`request.app.state` / `ws.app.state` in one place. Each is a one-liner so the lifespan
wiring is the single source of truth for what these objects are.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request, WebSocket

if TYPE_CHECKING:
    from app.agents.registry import AgentRegistry
    from app.orchestrator.orchestrator import Orchestrator
    from app.api.events import WSManager
    from app.run_registry import RunRegistry
    from app.grant_access.service import GrantAccessService


def get_registry(request: Request) -> "AgentRegistry":
    """Return the AgentRegistry from request.app.state."""
    return request.app.state.registry


def get_orchestrator(request: Request) -> "Orchestrator":
    """Return the Orchestrator from request.app.state."""
    return request.app.state.orchestrator


def get_ws_manager(request: Request) -> "WSManager":
    """Return the WSManager from request.app.state."""
    return request.app.state.ws_manager


def get_run_registry(request: Request) -> "RunRegistry":
    """Return the RunRegistry from request.app.state."""
    return request.app.state.run_registry


def get_grant_access_service(request: Request) -> "GrantAccessService":
    """Return the GrantAccessService from request.app.state (DI for the route)."""
    return request.app.state.grant_access_service


def get_orchestrator_ws(ws: WebSocket) -> "Orchestrator":
    """Return the Orchestrator from ws.app.state."""
    return ws.app.state.orchestrator


def get_ws_manager_ws(ws: WebSocket) -> "WSManager":
    """Return the WSManager from ws.app.state."""
    return ws.app.state.ws_manager
