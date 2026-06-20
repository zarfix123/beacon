"""respond_for_agent: the boundary pipeline inside the responding agent (router.md,
BUILD_INDEX.md step 18).

Responsibility: for one agent, run search -> gate.evaluate (with issue_grant +
registry.party_name) -> build_response_item. This is the retrieve->gate->redact/verify
pipeline that runs INSIDE the responding agent (the boundary). Returns already-gated
ResponseItems. This is a SKELETON — no logic.
"""
from __future__ import annotations

from app.models import ResponseItem


async def respond_for_agent(agent_id: str, query: str) -> list[ResponseItem]:
    """Run the boundary pipeline for one agent and return already-gated items.

    search(query, agent_id) -> for each chunk: gate.evaluate(...) -> build_response_item.
    The gate (and redaction/verification it triggers) runs here, inside the responder,
    before any item is handed back to the router/orchestrator.
    """
    raise NotImplementedError("respond_for_agent is a skeleton stub")
