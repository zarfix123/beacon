"""Meta + demo-control routes (Phase 4): GET /health, GET /agents, POST /demo/reset.

Small, demo-serving endpoints the live client needs — NOT product features:
  - GET /health   : run.sh readiness probe.
  - GET /agents   : the 3 parties [{id, party_name}] so the UI renders real names + builds
                    the constellation dynamically (vs hardcoded Atlas/Lyra/Vega).
  - POST /demo/reset : re-apply the locked demo tiers to the LIVE in-memory index, re-arming
                    the granted chunk between rehearsal takes WITHOUT a server restart.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Liveness probe for run.sh / smoke checks."""
    return {"status": "ok"}


@router.get("/agents")
async def agents(request: Request) -> list[dict]:
    """The registered parties, in stable order: [{id, party_name, transport}].

    `transport` is the static, config-level federation badge: "mcp" for a party Beacon
    federates over a real MCP server, "local" for an in-process party. (The *live* per-item
    transport — which flips to "fallback" on an MCP failure — rides on each response-item.)
    """
    registry = request.app.state.registry
    mcp_agents = getattr(request.app.state, "mcp_agents", set()) or set()
    return [
        {
            "id": aid,
            "party_name": registry.party_name(aid),
            "transport": "mcp" if aid in mcp_agents else "local",
        }
        for aid in registry.all_ids()
    ]


@router.post("/demo/reset")
async def demo_reset(request: Request) -> dict:
    """Re-arm the demo: re-apply the locked tiers to the live index (grant-access flips one
    chunk to public in memory; this resets it to restricted so the next take shows the
    redacted card). Returns the applied {chunk_id: visibility}."""
    from app.demo import apply_demo_tiers

    applied = apply_demo_tiers(request.app.state.registry)
    return {"reset": applied}
