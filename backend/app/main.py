"""FastAPI entrypoint: create_app() + lifespan (api-websocket.md §2.1, BUILD_INDEX.md §6).

Responsibility: construct the FastAPI app, run the startup wiring inside `lifespan`
(build registry, set the search registry, build EventBus + WSManager + Router +
Orchestrator + RunRegistry + GrantAccessService into app.state), add CORSMiddleware,
and mount the HTTP / WS / grant-access routers.

This module owns the WIRING; the components it imports are implemented in their own
modules. Run target: `uvicorn app.main:app --reload --port 8000`.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager, AsyncExitStack

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
from app.mcp.client import connect_mcp, make_mcp_responder, make_dispatch_responder
from app.api import http as http_routes
from app.api import ws as ws_routes
from app.api import meta as meta_routes
from app.grant_access import routes as grant_access_routes

_log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup wiring (BUILD_INDEX.md §6), in order:

    1. load settings;
    2. build the registry (3 isolated AgentIndex objects, isolation asserted);
    3. wire search (set the registry on retrieval.search; BEACON_SEARCH selects backend);
    4. build the event plumbing (one EventBus, one WSManager subscribing per query_id);
    5. build the Router (respond_for_agent injected) + Orchestrator + RunRegistry +
       GrantAccessService; stash all into app.state;
    6. (middleware + routers are added in create_app()).

    """
    # ---- 1. settings ----
    settings = get_settings()

    # ---- 2. registry (3 isolated agents) ----
    registry = build_registry(with_embeddings=settings.beacon_search in ("cosine", "hybrid"))

    # ---- 3. wire search + responder (both need the registry: search for chunks,
    #         responder for party_name resolution on the gated items) ----
    search_module.set_registry(registry)
    set_responder_registry(registry)

    # pre-warm: build each party's BM25 index + load the embedding model now, so the first
    # LIVE query doesn't pay the ~250ms lazy cold-start. One-time cost at startup.
    for _aid in registry.all_ids():
        try:
            search_module.search("warmup", _aid, 1)
        except Exception:
            pass

    # ---- 3b. MCP federation (Phase 5) — optionally serve some parties over a real MCP server.
    # BEACON_MCP_AGENTS (comma-separated agent_ids) + BEACON_MCP_URL turn it on; BEACON_MCP=off forces
    # all-local. The dispatcher routes those parties over MCP and everyone else stays local; ANY
    # connect/call failure falls back to the in-process responder — the demo is never at the mercy
    # of the MCP server. `app.state.mcp_agents` drives the GET /agents "via MCP" badge.
    responder_fn = respond_for_agent
    mcp_agents: set[str] = set()
    app.state.mcp_stack = None
    mcp_url = os.getenv("BEACON_MCP_URL", "").strip()
    mcp_agent_ids = [a.strip() for a in os.getenv("BEACON_MCP_AGENTS", "").split(",") if a.strip()]
    if os.getenv("BEACON_MCP", "").lower() != "off" and mcp_url and mcp_agent_ids:
        stack = AsyncExitStack()
        try:
            session = await connect_mcp(stack, mcp_url)
            mcp_map = {aid: make_mcp_responder(session, aid) for aid in mcp_agent_ids}
            responder_fn = make_dispatch_responder(respond_for_agent, mcp_map)
            mcp_agents = set(mcp_agent_ids)
            app.state.mcp_stack = stack
            _log.info("MCP federation active: %s via %s", ", ".join(mcp_agent_ids), mcp_url)
        except Exception as exc:                      # server down/unreachable -> all-local
            await stack.aclose()
            _log.warning("MCP connect to %s failed (%s); serving all parties locally", mcp_url, exc)
    app.state.mcp_agents = mcp_agents

    # ---- 4. event plumbing ----
    bus = EventBus()
    ws_manager = WSManager(bus)

    # ---- 5. router + orchestrator + run registry + grant-access service ----
    router = Router(registry=registry, bus=bus, responder=responder_fn)

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

    # ---- shutdown: close the MCP client session/transport if we opened one ----
    stack = getattr(app.state, "mcp_stack", None)
    if stack is not None:
        await stack.aclose()


def create_app() -> FastAPI:
    """Construct the FastAPI app: lifespan, CORS, and mounted routers."""
    settings = get_settings()
    app = FastAPI(title="Beacon Backend", lifespan=lifespan)
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
    app.include_router(meta_routes.router)                          # GET /health,/agents; POST /demo/reset
    return app


# `uvicorn app.main:app` — the ASGI app the server imports.
app = create_app()
