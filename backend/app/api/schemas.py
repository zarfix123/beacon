"""Pydantic WIRE models — verbatim from the frozen contract (api-websocket.md §2.5,
grant-access.md §2.6).

Responsibility: the ONLY place the wire shapes are declared. `embedding`/`score` are
NEVER on any outbound model — the boundary is enforced at the type level. Snake_case,
same keys as shared/contracts/api-websocket.md. These are real shape declarations (no
NotImplementedError): they are the freeze point with the frontend mock and carry no
behavior beyond field definitions.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

Decision = Literal["full", "redacted", "denied"]
Visibility = Literal["public", "restricted", "private"]


# ---- POST /query ------------------------------------------------------------
class QueryRequest(BaseModel):
    query: str
    from_agent: Optional[str] = None         # defaults to settings.default_asker


class QueryResponse(BaseModel):
    query_id: str
    from_agent: str
    agents: list[str]                        # party Agent.ids being fanned out to


# ---- WS event frames (type-discriminated) -----------------------------------
class AgentActivatedEvent(BaseModel):
    type: Literal["agent-activated"] = "agent-activated"
    query_id: str
    agent_id: str
    party_name: str
    status: Literal["searching"] = "searching"


class ResponseItemEvent(BaseModel):
    type: Literal["response-item"] = "response-item"
    query_id: str
    chunk_id: str                            # transport addition (grant-access wiring)
    source_agent_id: str                     # transport addition (keys card to node)
    answer: Optional[str]                    # full=text, redacted=gist, denied=null
    source_party: str
    source_doc_title: Optional[str]
    decision: Decision
    verified: bool


class ProvenanceEntry(BaseModel):
    source_party: str
    source_doc_title: Optional[str]
    decision: Decision
    verified: bool
    source_agent_id: str
    chunk_id: str


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    query_id: str
    synthesized_answer: str
    provenance: list[ProvenanceEntry]
    item_count: int


# ---- WS client->server submit + ack (WS-driven option) ----------------------
class WSQueryFrame(BaseModel):
    type: Literal["query"]
    query: str
    from_agent: Optional[str] = None


class WSAck(QueryResponse):
    type: Literal["ack"] = "ack"


# ---- POST /grant_access (api-websocket.md §2) -------------------------------
class GrantAccessRequest(BaseModel):
    chunk_id: str
    query_id: str


class GrantAccessResponse(BaseModel):
    chunk_id: str
    new_visibility: Visibility               # "public" for the demo
    query_id: str
    rerunning: bool
