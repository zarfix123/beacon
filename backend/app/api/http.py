"""POST /query handler (api-websocket.md §2.7).

Responsibility: resolve the asker (default from settings), compute agents[] (parties
minus asker), mint query_id, write RunContext to the run_registry, schedule the
orchestrator run fire-and-forget, and return {query_id, from_agent, agents}
immediately. This is a SKELETON — no logic.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.api import schemas

router = APIRouter()


@router.post("/query", response_model=schemas.QueryResponse)
async def submit_query(body: schemas.QueryRequest, request: Request) -> schemas.QueryResponse:
    """Mint a query_id, record run state, kick the fan-out, return immediately.
    SKELETON — no logic."""
    raise NotImplementedError("submit_query is a skeleton stub")
