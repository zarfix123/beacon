"""Pure WS event builders (router.md §2.3, api-websocket.md).

Responsibility: pure dict construction matching the frozen WS payloads — no logic.
`agent_activated_event` and `response_item_event` produce exactly the contract's keys
and literals. This is a SKELETON — no logic.
"""
from __future__ import annotations

from app.models import ResponseItem


def agent_activated_event(query_id: str, agent_id: str, party_name: str) -> dict:
    """Build the frozen `agent-activated` frame:
    {type, query_id, agent_id, party_name, status:"searching"}."""
    return {
        "type": "agent-activated",
        "query_id": query_id,
        "agent_id": agent_id,
        "party_name": party_name,
        "status": "searching",          # single MVP value, frozen
    }


def response_item_event(query_id: str, item: ResponseItem) -> dict:
    """Build the frozen `response-item` frame: {type:"response-item", query_id, ...item}.
    The item already carries the 5 canonical fields + chunk_id + source_agent_id."""
    return {"type": "response-item", "query_id": query_id, **item}
