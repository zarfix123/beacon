# Beacon — BUILD doc: Permission Gate (3-tier full / redacted / denied)

> **Subsystem owner:** Dennis (backend / the wedge).
> **Status:** plan + index. This is a build map, not an implementation. Code below is *sketch/pseudocode* — signatures and shapes are load-bearing; bodies are illustrative.
> **Scope guard (spec §5):** flat numpy/Chroma index, 3 in-process agents, seeded corpora, no prod auth, no knowledge graph. The gate is plain Python policy functions keyed off `chunk.visibility` (spec §7).
> **Frozen contracts (DO NOT contradict):** [`data-model.md`](../../shared/contracts/data-model.md), [`search-interface.md`](../../shared/contracts/search-interface.md), [`api-websocket.md`](../../shared/contracts/api-websocket.md).

---

## 1. Purpose & where it sits in the query flow

The Permission Gate is **the wedge**: enforced permission at the owner's boundary (spec §1, §3). It is a per-chunk policy check, keyed off `chunk.visibility` (`public` | `restricted` | `private`), that runs **inside the responding agent, BEFORE any content crosses the boundary**. It maps every retrieved hit to a `Decision` (`full` | `redacted` | `denied`) and emits a **boundary-safe object** from which a `restricted` payload is *physically absent* — so nothing downstream (orchestrator, synthesis, WebSocket, frontend) can leak it even by accident.

### Position in the query flow (spec §10, ordering from §9 — *retrieve first, gate second*)

```
POST /query (api layer)                                    ← other subsystem (API)
   │
   ▼
orchestrator.fan_out()                                     ← other subsystem (orchestrator)
   │  for each party agent, in-process:
   ▼
┌───────────────── RESPONDING AGENT BOUNDARY ─────────────────┐
│  hits = search(query, agent_id, top_k)   (ALL tiers)        │  ← Hao's search (stub→real)
│  for chunk in hits:                                          │
│      decision = gate.evaluate(chunk, request_ctx)  ◀── THIS SUBSYSTEM
│      #   public    -> GatedResult(FULL,    payload present)  │
│      #   restricted-> GatedResult(REDACTED, gist via Claude) │
│      #   private   -> GatedResult(DENIED,  payload ABSENT)   │
│  emit only GatedResult objects across the boundary  ─────────┼──▶ orchestrator collects
└──────────────────────────────────────────────────────────────┘
   │
   ▼
orchestrator: verification pass (full only) + synthesis      ← other subsystem
   │
   ▼
WebSocket response-item / done events                        ← other subsystem (API/WS)
```

**Key invariant (spec §3, §6):** the raw `chunk.text` of a `restricted` or `private` chunk **never exists in any object that leaves the gate**. The gate does not "filter on the way out"; it constructs a new, content-free object for non-public tiers. Leakage is impossible because the bytes are simply not there to leak. The redaction Claude call also runs **inside** the gate boundary (it receives the restricted text, returns a gist; the text is discarded immediately after).

### What the gate is NOT responsible for

- **Retrieval** — Hao's `search()`. Gate consumes its output (spec §9).
- **Verification** — the orchestrator runs the verification Claude pass on `full` content it received. The gate only sets `verified=False` as the safe default; the orchestrator flips it to `True/False` after grounding-check. (Noted under Risks: ownership seam.)
- **Synthesis & WebSocket framing** — orchestrator + API layer.
- **Visibility mutation** — `grant_access` toggles `chunk.visibility` in the index, then the orchestrator re-runs the query, which re-invokes the gate fresh. The gate itself is stateless w.r.t. the toggle (Risk §7).

---

## 2. Files / modules to create under `backend/app/`

All gate code lives in a self-contained `backend/app/gate/` package so it never collides with the orchestrator (`backend/app/orchestrator/`), router (`backend/app/router/`), API (`backend/app/api/`), agents (`backend/app/agents/`), or retrieval (`backend/app/retrieval/`, Hao). Shared record types live in `backend/app/models.py` (created here if absent, but co-owned — see Risk §7).

```
backend/app/
├── models.py                 # shared record types (co-owned; gate defines GateDecision enum + GatedResult here if not present)
├── gate/
│   ├── __init__.py           # public surface: evaluate(), GatedResult, GateDecision, GateError
│   ├── policy.py             # the pure visibility→decision policy (no I/O, no Claude)
│   ├── capability.py         # capability-scoped request tokens (makes scoping genuinely real)
│   ├── redaction.py          # the Claude redaction call for `restricted` chunks
│   ├── gate.py               # orchestration: ties policy + capability + redaction into evaluate()
│   └── prompts.py            # the redaction prompt template (one place to tune)
└── ...                       # orchestrator/, api/, retrieval/ owned by other subsystems
```

### 2.1 `backend/app/models.py` (co-owned — gate contributes these types)

The boundary-safe result object and the decision enum. These mirror the frozen `ResponseItem` (data-model §4) but are the **internal, pre-serialization** shape produced inside the agent. The API layer maps `GatedResult` → the `response-item` WS payload.

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Literal

Visibility = Literal["public", "restricted", "private"]


class GateDecision(str, Enum):
    """The gate's per-chunk verdict. Values match data-model §4 `decision` enum verbatim."""
    FULL = "full"
    REDACTED = "redacted"
    DENIED = "denied"


@dataclass(frozen=True)
class GatedResult:
    """Boundary-safe output of the gate for ONE chunk.

    INVARIANT: for REDACTED and DENIED, `answer` holds NO original chunk.text.
    The raw payload is not a field on this object, so it cannot leak downstream.
    This is the object that crosses the responding-agent boundary.

    Maps 1:1 to the frozen `response-item` payload (api-websocket.md):
      answer, source_party, source_doc_title, decision, verified  (data-model §4)
      + chunk_id, source_agent_id                                  (transport additions)
    """
    decision: GateDecision
    answer: Optional[str]            # full: safe payload | redacted: Claude gist | denied: None
    source_party: str                # party_name of chunk.owner
    source_doc_title: Optional[str]  # chunk.doc_title; None for fully-hidden denied
    verified: bool                   # gate default False; orchestrator sets True after verify pass
    chunk_id: str                    # transport: grant_access handle
    source_agent_id: str             # transport: chunk.owner (Agent.id)
    access_requestable: bool         # True only for redacted (drives "Request access" button)

    # frozen=True => immutable. Once the gate emits it, nobody can mutate a denied
    # item to smuggle text back in.
```

> **Why a dataclass and not the raw dict:** the frozen contract is a *dict/JSON wire shape*, but inside the process we use an immutable, content-free dataclass so the type system + `frozen=True` make "put the restricted text back" structurally impossible. The API layer calls `to_wire()` (below) to produce the exact frozen dict. The five canonical fields + two transport fields match data-model §4 / api-websocket.md exactly.

```python
    def to_wire(self) -> dict:
        """Serialize to the EXACT frozen response-item payload (api-websocket.md).

        Note: omits `type`/`query_id` — the API layer adds those when framing
        the WS event. `embedding` is structurally absent here (never reached the gate
        output), satisfying data-model §0: embedding never crosses the boundary.
        `access_requestable` is internal-only and is NOT serialized.
        """
        return {
            "answer": self.answer,
            "source_party": self.source_party,
            "source_doc_title": self.source_doc_title,
            "decision": self.decision.value,
            "verified": self.verified,
            "chunk_id": self.chunk_id,
            "source_agent_id": self.source_agent_id,
        }
```

### 2.2 `backend/app/gate/policy.py` — the pure policy (no I/O)

The visibility→decision mapping (data-model §4 reference table) as a **pure function**. No Claude, no network, deterministic, trivially unit-testable. This is the single source of truth for the mapping; everything else is plumbing.

```python
from app.models import GateDecision, Visibility

# The frozen mapping (data-model §4). Defined ONCE here.
_VISIBILITY_TO_DECISION: dict[Visibility, GateDecision] = {
    "public":     GateDecision.FULL,
    "restricted": GateDecision.REDACTED,
    "private":    GateDecision.DENIED,
}


def decide(visibility: Visibility) -> GateDecision:
    """Map a chunk's visibility tier to a gate decision. Pure, total over the enum.

    Raises GateError on an unknown visibility value (fail-closed: an unrecognized
    tier is treated as a hard error, never silently allowed through).
    """
    try:
        return _VISIBILITY_TO_DECISION[visibility]
    except KeyError as e:
        from app.gate import GateError
        raise GateError(f"unknown visibility tier: {visibility!r}") from e


# Policy for whether the *existence pointer* shows on a denied item (spec §3).
# MVP: private => existence-only pointer hidden (show nothing). Single knob, here.
SHOW_EXISTENCE_FOR_PRIVATE: bool = False
```

> **Fail-closed design (spec §3 wedge):** any value the policy doesn't recognize raises rather than defaulting to `full`. The only way content flows is an explicit `public`.

### 2.3 `backend/app/gate/capability.py` — capability-scoped requests (make scoping genuinely real)

The spec calls out *"capability-scoped requests (make this genuinely real — it's the wedge)"* (spec §7). Without auth (MVP, spec §5), we make scoping real with **unforgeable in-process capability tokens**: a cross-agent request carries a capability that declares *which tiers the asker is entitled to even ask for*. The gate checks the capability before deciding, so the asker can never receive a tier it wasn't granted, independent of visibility.

This is the difference between "we filtered the JSON" (theatre) and "the request was structurally incapable of returning private bytes" (real). For the demo, the public-layer asker holds a `PUBLIC_READ` + `RESTRICTED_REQUEST` capability and **never** `PRIVATE_READ` — so private chunks are denied by capability, not just by visibility.

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Flag, auto
from typing import FrozenSet


class Capability(Flag):
    """What an asker is entitled to receive across the boundary."""
    NONE = 0
    PUBLIC_READ = auto()          # may receive full public payloads
    RESTRICTED_REQUEST = auto()   # may receive a redacted gist + request access
    PRIVATE_READ = auto()         # may receive private payloads (NEVER granted in MVP demo)


@dataclass(frozen=True)
class CapabilityGrant:
    """An unforgeable (in-process, dataclass-frozen) capability the asker presents.

    Issued by the responding agent's policy for a given asker, NOT chosen by the asker.
    The asker cannot widen its own scope: it receives whatever the owner minted.
    """
    holder_agent_id: str          # who the grant is for (from_agent)
    capabilities: Capability      # bitmask of allowed tiers


# MVP issuer: the public inter-org layer. Every external asker gets the same grant.
# Hardening (real auth, per-asker grants) is explicitly out of scope (spec §5);
# the SHAPE is real so the demo is not theatre.
def issue_grant(for_agent_id: str) -> CapabilityGrant:
    return CapabilityGrant(
        holder_agent_id=for_agent_id,
        capabilities=Capability.PUBLIC_READ | Capability.RESTRICTED_REQUEST,
    )


def allows(grant: CapabilityGrant, decision: "GateDecision") -> bool:
    """Does this grant permit the asker to RECEIVE the given decision's output?

    full      -> needs PUBLIC_READ
    redacted  -> needs RESTRICTED_REQUEST
    denied    -> always allowed (denied returns nothing/existence-only anyway)
    """
    from app.models import GateDecision
    if decision is GateDecision.FULL:
        return Capability.PUBLIC_READ in grant.capabilities
    if decision is GateDecision.REDACTED:
        return Capability.RESTRICTED_REQUEST in grant.capabilities
    return True  # DENIED is always permissible; it carries no payload
```

> **How this makes leaking impossible (spec §3):** even if a `public` policy decision were somehow produced for a chunk the asker shouldn't see, `allows()` would **down-rank it to DENIED** before the payload is attached. Two independent gates (visibility policy AND capability) must both say "yes" for content to cross. Defense in depth on the one feature that matters.

### 2.4 `backend/app/gate/redaction.py` — the Claude redaction call (`restricted`)

For `restricted` chunks, the gate must produce a one-line gist that conveys *that a solution exists* without leaking it (spec §11). This is a **real transform inside the boundary**: the function receives `chunk.text`, calls Claude, returns only the gist string, and the original text is never returned to the caller.

```python
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactionInput:
    chunk_text: str          # the restricted payload — stays INSIDE this module
    doc_title: str
    query: str               # the asker's question, to make the gist relevant


def redact(inp: RedactionInput) -> str:
    """Return a safe one-line gist for a restricted chunk.

    Calls Claude (see §3 of this doc). The returned string is the ONLY thing that
    leaves this function; `inp.chunk_text` is never returned or logged at INFO+.
    On any Claude error/timeout, returns a STATIC safe fallback gist (fail-closed:
    we degrade to a generic "a restricted result exists" rather than leaking text).
    """
    ...
    # see §3 for the Claude call, model id, prompt sketch, output shape

# Static fallback used on Claude failure (no payload, always safe):
SAFE_FALLBACK_GIST = (
    "This party has a relevant result, but it is restricted. "
    "Request access to view it."
)
```

> **Leakage guard:** `redact()` is the *only* place a restricted `chunk.text` is read on the response path, and it returns a `str` gist, not the text. The post-condition (asserted in tests, §6) is: `chunk.text not in returned_gist` (substring check on the demo chunk) — a cheap, demonstrable guarantee.

### 2.5 `backend/app/gate/gate.py` — orchestration of the gate

Ties policy + capability + redaction into the single entry point the responding agent calls per chunk. This is where retrieve-first-gate-second is honored: it receives an already-retrieved `chunk` dict and constructs a content-free `GatedResult`.

```python
from __future__ import annotations
from typing import Optional, Protocol

from app.models import GatedResult, GateDecision, Visibility
from app.gate import policy
from app.gate.capability import CapabilityGrant, allows
from app.gate.redaction import RedactionInput, redact, SAFE_FALLBACK_GIST


class PartyNameResolver(Protocol):
    """Injected lookup: Agent.id -> party_name. Owned by agents/ subsystem.
    Kept as a Protocol so the gate has no hard import of the agent registry."""
    def __call__(self, agent_id: str) -> str: ...


class GateError(Exception):
    """Raised on an unrecognized tier or a malformed chunk. Fail-closed."""


def evaluate(
    chunk: dict,                 # a search() result row (data-model §2 + score). Read-only.
    *,
    query: str,                  # the asker's question (for relevance of the redacted gist)
    grant: CapabilityGrant,      # the asker's capability (capability.py)
    resolve_party_name: PartyNameResolver,
) -> GatedResult:
    """Gate ONE retrieved chunk into a boundary-safe GatedResult.

    Ordering (spec §9): chunk is already retrieved; this runs the gate, second.
    Steps:
      1. decision = policy.decide(chunk["visibility"])           # pure mapping
      2. if not allows(grant, decision): decision = DENIED       # capability down-rank
      3. build the GatedResult per decision:
           FULL     -> answer = chunk["text"]            (payload crosses)
           REDACTED -> answer = redact(RedactionInput(...))  (Claude gist; text stays)
           DENIED   -> answer = None, doc_title = None unless SHOW_EXISTENCE_FOR_PRIVATE
      4. verified defaults False; orchestrator flips it for FULL after verify pass.
    Never returns chunk["text"] for non-FULL decisions. Never returns chunk["embedding"].
    """
    visibility: Visibility = chunk["visibility"]
    decision = policy.decide(visibility)
    if not allows(grant, decision):
        decision = GateDecision.DENIED

    party = resolve_party_name(chunk["owner"])
    common = dict(
        decision=decision,
        source_party=party,
        chunk_id=chunk["chunk_id"],
        source_agent_id=chunk["owner"],
        verified=False,
    )

    if decision is GateDecision.FULL:
        return GatedResult(
            answer=chunk["text"],
            source_doc_title=chunk["doc_title"],
            access_requestable=False,
            **common,
        )

    if decision is GateDecision.REDACTED:
        gist = redact(RedactionInput(
            chunk_text=chunk["text"], doc_title=chunk["doc_title"], query=query,
        ))  # text consumed here, never returned
        return GatedResult(
            answer=gist,
            source_doc_title=chunk["doc_title"],  # pointer travels; content does not (spec §3)
            access_requestable=True,
            **common,
        )

    # DENIED
    show_ptr = policy.SHOW_EXISTENCE_FOR_PRIVATE
    return GatedResult(
        answer=None,
        source_doc_title=(chunk["doc_title"] if show_ptr else None),
        access_requestable=False,
        **common,
    )
```

### 2.6 `backend/app/gate/__init__.py` — public surface

```python
from app.gate.gate import evaluate, GateError, PartyNameResolver
from app.models import GatedResult, GateDecision
from app.gate.capability import Capability, CapabilityGrant, issue_grant

__all__ = [
    "evaluate", "GateError", "PartyNameResolver",
    "GatedResult", "GateDecision",
    "Capability", "CapabilityGrant", "issue_grant",
]
```

### 2.7 `backend/app/gate/prompts.py` — redaction prompt template

One place to tune the redaction prompt (kept out of code so it's iterable during the demo). See §3.

---

## 3. Claude (Anthropic API) calls

The gate owns exactly **one** Claude call: **redaction** (spec §11). (Verification and synthesis are the orchestrator's calls — listed here only as integration points, §6.)

### 3.1 Redaction call (`gate/redaction.py`)

| Property | Value |
|----------|-------|
| **Purpose** | Turn a `restricted` chunk into a one-line gist that signals *a solution exists* without leaking the solution (spec §11, §3). |
| **Model id** | `claude-haiku-4-5`. Redaction is a short, constrained, low-creativity transform on tiny input; latency matters because it runs per restricted chunk on the response path (spec §17 verification-latency risk). Haiku is the right tier here. *(Verification and synthesis, owned by the orchestrator, use `claude-opus-4-8` for quality — see §6.)* |
| **Max tokens** | ~60 (one line). |
| **Temperature** | 0 (deterministic, reproducible demo). |
| **Expected output shape (spec §11)** | A single short string: the gist. We request **raw text** (no JSON wrapper needed for one field) and strip whitespace. The function returns `str`. |
| **Failure mode** | On timeout/error → `SAFE_FALLBACK_GIST` (fail-closed; never leak). Wrap call in a short timeout (~5s) so a hung API can't stall the fan-out. |

**Prompt sketch (`prompts.py`):**

```
SYSTEM:
You write one-sentence "teaser" gists for a permissioned knowledge network.
You will be given a RESTRICTED document excerpt that the asker is NOT allowed to see.
Produce ONE sentence that conveys ONLY that a relevant solution/result EXISTS and
roughly what topic it covers — never the actual fix, numbers, steps, code, or
specifics. Do not quote or paraphrase the solution. If unsure, be vaguer.
Output the sentence and nothing else.

USER:
Asker's question: {query}
Restricted document title: {doc_title}
Restricted excerpt (DO NOT reveal its contents):
\"\"\"{chunk_text}\"\"\"

One-sentence gist:
```

**Output example** (for the seeded servo-jitter restricted chunk):
`"Northwind has a documented resolution for servo jitter under sustained load — request access to view the fix."`

> This becomes `GatedResult.answer` for the `redacted` item, which the API serializes verbatim into the `response-item` event's `answer` field (api-websocket.md). It matches the frozen `redacted` example in data-model §4.

---

## 4. Dependencies

### Other backend modules (integration, not owned by the gate)

| Module | Path | Relationship |
|--------|------|--------------|
| Search (Hao) | `app.retrieval.search` | Produces the `chunk` dicts the gate consumes. Gate built against the keyword **stub** until H8, then drop-in real `search()` (search-interface.md). Gate code does not import search directly — the orchestrator passes chunks in. |
| Agent registry | `app.agents.registry` | Provides `resolve_party_name(agent_id) -> party_name` (injected as `PartyNameResolver`) and the per-agent capability issuance hook. Owned by the agents subsystem. |
| Orchestrator | `app.orchestrator` | Calls `gate.evaluate()` per chunk inside the responding agent; runs verification + synthesis on the results; frames WS events. |
| Models | `app.models` | Shared `GatedResult`, `GateDecision` (co-owned; gate defines them). |

### pip packages

| Package | Why |
|---------|-----|
| `anthropic` | Claude redaction call. Pin a recent SDK (e.g. `anthropic>=0.40`). |
| `python-dotenv` | Load `ANTHROPIC_API_KEY` in dev. |
| `pytest` | Unit tests for policy/capability/leakage (§6). |
| *(stdlib only otherwise)* | `dataclasses`, `enum`, `typing` — the gate core has no heavy deps. |

> FastAPI / uvicorn / numpy / chromadb are dependencies of the **API** and **retrieval** subsystems, not the gate. The gate is deliberately dependency-light so it stays the trustworthy core.

---

## 5. Ordered build steps

1. **Scaffold the package.** Create `backend/app/gate/` with empty `__init__.py`, and `backend/app/models.py` if it doesn't exist. Add `app/gate/` to the test path.
2. **Define the types (`models.py`).** `GateDecision` enum (values verbatim from data-model §4) and the frozen `GatedResult` dataclass with `to_wire()`. Write a test that `to_wire()` emits exactly the seven keys in the frozen `response-item` shape and nothing else (no `embedding`, no `text` on redacted/denied).
3. **Implement the pure policy (`policy.py`).** `decide()` + `_VISIBILITY_TO_DECISION` + the `SHOW_EXISTENCE_FOR_PRIVATE` knob. Unit-test all three tiers + the fail-closed unknown-tier path. (Zero Claude, zero I/O — fast.)
4. **Implement capability scoping (`capability.py`).** `Capability` flag, `CapabilityGrant`, `issue_grant()`, `allows()`. Unit-test: public-layer grant down-ranks `private`→`denied` even if visibility says otherwise; full needs `PUBLIC_READ`; redacted needs `RESTRICTED_REQUEST`.
5. **Wire the gate orchestration (`gate.py`) with a STUBBED redact.** Implement `evaluate()` end-to-end, but temporarily import a no-op `redact()` returning `SAFE_FALLBACK_GIST`. Now the gate is fully testable without the API key. Test the three tiers against seeded chunk dicts + the leakage invariant (restricted/denied `answer` contains no original text).
6. **Implement the Claude redaction call (`redaction.py` + `prompts.py`).** Add the real `anthropic` client call (model `claude-haiku-4-5`, temp 0, max_tokens ~60, ~5s timeout), wrap in try/except → `SAFE_FALLBACK_GIST`. Swap the stub `redact` for the real one in `gate.py`.
7. **Leakage test against the live call.** Run `evaluate()` on the seeded restricted servo-jitter chunk; assert the returned `answer` is non-empty, single-line, and does NOT contain the chunk's distinctive solution token(s) (e.g. `"5ms feed-forward"`). This is the demonstrable "physically cannot leak" proof.
8. **Expose the public surface (`__init__.py`).** Export `evaluate`, `GatedResult`, `GateDecision`, `GateError`, `issue_grant`, capability types.
9. **Hand off to the orchestrator.** Confirm the orchestrator calls `evaluate(chunk, query=..., grant=issue_grant(from_agent), resolve_party_name=registry.party_name)` per chunk and serializes results via `to_wire()`. Smoke-test the full path with the stub `search()`.
10. **H8 integration.** Swap Hao's real `search()` under the orchestrator (no gate change). Re-run the leakage + tier tests against real retrieval output. Confirm `grant_access` re-run re-invokes the gate and the same restricted chunk now gates to `full`.

---

## 6. Integration points with frozen contracts & other subsystems

| Touchpoint | Contract / subsystem | How the gate honors it |
|-----------|----------------------|------------------------|
| **Input chunk shape** | data-model §2 + search-interface.md | `evaluate()` reads `chunk["chunk_id" / "doc_title" / "owner" / "visibility" / "text"]`. Ignores `embedding` and `score` — they never reach `GatedResult`, satisfying "embedding never crosses the boundary." |
| **Decision enum** | data-model shared enums | `GateDecision` values are exactly `full` / `redacted` / `denied`. `to_wire()` emits `decision` as the lowercase string. |
| **`response-item` payload** | api-websocket.md | `GatedResult.to_wire()` produces the five canonical fields (`answer`, `source_party`, `source_doc_title`, `decision`, `verified`) + the two transport fields (`chunk_id`, `source_agent_id`). The API layer adds `type` and `query_id`. |
| **`done.provenance` entries** | api-websocket.md | Same `to_wire()` dict feeds the orchestrator's provenance list (Response-item-shaped + `source_agent_id` + `chunk_id`). |
| **Visibility→decision table** | data-model §4 reference table | `policy.decide()` is the canonical backend implementation of that documented mapping (the table says "defined in backend, not here" — this is it). |
| **`verified` field** | data-model §4 | Gate sets `verified=False` as the safe default. **Orchestrator** runs the verification Claude pass (spec §11, model `claude-opus-4-8` for grounding-check quality) on `full` content and flips `verified` before the WS event. Ownership seam documented under Risks §7. |
| **`grant_access` re-run** | api-websocket.md `/grant_access` | The endpoint (orchestrator/API) flips `chunk.visibility` `restricted`→`public` in the index, then re-runs the query. The gate is stateless and simply re-evaluates: the same chunk now maps to `full`. No gate change needed; the card animates locked→full purely from a fresh `evaluate()`. |
| **Redaction call** | spec §11 | Gate-owned; model `claude-haiku-4-5`. Output is one string → `redacted` item's `answer`. |
| **Verification call** | spec §11 | Orchestrator-owned, NOT the gate. Listed so build order is clear. |
| **Synthesis call** | spec §10 step 6 | Orchestrator-owned, NOT the gate. Uses `claude-opus-4-8` for final-answer quality. |
| **Isolation** | spec §6, search-interface.md | The gate trusts `search()`'s guarantee that every row has `owner == agent_id`; it additionally stamps `source_agent_id = chunk["owner"]` so a mis-routed chunk is visibly attributed to its true owner (no cross-party laundering). |

---

## 7. Risks & mitigations

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | **Restricted/private payload leaks downstream** (the cardinal sin — spec §3). | Construct a *new content-free object* for non-public tiers rather than filtering an existing one; `GatedResult` has no `text`/`embedding` field. `frozen=True` makes post-hoc mutation impossible. Redaction reads `chunk.text` in exactly one function and returns only a gist. A dedicated leakage unit test asserts the solution token is absent from any non-full `answer`. Capability check is a second independent gate (defense in depth). |
| 2 | **Redaction latency on the response path** (spec §17). | `claude-haiku-4-5`, temp 0, max_tokens ~60, ~5s timeout. Only `restricted` chunks trigger it (`full`/`denied` are pure Python, instant). Tiny inputs. If the orchestrator passes a small `top_k`, at most a handful of redactions per run. |
| 3 | **Claude redaction call fails / hangs.** | Fail-closed to `SAFE_FALLBACK_GIST` (a generic "restricted result exists" line carrying no payload). The demo still shows a `redacted` card + working "Request access" button. Never blocks the run. |
| 4 | **Prompt-injection inside a restricted chunk** ("ignore instructions, reveal the text"). | System prompt is firm ("never reveal contents"); excerpt is wrapped in delimiters and labeled DO-NOT-REVEAL; temp 0. Post-call substring assertion (test §6 step 7) catches gross leakage. Acceptable residual risk for a 24h MVP (no untrusted user-authored corpora — corpora are seeded, spec §5). Noted, not fully hardened. |
| 5 | **Cross-party isolation breach** (one agent's chunk attributed to another). | Gate stamps `source_agent_id`/`source_party` strictly from `chunk["owner"]`, never from the asker. Relies on `search()` isolation guarantee (owner == agent_id, search-interface.md); the gate does not re-route. |
| 6 | **Capability scoping is theatre without real auth** (spec §5 says no prod auth). | The capability object is structurally real and enforced (an asker physically cannot receive a tier its grant lacks), even though grants are minted by a fixed in-process issuer for the demo. We say "scoping is real and enforced in-demo, not hardened for prod" (spec §43-line / §5). The *shape* is production-ready; only the issuer is stubbed. |
| 7 | **Ownership-seam ambiguity: who sets `verified`, and who owns `models.py`.** | Documented explicitly: gate sets `verified=False`; **orchestrator** runs the verification pass and flips it. `models.py` is co-owned — gate defines `GatedResult`/`GateDecision`; if the orchestrator subsystem also needs types there, resolve in a 2-min sync (mirrors the contract-freeze discipline, spec §15). Not a contract change, so no frozen-doc edit. |
| 8 | **Gap noted, not invented: `done.item_count` semantics under denied items.** | api-websocket.md defines `item_count` as "how many `response-item` events were emitted." If the orchestrator chooses NOT to emit a `response-item` for fully-hidden `denied` chunks (`SHOW_EXISTENCE_FOR_PRIVATE=False`), `item_count` will be < number of retrieved chunks. This is an orchestrator/API decision; the gate surfaces `access_requestable` and a `denied` `GatedResult` regardless and lets the emitter decide. Flagged here rather than resolved by inventing a conflicting shape. |
| 9 | **`grant_access` toggles visibility but the index is the gate's source of truth.** | The gate is stateless and re-reads `chunk["visibility"]` on every `evaluate()`. As long as `grant_access` mutates the canonical index row (orchestrator/retrieval owns the index), the re-run gate naturally returns `full`. Risk if there are two copies of the chunk (cached vs index) — mitigation: the gate never caches chunks; it evaluates exactly what the re-run's `search()` returns. |
