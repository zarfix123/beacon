# Beacon — Master Backend Build Index

> **This is the single entry-point document for building the entire Beacon backend.**
> Read this first. It reconciles the seven subsystem build docs into one canonical
> file layout, one ordered build plan mapped to the hackathon checkpoints, one
> dependency list, and one startup-wiring plan. Where the subsystem docs disagreed
> on a path, this index picks the canonical one — **follow the tree here, not the
> per-subsystem paths.**

---

## 1. Overview — what the backend is, and the wedge

Beacon is a **permissioned knowledge-brokering network**: three independent party
agents (`agent_northwind`, `agent_helios`, `agent_quanta`), each with its own
isolated seeded corpus and flat vector index, that query each other for
already-solved engineering problems and share only what the owner authorizes.

The backend is the whole wedge — and the wedge is two trust/security primitives
that no competitor combines:

1. **Enforced permission at the owner's boundary.** Every retrieved chunk passes
   through a per-chunk **permission gate** *inside the responding agent* that maps
   `visibility → decision` (`public→full`, `restricted→redacted`, `private→denied`)
   **before any content crosses the cross-agent boundary**. Restricted/private raw
   text is structurally absent from what leaves the responder — leakage is made
   *impossible*, not merely *filtered*. Retrieve first, gate second (spec §9).
2. **Verified provenance.** Every `full` answer that crosses the boundary is run
   through a Claude grounding pass that flags fabricated citations (`verified ✓` /
   `unverifiable ✗`), and every shared answer carries a provenance pointer
   (party, doc title, owner). This catches the demo's fabricated-source kicker.

Around those two sit the supporting machinery: the retrieval substrate (isolated
indexes + `search()` with a keyword stub until Hao's cosine lands at H8), the
redaction Claude call (restricted → safe one-line gist), the router (in-process
fan-out + live WebSocket events), the orchestrator (plan → fan out → collect →
verify → synthesize, living in the asking agent), the FastAPI HTTP/WS edge, and
the grant-access-live hero beat (toggle one chunk's visibility, replay the query
on the same `query_id`, watch the card flip amber→green on stage).

**MVP scope (spec §5):** flat index, 3 in-process agents, seeded corpora (10–30
chunks each), one locked demo query, no production auth, no DB, no GraphRAG.

---

## 2. Canonical directory tree

This is the **authoritative** layout. It reconciles every collision in the
subsystem docs (see §2.1). Anything not on this tree should not be created without
a sync.

```
backend/
├── BUILD_INDEX.md                  # this file — the entry point
├── README.md                       # short orientation -> points here + contracts
├── requirements.txt                # consolidated pins (see §5)
├── .env.example                    # ANTHROPIC_API_KEY=, BEACON_SEARCH=stub, ...
├── pytest.ini                      # async test config (asyncio_mode = auto)
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI entrypoint: create_app() + lifespan; `app`
│   ├── config.py                   # pydantic-settings: CORS, seed paths, model ids, top_k, default asker
│   ├── deps.py                     # request.app.state accessors (orchestrator, ws_manager, services)
│   ├── models.py                   # SHARED record shapes — single source of truth (Chunk, Agent,
│   │                               #   CrossAgentRequest, ResponseItem, GateDecision, GatedResult,
│   │                               #   ProvenancePointer, VerifyResult, GrantAccessRequest/Response)
│   ├── run_registry.py             # query_id -> RunContext(query, from_agent); written at /query, read at replay
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   └── ids.py                  # new_query_id() -> "q_" + hex
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── registry.py             # AgentRegistry: 3 isolated agents, get/all_ids/party_name/find_chunk;
│   │   │                           #   build_registry(with_embeddings); KeyError on unknown id; AGENT_DEFS
│   │   ├── index.py                # AgentIndex (agent_id, chunks, matrix); load_agent_index();
│   │   │                           #   isolation invariant owner==agent_id; set_visibility() (grant_access mutator)
│   │   ├── agent.py                # RuntimeAgent: identity + own AgentIndex; .search(); .respond(gate_fn) seam
│   │   ├── embeddings.py           # embed_texts/embed_query; EMBED_MODEL, EMBED_DIM (NOT Claude — MiniLM/Voyage)
│   │   └── corpus.py               # corpus load helpers + isolation assert (used by registry/index)
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   └── search.py               # FROZEN search(query, agent_id, top_k) entry; _keyword_stub + _cosine_search;
│   │                               #   dispatch via BEACON_SEARCH; gate-free, all tiers, KeyError on unknown id
│   │
│   ├── gate/
│   │   ├── __init__.py             # public surface: evaluate, GatedResult, GateDecision, GateError, issue_grant
│   │   ├── gate.py                 # evaluate(chunk, *, query, grant, resolve_party_name) -> GatedResult; entry point
│   │   ├── policy.py               # pure decide(visibility)->GateDecision; fail-closed; SHOW_EXISTENCE_FOR_PRIVATE
│   │   └── capability.py           # Capability/CapabilityGrant; issue_grant(); allows() — second independent gate
│   │
│   ├── claude/
│   │   ├── __init__.py
│   │   ├── client.py               # SHARED AsyncAnthropic client + model-id constants + complete_text()/parse +
│   │   │                           #   cached_system_block(); used by redaction, verification, synthesis
│   │   ├── prompts.py              # frozen, byte-stable system/user prompt templates (cache-friendly)
│   │   ├── redaction.py            # redact(chunk)->str: restricted text -> safe one-line gist; leak-guard + fallback
│   │   ├── verification.py         # verify_answer(answer, source_text)->VerifyResult; fail-closed verified=False
│   │   └── synthesis.py            # synthesize(query, items, redacted)->str: final cited answer; empty-input guard
│   │
│   ├── provenance/
│   │   ├── __init__.py
│   │   ├── pointer.py              # assemble_provenance(chunk, *, payload_hidden) -> ProvenancePointer (no text/embedding)
│   │   └── assembler.py            # build_response_item(chunk, decision) -> ResponseItem; verify ONLY full
│   │
│   ├── router/
│   │   ├── __init__.py             # Router, build_default_registry, event builders
│   │   ├── router.py               # Router.dispatch(query_id, from_agent, query): emit all agent-activated first,
│   │   │                           #   then concurrent responder calls, emit response-item per resolved item
│   │   ├── responder.py            # respond_for_agent(agent_id, query) -> list[ResponseItem]: search->gate->
│   │   │                           #   redact/verify pipeline that runs INSIDE the responding agent (the boundary)
│   │   └── events.py               # pure event builders: agent_activated_event(), response_item_event()
│   │
│   ├── events/
│   │   ├── __init__.py
│   │   └── bus.py                  # EventBus: in-process async pub/sub keyed by query_id (subscribe/emit/unsubscribe)
│   │
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   └── orchestrator.py         # Orchestrator.run(query, from_agent, query_id=None): resolve asker, fan out via
│   │                               #   router, collect GatedItems, verify full, emit response-item, synthesize, done
│   │
│   ├── grant_access/
│   │   ├── __init__.py
│   │   ├── service.py              # GrantAccessService: toggle_visibility + grant_and_rerun + replay(query_id)
│   │   └── routes.py               # POST /grant_access router: validate -> ack -> BackgroundTasks replay
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── schemas.py              # Pydantic WIRE models verbatim from contract (QueryRequest/Response,
│   │   │                           #   AgentActivatedEvent, ResponseItemEvent, DoneEvent+ProvenanceEntry, WSQueryFrame/WSAck)
│   │   ├── events.py               # WSManager: query_id -> set[WebSocket]; best-effort emit; bridges EventBus -> sockets
│   │   ├── http.py                 # POST /query handler: resolve asker, agents[], mint id, run_registry.put, kick run
│   │   └── ws.py                   # /ws/query: WS-driven (type:query->ack) + POST+WS (type:subscribe); disconnect cleanup
│   │
│   └── data/
│       ├── agents.json             # 3 locked agents: ids + party_names + scope_policy "three_tier"
│       ├── corpora/
│       │   ├── agent_northwind.json   # 10-30 chunks, mixed tiers; demo query hits >=1 restricted chunk
│       │   ├── agent_helios.json      # 10-30 chunks, mixed tiers
│       │   └── agent_quanta.json      # 10-30 chunks, mixed tiers; includes a private chunk (denied badge)
│       └── embeddings.npz           # generated cache of corpus embeddings keyed by chunk_id (index-once-before-demo)
│
├── scripts/
│   └── build_embeddings.py         # one-shot offline: read corpora, embed every chunk, write data/embeddings.npz
│
└── tests/
    ├── __init__.py
    ├── conftest.py                 # fixtures: fake EventBus/WSManager sink, fake responder, seeded chunk dicts
    ├── test_models.py              # ResponseItem/GatedResult.to_wire() emits exactly the 7 frozen keys
    ├── test_search_stub.py         # own-agent only, all tiers, desc score, <=top_k, KeyError, [] on no hit
    ├── test_isolation.py           # searching A returns zero B/C-owned chunks (the security claim)
    ├── test_gate_policy.py         # 3 tiers + fail-closed unknown tier; capability down-rank private->denied
    ├── test_gate_leakage.py        # no raw text/embedding in non-full GatedResult (the cardinal-sin test)
    ├── test_redaction.py           # gist non-empty/one-line, no >=6-word verbatim run, deterministic, fallback
    ├── test_verification.py        # supported->True, contradicting->False, fail-closed on API error
    ├── test_provenance.py          # assemble_provenance never reads text/embedding; internal fields not on wire
    ├── test_orchestrator.py        # event order: all agent-activated, then N response-item, then exactly one done
    ├── test_router.py              # all agent-activated before any response-item; event dicts match contract
    └── test_grant_access.py        # toggle -> replay on same query_id -> response-item now full/verified
```

### 2.1 Reconciled path collisions (read before coding)

The subsystem docs referenced the same concepts under different paths. **These are
the canonical decisions** — defer to this table over any individual doc:

| Concept | Variants seen in subsystem docs | **Canonical path** |
|---|---|---|
| Shared record shapes | `app/models.py` (everywhere) | `app/models.py` — **flat, single file, single source of truth.** Co-owned; whoever scaffolds first writes it, everyone else imports. Holds Chunk, Agent, CrossAgentRequest, ResponseItem, GateDecision, GatedResult, ProvenancePointer, VerifyResult, GrantAccess* shapes. |
| Agent registry | `app/registry.py`, `app/agents.py`, `app/router/registry.py`, `app/core/registry.py` | `app/agents/registry.py` — **one registry.** Router/API import it; do not duplicate a second registry under `router/` or `core/`. |
| Agent index | `app/corpus.py` (AgentIndex), `app/agents/index.py` | `app/agents/index.py` — holds `AgentIndex` + `load_agent_index` + `set_visibility` (the grant_access mutator). `corpus.py` keeps load helpers only. |
| Runtime agent | `app/agent.py` | `app/agents/agent.py` (`RuntimeAgent`). |
| Search | `app/search.py`, `app/retrieval.py` | `app/retrieval/search.py` — the frozen `search()`. |
| Permission gate | `app/gate.py` (flat) vs `app/gate/` (package) | `app/gate/` **package** (gate.py / policy.py / capability.py). The flat `app/gate.py` references in other docs mean "the gate package". |
| Redaction | `app/gate/redaction.py`, `app/claude/redaction.py`, `app/redaction.py` | `app/claude/redaction.py` — lives with the other Claude calls under one shared client. The gate *calls* it; it does not own it. |
| Verification | `app/provenance/verify.py`, `app/verification.py`, `app/claude/...` | `app/claude/verification.py` for the Claude call; `app/provenance/` owns pointer assembly + the `build_response_item` branch that *invokes* verification only for `full`. |
| Synthesis | `app/synthesis.py` | `app/claude/synthesis.py`. |
| Shared Claude client | `app/claude/client.py`, `app/llm/client.py`, `app/llm.py` | `app/claude/client.py` — **one** AsyncAnthropic client + model constants + `complete_text`/`parse` + `cached_system_block`. |
| Live-event transport | router's `app/events/bus.py` (EventBus) **and** API's `app/api/events.py` (WSManager) | **Keep both, layered.** `events/bus.py` is the in-process pub/sub the orchestrator/router emit into (decoupled from sockets). `api/events.py` `WSManager` subscribes to the bus per `query_id` and forwards frames to live sockets. One emit path, one socket bridge. |
| Seed data dir | `app/seed/`, `data/`, `backend/data/` | `app/data/` (`agents.json` + `corpora/*.json` + `embeddings.npz`). |

**Model id note:** the subsystem docs disagree on Claude model tiers (Opus vs Haiku
for redaction/verification). Canonical MVP default: **all three calls on
`claude-opus-4-8`**, with **verification as the single sanctioned downgrade to
`claude-haiku-4-5`** if the live loop is latency-bound — swappable via one constant
in `app/claude/client.py`. See open question OQ-6.

---

## 3. Index — contracts and subsystem docs

### Frozen contracts (the seam — edit only with a 2-minute sync)
- [Data model](../shared/contracts/data-model.md) — Agent / Chunk / Cross-agent request / Response item; shared enums; visibility→decision reference table.
- [`search()` interface](../shared/contracts/search-interface.md) — `search(query, agent_id, top_k=5) -> list[Chunk]`; keyword stub; H8 drop-in swap.
- [HTTP + WebSocket API](../shared/contracts/api-websocket.md) — `POST /query`, `POST /grant_access`, `ws://localhost:8000/ws/query`; `agent-activated` / `response-item` / `done` events.

### Subsystem build docs (in canonical build order)
1. [Agents, Isolated Corpus & Flat Vector Index](./docs/agents-corpus-index.md) — retrieval substrate, `search()` + keyword stub, embeddings.
2. [Permission Gate (full / redacted / denied)](./docs/permission-gate.md) — **wedge piece 1**: per-chunk policy + capability + content-free GatedResult.
3. [Redaction Claude Call](./docs/redaction.md) — **wedge piece 1**: restricted text → safe one-line gist, leak-guarded.
4. [Provenance Assembly & Verification](./docs/provenance-verification.md) — **wedge piece 2**: grounding check + provenance pointer.
5. [Router (discovery, cross-agent query, live events)](./docs/router.md) — in-process fan-out + `agent-activated`/`response-item` timing + EventBus.
6. [Orchestrator (plan, fan out, collect, verify, synthesize)](./docs/orchestrator.md) — coordination core in the asking agent + synthesis Claude call.
7. [FastAPI App: HTTP Endpoints & WebSocket Server](./docs/api-websocket.md) — the transport edge; startup wiring; WSManager.
8. [Grant-Access-Live (hero beat)](./docs/grant-access.md) — the coupled feature: toggle visibility + replay on the same `query_id`.

---

## 4. The single ordered build plan (merged, mapped to H1–H18)

One sequence across all subsystems. Checkpoints are spec §16. **The wedge —
gate (steps 9–11), redaction (12–13), verification (15–16) — is sequenced first
after the substrate, because it is the differentiator and everything else either
feeds it or transports it.** Stub seams keep every step unblocked.

> Legend: `H1-3` = hours 1–3; `H8`/`H13`/`H18` = integration checkpoints.

| # | Checkpoint | Subsystem | Action | Depends on |
|---|---|---|---|---|
| 1 | H0-1 | repo/scaffold | Scaffold `backend/app/` tree per §2 (all `__init__.py`, `data/`, `scripts/`, `tests/`), write `requirements.txt`, `.env.example`, `pytest.ini`. | — |
| 2 | H0-1 | models | Write `app/models.py` verbatim against data-model.md (Chunk, Agent, CrossAgentRequest, ResponseItem) + enums (GateDecision). Unblocks every sibling. | 1 |
| 3 | H0-1 (joint w/ Hao) | data/seed | Author `app/data/agents.json` + `corpora/*.json` (10–30 chunks/agent, exact data-model fields minus embedding) and **lock the demo query**: must hit mixed tiers incl. ≥1 restricted (Northwind servo-jitter) + ≥1 private (Quanta) for the denied badge. | 2 |
| 4 | H1-3 | agents | `app/agents/index.py` `AgentIndex` + `load_agent_index(with_embeddings=False)`; assert isolation invariant (owner==agent_id); `corpus.py` load helpers. | 3 |
| 5 | H1-3 | agents | `app/agents/registry.py` `build_registry(with_embeddings=False)` + `AgentRegistry` (get/all_ids/party_name/find_chunk; KeyError on unknown id). Verify 3 separate AgentIndex objects, no shared lists. | 4 |
| 6 | H1-3 | retrieval | `app/retrieval/search.py` STUB path: `search()` dispatch + `_keyword_stub()` per search-interface algorithm; wire registry. Gate-free, all tiers. | 5 |
| 7 | H1-3 | agents | `app/agents/agent.py` `RuntimeAgent`: `.search()` delegating to `search()`, `.respond(gate_fn)` seam (retrieve-first ordering, no gate logic). | 6 |
| 8 | H1-3 | retrieval/agents | Smoke-test the stub on the locked demo query for all 3 agents: own-agent only, all tiers present, descending score, ≤top_k, KeyError on bogus id, `[]` on no-keyword. Run `test_search_stub.py` + `test_isolation.py`. | 6,7 |
| 9 | H3-8 | **gate** | `app/gate/policy.py` pure `decide(visibility)->GateDecision` + fail-closed unknown tier + `SHOW_EXISTENCE_FOR_PRIVATE`. Unit-test all 3 tiers + unknown (no Claude, no I/O). | 2 |
| 10 | H3-8 | **gate** | `app/gate/capability.py` `Capability`/`CapabilityGrant`/`issue_grant()`/`allows()` — second independent gate (public grant down-ranks private→denied). | 9 |
| 11 | H3-8 | **gate** | `app/gate/gate.py` `evaluate(chunk, *, query, grant, resolve_party_name)` end-to-end with a temporary no-op redact returning a static fallback gist; add `GatedResult` + `to_wire()` to `models.py`. **Leakage test:** no raw text/embedding in non-full GatedResult. | 10 |
| 12 | H3-8 | **redaction** | `app/claude/client.py` shared AsyncAnthropic client + model constants + `complete_text`/`cached_system_block`; `app/claude/prompts.py` frozen redaction prompt. | 2 |
| 13 | H3-8 | **redaction** | `app/claude/redaction.py` `redact(chunk)`: real Claude call (max_tokens~80, temp/sampling per Opus 4.8) + deterministic leak-guard + `_safe_fallback`; swap into `gate.py`. Test against the seeded restricted servo chunk: gist exists, one line, does NOT contain the solution token. | 12,11 |
| 14 | **H8** | retrieval/integration | **H8 swap:** `app/agents/embeddings.py` (pin EMBED_MODEL/EMBED_DIM) + `scripts/build_embeddings.py` (write `data/embeddings.npz`) + `_cosine_search()` behind `BEACON_SEARCH=cosine`, OR delegate `search()` to Hao's real module. Re-run step-8 tests; sync EMBED_MODEL/EMBED_DIM with Hao. Drop-in, no call-site change. | 8,13 |
| 15 | H8-13 | **verification** | `app/claude/verification.py` `verify_answer(answer, source_text)->VerifyResult` (structured `parse`, max_tokens=128, frozen cached system block, fail-closed verified=False). Smoke-test one supported (True) + one contradicting (False) pair. | 12 |
| 16 | H8-13 | **provenance** | `app/provenance/pointer.py` `assemble_provenance()` (never reads text/embedding) + `app/provenance/assembler.py` `build_response_item(chunk, decision)` — verify ONLY `full`; redacted/denied stay verified=False; delegate redacted gist to redaction. | 15,13 |
| 17 | H8-13 | events/router | `app/events/bus.py` `EventBus` (subscribe/emit/unsubscribe via put_nowait); unit-test two queues on one query_id both receive. | 1 |
| 18 | H8-13 | router | `app/router/responder.py` `respond_for_agent(agent_id, query)`: search → gate.evaluate (with issue_grant + registry.party_name) → build_response_item. The boundary pipeline, inside the responder. | 16,7 |
| 19 | H8-13 | router | `app/router/events.py` builders + `app/router/router.py` `Router.dispatch()`: emit ALL `agent-activated` before awaiting any responder, then concurrent responder calls, emit one `response-item` per item; return flat list. Test event ordering against a fake responder, dicts byte-match contract. | 17,18 |
| 20 | H8-13 | orchestrator | `app/orchestrator/orchestrator.py` `Orchestrator.run(query, from_agent, query_id=None)`: resolve asker, allocate query_id (reuse if given), fan out via router, collect, drive verification (bounded concurrency), emit `response-item`, then synthesize + emit one `done`. Test order: all agent-activated → N response-item → exactly one done. | 19 |
| 21 | H8-13 | **synthesis** | `app/claude/synthesis.py` `synthesize(query, items, redacted)`: verified-full only, restricted as existence-only access ask, empty-input guard. Snapshot-test the prompt contains NO restricted payloads (leakage guard). Wire into orchestrator `done`. | 20 |
| 22 | H8-13 | api | `app/config.py` (Settings/get_settings: CORS, seed paths, model ids, top_k, default asker), `app/core/ids.py` (`new_query_id`), `app/api/schemas.py` (wire models verbatim — the freeze point with Hao's mock). | 2 |
| 23 | H8-13 | api | `app/api/events.py` `WSManager` (subscribe/emit-by-query_id/unsubscribe) bridging `EventBus` → live sockets; `app/deps.py` accessors. | 17,22 |
| 24 | H8-13 | api | `app/api/http.py` `POST /query` (resolve asker, compute `agents[]` excluding asker, mint id, `run_registry.put`, fire-and-forget run, return QueryResponse) + `app/run_registry.py` `RunRegistry`. | 23,20 |
| 25 | H8-13 | api | `app/api/ws.py` `/ws/query` (WS-driven `type:query`→`ack`; POST+WS `type:subscribe`; disconnect cleanup). | 23,24 |
| 26 | H8-13 | api | `app/main.py` `create_app()` + lifespan (build_registry, set search registry, build WSManager + Orchestrator into `app.state`, CORSMiddleware, mount routers). Run `uvicorn app.main:app`. | 24,25 |
| 27 | **H13** | integration | **H13 vertical demo:** point Hao's frontend at `ws://localhost:8000/ws/query`; smoke both transports on the locked query; assert no WS frame contains `embedding` or full restricted text; verified-check + redacted gist + synthesized answer + provenance all render. | 26,21,14 |
| 28 | H13-18 | grant_access | `app/agents/index.py` add `set_visibility(chunk_id, visibility)` (resolve owner from global chunk_id, mutate one row, ChunkNotFoundError on miss); unit-test isolation (only that row changes). | 5 |
| 29 | H13-18 | grant_access | `GrantAccessRequest/Response` in `models.py`; `app/grant_access/service.py` `GrantAccessService` (toggle_visibility + grant_and_rerun + replay); `app/grant_access/routes.py` `POST /grant_access` (ack + BackgroundTasks replay on same query_id); mount in `main.py`. | 28,24,20 |
| 30 | **H18** | grant_access/integration | **H18 hero beat:** end-to-end — POST /query (redacted card) → POST /grant_access (200 `{new_visibility:"public", rerunning:true}`) → fresh agent-activated/response-item(`full`,`verified`)/done on the same query_id. Idempotency pass (double-click). Pair with Hao on the grey→green animation. | 29,27 |

---

## 5. Consolidated pip dependencies

`backend/requirements.txt` (MVP — no DB, no auth, no Chroma):

```
fastapi
uvicorn[standard]          # ASGI server + websockets extra
pydantic>=2
pydantic-settings
anthropic>=0.40            # redaction / verification / synthesis Claude calls
python-dotenv              # load ANTHROPIC_API_KEY in dev
numpy                      # cosine math + embedding matrices
sentence-transformers      # local all-MiniLM-L6-v2 embeddings (no key, deterministic) — pick ONE provider
torch                      # sentence-transformers backend
# voyageai                 # ALT to sentence-transformers+torch (hosted, needs VOYAGE_API_KEY)
pytest                     # unit tests
pytest-asyncio             # async orchestrator/router/verify tests
# chromadb                 # OPTIONAL — only if Hao's substrate uses it; plain numpy is simpler for tiny corpora
```

**Embedding provider:** pick exactly one. Default **local sentence-transformers
`all-MiniLM-L6-v2`** (no API key, deterministic, removes network latency) — note
this is NOT a Claude model; Anthropic has no embeddings endpoint. The stub path is
model-free so backend dev is never blocked on this choice.

---

## 6. FastAPI app entrypoint plan (how the pieces wire at startup)

Entry: `uvicorn app.main:app --reload --port 8000`. `app = create_app()` in
`app/main.py`. Startup wiring, in order, inside the `lifespan`:

1. **Load settings** — `config.get_settings()` reads `ANTHROPIC_API_KEY`, CORS
   origins (Vite 5173 / CRA 3000), seed paths, `top_k`, default asker, `BEACON_SEARCH`,
   the three Claude model ids.
2. **Build the registry** — `agents.registry.build_registry(with_embeddings=...)`
   loads `app/data/agents.json` + `corpora/*.json` into 3 isolated `AgentIndex`
   objects, asserts `owner == agent_id` and enum validity at load, attaches the
   embedding matrix from `data/embeddings.npz` when in cosine mode.
3. **Wire search** — set the registry on `retrieval.search` so `search(query,
   agent_id, top_k)` resolves the agent's index. `BEACON_SEARCH=stub|cosine`
   selects the backend (drop-in identical shape).
4. **Build the event plumbing** — one `EventBus` instance, and one `WSManager`
   that subscribes to the bus per `query_id` and forwards frames to live sockets.
5. **Build the Orchestrator** — `Orchestrator(emit=ws/bus sink)` holding the
   registry, the `Router` (with `respond_for_agent` injected as the ResponderFn),
   verification, and synthesis. Stash registry / orchestrator / ws_manager /
   run_registry / grant_access_service into `app.state`; `deps.py` reads them off
   `request.app.state` / `ws.app.state`.
6. **Middleware + routers** — add `CORSMiddleware`, then
   `app.include_router()` for the HTTP query router (`api/http.py`), the WS route
   (`api/ws.py`), and the grant-access router (`grant_access/routes.py`).

**Request-time flow:** `POST /query` resolves the asker (default from settings),
computes `agents[]` = parties minus asker, mints `q_…`, calls
`run_registry.put(query_id, query, from_agent)`, schedules
`orchestrator.run(...)` as a fire-and-forget asyncio task, and returns
`{query_id, from_agent, agents}` immediately. The task fans out via the router
(emitting `agent-activated` per party into the bus), each responder runs
search→gate→redact/verify **inside the responding agent**, the orchestrator emits
`response-item` per resolved item, then verifies `full` items, synthesizes, and
emits one `done`. The WS endpoint either drives the run (`type:query`→`ack`) or
subscribes an existing `query_id` (POST+WS). `POST /grant_access` flips one
chunk's visibility via `AgentIndex.set_visibility`, then replays
`orchestrator.run(..., query_id=original)` on the same id so a fresh
agent-activated→response-item→done cycle streams. **Outbound Pydantic schemas have
no `embedding`/`score`/raw-`text` fields — the boundary is enforced at the type
level.**

---

## 7. Open questions / contract gaps (resolve in a 2-minute sync before/at build)

These are underspecified in the frozen contracts. None require widening a frozen
shape; each is a small policy choice or a coordination point. Resolve at the
hour-0 sync (OQ-1, OQ-3, OQ-6) or the relevant checkpoint.

1. **OQ-1 — Demo asker identity.** `POST /query.from_agent` is optional and
   "defaults to a fixed demo asker." If the default IS one of the 3 parties,
   fan-out is to 2 (matches the `agent_helios` example, `item_count: 2`). If it's
   a non-party 4th id (e.g. `agent_asker`), fan-out is to all 3. **Decision needed
   hour 0:** lock `agent_helios` as the demo asker (clean 2-party fan-out, matches
   the contract example) or register a non-party asker. Router/orchestrator support
   either with no code change.

2. **OQ-2 — Denied items: emit a frame or not?** The contract allows a denied item
   to show existence-only OR nothing. It's ambiguous whether a fully-denied party
   emits a `response-item`. **Proposed MVP:** emit a `denied` response-item only
   for existence-only (`answer:null`, `source_doc_title:null`); emit nothing for
   full-deny. Frontend/UX call; only *whether* the frame is sent changes, never the
   shape.

3. **OQ-3 — `item_count` semantics.** If denied/hidden items don't emit a
   `response-item`, `item_count` < retrieved-chunk count. Lock `item_count` =
   number of `response-item` events actually emitted this run (single source of
   truth in the orchestrator's `_finish`). Confirm Hao reads it as that.

4. **OQ-4 — Provenance `timestamp`.** Spec §3 names a provenance "timestamp" but
   the frozen data-model §4 / WS payloads carry none. Keep `timestamp` internal to
   `ProvenancePointer` (logs/debug only); do NOT put it on any wire shape.
   Surfacing it later is a 2-minute data-model amendment, not a unilateral edit.

5. **OQ-5 — No WS error frame.** The frozen WS contract defines only
   `agent-activated`/`response-item`/`done` — there is no error event. A fully
   failed run must still emit a terminal `done` (fallback synthesized answer +
   partial/empty provenance) so the client never hangs. A real error channel is a
   post-MVP contract sync, not an invented event.

6. **OQ-6 — Claude model tiers per call.** Subsystem docs disagree
   (Opus vs Haiku for redaction/verification). **Lock:** redaction +
   verification + synthesis all default to `claude-opus-4-8`; **verification is
   the one sanctioned downgrade to `claude-haiku-4-5`** if the live loop is
   latency-bound, via a single constant in `app/claude/client.py`. Confirm the
   final tiers at H13 once latency is measured. (Param note: Haiku 4.5 rejects
   `effort`/`thinking`; Opus 4.8 drops sampling params — keep call args minimal.)

7. **OQ-7 — Embedding provider + EMBED_DIM.** sentence-transformers MiniLM
   (dim 384, local, no key) vs hosted Voyage. Must be locked WITH Hao at H8 so the
   corpus model and query model match (mismatch → garbage cosine). Pin
   `EMBED_MODEL`/`EMBED_DIM` in one constant; the seed JSON `embedding` is a
   placeholder until then.

8. **OQ-8 — `run_registry` ownership.** The frozen `grant_access` body carries only
   `{chunk_id, query_id}`, so server-side run state (`query → from_agent`) is
   REQUIRED to replay. Canonical home: `app/run_registry.py`, written by the
   `/query` handler at mint time. If the orchestrator already retains run state,
   collapse `RunRegistry` to a reader. **Do not widen the frozen request body.**
   If `/query` forgets `registry.put(...)`, every grant_access 404s — assert it in
   the grant-access smoke test (step 30).

9. **OQ-9 — Optional cosine min-score floor.** Contracts define no min-score floor;
   the stub may surface low-relevance noise. Left to `top_k` only for MVP. If noise
   hurts the demo, add an optional floor in `_cosine_search` ONLY — never in the
   stub, never as a visibility filter (that would be gating inside retrieval).

---

## 8. Scope addendum — decisions locked with Dennis (supersedes where noted)

Decided after the initial index. These take precedence over the section they amend.

### 8.1 Retrieval substrate is now backend-owned (Hao = frontend only)
Hao is building frontend only, so the retrieval substrate that was "Hao's H8 swap"
is now Dennis's. **Step 14 is no longer optional/delegated** — Dennis implements:
- `app/agents/embeddings.py` — real embeddings via **sentence-transformers `all-MiniLM-L6-v2`** (local, no API key, dim 384). NOT a Claude call (Anthropic has no embeddings endpoint).
- `_cosine_search()` in `retrieval/search.py` — the real cosine path behind the frozen `search()`.
- `scripts/build_embeddings.py` — generate `data/embeddings.npz` offline.
The keyword stub stays as the H1–3 unblock **and** a live fallback. `search()` interface unchanged. Add `sentence-transformers` + `torch` to `requirements.txt`.

### 8.2 Corpora are REAL Claude-account data, not mock (supersedes Step 3)
Each of the 3 parties = **real exported data from a real Claude account** (Dennis, Hao, and the team's third account):
1. Each person exports their Claude.ai conversation history (account settings → data export — confirm exact steps).
2. Chunk per spec §9 (one question+resolution per chat thread).
3. **Tiers (public/restricted/private) are assigned by hand** — content is real; the visibility labels are curated. (At scale, parties set their own policy; here we set it for our 3 accounts.)
4. Curate the locked demo query so it lands on the intended tiers across parties.

**Team action (hour 0):** ensure each account actually holds ≥1 real, on-topic engineering conversation, and that the spread yields ≥1 restricted (redact/grant beat) + ≥1 private (denied badge). Personal history alone won't — have real on-topic conversations in each account *before* export.

### 8.3 Per-party Claude personas
Each agent gets a distinct system-prompt persona ("You are <Party>'s knowledge agent…") in `app/claude/prompts.py`, so the parties read as genuinely separate Claude-backed agents, not one model. Cheap — do it with the agent/registry wiring (Step 5/7).

### 8.4 MCP — the scale path, not the MVP transport
- `search()` is the seam: an MCP-backed retrieval is a drop-in behind it, no change to gate/orchestrator/frontend.
- **Faithfulness rule:** the gate must run *inside* the party's boundary, so any MCP server used must do retrieve→gate→redact internally and return **only gated items** — never raw restricted text.
- **MVP:** local cosine, no MCP on the critical path.
- **Stretch (H18 buffer only, feature-flagged, local fallback):** wire ONE party behind a real MCP server (gate inside) for the "genuinely MCP" pitch beat; two parties stay local to guarantee the demo.
- **Pitch framing:** "parties connect live knowledge via MCP; corpora are seeded from our real accounts for the demo; the gate + provenance is what we built."

### 8.5 New backend items to add (from the gap analysis)
- **Deterministic retrieval sanity check** — assert the locked query retrieves the intended real chunks across all 3 parties (repeatable live demo).
- **Terminal `done` on failure** (OQ-5) — a failed run still emits `done` so the UI never hangs; make it an explicit orchestrator step.
- **Dev/launch tooling** — `run.sh`/Makefile + `.env` bootstrap + a seed-reset to re-run the demo cleanly between rehearsals.
- **Optional:** fabricated-source fixture for the verification `✗` kicker (demo step 7).
