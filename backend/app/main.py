"""FastAPI entrypoint: create_app() + lifespan (api-websocket.md §2.1, BUILD_INDEX.md §6).

Responsibility: construct the FastAPI app, run the startup wiring inside `lifespan`
(build registry, set the search registry, build EventBus + WSManager + Router +
Orchestrator + RunRegistry + GrantAccessService into app.state), add CORSMiddleware,
and mount the HTTP / WS / grant-access routers.

This module owns the WIRING; the components it imports are implemented in their own
modules. Run target: `uvicorn app.main:app --reload --port 8000`.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.agents.registry import build_registry
from app.events.bus import EventBus
from app.api.events import WSManager
from app.orchestrator.orchestrator import Orchestrator
from app.run_registry import RunRegistry
from app.grant_access.service import GrantAccessService
from app.retrieval import search as search_module
from app.router.router import Router
from app.router.responder import respond_for_agent, set_registry as set_responder_registry
from app.api import http as http_routes
from app.api import ws as ws_routes
from app.grant_access import routes as grant_access_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup wiring (BUILD_INDEX.md §6), in order:

    1. load settings;
    2. build the registry (3 isolated AgentIndex objects, isolation asserted);
    3. wire search (set the registry on retrieval.search; RELAY_SEARCH selects backend);
    4. build the event plumbing (one EventBus, one WSManager subscribing per query_id);
    5. build the Router (respond_for_agent injected) + Orchestrator + RunRegistry +
       GrantAccessService; stash all into app.state;
    6. (middleware + routers are added in create_app()).

    """
    # ---- 1. settings ----
    settings = get_settings()

    # ---- 2. registry (3 isolated agents) ----
    registry = build_registry(with_embeddings=(settings.relay_search == "cosine"))

    # ---- 3. wire search + responder (both need the registry: search for chunks,
    #         responder for party_name resolution on the gated items) ----
    search_module.set_registry(registry)
    set_responder_registry(registry)

    # ---- 4. event plumbing ----
    bus = EventBus()
    ws_manager = WSManager(bus)

    # ---- 5. router + orchestrator + run registry + grant-access service ----
    router = Router(registry=registry, bus=bus, responder=respond_for_agent)

    async def _emit(event: dict) -> None:
        # Orchestrator/router emit into the bus; the WSManager pump forwards to sockets.
        await bus.emit(event["query_id"], event)

    # run_registry is built BEFORE the orchestrator: it holds both the RunContext (for
    # grant-access replay) and the per-query_id item cache the targeted replay reuses.
    run_registry = RunRegistry()
    orchestrator = Orchestrator(
        registry=registry, router=router, emit=_emit, run_registry=run_registry,
        top_k=settings.top_k,
    )
    grant_access_service = GrantAccessService(
        registry=registry, orchestrator=orchestrator, run_registry=run_registry,
    )

    app.state.settings = settings
    app.state.registry = registry
    app.state.bus = bus
    app.state.ws_manager = ws_manager
    app.state.router = router
    app.state.orchestrator = orchestrator
    app.state.run_registry = run_registry
    app.state.grant_access_service = grant_access_service

    yield
    # Nothing to tear down for the MVP (in-process, no external connections).


def create_app() -> FastAPI:
    """Construct the FastAPI app: lifespan, CORS, and mounted routers."""
    settings = get_settings()
    app = FastAPI(title="Relay Backend", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,                                    # no prod auth/cookies (spec §5)
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(http_routes.router)                          # POST /query
    app.include_router(ws_routes.router)                            # WS /ws/query
    app.include_router(grant_access_routes.router)                  # POST /grant_access
    return app


# `uvicorn app.main:app` — the ASGI app the server imports.
app = create_app()
