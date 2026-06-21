"""POST /query handler (api-websocket.md §2.7).

Responsibility: resolve the asker (default from settings), compute agents[] (parties
minus asker), mint query_id, write RunContext to the run_registry, schedule the
orchestrator run fire-and-forget, and return {query_id, from_agent, agents}
immediately. This is a SKELETON — no logic.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.api import schemas
from app.orchestrator.orchestrator import new_query_id
from app.run_registry import RunContext

router = APIRouter()


@router.post("/query", response_model=schemas.QueryResponse)
async def submit_query(body: schemas.QueryRequest, request: Request) -> schemas.QueryResponse:
    """Resolve the asker, mint a query_id, record run state, kick the fan-out
    fire-and-forget, and return {query_id, from_agent, agents} immediately. Events stream
    over the WS once a socket subscribes to query_id (the bus replays any earlier frames)."""
    state = request.app.state
    asker = body.from_agent or state.settings.default_asker
    query_id = new_query_id()
    agents = [aid for aid in state.registry.all_ids() if aid != asker]

    state.run_registry.put(RunContext(query_id=query_id, query=body.query, from_agent=asker))
    state.orchestrator.start_run(query_id, asker, body.query)
    return schemas.QueryResponse(query_id=query_id, from_agent=asker, agents=agents)
