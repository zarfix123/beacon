# Beacon Backend — BUILD: Grant-Access-Live (the hero beat)

> **Status: BUILD PLAN (index, not implementation).** Owner: Dennis (backend). Frontend half (button + animation): Hao.
> This is a plan/index — file responsibilities, signatures, Claude-call sketches, build order. Code blocks are **sketches**, not the final implementation.
> Honors the three frozen contracts at `/home/dennis/Projects/beacon/shared/contracts/` verbatim. Where a contract is silent, gaps are flagged under **Risks** rather than invented.

---

## 0. TL;DR

`POST /grant_access {chunk_id, query_id}` flips one chunk's `visibility` (`restricted → public`) in the owning agent's in-memory index, then **re-runs the original query through the same orchestrator**. The re-run streams a fresh `agent-activated → response-item → done` cycle on the **same `query_id`**, so the frontend card animates from amber/redacted/grey to green/full/verified live on stage.

The feature is deliberately thin: it is a **mutation + a replay**. Almost all of its behavior is borrowed from subsystems built earlier (gate, agents-index, orchestrator, WS hub). The grant-access subsystem itself owns exactly two new things: the **mutation** (toggle one chunk) and the **replay trigger** (look up the stored query, re-invoke the orchestrator). Everything else is reuse.

---

## 1. Purpose & where it sits in the query flow (spec §10, §12 hero beat, §15 coupled feature)

The normal query flow (spec §10):

1. User submits a public engineering question → `POST /query` (or WS `type:query`).
2. Asking agent fans out to the party agents via the in-process router; emits `agent-activated` per party.
3. Each party runs `search()` (cosine top-k) over **its own** index → retrieve-first.
4. Each party passes hits through the **gate** *inside the responding agent, before content crosses the boundary* (spec §3, §6): `public→full`, `restricted→redacted` (Claude redaction), `private→denied`. Emits one `response-item` per resolved chunk.
5. Asking agent verifies any returned **full** content (Claude verification pass) and synthesizes.
6. Emits one `done` with `synthesized_answer` + `provenance` + `item_count`.

**Grant-access is step 4-bis, replayed.** On stage, a `restricted` chunk surfaced as a redacted/amber card with a "Request access from [Party]" button. Clicking it:

```
POST /grant_access {chunk_id, query_id}
        │
        ├─ (a) MUTATE: agents-index flips that chunk's visibility restricted → public   [new code]
        │      (the gate is NOT touched — only the data it reads from changes)
        │
        ├─ (b) ACK:    return {chunk_id, new_visibility, query_id, rerunning:true}       [new code]
        │
        └─ (c) REPLAY: look up the stored CrossAgentRequest for query_id, re-invoke the   [new code: trigger;
               orchestrator on the SAME query_id (background task).                        reused: orchestrator]
                      │
                      └─ orchestrator re-runs §10 steps 2–6 → fresh agent-activated →
                         response-item → done stream on the same query_id. The chunk that
                         was redacted now retrieves the same row but the gate maps it to
                         `full` (its visibility is now public), runs verification, and the
                         card resolves to green/verified. "The wall comes down."
```

The ordering constraint is preserved automatically: the re-run goes through the **same retrieve → gate → (redact|verify)** path, so retrieve-first-gate-second (spec §9) and gate-runs-inside-the-responding-agent (spec §3, §6) hold on the replay exactly as on the first run. Grant-access adds **no** new gating logic — it only changes one chunk's stored `visibility` so the *existing* gate produces a different decision.

---

## 2. Files / modules under `backend/app/`

> **Path-collision policy.** This subsystem is cross-cutting, so it must not own files that the gate / agents-index / orchestrator / API subsystems own. The grant-access subsystem owns **only** files under `backend/app/grant_access/` plus one route file and one shared run-registry file (flagged below as a coordination point). Everything else it *consumes* via imports. Files marked **(consumed)** are owned by other subsystems and listed only so the dependency is explicit — do not create them here.

```
backend/app/
├── grant_access/
│   ├── __init__.py
│   ├── service.py          # NEW — owns the toggle + replay-trigger logic
│   └── routes.py           # NEW — owns POST /grant_access (FastAPI APIRouter)
├── run_registry.py         # NEW (shared seam) — stores per-query_id run context for replay
│
├── agents/
│   └── index.py            # (consumed) agents-index: holds chunks; ADD set_visibility()
├── gate/
│   └── gate.py             # (consumed) visibility→decision; UNCHANGED by this feature
├── orchestrator/
│   └── orchestrator.py     # (consumed) fan-out/collect/verify/synthesize; ADD run(..., query_id=)
├── ws/
│   └── hub.py              # (consumed) WS connection registry + emit-by-query_id; UNCHANGED
├── models.py               # (consumed) Pydantic request/response shapes; ADD GrantAccess models
└── main.py                 # (consumed) app factory; include grant_access.routes router
```

### 2.1 `backend/app/grant_access/service.py` — NEW (the only real logic)

Single responsibility: toggle one chunk's visibility, then kick off a replay of the stored query. Holds **no** gate logic and **no** orchestration logic — it calls into both.

```python
from dataclasses import dataclass
from typing import Literal, Optional

from app.agents.index import AgentIndex          # consumed
from app.orchestrator.orchestrator import Orchestrator  # consumed
from app.run_registry import RunRegistry, RunContext     # shared seam
from app.ws.hub import WSHub                      # consumed

Visibility = Literal["public", "restricted", "private"]


@dataclass
class GrantResult:
    chunk_id: str
    new_visibility: Visibility
    query_id: str
    rerunning: bool


class ChunkNotFoundError(KeyError): ...      # → 404
class UnknownQueryError(KeyError): ...        # → 404


class GrantAccessService:
    """Owns the two new behaviors: (a) mutate one chunk's visibility,
    (b) trigger a replay of the original query through the orchestrator."""

    def __init__(
        self,
        index: AgentIndex,
        orchestrator: Orchestrator,
        registry: RunRegistry,
        hub: WSHub,
    ) -> None:
        self._index = index
        self._orch = orchestrator
        self._registry = registry
        self._hub = hub

    def toggle_visibility(
        self,
        chunk_id: str,
        *,
        target: Visibility = "public",
    ) -> Visibility:
        """Flip one chunk's stored visibility in its owning agent's index.
        For the demo: restricted -> public. Raises ChunkNotFoundError on miss.
        Mutates ONLY the index row; the gate is not involved here — it will
        simply read the new value on the replay."""
        # index resolves which agent owns chunk_id (isolation: only that index row changes)
        return self._index.set_visibility(chunk_id, target)   # see 2.4

    async def grant_and_rerun(self, chunk_id: str, query_id: str) -> GrantResult:
        """Endpoint entrypoint. Validate, toggle, ACK, then schedule the replay.
        The replay is fire-and-forget (background task) so the HTTP response
        returns immediately — results stream over the WS, per the contract."""
        run: Optional[RunContext] = self._registry.get(query_id)
        if run is None:
            raise UnknownQueryError(query_id)

        new_visibility = self.toggle_visibility(chunk_id, target="public")

        # Replay is scheduled by the route via BackgroundTasks / asyncio.create_task
        # (kept out of this method so the HTTP ACK is not blocked on the re-run).
        return GrantResult(
            chunk_id=chunk_id,
            new_visibility=new_visibility,
            query_id=query_id,
            rerunning=True,
        )

    async def replay(self, query_id: str) -> None:
        """Re-invoke the orchestrator for the stored query on the SAME query_id.
        Emits a fresh agent-activated -> response-item -> done cycle. This is a
        thin wrapper over Orchestrator.run — no new orchestration logic here."""
        run = self._registry.get(query_id)
        if run is None:
            raise UnknownQueryError(query_id)
        # Reuse the orchestrator verbatim; pass the SAME query_id so WS events correlate.
        await self._orch.run(
            query=run.query,
            from_agent=run.from_agent,
            query_id=query_id,        # <-- reuse the id, do NOT mint a new one
        )
```

Key functions/classes: `GrantAccessService.toggle_visibility`, `GrantAccessService.grant_and_rerun`, `GrantAccessService.replay`, `GrantResult`, `ChunkNotFoundError`, `UnknownQueryError`.

### 2.2 `backend/app/grant_access/routes.py` — NEW (the endpoint)

Single responsibility: bind `POST /grant_access` to the service, shape the response per the frozen API contract, schedule the replay so the ACK returns immediately.

```python
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.grant_access.service import (
    GrantAccessService, ChunkNotFoundError, UnknownQueryError,
)
from app.models import GrantAccessRequest, GrantAccessResponse
from app.deps import get_grant_access_service     # consumed (DI wiring in main.py)

router = APIRouter()


@router.post("/grant_access", response_model=GrantAccessResponse)
async def grant_access(
    body: GrantAccessRequest,
    background: BackgroundTasks,
    svc: GrantAccessService = Depends(get_grant_access_service),
) -> GrantAccessResponse:
    try:
        result = await svc.grant_and_rerun(body.chunk_id, body.query_id)
    except ChunkNotFoundError:
        raise HTTPException(status_code=404, detail="unknown chunk_id")
    except UnknownQueryError:
        raise HTTPException(status_code=404, detail="unknown query_id")

    # Schedule the re-run AFTER the ACK is built; the contract says results
    # stream on the WS, so the HTTP call returns {rerunning: true} immediately.
    background.add_task(svc.replay, body.query_id)

    return GrantAccessResponse(
        chunk_id=result.chunk_id,
        new_visibility=result.new_visibility,
        query_id=result.query_id,
        rerunning=result.rerunning,
    )
```

> **Contract pin (api-websocket.md §2):** request `{chunk_id, query_id}`; response `200 {chunk_id, new_visibility, query_id, rerunning}`. `new_visibility` uses the visibility enum (`"public"` for the demo). Do not add or rename fields.

### 2.3 `backend/app/run_registry.py` — NEW (shared seam — coordinate with orchestrator owner)

Single responsibility: remember enough about each `query_id` run to replay it. Grant-access **cannot** replay without the original `query` + `from_agent`, and the frozen `POST /grant_access` body carries only `{chunk_id, query_id}` — so the original request must be stored at `/query` time and looked up by `query_id`.

```python
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional


@dataclass(frozen=True)
class RunContext:
    query_id: str
    query: str
    from_agent: str
    # MVP: 3 in-process agents, single process → a plain dict is enough.
    # Optionally cache last run's chunk_ids/decisions for sanity checks (not required).


class RunRegistry:
    """In-memory map query_id -> RunContext. Written by the /query handler at
    fan-out time; read by GrantAccessService.replay. Single source of truth for
    'what was the original question for this query_id'."""

    def __init__(self) -> None:
        self._runs: dict[str, RunContext] = {}
        self._lock = Lock()

    def put(self, ctx: RunContext) -> None:
        with self._lock:
            self._runs[ctx.query_id] = ctx

    def get(self, query_id: str) -> Optional[RunContext]:
        with self._lock:
            return self._runs.get(query_id)
```

> **Coordination point (flag to orchestrator/api owner):** the `/query` handler must call `registry.put(RunContext(query_id, query, from_agent))` when it mints `query_id`. This is the one place grant-access reaches into another subsystem's write path. Agree it at the H13 checkpoint. If the orchestrator already retains per-`query_id` state, grant-access can read that instead and `run_registry.py` collapses to a thin accessor — note under Risks.

### 2.4 `backend/app/agents/index.py` — (consumed) ADD one method

The agents-index subsystem owns this file. Grant-access needs **one** new method on it (the mutation). Add it; do not duplicate the index here.

```python
class AgentIndex:
    # ... existing: per-agent flat chunk lists, search() backing store, get(chunk_id), etc.

    def set_visibility(self, chunk_id: str, visibility: Visibility) -> Visibility:
        """Mutate the stored visibility of one chunk in its owning agent's list.
        Resolves the owning agent from chunk_id (chunks are globally unique).
        Returns the new visibility. Raises ChunkNotFoundError if chunk_id is unknown.
        Isolation invariant preserved: only the row whose chunk_id matches changes;
        no other agent's index is read or written."""
        chunk = self._by_chunk_id.get(chunk_id)   # flat dict over all agents' rows
        if chunk is None:
            raise ChunkNotFoundError(chunk_id)
        chunk["visibility"] = visibility           # in-place; embedding/text untouched
        return visibility
```

> This is a pure data mutation on the shared index — the **gate is not modified**. The gate keeps mapping visibility→decision as before; it just sees `public` now for that chunk on the replay. That is the whole trick.

### 2.5 `backend/app/orchestrator/orchestrator.py` — (consumed) ENSURE `run(..., query_id=)`

The orchestrator subsystem owns the run loop. Grant-access requires only that `run()` **accept an existing `query_id`** rather than always minting one, so the replay correlates on the same id.

```python
class Orchestrator:
    async def run(
        self,
        query: str,
        from_agent: str,
        query_id: str | None = None,   # <-- grant-access passes the SAME id on replay
    ) -> None:
        """Fan out -> gate (inside each agent) -> verify -> synthesize, emitting
        agent-activated / response-item / done over the WS hub keyed by query_id.
        If query_id is None (first /query), mint one; if provided (grant_access
        replay), reuse it so the frontend updates the existing cards."""
        ...
```

> If the orchestrator already takes `query_id`, no change. Otherwise this is a one-line signature addition — flag at H13.

### 2.6 `backend/app/models.py` — (consumed) ADD two Pydantic models

```python
from typing import Literal
from pydantic import BaseModel

Visibility = Literal["public", "restricted", "private"]


class GrantAccessRequest(BaseModel):
    chunk_id: str
    query_id: str


class GrantAccessResponse(BaseModel):
    chunk_id: str
    new_visibility: Visibility
    query_id: str
    rerunning: bool
```

### 2.7 `backend/app/main.py` — (consumed) wire the router

```python
from app.grant_access.routes import router as grant_access_router
app.include_router(grant_access_router)   # exposes POST /grant_access
```

---

## 3. Claude (Anthropic API) calls

**Grant-access itself makes ZERO new Claude calls.** It mutates data and replays. The Claude calls that make the resolved card meaningful (redaction → no longer needed once public; verification → now runs because content crosses the boundary as `full`; synthesis) all live in the **gate** and **orchestrator** subsystems and fire automatically on the replay. They are documented here because the hero beat's payoff (`verified ✓`, full answer, updated synthesis) depends on them running correctly on the re-run, and the redaction/verification prompts and shapes are spec §11.

All calls use the official Anthropic Python SDK (`anthropic`), default `client = anthropic.Anthropic()` (reads `ANTHROPIC_API_KEY` from env), `thinking={"type": "adaptive"}`. Tiny corpora → cache embeddings, tight prompts (spec §17 latency mitigation).

### 3.1 Verification (the one that flips on grant-access) — spec §11

- **When on the replay:** the formerly-restricted chunk is now `public` → gate decision `full` → its `text` crosses the boundary → orchestrator runs the verification pass on the returned answer. This is what turns the card `verified ✓` (green). On the first run it was `redacted`/`verified:false` and verification did not run.
- **Purpose:** confirm the returned answer is grounded in the cited chunk; catch fabricated citations (spec §11, §13 kicker).
- **Model:** `claude-opus-4-8` — grounding judgment is the trust wedge; quality over cost. (`claude-haiku-4-5` is acceptable only if verification latency on stage is a problem and the yes/no judgment proves robust on the locked demo query — measure first; do not downgrade blind.)
- **Prompt sketch:**
  ```
  System: You verify whether an answer is fully supported by a single source passage.
          Answer with a strict JSON object only.
  User:   SOURCE PASSAGE:
          <<<{chunk.text}>>>
          ANSWER TO CHECK:
          <<<{answer}>>>
          Is every claim in the answer supported by the source passage? No outside knowledge.
  ```
- **Expected output shape (spec §11 — yes/no → `verified` boolean):** use structured output via `output_config={"format": {"type": "json_schema", "schema": {...}}}`:
  ```json
  { "supported": true, "reason": "one short clause" }
  ```
  Map `supported` → `ResponseItem.verified`. (`reason` is for logs/debug; not serialized into the contract payload.)

### 3.2 Redaction — spec §11 (runs on the FIRST run; not on the granted re-run)

- **When:** a `restricted` chunk on the first run (and on any re-run for chunks still `restricted`). Once grant-access flips the demo chunk to `public`, redaction no longer fires for it — it becomes `full` instead. Documented so the contrast is clear.
- **Purpose:** produce a one-line gist conveying *that* a solution exists without leaking the payload — content never crosses the boundary (spec §3, §11). This is the amber/locked card the button sits on.
- **Model:** `claude-opus-4-8` — the gist must be safe (no leakage) and compelling; this is the on-stage "wow" card. (`claude-haiku-4-5` is a reasonable cheaper tier here since the transform is short and low-risk, but the leakage bar argues for opus on the demo; pick haiku only if redaction latency is the bottleneck.)
- **Prompt sketch:**
  ```
  System: You write a single-sentence teaser that conveys THAT a solution exists,
          WITHOUT revealing any specifics (no numbers, params, root causes, steps).
  User:   RESTRICTED PASSAGE (do not reveal its contents):
          <<<{chunk.text}>>>
          PARTY: {source_party}
          Write one sentence: "<Party> has a documented fix for <general topic>.
          Request access to view the resolution."
  ```
- **Expected output shape:** a single string → `ResponseItem.answer` for the `redacted` item. Plain text completion (one short text block) is fine; no schema needed.

### 3.3 Synthesis — spec §10 step 6

- **When:** at the end of every run, including the grant-access re-run. On the re-run it re-synthesizes with the now-`full` Northwind answer folded in, so the left-panel answer and `provenance` update too.
- **Model:** `claude-opus-4-8` — final user-facing answer quality.
- **Prompt sketch:** "Given these per-party verified answers and citations, write the final answer with inline citations." Inputs are the collected `full` (verified) response items.
- **Expected output shape:** `{ synthesized_answer: str, provenance: [...] }` feeding the `done` event (`synthesized_answer`, `provenance[]` Response-item-shaped + `source_agent_id`/`chunk_id`, `item_count`).

> All three are reused, not built here. Grant-access's only obligation is to **not break their inputs**: the replay must hand the orchestrator the same `query`/`from_agent` and the same `query_id` so the gate sees the mutated visibility and the downstream Claude calls run against the now-`full` chunk.

---

## 4. Dependencies

### Other backend modules (consumed)
- `app.agents.index.AgentIndex` — owns chunks; grant-access adds `set_visibility()` and uses it for the toggle, plus `get(chunk_id)` for validation. **The mutation target.**
- `app.orchestrator.orchestrator.Orchestrator` — `run(query, from_agent, query_id=...)`; grant-access reuses it for the replay. **The replay engine.**
- `app.gate.gate` — visibility→decision mapping (`public→full`, `restricted→redacted`, `private→denied`). **Unchanged**; grant-access depends on it producing a different decision purely because the stored visibility changed.
- `app.ws.hub.WSHub` — connection registry + emit-by-`query_id`. **Unchanged**; grant-access depends on the replay's events reaching the same WS clients keyed by the reused `query_id`.
- `app.run_registry.RunRegistry` — query_id → original request. **New shared seam** (written at `/query`, read at replay).
- `app.models` — Pydantic shapes; add the two grant-access models.
- `app.deps` — DI providers (`get_grant_access_service`, etc.) wired in `main.py`.

### pip packages
- `fastapi` — `APIRouter`, `BackgroundTasks`, `HTTPException`, `Depends`.
- `pydantic` — request/response models (FastAPI dep).
- `anthropic` — official SDK (used transitively via gate/orchestrator; no direct call in grant-access).
- `uvicorn` — dev server (run target, not imported).
- (transitive, owned elsewhere) `numpy` and/or `chromadb` for the flat index — MVP per spec §5/§7; grant-access does not import them.

No new third-party dependency is introduced by this subsystem.

---

## 5. Ordered build steps

> Slots into spec §16 H13–H18 ("Dennis builds the `grant_access` endpoint (toggle + re-run)"), after the orchestrator + WS are live (H13 vertical demo). Build against the keyword `search()` stub until H8's real retrieval; grant-access is retrieval-agnostic so the stub is fine throughout.

1. **Add the run registry** (`run_registry.py`). Define `RunContext` + `RunRegistry`. Wire it as a singleton in `deps.py`/`main.py`. **Coordinate**: have the `/query` handler call `registry.put(...)` at fan-out. (If orchestrator already stores per-run state, make `RunRegistry` a thin reader instead — decide at H13.)
2. **Add `AgentIndex.set_visibility(chunk_id, visibility)`** in `agents/index.py`. Resolve owning agent from the global `chunk_id` map; mutate in place; raise `ChunkNotFoundError` on miss. Unit-test: toggle a known seed chunk, assert only that row changed and no other agent's rows moved (isolation).
3. **Confirm `Orchestrator.run` accepts `query_id`** (`orchestrator/orchestrator.py`). Add the optional param if missing; ensure it reuses the id for all emitted events. Unit-test: two `run()` calls with the same `query_id` emit events all carrying that id.
4. **Build `GrantAccessService`** (`grant_access/service.py`): `toggle_visibility`, `grant_and_rerun`, `replay`. Inject `AgentIndex`, `Orchestrator`, `RunRegistry`, `WSHub`. Keep replay out of `grant_and_rerun` (route schedules it).
5. **Add Pydantic models** (`models.py`): `GrantAccessRequest`, `GrantAccessResponse` — exact field names/enum from the contract.
6. **Build the route** (`grant_access/routes.py`): `POST /grant_access`; validate → `grant_and_rerun` → ACK → `background.add_task(svc.replay, query_id)`. Map `ChunkNotFoundError`/`UnknownQueryError` → 404.
7. **Wire DI + router** in `deps.py` + `main.py` (`get_grant_access_service`, `include_router`).
8. **End-to-end smoke test against the locked demo query** (spec §16 H13 fixture):
   - `POST /query` → capture `query_id`; observe a `redacted` `response-item` for the Northwind chunk (amber/verified:false) and a `done`.
   - `POST /grant_access {that chunk_id, query_id}` → assert `200 {new_visibility:"public", rerunning:true}`.
   - On the WS for that `query_id`: assert a fresh `agent-activated` per party, a `response-item` for the chunk now `decision:"full"`/`verified:true`/full `answer`, and a new `done` with updated `synthesized_answer` + `provenance`.
9. **Idempotency / replay-safety pass**: double-click the button (two `grant_access` on the same chunk) → second toggle is a no-op (already `public`), still replays cleanly; no duplicate-card or crash. (See Risks.)
10. **Hand the endpoint shape to Hao** (already frozen in api-websocket.md) and pair on the H13–H18 animation: button → `POST /grant_access` → listen on same `query_id` → card grey→green.

---

## 6. Integration points with the frozen contracts & other subsystems

| Touch point | Contract / subsystem | What grant-access relies on |
|---|---|---|
| `POST /grant_access` req/resp | api-websocket.md §2 | `{chunk_id, query_id}` in; `{chunk_id, new_visibility, query_id, rerunning}` out. Exact fields, `new_visibility` ∈ visibility enum (`"public"` for demo). |
| Re-run streaming | api-websocket.md §WS | Replay emits `agent-activated` (re-emitted per agent on a `grant_access` re-run — explicitly allowed by the contract), `response-item`, and one new `done`, all on the **same `query_id`**. |
| `response-item` shape | data-model.md §4 + api-websocket.md | The resolved card carries the 5 canonical fields + `chunk_id` + `source_agent_id`. Grant-access produces no new shape — the orchestrator/gate emit it; the only change is `decision` flips `redacted→full`, `verified` flips `false→true`, `answer` becomes the full text. |
| `done` shape | api-websocket.md §done | One additional `done` per re-run with `synthesized_answer`, `provenance[]`, `item_count`. |
| Visibility mutation | data-model.md §2 ("Mutable only via `grant_access`") | `Chunk.visibility` is the field flipped; `embedding`/`text`/`doc_title`/`owner` untouched. The data model explicitly designates `grant_access` as the only mutator — this subsystem is that mutator. |
| Gate decision | data-model.md gate table; gate subsystem | Gate is **unchanged**. Grant-access depends on the documented mapping (`public→full`) so a mutated chunk resolves to `full` on replay. |
| `search()` | search-interface.md | Returns **all** tiers unfiltered; the granted chunk re-appears in retrieval on the replay with its new visibility. Grant-access never calls `search()` directly and is agnostic to stub-vs-real retrieval (H8 swap doesn't affect it). |
| Orchestrator reuse | spec §6, §10; orchestrator subsystem | `run(query, from_agent, query_id=)` re-invoked verbatim — gate-runs-inside-agent and retrieve-first-gate-second are inherited, not re-implemented. |
| `/query` write to registry | api-websocket.md §1; orchestrator/api subsystem | The one place grant-access needs another subsystem to write on its behalf: store `RunContext` at `query_id` mint time. |

---

## 7. Risks & mitigations

- **Replay latency on stage (spec §17).** The re-run does a full fan-out + verification + synthesis (3 Claude calls minimum) live. *Mitigations:* tiny seed corpora; cache embeddings; tight verify/synthesis prompts; `claude-opus-4-8` but small `max_tokens`; consider `claude-haiku-4-5` for verification only if measured stage latency is unacceptable on the locked query. The HTTP ACK returns immediately (`rerunning:true`) and results stream — the button feels instant even though synthesis takes a beat. Optionally pre-warm the prompt cache before the demo.
- **Permission leakage / gate bypass (spec §3, §6).** The whole feature is "let content through that previously couldn't." *Mitigation:* grant-access only mutates **stored data**, then re-runs the **same** gate — it adds **no** path that emits content without going through retrieve→gate→(redact|verify) inside the responding agent. There is no code path that turns a `redacted` item into `full` *without* changing the underlying `visibility` first. Never special-case `chunk_id` to skip the gate.
- **Isolation breach (spec §6).** A buggy `set_visibility` could touch the wrong agent's index. *Mitigation:* resolve the owning agent strictly from the globally-unique `chunk_id`; mutate exactly one row; unit-test that no other agent's rows change. The replay still searches each agent's own index only.
- **Double-click / re-grant idempotency.** Two `grant_access` calls on the same chunk, or a click after it's already public. *Mitigation:* `toggle_visibility(target="public")` is idempotent (already-public → no-op, still returns `public`); the replay is safe to run twice (frontend keys cards by `source_agent_id`+`chunk_id` per the contract, so a repeat `response-item` updates the same card). No dedup needed for the MVP.
- **`run_registry` is the single point that must be populated at `/query` time (coordination risk).** If the `/query` handler forgets to `registry.put(...)`, every `grant_access` 404s with `unknown query_id`. *Mitigation:* make registry write part of the `/query` happy path in step 1; assert it in the end-to-end smoke test (step 8). **Contract gap flagged, not invented:** the frozen `POST /grant_access` body is only `{chunk_id, query_id}` and carries neither the original `query` nor `from_agent`, so server-side run state is *required* to replay. The contracts don't specify where that state lives — `run_registry.py` is the proposed home; if the orchestrator already retains it, collapse the registry to a reader. Do **not** widen the frozen request body to carry the query (that would require a 2-minute sync and contradicts the contract).
- **Lost run state across restart.** In-memory registry is wiped on process restart; a `grant_access` against a pre-restart `query_id` 404s. *Mitigation:* acceptable for the MVP/demo (single process, single sitting, spec §5 "no production auth", §17 "start in-process"); re-submit the query if the backend restarted. Note for graders, don't engineer persistence.
- **`grant_access` before the first `done` (race).** Button pressed while the first run is still streaming. *Mitigation:* the toggle + replay are independent of the first run's completion; worst case the user sees two overlapping streams on the same `query_id`. For the scripted demo this won't happen; if it must be hardened, gate the button on the frontend until the first `done` (Hao) — not a backend concern for the MVP.
- **Background-task failure is silent.** `BackgroundTasks`/`create_task` swallows exceptions from `replay`. *Mitigation:* wrap `replay` body in try/except that logs and (optionally) emits a WS error frame — but note the WS contract defines no error event, so for the MVP log-and-drop is acceptable; flag if an error event is wanted (would need a contract sync).
