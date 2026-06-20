"""POST /grant_access route (grant-access.md §2.2).

Responsibility: bind POST /grant_access to GrantAccessService, shape the response per
the frozen API contract ({chunk_id, new_visibility, query_id, rerunning}), and
schedule the replay (BackgroundTasks) so the ACK returns immediately. Maps
ChunkNotFoundError / UnknownQueryError -> 404. This is a SKELETON — no logic.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.agents.index import ChunkNotFoundError
from app.api import schemas
from app.deps import get_grant_access_service
from app.grant_access.service import GrantAccessService, UnknownQueryError

router = APIRouter()


@router.post("/grant_access", response_model=schemas.GrantAccessResponse)
async def grant_access(
    body: schemas.GrantAccessRequest,
    background: BackgroundTasks,
    svc: GrantAccessService = Depends(get_grant_access_service),
) -> schemas.GrantAccessResponse:
    """Toggle one chunk's visibility, ACK, and schedule the replay on the same
    query_id. SKELETON — no logic."""
    raise NotImplementedError("grant_access route is a skeleton stub")
