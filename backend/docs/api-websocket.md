# BUILD — FastAPI App: HTTP Endpoints + WebSocket Server

> **Subsystem owner:** Dennis (backend). **Status:** plan / index — *not* an implementation.
> This document specifies the FastAPI service that exposes `POST /query` and the
> `ws://localhost:8000/ws/query` channel, wires the orchestrator + router + gate
> together, loads agents/corpora at startup, and emits the live WebSocket events.
>
> **Frozen contracts this subsystem MUST honor (do not contradict):**
> - Data model — `/home/dennis/Projects/beacon/shared/contracts/data-model.md`
> - search() interface — `/home/dennis/Projects/beacon/shared/contracts/search-interface.md`
> - API + WebSocket — `/home/dennis/Projects/beacon/shared/contracts/api-websocket.md`
> - Spec — `/home/dennis/Projects/beacon/docs/beacon-spec.md` (sections 5, 6, 9, 10, 11, 12)

---

## 1. Purpose & where it sits in the query flow

This is the **HTTP/WS edge of the backend**. It does not contain business logic —
it is the transport + orchestration shell that the gate, redaction, verification,
and synthesis subsystems plug into. Mapping to spec section 10 (the query loop):

| Spec §10 step | Who does it | This subsystem's role |
|---|---|---|
| 1. User submits a public question | Frontend → `POST /query` (or WS `type:query`) | **Accept** the request, validate, mint `query_id`, return `{query_id, from_agent, agents[]}`, kick off fan-out. |
| 2. Asking agent fans out to the 3 party agents via router | Orchestrator + Router | **Drive** the orchestrator; **emit** one `agent-activated` event per party at dispatch. |
| 3. Each party runs cosine top-k over its own index | `search()` (Hao's, or the stub) | **Call** via the router; never reads another agent's index. |
| 4. Each party passes hits through the **gate** | Gate subsystem (in the responding agent) | **Invoke** the gate *inside* the responding agent, before content crosses the boundary; **emit** one `response-item` per resolved chunk. |
| 5. Asker collects responses, runs verification | Verification subsystem | **Await** collection; verification runs as part of resolving each `full` item. |
| 6. Asker synthesizes final answer with citations | Synthesis subsystem | **Emit** the single `done` event with `synthesized_answer` + `provenance[]` + `item_count`. |

The hard ordering — **retrieve first, gate second, content never leaves the owner
unredacted** (spec §3, §6, §9) — is enforced structurally: the router calls
`search()` (gate-free), hands the raw chunks to the *responding agent*, and the
responding agent runs the gate locally and returns only gated `ResponseItem`s.
The HTTP/WS layer only ever sees post-gate `ResponseItem`s, so `embedding`, full
`text` of restricted chunks, etc. physically cannot be serialized to the client.

`grant_access` (the hero beat) is **out of scope for this doc** beyond two
integration hooks noted in §7: it re-uses this layer's `WSManager.emit()` and the
orchestrator's run-by-`query_id` re-execution. It is owned by a sibling doc.

---

## 2. Files / modules to create under `backend/app/`

Package layout chosen so the gate / redaction / verification / orchestrator /
router / grant_access subsystems live in their **own files** and never collide
with this edge layer. This doc *owns* the bold files; the rest are
**dependencies it imports** (stubs/contracts defined by sibling docs).

```
backend/
  app/
    __init__.py
    main.py                 ← OWNED: FastAPI entrypoint, lifespan, CORS, route mounting
    config.py               ← OWNED: settings (CORS origins, model ids, top_k, host/port)
    deps.py                 ← OWNED: app-state accessors (registry, orchestrator, ws manager)
    api/
      __init__.py
      http.py               ← OWNED: POST /query handler (+ thin grant_access delegation hook)
      ws.py                 ← OWNED: /ws/query WebSocket endpoint + frame loop
      schemas.py            ← OWNED: Pydantic request/response + event models (wire shapes)
      events.py             ← OWNED: WSManager (connection registry + emit-by-query_id)
    core/
      __init__.py
      registry.py           ← OWNED: AgentRegistry — startup load of agents + corpora
      ids.py                ← OWNED: query_id minting
    orchestrator.py         ← DEP (sibling): plan→fan-out→collect→verify→synthesize
    router.py               ← DEP (sibling): in-process fan-out to party agents
    agent.py                ← DEP (sibling): responding agent (runs gate locally)
    gate.py                 ← DEP (sibling): visibility→decision mapping
    redaction.py            ← DEP (sibling): Claude redaction pass
    verification.py         ← DEP (sibling): Claude verification pass
    synthesis.py            ← DEP (sibling): Claude synthesis pass
    search.py               ← DEP (Hao @ H8): real search(); ships as keyword STUB first
    grant_access.py         ← DEP (sibling): grant_access endpoint logic (separate doc)
  data/
    agents.json             ← seed: the 3 Agent records
    corpora/
      agent_northwind.json  ← seed: chunks for one party
      agent_helios.json
      agent_quanta.json
  docs/
    api-websocket.md        ← this file
  requirements.txt
```

### 2.1 `main.py` — entrypoint, lifespan, CORS *(OWNED)*

Responsibility: construct the `FastAPI` app, load agents+corpora once at startup
into app state, add CORS for the local frontend, mount the HTTP and WS routers.

Key signatures (sketch):

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.core.registry import AgentRegistry
from app.api.events import WSManager
from app.orchestrator import Orchestrator
from app.api import http, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    registry = AgentRegistry.load(
        agents_path=settings.agents_path,
        corpora_dir=settings.corpora_dir,
    )                                   # reads seed JSON, builds in-memory indexes
    ws_manager = WSManager()
    orchestrator = Orchestrator(        # sibling subsystem; depends on registry + search
        registry=registry,
        ws_manager=ws_manager,
        settings=settings,
    )
    app.state.settings = settings
    app.state.registry = registry
    app.state.ws_manager = ws_manager
    app.state.orchestrator = orchestrator
    yield
    # nothing to tear down for MVP (in-process, no external connections)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Beacon Backend", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,   # e.g. ["http://localhost:5173", "http://localhost:3000"]
        allow_credentials=False,               # no prod auth / cookies in MVP (spec §5)
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(http.router)            # POST /query (+ grant_access mount)
    app.include_router(ws.router)              # WS /ws/query
    return app


app = create_app()                             # `uvicorn app.main:app`
```

> **CORS note:** WebSocket upgrades are *not* governed by `CORSMiddleware`.
> Browser WS clients don't send CORS preflight, and `ws://localhost` from a
> localhost dev origin is allowed by browsers. So CORS config only needs to cover
> the two HTTP endpoints (`/query`, `/grant_access`). Keep `allow_origins`
> explicit (Vite default `5173`, CRA `3000`) rather than `"*"` so the frontend's
> exact dev origin is whitelisted; `"*"` also works for the MVP since no creds.

### 2.2 `config.py` — settings *(OWNED)*

```python
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    agents_path: str = "data/agents.json"
    corpora_dir: str = "data/corpora"
    default_asker: str = "agent_helios"     # /query.from_agent default (contract: optional field)
    top_k: int = 5                          # passed to search(); small for low verify latency (§17)
    # Claude model ids (see §3)
    model_redaction: str = "claude-opus-4-8"
    model_verification: str = "claude-opus-4-8"
    model_synthesis: str = "claude-opus-4-8"
    anthropic_api_key: str | None = None    # from env ANTHROPIC_API_KEY

    class Config:
        env_prefix = "BEACON_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### 2.3 `core/registry.py` — startup load of agents + corpora *(OWNED)*

Responsibility: read the seed JSON once at startup and hold the authoritative
in-memory state. This is the single source of truth for: the 3 `Agent` records,
each agent's flat chunk index (keyed by `agent_id`), the `chunk_id → chunk`
lookup, and `agent_id → party_name` resolution. Used by the router (which agents
exist, which index to search), the responding agent / gate, and the WS emitter
(to fill `party_name` on `agent-activated`).

```python
from dataclasses import dataclass, field


@dataclass
class AgentRegistry:
    agents: dict[str, dict]              # agent_id -> Agent record (id, party_name, scope_policy)
    indexes: dict[str, list[dict]]       # agent_id -> list[Chunk] (the flat per-agent index)
    chunks_by_id: dict[str, dict]        # chunk_id -> Chunk (for grant_access + provenance joins)

    @classmethod
    def load(cls, agents_path: str, corpora_dir: str) -> "AgentRegistry":
        """Read seed JSON; build indexes keyed by agent_id and a chunk_id lookup.
        Validates: every chunk.owner is a known agent_id; ids unique; visibility
        in the frozen enum. Embeddings may be absent in the stub fixtures."""
        ...

    def party_agent_ids(self, exclude: str | None = None) -> list[str]:
        """The Agent.ids to fan out to (all agents minus the asker)."""
        ...

    def party_name(self, agent_id: str) -> str:
        ...

    def get_chunk(self, chunk_id: str) -> dict:
        """Used by grant_access to toggle visibility; KeyError if unknown."""
        ...
```

> **Isolation invariant (spec §6):** `indexes` is keyed by `agent_id` and each
> chunk's `owner == agent_id`. The router/`search()` only ever receives one
> `agent_id` per call, so no agent can read another's index. The registry asserts
> `chunk["owner"] == agent_id` for every row at load time.

### 2.4 `core/ids.py` — query_id minting *(OWNED)*

```python
import secrets


def new_query_id() -> str:
    """Contract example shape: 'q_8f3a2c'. Opaque; correlates all WS events."""
    return "q_" + secrets.token_hex(3)
```

### 2.5 `api/schemas.py` — wire shapes (Pydantic) *(OWNED)*

Pydantic models mirroring the frozen contract **exactly** (snake_case, same keys).
These are the only place the wire shapes are declared; everything else passes
plain dicts that conform. `embedding` and `score` are **never** in any outbound
model — that is how the boundary is enforced at the type level.

```python
from typing import Literal, Optional
from pydantic import BaseModel

Decision = Literal["full", "redacted", "denied"]
Visibility = Literal["public", "restricted", "private"]

# ---- POST /query ----
class QueryRequest(BaseModel):
    query: str
    from_agent: Optional[str] = None         # defaults to settings.default_asker

class QueryResponse(BaseModel):
    query_id: str
    from_agent: str
    agents: list[str]                        # party Agent.ids being fanned out to

# ---- WS event frames (type-discriminated) ----
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

# ---- WS client->server submit + ack (WS-driven option) ----
class WSQueryFrame(BaseModel):
    type: Literal["query"]
    query: str
    from_agent: Optional[str] = None

class WSAck(QueryResponse):
    type: Literal["ack"] = "ack"
```

### 2.6 `api/events.py` — WebSocket manager / event emitter *(OWNED)*

Responsibility: track live WS connections and **emit events keyed by `query_id`**.
Because the WS-driven path has one connection bound to the run it submitted, and
the POST+WS path has connections that *subscribe* to a `query_id`, the manager
maps `query_id → set[WebSocket]`. The orchestrator calls `emit(...)`; it never
touches the socket directly.

```python
import asyncio
from fastapi import WebSocket
from app.api import schemas


class WSManager:
    def __init__(self) -> None:
        self._subs: dict[str, set[WebSocket]] = {}     # query_id -> sockets
        self._lock = asyncio.Lock()

    async def subscribe(self, query_id: str, ws: WebSocket) -> None:
        ...

    async def unsubscribe_socket(self, ws: WebSocket) -> None:
        """Drop a socket from every query_id on disconnect."""
        ...

    async def emit(self, event: schemas.BaseModel) -> None:
        """Serialize `event` (has .query_id) to JSON and send to all subscribers
        of that query_id. Best-effort: a send failure removes that socket, never
        aborts the run. Safe to call from orchestrator tasks."""
        payload = event.model_dump()
        ...

    # Convenience wrappers the orchestrator uses (keep call sites declarative):
    async def agent_activated(self, query_id, agent_id, party_name): ...
    async def response_item(self, query_id, item: dict): ...      # item = gated ResponseItem + ids
    async def done(self, query_id, synthesized_answer, provenance, item_count): ...
```

> **Ordering guarantee:** `response-item` events "may arrive in any order across
> parties" (contract), but `done` MUST be last for a run. The orchestrator awaits
> all party tasks before calling `done()`, so emit-ordering is the orchestrator's
> responsibility; `WSManager` just forwards. `agent-activated` for every party is
> emitted *before* any `response-item` because dispatch precedes resolution.

### 2.7 `api/http.py` — `POST /query` handler *(OWNED)*

```python
from fastapi import APIRouter, Request
from app.api import schemas
from app.deps import get_orchestrator
from app.core.ids import new_query_id

router = APIRouter()

@router.post("/query", response_model=schemas.QueryResponse)
async def submit_query(body: schemas.QueryRequest, request: Request):
    orch = get_orchestrator(request)
    asker = body.from_agent or orch.settings.default_asker
    parties = orch.registry.party_agent_ids(exclude=asker)   # the nodes that will pulse
    query_id = new_query_id()
    # Fire-and-forget: kick the fan-out as a background task; return immediately.
    orch.start_run(query_id=query_id, from_agent=asker, query=body.query)  # schedules asyncio task
    return schemas.QueryResponse(query_id=query_id, from_agent=asker, agents=parties)

# grant_access is mounted here too but its logic lives in app/grant_access.py (separate doc):
#   from app.grant_access import router as grant_router
#   router.include_router(grant_router)
```

> `start_run` returns synchronously after scheduling the work
> (`asyncio.create_task`), so the HTTP response is fast (contract: "Returns
> immediately with a `query_id`; live results stream over the WebSocket"). The
> task drives orchestrator → router → gate → verify → synth, emitting events via
> `WSManager` as it goes.

### 2.8 `api/ws.py` — `/ws/query` endpoint + frame loop *(OWNED)*

Supports **both** transport options from the contract on one endpoint:
1. **WS-driven:** first frame is `{type:"query", ...}` → server acks with
   `{type:"ack", query_id, from_agent, agents}` then streams events on this socket.
2. **POST+WS:** client first `POST /query` to get a `query_id`, then sends a
   subscribe frame (or the same socket is registered) and listens.

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.api import schemas
from app.deps import get_orchestrator_ws, get_ws_manager_ws
from app.core.ids import new_query_id

router = APIRouter()

@router.websocket("/ws/query")
async def ws_query(ws: WebSocket):
    await ws.accept()
    orch = get_orchestrator_ws(ws)            # reads ws.app.state
    mgr = get_ws_manager_ws(ws)
    try:
        while True:
            frame = await ws.receive_json()
            kind = frame.get("type")
            if kind == "query":                 # WS-driven submit
                req = schemas.WSQueryFrame(**frame)
                asker = req.from_agent or orch.settings.default_asker
                parties = orch.registry.party_agent_ids(exclude=asker)
                query_id = new_query_id()
                await mgr.subscribe(query_id, ws)       # bind this socket to the run
                ack = schemas.WSAck(query_id=query_id, from_agent=asker, agents=parties)
                await ws.send_json(ack.model_dump())
                orch.start_run(query_id=query_id, from_agent=asker, query=req.query)
            elif kind == "subscribe":           # POST+WS: listen to an existing query_id
                await mgr.subscribe(frame["query_id"], ws)
            # else: ignore unknown frames (forward-compat)
    except WebSocketDisconnect:
        await mgr.unsubscribe_socket(ws)
```

> The `subscribe` frame is the documented "POST + WS" path's listen mechanism
> (the contract says "then listens on the WS for events with that id" — a tiny
> subscribe envelope makes that explicit without adding new event shapes). If the
> team prefers, the POST handler could instead broadcast to *all* open sockets and
> let the client filter by `query_id`; the subscribe approach is cleaner and is
> noted under §6 as the recommended choice.

### 2.9 `deps.py` — app-state accessors *(OWNED)*

Thin helpers so handlers read `request.app.state` / `ws.app.state` in one place.

```python
from fastapi import Request, WebSocket
def get_orchestrator(request: Request): return request.app.state.orchestrator
def get_ws_manager(request: Request):  return request.app.state.ws_manager
def get_orchestrator_ws(ws: WebSocket): return ws.app.state.orchestrator
def get_ws_manager_ws(ws: WebSocket):   return ws.app.state.ws_manager
```

### 2.10 Orchestrator contract this layer depends on *(DEP — sibling doc)*

This edge layer needs exactly this surface from `orchestrator.py`:

```python
class Orchestrator:
    registry: AgentRegistry
    settings: Settings
    def start_run(self, query_id: str, from_agent: str, query: str) -> None:
        """Schedule (asyncio.create_task) the full fan-out for this query_id.
        Internally: emit agent-activated per party -> router.fan_out (search+gate
        inside each responding agent) -> collect ResponseItems -> verify ->
        synthesize -> emit response-item per item and a final done. Never raises
        into the caller; errors are caught and surfaced as a done with a fallback
        synthesized_answer (see §6 error handling)."""
```

The router/agent/gate split (also sibling docs) keeps the *retrieve-first /
gate-in-responder* ordering; this doc does not re-specify them but **requires**
that `response-item` events carry only post-gate fields.

---

## 3. Claude (Anthropic API) calls

This edge layer makes **no Claude calls itself** — they live in the sibling
`redaction.py`, `verification.py`, `synthesis.py` modules, invoked during a run.
They are documented here because the model ids and output shapes are part of what
this subsystem orchestrates and must allocate config for (spec §11). All three use
the official `anthropic` Python SDK (`anthropic.AsyncAnthropic()`), so they can be
`await`ed inside the orchestrator's asyncio task without blocking the event loop.

**Model choice:** `claude-opus-4-8` for all three. Redaction and verification are
the two trust-critical passes (spec §11 — they *are* the product's wedge); a wrong
redaction leaks, a wrong verification mislabels provenance. Synthesis is the
user-facing answer. Quality matters more than cost on a 3-party, tiny-corpus demo,
so Opus is the right tier. `claude-haiku-4-5` is a *reasonable fallback for
verification only* if latency becomes the bottleneck (spec §17) — the verify
prompt is a tight yes/no grounding check that Haiku handles well — but default to
Opus and only downgrade with measurement. Redaction and synthesis stay on Opus.

Use `thinking={"type": "adaptive"}` is **not** needed for these short, bounded
calls; omit `thinking` (defaults off on Opus 4.8) to minimize latency. Cap output
tightly per call.

### 3.1 Redaction — restricted chunks (spec §11)

- **Where:** `redaction.py`, called by the responding agent when the gate decides
  `restricted` → `redacted`, *before* content crosses the boundary.
- **Purpose:** turn a restricted chunk's `text` into a one-line gist that conveys
  *that* a solution exists without leaking it. The full `text` never leaves the
  agent; only the returned gist becomes `ResponseItem.answer`.
- **Model:** `claude-opus-4-8`. `max_tokens≈80`.
- **Prompt sketch (system + user):**
  ```
  system: "You produce a single safe sentence confirming a relevant solution
           EXISTS without revealing its content. Never include specifics: no
           numbers, parameter names, code, or step-by-step. One sentence."
  user:   "Party: {party_name}\nDoc: {doc_title}\nQuestion: {query}\n
           Restricted content (DO NOT reveal):\n{chunk_text}\n
           Write the one-line gist."
  ```
- **Output shape:** plain string → `ResponseItem.answer`. e.g.
  `"Northwind has a documented fix for servo jitter under load. Request access to view the resolution."`
  `verified=false`, `decision="redacted"` (data-model §4 redacted example).

### 3.2 Verification — returned full content (spec §11)

- **Where:** `verification.py`, called for every `full` item after retrieval.
- **Purpose:** confirm the answer text is grounded in its cited chunk. Drives
  `ResponseItem.verified`. Catches fabricated citations (demo kicker, §13 step 7).
- **Model:** `claude-opus-4-8` (Haiku-4-5 acceptable if latency-bound — see above).
  `max_tokens≈10`. Use structured output for a clean boolean.
- **Prompt sketch:**
  ```
  system: "You judge whether an ANSWER is fully supported by the SOURCE text.
           Answer strictly with the schema. 'supported' is true only if every
           claim in the answer appears in or follows directly from the source."
  user:   "SOURCE:\n{chunk_text}\n\nANSWER:\n{answer}\n\nIs the answer supported?"
  output_config: {"format": {"type": "json_schema",
                  "schema": {"type":"object",
                             "properties":{"supported":{"type":"boolean"}},
                             "required":["supported"],
                             "additionalProperties": false}}}
  ```
- **Output shape:** `{"supported": bool}` → `ResponseItem.verified`. `true` →
  render `verified ✓`; `false` → `unverifiable ✗`.

### 3.3 Synthesis — final answer (spec §10 step 6)

- **Where:** `synthesis.py`, called once per run after all parties resolve.
- **Purpose:** compose the user-facing answer with inline citations from the
  collected `full`/`redacted` items. Feeds the `done` event.
- **Model:** `claude-opus-4-8`. `max_tokens≈400`.
- **Prompt sketch:**
  ```
  system: "Synthesize a concise answer to the user's question from the provided
           party findings. Cite each fact by party name. If a party only has a
           restricted/redacted result, mention that an access request is pending;
           do not invent its content. Do not use facts that were not provided."
  user:   "Question: {query}\n\nFindings:\n
           - {party}: decision={decision}, verified={verified}, text={answer}\n ...
           \nWrite the synthesized answer with inline party citations."
  ```
- **Output shape:** plain string → `DoneEvent.synthesized_answer`. The
  `provenance[]` entries are built **mechanically** by this layer from the
  collected items (not by Claude) so they exactly match the emitted
  `response-item`s (data-model §4 fields + `source_agent_id` + `chunk_id`).
  `item_count` = number of `response-item`s emitted this run.

---

## 4. Dependencies

### 4.1 Other backend modules (sibling subsystems / contracts)
- `app.orchestrator.Orchestrator` — drives the run; this layer calls `start_run`.
- `app.router` — in-process fan-out (calls `search()`, hands chunks to responder).
- `app.agent` + `app.gate` — responding agent runs the gate locally (boundary).
- `app.redaction`, `app.verification`, `app.synthesis` — the 3 Claude passes (§3).
- `app.search.search(query, agent_id, top_k)` — Hao's at H8; **keyword STUB** until
  then (search-interface contract). This layer wires it in; the stub guarantees a
  mixed-visibility hit set incl. ≥1 restricted chunk so the gate/redaction/grant
  beat are exercisable pre-integration.
- `app.grant_access` — separate doc; mounted under `api/http.py`, re-uses
  `WSManager.emit` and orchestrator re-run.

### 4.2 pip packages (→ `backend/requirements.txt`)
```
fastapi
uvicorn[standard]        # ASGI server + websockets extra (wsproto/websockets)
pydantic>=2
pydantic-settings
anthropic                # Claude SDK (AsyncAnthropic) — used by sibling Claude modules
python-dotenv            # .env loading (or rely on pydantic-settings env_file)
numpy                    # Hao's real search() at H8; harmless to pin now
```
No DB, no auth libs, no Chroma required for MVP (flat numpy/in-memory — spec §5/§7).

---

## 5. Ordered build steps

1. **Scaffold the package** (§2 tree): create `backend/app/` with empty
   `__init__.py`s, `requirements.txt`, and `data/` with the seeded `agents.json`
   + three `corpora/*.json` (joint hour-0 seed task — spec §15/§16; lock the demo
   query here so the stub returns a mixed-visibility hit set).
2. **`config.py`** — `Settings` + `get_settings()`; set CORS origins to the
   frontend dev origin(s) and the three model ids.
3. **`core/registry.py`** — `AgentRegistry.load()` reading the seed JSON; assert
   isolation (`chunk.owner == agent_id`) and enum validity at load. Unit-smoke it.
4. **`core/ids.py`** — `new_query_id()`.
5. **`api/schemas.py`** — all Pydantic wire models (§2.5), matching the frozen
   contract verbatim. This is the freeze point with the frontend mock fixture.
6. **`api/events.py`** — `WSManager` (subscribe / emit-by-query_id / unsubscribe).
7. **Stub orchestrator** — implement `Orchestrator.start_run` against the **search
   stub** with placeholder gate/redaction/verify/synth (sibling docs land the real
   ones). Emit the full `agent-activated → response-item → done` cycle so the WS
   path is testable end-to-end before any Claude call exists.
8. **`api/http.py`** — `POST /query` → mint id, compute `agents[]`, schedule run,
   return `QueryResponse`. (`grant_access` mount left as a no-op import hook.)
9. **`api/ws.py`** — `/ws/query` accept loop: `type:query` → ack + run;
   `type:subscribe` → bind socket; disconnect cleanup.
10. **`main.py`** — `create_app()` + `lifespan` (load registry, build WSManager +
    Orchestrator into `app.state`), add `CORSMiddleware`, mount routers.
11. **Run + smoke:** `uvicorn app.main:app --reload --port 8000`. Verify with a
    `wscat`/browser client: WS-driven submit returns `ack` then streams the three
    event types; `POST /query` + subscribe streams the same. Confirm `embedding`
    and full restricted `text` never appear in any frame.
12. **H8 integration:** swap `app.search` stub for Hao's real `search()`
    (drop-in, no call-site change); re-run smoke against the locked demo query.
13. **Wire real Claude passes** (sibling docs) into the orchestrator; set
    `ANTHROPIC_API_KEY`; verify `verified ✓`/`✗`, redacted gist, synthesized
    answer + provenance.
14. **H13 integration:** point the frontend WS client at `ws://localhost:8000/ws/query`;
    first full vertical demo.

---

## 6. Integration points with frozen contracts & other subsystems

- **`POST /query` request/response** — `QueryRequest`/`QueryResponse` match
  api-websocket.md §1 exactly: response is `{query_id, from_agent, agents[]}`;
  `from_agent` optional, defaults to `settings.default_asker`. `agents[]` is the
  party fan-out list (asker excluded) — the nodes the frontend pre-renders.
- **WS events** — `agent-activated`, `response-item`, `done` payloads match
  api-websocket.md §"WebSocket" verbatim, including the transport-only
  `chunk_id` / `source_agent_id` on `response-item` and each `provenance` entry.
  Every frame carries `type` + `query_id`.
- **Two transport options** — both supported on the single `/ws/query` endpoint
  (WS-driven `type:query`→`type:ack`; POST+WS via `type:subscribe`). Event shapes
  are identical either way, matching the frontend mock fixture. *Recommended pick:*
  default to **WS-driven** for the demo (one socket, simplest), keep `subscribe`
  for the POST path.
- **Data model** — `ResponseItem` carries the 5 canonical §8 fields
  (`answer, source_party, source_doc_title, decision, verified`) plus the two
  transport ids. `embedding` and `score` are structurally excluded from all
  outbound schemas. `source_party` resolved via `registry.party_name(owner)`;
  `source_doc_title` = chunk `doc_title`.
- **search() interface** — consumed via the router with `(query, agent_id, top_k)`;
  this layer passes `settings.top_k`. Returns all visibility tiers unfiltered; the
  gate (downstream, in the responding agent) maps visibility→decision.
- **Gate / boundary (spec §3, §6, §9)** — enforced by *who calls what*: router →
  `search()` (gate-free) → responding agent runs gate locally → returns gated
  `ResponseItem`s → this layer emits them. The HTTP/WS layer never sees pre-gate
  content.
- **grant_access (separate doc)** — re-runs the original query on the same
  `query_id` and re-emits a fresh `agent-activated → response-item → done` cycle
  via this layer's `WSManager`. This layer exposes the hooks (mounted route +
  `emit`); the toggle/re-run logic is out of scope here.
- **Error handling convention** — a run that fails internally (search error,
  Claude timeout, etc.) is caught in the orchestrator task and surfaced as a
  terminal `done` with a fallback `synthesized_answer` (e.g. "Some parties could
  not be reached.") and whatever `response-item`s succeeded, so the frontend run
  always terminates. Unknown WS frames are ignored (forward-compat). Unknown
  `from_agent` → 400 (mirrors `search()` raising `KeyError` on unknown agent).

---

## 7. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **Content leakage across the boundary** | Restricted/private `text` or raw `embedding` reaches the client → kills the entire wedge. | Structural enforcement: outbound Pydantic models (`ResponseItemEvent`, `ProvenanceEntry`) have **no** `text`/`embedding`/`score` fields, so they cannot serialize. Gate runs *inside* the responding agent before content crosses; this layer only handles post-gate `ResponseItem`s. Add a smoke assertion in step 11 that no WS frame contains `embedding`/full restricted text. |
| **Agent isolation broken** | One party's index leaks into another → not "separate parties" (spec §6). | `registry.indexes` keyed by `agent_id`; `search(agent_id)` returns only `owner==agent_id` rows; registry asserts this at load. Router never passes more than one `agent_id` per call. |
| **Verification / Claude latency** (spec §17) | Slow `done`; demo drags. | Tiny corpora; small `top_k` (5); short `max_tokens` per call; `AsyncAnthropic` so the 3 passes run concurrently with party fan-out where possible; verification can drop to `claude-haiku-4-5` if measured too slow (Opus default). Emit `agent-activated` *immediately* at dispatch so the graph animates while Claude works. |
| **`done` emitted before all parties resolve / out of order** | Frontend shows a partial answer or wrong `item_count`. | Orchestrator `await`s all party tasks before `synthesis` + `done`; `WSManager` only forwards. `item_count` computed from the actual emitted `response-item` count. |
| **WebSocket disconnect mid-run** | Orphaned tasks / send errors. | `WSManager.emit` is best-effort: a failed send removes that socket, never aborts the run. `WebSocketDisconnect` triggers `unsubscribe_socket`. Run continues (idempotent emit). |
| **CORS / WS connection blocked from the frontend** | Frontend can't reach backend at H13. | Explicit `allow_origins` for Vite (`5173`) + CRA (`3000`); WS upgrades aren't CORS-gated for localhost. Documented base URL `http://localhost:8000`, WS `ws://localhost:8000/ws/query`. |
| **Search stub vs real cosine scores diverge** | Threshold tuning against stub misleads (search-interface note). | Don't tune score thresholds against the stub; treat empty `search()` result as "no hit". Swap is drop-in at H8 with zero call-site change; re-smoke against the locked demo query. |
| **Two-transport ambiguity** | Frontend and backend disagree on submit path. | Both supported on one endpoint with identical event shapes; recommend WS-driven for the demo, keep `subscribe` for POST path. Decision noted in §6 so it's not re-litigated. |
| **Gap: `denied` items with no payload** (contract allows existence-only *or* nothing) | Ambiguous whether a `denied` party emits a `response-item` at all. | **Noted as a gap, not invented away:** MVP choice is to emit a `denied` `response-item` only when showing existence-only (`answer=null`, `source_doc_title=null`); emit nothing for full-deny. This is a frontend/UX call (data-model §4 says "or nothing at all") — confirm in the 2-min sync before H13; do not change the shape, only whether the frame is sent. |
| **Long-running orchestrator task leaks** | Many abandoned tasks if clients spam queries. | MVP/demo scope is tiny; tasks are short-lived and self-complete with a terminal `done`. Acceptable for the hackathon; note for hardening only. |
