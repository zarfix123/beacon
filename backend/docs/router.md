# Beacon Backend — BUILD doc: Router (discovery, cross-agent query, live events)

> **Status: PLAN / INDEX.** This is a build plan, not an implementation. Code blocks are
> sketches/pseudocode showing signatures and control flow, not finished functions.
> Owner: Dennis (backend). Aligns with the three frozen contracts under
> `shared/contracts/` and spec sections 6, 9, 10, 11, 15. Do not contradict the frozen
> shapes; gaps are flagged under **Risks**, not invented around.

---

## 1. Purpose and place in the query flow

The **Router** is the discovery + dispatch layer that lets the asking agent find the other
party agents and fan a query out to them, while streaming live `agent-activated` /
`response-item` / `done` events to the UI so the network graph animates (spec sections 6
and 10; UI section 12).

It owns three things and nothing else:

1. **Discovery** — an in-process **registry** of the 3 seeded agents (`agent_northwind`,
   `agent_helios`, `agent_quanta`), keyed by `Agent.id`, exposing the "who can I ask" list
   minus the asker.
2. **Dispatch / fan-out** — a `dispatch()` function that takes a
   [Cross-agent request](../../shared/contracts/data-model.md#3-cross-agent-request)
   (`{from_agent, query}`), resolves the target party set, and for **each target** invokes
   the per-agent responding pipeline (retrieve → gate → redact/verify).
3. **Live-event timing** — a thin **emit hook** the router calls at exactly the right
   moments: `agent-activated` the instant a target is dispatched (before its search), and
   `response-item` once that target's chunk has fully resolved through the gate. The
   orchestrator emits the final `done`.

Where it sits in the spec section 10 loop:

```
spec §10 step                         module that owns it
-------------------------------------- ----------------------------------------
1. User submits question               api/routes.py  (POST /query, WS frame)
2. Asker fans out to party agents  --> router.dispatch()          <-- THIS DOC
3. Each party runs cosine top-k        search() (Hao) called inside responder
4. Each passes hits through the gate    responder pipeline (gate/redaction) <- sibling
5. Asker collects + verifies            orchestrator.run_query()  <- sibling
6. Asker synthesizes + cites            orchestrator.synthesize() <- sibling
```

The router is the **fan-out engine and the event clock**. It does NOT decide gate verdicts,
does NOT call Claude, and does NOT synthesize — it *calls into* the responder pipeline that
does (the gate runs inside the responding agent, before content crosses the boundary; spec
sections 3 and 6). This keeps the wedge (gate enforcement) physically inside the responder
and keeps the router a transport concern.

### Boundary discipline (why the gate is NOT here)

Per spec sections 3/6 and the data-model gate table: enforcement runs **inside the
responding agent before content crosses the boundary**. The router's contract with a
responder is "give me a finished, already-gated `ResponseItem`." The router never sees raw
`restricted`/`private` `text`; it receives only what the responder chose to release. That
ordering (retrieve first, gate second, *then* hand to router) is the product, so it is
enforced by module boundary, not convention.

---

## 2. Files / modules to create under `backend/app/`

All router-owned code lives under `backend/app/router/` plus one shared event-bus module.
Paths are chosen to NOT collide with the sibling subsystems (the API layer, the
gate/redaction/verification responder pipeline, the orchestrator, and Hao's retrieval).

```
backend/app/
├── router/
│   ├── __init__.py          # re-exports Router, dispatch, build_default_router
│   ├── registry.py          # AgentRegistry: discovery over the 3 seeded agents
│   ├── dispatch.py          # Router.dispatch(): fan-out + per-target pipeline call
│   └── types.py             # router-local TypedDicts: DispatchTarget, AgentRecord
├── events/
│   ├── __init__.py
│   └── bus.py               # EventBus: async pub/sub keyed by query_id (WS fan-in)
│
│  # --- referenced, owned by sibling subsystems (NOT created here) ---
├── agents/
│   └── responder.py         # respond_for_agent(): retrieve→gate→redact/verify  (sibling)
├── orchestrator.py          # run_query(), synthesize(), emits `done`            (sibling)
├── gate.py                  # visibility→decision + redaction/verification calls (sibling)
├── retrieval.py             # search() — Hao's substrate (stub until H8)         (sibling)
├── api/routes.py            # POST /query, /grant_access, WS /ws/query           (sibling)
└── models.py                # Pydantic models for the frozen wire shapes         (shared)
```

> Path-collision note: the gate/redaction/verification, orchestrator, and API are also
> Dennis's, but they get their own files. The router strictly does not write into
> `gate.py`, `orchestrator.py`, `api/routes.py`, or `retrieval.py`. The only new shared
> surface the router introduces is `events/bus.py`, which the orchestrator and API also
> import (single event channel — see §6).

### 2.1 `router/types.py` — router-local shapes

Small TypedDicts the router passes around internally. These are NOT new wire shapes (the
wire shapes are frozen in `data-model.md` / `api-websocket.md`); they are in-process helpers.

```python
from typing import TypedDict, Callable, Awaitable

class AgentRecord(TypedDict):
    """A registry entry. Superset of the frozen Agent record (data-model §1)
    plus the in-process handle used to call that agent's responder pipeline."""
    id: str            # Agent.id, e.g. "agent_northwind"  (frozen, data-model §1)
    party_name: str    # display name                      (frozen, data-model §1)
    scope_policy: str  # "three_tier" for MVP              (frozen, data-model §1)

class DispatchTarget(TypedDict):
    """One party the asker will fan out to."""
    agent_id: str
    party_name: str
```

### 2.2 `router/registry.py` — discovery

In-process registry of the 3 agents. Built once at startup from the seed manifest. Pure
data + lookup; no I/O, no Claude, no async.

```python
class AgentRegistry:
    def __init__(self, agents: list[AgentRecord]) -> None:
        self._by_id: dict[str, AgentRecord] = {a["id"]: a for a in agents}

    def get(self, agent_id: str) -> AgentRecord:
        """Raise KeyError on unknown id (mirrors search()'s contract)."""
        return self._by_id[agent_id]

    def all_ids(self) -> list[str]:
        ...

    def discover(self, from_agent: str) -> list[DispatchTarget]:
        """Discovery: every party EXCEPT the asker, in stable order.
        This list is exactly the `agents` array returned by POST /query
        (api-websocket §POST /query) and the set of nodes that will pulse.
        Raises KeyError if from_agent is unknown."""
        return [
            {"agent_id": a["id"], "party_name": a["party_name"]}
            for aid, a in self._by_id.items()
            if aid != from_agent
        ]

def build_default_registry(seed_path: str = "data/agents.json") -> AgentRegistry:
    """Load the 3 locked agents from the seed manifest at startup."""
    ...
```

> **Self-exclusion is deliberate.** When `from_agent` is one of the 3 (e.g. the
> `api-websocket.md` example uses `agent_helios` as asker), discovery returns the **other 2**
> — which is why that contract example shows `agents: ["agent_northwind","agent_quanta"]`
> and `item_count: 2`. If `from_agent` is the default demo asker id that is *not* one of the
> 3 parties, discovery returns all 3. See **Risks** for the asker-identity gap.

### 2.3 `router/dispatch.py` — fan-out + event timing

The heart of the subsystem. Resolves targets, emits `agent-activated` per target *before*
search, calls the responder pipeline per target, emits `response-item` when each resolves.

```python
from typing import Callable, Awaitable, Optional
from app.router.registry import AgentRegistry
from app.router.types import DispatchTarget
from app.events.bus import EventBus

# Injected responder: the sibling responder pipeline (agents/responder.py).
# Signature is the router's only coupling to the gate/redaction subsystem.
ResponderFn = Callable[[str, str], Awaitable[list["ResponseItem"]]]
#               (agent_id, query) -> already-gated ResponseItems for that agent
#  ResponseItem == the frozen data-model §4 shape (+ chunk_id, source_agent_id transport fields)

class Router:
    def __init__(
        self,
        registry: AgentRegistry,
        bus: EventBus,
        responder: ResponderFn,
        max_concurrency: int = 3,
    ) -> None:
        ...

    async def dispatch(
        self,
        query_id: str,
        from_agent: str,
        query: str,
    ) -> list["ResponseItem"]:
        """Fan a Cross-agent request out to every discovered party.

        For each target, IN ORDER OF DISPATCH:
          1. emit `agent-activated` (node pulse)        <-- before search
          2. await responder(agent_id, query)           <-- retrieve→gate→transform
          3. emit one `response-item` per returned item <-- after gate
        Returns the flat list of all items (for the orchestrator to verify/synthesize).
        The orchestrator emits `done` after this returns.

        Targets run CONCURRENTLY (asyncio.gather) so nodes pulse together and the
        graph lights up at once; `agent-activated` is emitted for ALL targets before
        any responder is awaited, so the UI sees the full fan-out instantly.
        """
        targets = self.registry.discover(from_agent)   # KeyError -> 404 upstream

        # Phase 1: light up every node immediately (pulse before any latency).
        for t in targets:
            await self.bus.emit(query_id, agent_activated_event(query_id, t))

        # Phase 2: run each responder; stream response-items as they resolve.
        async def run_one(t: DispatchTarget) -> list["ResponseItem"]:
            items = await self.responder(t["agent_id"], query)  # gate runs INSIDE here
            for item in items:
                await self.bus.emit(query_id, response_item_event(query_id, item))
            return items

        results = await asyncio.gather(*(run_one(t) for t in targets))
        return [item for sub in results for item in sub]
```

Event-builder helpers (pure dict construction matching the frozen WS payloads in
`api-websocket.md`; no logic):

```python
def agent_activated_event(query_id: str, t: DispatchTarget) -> dict:
    return {
        "type": "agent-activated",
        "query_id": query_id,
        "agent_id": t["agent_id"],
        "party_name": t["party_name"],
        "status": "searching",          # single MVP value, frozen
    }

def response_item_event(query_id: str, item: "ResponseItem") -> dict:
    # item already carries the 5 canonical fields + chunk_id + source_agent_id.
    return {"type": "response-item", "query_id": query_id, **item}
```

> **Concurrency choice (frozen-compatible):** the contract says `response-item` "may arrive
> in any order across parties; client keys cards by `source_agent_id`." So concurrent
> fan-out is explicitly allowed and is the better demo (all nodes pulse at once). If a
> deterministic demo cadence is wanted, swap `gather` for a sequential `for` loop with a
> small `asyncio.sleep` — same events, controlled order. Kept behind `max_concurrency`.

### 2.4 `events/bus.py` — the live-event channel

A tiny in-process async pub/sub so `dispatch()` (and the orchestrator's `done`) can emit
without holding a reference to the WebSocket. The WS handler in `api/routes.py` subscribes
per `query_id` and forwards frames to the socket. This is the seam that makes both transport
options in `api-websocket.md` (WS-driven and POST+WS) work off one code path.

```python
import asyncio

class EventBus:
    def __init__(self) -> None:
        # query_id -> set of subscriber queues
        self._subs: dict[str, set[asyncio.Queue]] = {}

    def subscribe(self, query_id: str) -> asyncio.Queue:
        """WS handler calls this on connect; returns a queue of event dicts."""
        ...

    def unsubscribe(self, query_id: str, q: asyncio.Queue) -> None:
        ...

    async def emit(self, query_id: str, event: dict) -> None:
        """Push one event dict to every subscriber for this query_id.
        Non-blocking per subscriber (drop/never-block policy — see Risks)."""
        for q in self._subs.get(query_id, ()):
            q.put_nowait(event)
```

> Single shared `EventBus` instance lives in app state (`app.state.bus`), constructed at
> startup and injected into both the `Router` and the orchestrator. One channel, three event
> types, correlated by `query_id`.

---

## 3. Claude (Anthropic API) calls

**The router itself makes ZERO Claude calls.** This is intentional and on-spec: the two
real Claude calls (spec section 11) — **redaction** and **verification** — run *inside the
responder pipeline / orchestrator*, which are sibling modules. The router only triggers them
indirectly by awaiting `responder(agent_id, query)`. The synthesis call also belongs to the
orchestrator. Documented here so the boundary is explicit and to avoid duplicating the call
in the router by mistake.

For completeness (so the integration contract is clear), the calls the router *depends on*
the responder/orchestrator to make, per spec section 11:

| Call | Owner module | Model | Purpose | Output shape (spec §11) |
|------|--------------|-------|---------|--------------------------|
| **Redaction** | `gate.py` (responder) | `claude-opus-4-8` | For a `restricted` chunk: produce a one-line gist that conveys *that* a fix exists without leaking the payload. Content never crosses the boundary. | `{ "gist": str }` → becomes `ResponseItem.answer` for the `redacted` item. |
| **Verification** | `gate.py` / orchestrator | `claude-haiku-4-5` | For returned `full` content: "is this answer supported by the cited chunk, yes/no?" | `{ "verified": bool, "reason": str }` → `ResponseItem.verified`. |
| **Synthesis** | `orchestrator.py` | `claude-opus-4-8` | Combine verified items into the final cited answer + provenance. | `{ "synthesized_answer": str }` → the `done` event. |

**Model-choice rationale.** Use `claude-opus-4-8` for **redaction** and **synthesis**: both
are user-facing prose where leakage (redaction) or citation faithfulness (synthesis) is the
whole product, so quality wins. Use the cheaper `claude-haiku-4-5` for **verification**: it
is a constrained yes/no grounding check over a tiny chunk, latency-sensitive on the demo
path (spec section 17 calls out verification latency), and does not need top-tier reasoning —
a clear fit for the cheaper tier. These choices belong to the responder/orchestrator docs;
restated here only to pin the boundary.

**Redaction prompt sketch** (lives in `gate.py`, shown so the router→responder contract is
unambiguous):

```
System: You enforce a knowledge-sharing permission boundary. You are given a RESTRICTED
chunk owned by one party. Emit ONE sentence that signals a solution EXISTS and its topic,
revealing NO specifics (no numbers, parameters, code, root cause). Output JSON: {"gist": "..."}.

User: TOPIC HINT (from query): {query}
RESTRICTED CHUNK (never reveal verbatim): {chunk.text}
DOC TITLE (safe to name): {chunk.doc_title}
```

The router receives back only the finished `ResponseItem` (with `answer` = that gist), so
the raw `text` of a restricted chunk physically never reaches router code.

---

## 4. Dependencies

### Other backend modules
- `app/models.py` — Pydantic models for the frozen wire shapes (`ResponseItem`, the three
  WS event frames). Shared; the router imports `ResponseItem` for typing.
- `app/agents/responder.py` — `respond_for_agent(agent_id, query) -> list[ResponseItem]`
  (the gate/redaction-bearing pipeline). Injected into `Router` as `ResponderFn`. **Sibling
  subsystem**; the router only needs its signature, so the router can be built and tested
  against a fake responder before the real one exists.
- `app/retrieval.py` — `search()` (Hao). The router never calls it directly; the responder
  does. Listed because the responder the router awaits depends on it.
- `app/orchestrator.py` — calls `Router.dispatch()`, then verifies/synthesizes and emits
  `done`. Consumer of the router, not a dependency of it.

### pip packages
- `fastapi` — app + WebSocket route (consumed in `api/routes.py`, not in router core).
- `uvicorn[standard]` — ASGI server (`websockets` extra for the WS).
- `pydantic` (v2, ships with FastAPI) — wire-shape validation in `models.py`.
- `anthropic` — only used by the responder/orchestrator; the router does not import it.
- stdlib `asyncio` — fan-out (`gather`) and the event bus. No extra package.

> The router core (`registry.py`, `dispatch.py`, `events/bus.py`) depends on **only stdlib +
> typing**. FastAPI/anthropic stay in sibling modules. This keeps the router unit-testable
> with no server and no API key.

---

## 5. Ordered build steps

1. **Scaffold** `backend/app/router/` and `backend/app/events/` with empty `__init__.py`s.
   Add `backend/app/data/agents.json` seed manifest with the 3 locked agents
   (`agent_northwind`, `agent_helios`, `agent_quanta`) — ids and `party_name`s from
   `data-model.md §1`, `scope_policy: "three_tier"`.
2. **`events/bus.py`** — implement `EventBus` (subscribe / unsubscribe / `emit` with
   `put_nowait`). Unit-test: subscribe two queues to one `query_id`, emit, assert both
   receive; emit to an id with no subs is a no-op.
3. **`router/types.py`** — `AgentRecord`, `DispatchTarget` TypedDicts.
4. **`router/registry.py`** — `AgentRegistry` + `build_default_registry()`. Unit-test:
   `discover("agent_helios")` returns the other two in stable order; unknown id raises
   `KeyError`; default-asker (non-party) id returns all 3.
5. **Event builders** in `dispatch.py` — `agent_activated_event`, `response_item_event`.
   Assert their dict output byte-matches the frozen examples in `api-websocket.md` (field
   names, `type` literals, `status:"searching"`).
6. **`router/dispatch.py`** — `Router.dispatch()` against a **fake responder** that returns
   canned `ResponseItem`s (one `full`, one `redacted`, one `denied`) so the router is
   exercised before the real gate exists. Unit-test the event sequence: N `agent-activated`
   emitted before any `response-item`; one `response-item` per returned item; `dispatch`
   returns the flattened list.
7. **`router/__init__.py`** — re-export `Router`, `build_default_registry`, event builders.
8. **Integration seam** — hand the orchestrator a `Router` built with the **real**
   `respond_for_agent` once that sibling lands (checkpoint H8/H13). No router code changes:
   only the injected `ResponderFn` swaps from fake to real.
9. **Wire the WS** (in `api/routes.py`, sibling) — on connect, `bus.subscribe(query_id)`;
   loop `await queue.get()` → `websocket.send_json(event)`; on disconnect, `unsubscribe`.
   Smoke-test end-to-end: `POST /query` → see `agent-activated` ×2 → `response-item` ×2 →
   `done`.
10. **Grant-access re-run path** — confirm `grant_access` (sibling endpoint) re-invokes
    `Router.dispatch()` with the **same `query_id`**, producing a fresh
    `agent-activated → response-item → done` cycle on that id (api-websocket §grant_access).
    The router needs no special code for this — re-running `dispatch` is the whole mechanism.

---

## 6. Integration points with the frozen contracts and sibling subsystems

| Touch point | Frozen contract | How the router honors it |
|-------------|-----------------|--------------------------|
| Discovery list = `agents` array | `api-websocket.md` POST `/query` response | `registry.discover(from_agent)` produces exactly the `agents` array (asker excluded). `api/routes.py` returns it verbatim. |
| `agent-activated` payload | `api-websocket.md` event | `agent_activated_event()` emits `{type, query_id, agent_id, party_name, status:"searching"}` — exact keys, exact literal. |
| `response-item` payload | `api-websocket.md` event + `data-model.md §4` | Router forwards the responder's `ResponseItem` (5 canonical fields + `chunk_id` + `source_agent_id`) under `{type:"response-item", query_id, ...}`. Router adds NO fields and never sees `embedding`. |
| `done` event | `api-websocket.md` event | NOT emitted by the router — emitted by the orchestrator after `dispatch()` returns and synthesis completes. Router returns the item list that feeds `provenance` + `item_count`. |
| Cross-agent request shape | `data-model.md §3` | `dispatch(query_id, from_agent, query)` mirrors `{from_agent, query}`; `query_id` is the transport correlation id added by the API layer. |
| `search()` isolation | `search-interface.md` | Router never calls `search`; the responder does, with `owner == agent_id` isolation. Router only fans out per-agent-id, so isolation is preserved by construction (one responder call per party). |
| Gate ordering (retrieve→gate) | spec §9, §6 | Router awaits a *finished, already-gated* `ResponseItem` from the responder. The gate cannot run in the router; it has run before the router ever holds content. |
| `grant_access` re-run | `api-websocket.md` `/grant_access` | Re-invokes `Router.dispatch()` with the original `query_id`; identical event cycle streams on the same id. |
| Both WS transport options | `api-websocket.md` "Two transport options" | The `EventBus` decouples emission from the socket, so WS-driven and POST+WS share one dispatch path. |

---

## 7. Risks and mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Verification/redaction latency stalls the fan-out** (spec §17) — each `response-item` waits on a Claude call inside the responder. | High (demo feel) | Router emits all `agent-activated` events *before* awaiting any responder, so the graph lights up instantly even while content is still resolving. Concurrent `gather` overlaps the per-party Claude calls. Tiny corpora + low `top_k` + Haiku verification keep each call short. |
| **Leakage of restricted content through the router.** | Critical (it's the wedge) | Structural, not conventional: the router's only input from a party is an already-gated `ResponseItem` whose `answer` is the redaction *gist*, never raw `text`. The router has no access to `Chunk.text`/`embedding` at all. Gate runs inside the responder before return (spec §3/§6). |
| **Cross-party isolation breach** (one party's chunks bleed into another's results). | Critical | Router issues exactly one responder call per `agent_id`; the responder's `search(query, agent_id)` guarantees `owner == agent_id` (search contract). Router never aggregates indices or shares a responder across agent ids. |
| **A responder raises / hangs** (KeyError on unknown agent, Claude timeout). | Medium | Wrap each `run_one` in try/except and a per-call `asyncio.wait_for` timeout; on failure emit a synthetic `denied` `response-item` (or skip) so one slow party never blocks `done`. `discover()`'s `KeyError` on unknown `from_agent` surfaces as a 4xx in the API layer, not a crash. |
| **`done` fires before all `response-item`s** (ordering race). | Medium | Orchestrator awaits `dispatch()` (which awaits all responders) before emitting `done`. `item_count` in `done` lets the client cross-check it received that many `response-item`s. |
| **Slow/dead WS subscriber backs up the bus.** | Low | `emit` uses `put_nowait` on bounded queues; a full queue drops the frame rather than blocking dispatch. Demo is single-client, so this is a guardrail, not a hot path. |
| **GAP — asker identity is ambiguous.** `POST /query.from_agent` is optional and "defaults to a fixed demo asker." If that default equals one of the 3 parties, discovery drops it (fan-out to 2); if it's a 4th non-party id, fan-out is to all 3. The contracts show both (`agent_helios` asker → 2 targets; default → presumably 3). | Medium | Flagged per instructions rather than invented around. Recommendation for the hour-0 sync: define a non-party demo asker id (e.g. `agent_asker`) registered for discovery purposes so the default produces a clean 3-way fan-out, OR lock `agent_helios` as the demo asker so the frozen 2-target example holds. Router supports both with no code change — it just excludes whatever `from_agent` is passed. Resolve in the responder/orchestrator + API doc, not here. |
| **Same `query_id` re-run (grant_access) interleaves with a stale run's events.** | Low | The demo is sequential (grant happens after the first `done`). If concurrent re-runs were ever allowed, add a monotonically increasing `run_seq` inside the bus envelope — noted as a non-MVP extension, not built now. |
