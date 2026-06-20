"""Shared record shapes — the single source of truth for the whole backend.

Responsibility (BUILD_INDEX.md §2.1 "Shared record shapes" + every subsystem doc):
this flat module holds the canonical, co-owned record types so shapes cannot drift
across subsystems. Whoever scaffolds first writes it; everyone else imports from here.

Shapes held here (verbatim against shared/contracts/data-model.md and the gate /
provenance / orchestrator / grant-access build docs):
  - Visibility / Decision enums (shared enums table, data-model.md)
  - Chunk, Agent, CrossAgentRequest, ResponseItem  (data-model.md §1-4)
  - GateDecision enum + GatedResult dataclass       (permission-gate.md §2.1)
  - ProvenancePointer, VerifyResult                  (provenance-verification.md §2.1)
  - GrantAccessRequest, GrantAccessResponse          (grant-access.md §2.6)

Boundary rule (data-model.md): `embedding` is the ONLY field that never crosses the
API/WebSocket boundary; `score` is result-only. Outbound wire shapes (api/schemas.py)
deliberately omit both. This is a SKELETON — no logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional, TypedDict

try:  # NotRequired moved into typing in 3.11; fall back for 3.10.
    from typing import NotRequired
except ImportError:  # pragma: no cover
    from typing_extensions import NotRequired

# ---- shared enums (data-model.md shared-enums table) ------------------------
Visibility = Literal["public", "restricted", "private"]
Decision = Literal["full", "redacted", "denied"]


# ---- core record shapes (data-model.md §1-4) --------------------------------
class Chunk(TypedDict):
    """One row in an agent's flat index (data-model.md §2).

    `embedding` is server-side only (never serialized past the gate); `score` is
    added only on `search()` results. Both are NotRequired so the keyword stub
    fixture may omit them.
    """
    chunk_id: str
    parent_doc_id: str
    doc_title: str
    owner: str                            # an Agent.id; == the searched agent_id
    visibility: Visibility
    text: str
    embedding: NotRequired[list[float]]   # server-side only; stub may omit
    score: NotRequired[float]             # result-only, 0.0-1.0, added by search


class Agent(TypedDict):
    """One of the 3 independent parties (data-model.md §1)."""
    id: str
    party_name: str
    scope_policy: str                     # "three_tier" for MVP


class CrossAgentRequest(TypedDict):
    """The minimal envelope one agent sends to another (data-model.md §3)."""
    from_agent: str
    query: str


class ResponseItem(TypedDict):
    """One party's gated answer for one chunk (data-model.md §4).

    Produced downstream by the gate; defined here for one source of truth. The five
    canonical §8 fields plus the two transport additions for frontend wiring.
    """
    answer: Optional[str]
    source_party: str
    source_doc_title: Optional[str]
    decision: Decision
    verified: bool
    chunk_id: str                         # transport addition (grant_access handle)
    source_agent_id: str                  # transport addition (owning Agent.id)


# ---- gate shapes (permission-gate.md §2.1) ----------------------------------
class GateDecision(str, Enum):
    """The gate's per-chunk verdict. Values match data-model §4 `decision` verbatim."""
    FULL = "full"
    REDACTED = "redacted"
    DENIED = "denied"


@dataclass(frozen=True)
class GatedResult:
    """Boundary-safe output of the gate for ONE chunk (permission-gate.md §2.1).

    INVARIANT: for REDACTED and DENIED, no original `chunk.text` is present — the raw
    payload is not a field on this object, so it cannot leak downstream. `frozen=True`
    makes "put the restricted text back" structurally impossible. Maps 1:1 to the
    frozen `response-item` payload via `to_wire()`.
    """
    decision: GateDecision
    answer: Optional[str]            # full: payload | redacted: gist | denied: None
    source_party: str               # party_name of chunk.owner
    source_doc_title: Optional[str] # chunk.doc_title; None for fully-hidden denied
    verified: bool                  # gate default False; orchestrator flips after verify
    chunk_id: str                   # transport: grant_access handle
    source_agent_id: str            # transport: chunk.owner (Agent.id)
    access_requestable: bool        # internal-only; True only for redacted

    def to_wire(self) -> dict:
        """Serialize to the EXACT frozen response-item payload (api-websocket.md).

        Emits the five canonical fields + the two transport ids; `access_requestable`
        is internal-only and NOT serialized; `type`/`query_id` are added by the API
        layer. `embedding`/`text` are structurally absent.
        """
        raise NotImplementedError("GatedResult.to_wire is a skeleton stub")


# ---- provenance / verification shapes (provenance-verification.md §2.1) ------
@dataclass(frozen=True)
class ProvenancePointer:
    """The pointer half of the provenance/content split (spec §3).

    Travels even when the payload doesn't. `timestamp` is internal (logs/debug only)
    and is NOT serialized into any frozen WS payload (OQ-4 / provenance-verification.md).
    """
    source_party: str
    source_doc_title: Optional[str]
    owner: str                       # Agent.id == chunk.owner
    chunk_id: str
    timestamp: str                   # ISO-8601, assembly time (UTC). Internal/log only.


@dataclass(frozen=True)
class VerifyResult:
    """Output shape of the verification Claude call (provenance-verification.md §2.1)."""
    verified: bool                   # Claude's yes/no, mapped to bool
    reason: Optional[str] = None     # one short clause, logs/debug only — NOT on the wire


# ---- grant-access shapes (grant-access.md §2.6) -----------------------------
@dataclass(frozen=True)
class GrantAccessRequest:
    """Frozen POST /grant_access request body (api-websocket.md §2)."""
    chunk_id: str
    query_id: str


@dataclass(frozen=True)
class GrantAccessResponse:
    """Frozen POST /grant_access response body (api-websocket.md §2)."""
    chunk_id: str
    new_visibility: Visibility
    query_id: str
    rerunning: bool
