# Graph Report - beacon  (2026-06-20)

## Corpus Check
- 74 files · ~62,284 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 774 nodes · 1072 edges · 61 communities detected
- Extraction: 77% EXTRACTED · 23% INFERRED · 0% AMBIGUOUS · INFERRED: 244 edges (avg confidence: 0.78)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bf7380d5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]

## God Nodes (most connected - your core abstractions)
1. `AgentRegistry` - 21 edges
2. `redact()` - 16 edges
3. `verify_answer()` - 15 edges
4. `RuntimeAgent` - 15 edges
5. `Relay Build Spec v2` - 15 edges
6. `Chunk` - 13 edges
7. `AgentIndex` - 13 edges
8. `patch_claude()` - 13 edges
9. `Orchestrator` - 12 edges
10. `lifespan()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `Chunk Record Shape` --conceptually_related_to--> `Chunk`  [INFERRED]
  shared/contracts/data-model.md → backend/app/models.py
- `Agent Record Shape` --conceptually_related_to--> `Agent`  [INFERRED]
  shared/contracts/data-model.md → backend/app/models.py
- `Cross-Agent Request Shape` --conceptually_related_to--> `CrossAgentRequest`  [INFERRED]
  shared/contracts/data-model.md → backend/app/models.py
- `Response Item Shape` --conceptually_related_to--> `ResponseItem`  [INFERRED]
  shared/contracts/data-model.md → backend/app/models.py
- `Redaction Claude Call (restricted gist)` --conceptually_related_to--> `redact()`  [INFERRED]
  docs/relay-spec.md → backend/app/claude/redaction.py

## Hyperedges (group relationships)
- **In-Responder Search->Gate->Redact Boundary Pipeline** — agent_respond, redaction_redact, permission_gate_wedge, retrieve_first_gate_second [INFERRED 0.85]
- **FastAPI Startup Wiring (registry -> search -> bus -> orchestrator)** — registry_build_registry, index_load_agent_index, events_wsmanager, layered_event_transport [INFERRED 0.75]
- **Grant-Access Live Replay Loop** — index_set_visibility, schemas_grantaccessrequest, replay_same_query_id, grant_access_hero_beat [INFERRED 0.85]
- **Per-Chunk Gate Evaluation (policy + capability + result)** — gate_evaluate, policy_decide, capability_allows, models_gatedresult [INFERRED 0.85]
- **Orchestrator run pipeline: fan-out, verify, synthesize, emit** — orchestrator_run, verification_verify_answer, synthesis_synthesize, models_responseitem [INFERRED 0.80]
- **Grant-access toggle-and-replay flow** — routes_grant_access, service_grant_and_rerun, service_toggle_visibility, service_replay, orchestrator_run [INFERRED 0.80]
- **Retrieve-gate-redact/verify boundary pipeline** — responder_respond_for_agent, search_search, permission_gate_evaluate, provenance_build_response_item [INFERRED 0.85]
- **Grant-access toggle-and-replay hero beat** — grant_access_set_visibility, grant_access_replay, orchestrator_run_query, run_registry_runregistry [INFERRED 0.85]
- **Live WS event lifecycle (activated/item/done)** — events_agent_activated_event, events_response_item_event, api_websocket_done_event, router_eventbus [INFERRED 0.75]
- **Three Frozen Hour-0 Contracts** — contract_data_model, contract_search_interface, contract_api_websocket [EXTRACTED 1.00]
- **Query Loop: Router-Gate-Verify-Synthesize** — relay_router, relay_permission_gate, relay_verification_claude_call, relay_orchestrator_loop [EXTRACTED 1.00]
- **Three-Tier Visibility-to-Decision Mapping** — relay_three_tier_permission_model, datamodel_visibility_decision_enums, relay_redaction_claude_call [INFERRED 0.85]

## Communities (66 total, 25 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (50): GateDecision, The gate's per-chunk verdict. Values match data-model §4 `decision` verbatim., Visibility / Decision Enums + Gate Mapping, Enum, Exception, Flag, allows(), Capability (+42 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (56): H8 drop-in search swap, respond() gate seam, Retrieve-first, gate-second, agent-activated WS event, done WS event, WSManager (emit-by-query_id), cached_system_block, complete_text (+48 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (35): _passes_leak_guard(), Redaction Claude call: restricted text -> safe one-line gist (redaction.md §2.2), Return a safe one-line gist for a RESTRICTED chunk. Never returns chunk text., Return a safe one-line gist for a RESTRICTED chunk. Never returns chunk text., Deterministic content-free gist from owner-published doc_title only., Cheap deterministic backstop: reject if the gist shares a >=6-word verbatim, Deterministic, content-free gist (carries none of the restricted text). The, Reject if the gist is suspiciously long (>240 chars) or shares a >=6-word     ve (+27 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (37): agent-activated WS Event, done WS Event, response-item WS Event, POST /grant_access Endpoint, POST /query Endpoint, Frozen Contract 3: HTTP + WebSocket API, Frozen Contract 1: Data Model, Frozen Contract 2: search() Interface (+29 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (43): Query loop (spec section 10), response-item WS event, EventBus, allows, Capability, CapabilityGrant, issue_grant, get_settings (+35 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (38): Agent Isolation Invariant (owner == agent_id), RuntimeAgent.respond, RuntimeAgent, RuntimeAgent.search, assert_isolation, load_corpus_chunks, WSManager.emit, WSManager.subscribe (+30 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (26): _cosine_search(), _dense_order(), _get_bm25(), _hybrid_search(), _keyword_stub(), _lexical_order(), Frozen search() interface + keyword stub + real cosine (agents-corpus-index.md §, Lazily build + cache a BM25Okapi index over the agent's OWN chunks only.      To (+18 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (21): assert_isolation(), load_corpus_chunks(), Corpus load helpers + isolation assert (agents-corpus-index.md §2.3).  Responsib, Read app/data/corpora/<agent_id>.json into a list of Chunk dicts.      Asserts t, Raise if any chunk's `owner != agent_id` (spec §6 isolation guarantee)., Raise if any chunk's `owner != agent_id` (spec §6 isolation guarantee)., embed_query(), embed_texts() (+13 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (13): WSManager: bridge EventBus -> live sockets (api-websocket.md §2.6).  Responsibil, query_id -> set[WebSocket]; bridges EventBus frames to live sockets., Bind a socket to a query_id and start forwarding bus frames to it., Drop a socket from every query_id on disconnect., Send one event dict to all subscribers of query_id. Best-effort: a failed, WSManager, EventBus, EventBus: in-process async pub/sub keyed by query_id (router.md §2.4).  Responsi (+5 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (23): Agent, CrossAgentRequest, GatedResult, GrantAccessRequest, GrantAccessResponse, ProvenancePointer, Shared record shapes — the single source of truth for the whole backend.  Respon, The pointer half of the provenance/content split (spec §3).      Travels even wh (+15 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (9): ArrowIcon(), CheckIcon(), ChevronIcon(), DocIcon(), HandoffIcon(), LockIcon(), ResetIcon(), ShieldIcon() (+1 more)

### Community 11 - "Community 11"
Cohesion: 0.14
Nodes (14): build_response_item(), Finalize a GatedResult into the wire ResponseItem (provenance-verification.md §2, Turn one gated chunk into the canonical Response item.      `decision` is the ga, Turn one gated chunk into the canonical Response item.      full -> verify the a, assemble_provenance(), Provenance pointer assembly — no Claude (provenance-verification.md §2.2).  Buil, Build the provenance pointer from a gated chunk (data-model §2 dict).      Resol, Build the provenance pointer from a gated chunk (data-model §2 dict).      Reads (+6 more)

### Community 12 - "Community 12"
Cohesion: 0.16
Nodes (17): cached_system_block(), call_tool(), complete_text(), _first_block(), get_client(), _load_env_file(), parse(), Shared AsyncAnthropic client + model ids + helpers (redaction.md §2.1, provenanc (+9 more)

### Community 13 - "Community 13"
Cohesion: 0.14
Nodes (15): AgentIndex, _build_matrix(), ChunkNotFoundError, load_agent_index(), AgentIndex: one agent's isolated flat index (agents-corpus-index.md §2.3, grant-, Raised by set_visibility when chunk_id is unknown (-> 404 upstream)., Raised by set_visibility when chunk_id is unknown (-> 404 upstream)., One agent's isolated flat index. Holds ONLY this agent's chunks.      `matrix` i (+7 more)

### Community 14 - "Community 14"
Cohesion: 0.2
Nodes (17): _content_to_text(), _derive_title(), ingest_party(), is_noise(), iter_cc_sessions(), main(), _norm(), QAUnit (+9 more)

### Community 15 - "Community 15"
Cohesion: 0.17
Nodes (15): get_grant_access_service(), get_orchestrator(), get_orchestrator_ws(), get_registry(), get_run_registry(), get_ws_manager(), get_ws_manager_ws(), Request-time app.state accessors (api-websocket.md §2.9).  Responsibility: thin (+7 more)

### Community 16 - "Community 16"
Cohesion: 0.15
Nodes (11): AgentRegistry, build_registry(), AgentRegistry: the single agent_id -> Agent resolution point (agents-corpus-inde, Holds the 3 RuntimeAgents; the only place agent_id -> Agent resolution lives., Holds the 3 RuntimeAgents; the only place agent_id -> Agent resolution lives., Resolve an agent by id. Raises KeyError on unknown id (search() contract)., Resolve an agent by id. Raises KeyError on unknown id (search() contract)., Resolve party_name (for agent-activated / ResponseItem.source_party). (+3 more)

### Community 17 - "Community 17"
Cohesion: 0.35
Nodes (12): AgentActivatedEvent, DoneEvent, GrantAccessRequest, GrantAccessResponse, ProvenanceEntry, QueryRequest, QueryResponse, Pydantic WIRE models — verbatim from the frozen contract (api-websocket.md §2.5, (+4 more)

### Community 18 - "Community 18"
Cohesion: 0.18
Nodes (6): GrantAccessService, Owns the two new behaviors: mutate one chunk's visibility, and trigger a     rep, Flip one chunk's stored visibility (restricted -> public for the demo)., Validate the query_id, toggle the chunk, and build the ACK. The replay is, Re-invoke the orchestrator for the stored query on the SAME query_id,         st, Tests for app/grant_access/ (BUILD_INDEX.md §2 / step 30).  TODO: assert toggle_

### Community 19 - "Community 19"
Cohesion: 0.2
Nodes (7): Per-query_id run context for grant-access replay (grant-access.md §2.3, OQ-8)., The original request behind one query_id (grant-access.md §2.3)., In-memory map query_id -> RunContext. Single source of truth for     'what was t, Store run context at query mint time (/query happy path)., Look up the original request for a query_id; None if unknown., RunContext, RunRegistry

### Community 20 - "Community 20"
Cohesion: 0.21
Nodes (10): Frozen, byte-stable system/user prompt templates (cache-friendly).  One place fo, Build the per-call redaction user message. SKELETON — no logic., Build the per-call redaction user message., Build the per-call verification user message (delimited tags). SKELETON., Build the per-call synthesis user message. Must contain NO restricted     payloa, Build the per-call verification user message (delimited tags)., Build the per-call synthesis user message (Phase 3)., redaction_user() (+2 more)

### Community 21 - "Community 21"
Cohesion: 0.17
Nodes (3): Serialize to the EXACT frozen response-item payload (api-websocket.md)., Cardinal no-leak test: restricted/private content never crosses the boundary., Tests for app/models.py (BUILD_INDEX.md §2 / step 2).  Phase 1 scope: the frozen

### Community 22 - "Community 22"
Cohesion: 0.22
Nodes (7): RuntimeAgent: identity + own AgentIndex + the gate seam (agents-corpus-index.md, One party agent: identity + its own isolated index only., One party agent: identity + its own isolated index only., Retrieve over OWN index only. Delegates to search.search(query, self.id,, Retrieve over OWN index only. Delegates to search.search(query, self.id,, Seam for the GATE subsystem. retrieve-first, gate-second, IN this agent, RuntimeAgent

### Community 23 - "Community 23"
Cohesion: 0.2
Nodes (3): _agent(), hybrid_registry(), Hybrid retrieval (BM25 + static dense, RRF) — Phase 1.5.  Self-contained: builds

### Community 24 - "Community 24"
Cohesion: 0.31
Nodes (7): Config, get_settings(), Application settings (api-websocket.md §2.2).  Responsibility: pydantic-settings, Process-wide settings. Env-prefixed `RELAY_`, loaded from `.env` in dev., Return the cached process-wide Settings instance., Settings, BaseSettings

### Community 25 - "Community 25"
Cohesion: 0.28
Nodes (8): _agent(), fixture_registry(), make_chunk(), make_fake_client(), Deterministic hand-built registry: mixed tiers + known overlaps., Registry built from the ingested real corpora (keyword-stub mode)., Stand-in for AsyncAnthropic whose .messages.create returns a canned message (a, real_registry()

### Community 26 - "Community 26"
Cohesion: 0.32
Nodes (6): GrantResult, GrantAccessService: toggle + replay (grant-access.md §2.1).  Responsibility: the, Internal result of grant_and_rerun, shaped into GrantAccessResponse by the route, Raised when query_id has no stored RunContext (-> 404)., UnknownQueryError, KeyError

### Community 27 - "Community 27"
Cohesion: 0.29
Nodes (4): Orchestrator, Orchestrator.run: plan -> fan out -> collect -> verify -> synthesize (orchestrat, Drives one query run end-to-end. Transport-agnostic via an injected sink., Schedule run() as a fire-and-forget asyncio task and return immediately

### Community 28 - "Community 28"
Cohesion: 0.29
Nodes (4): Router.dispatch: fan-out + event timing (router.md §2.3).  Responsibility: resol, In-process fan-out engine + event clock., Fan a cross-agent request out to every discovered party.          Phase 1: emit, Router

### Community 29 - "Community 29"
Cohesion: 0.38
Nodes (5): create_app(), lifespan(), FastAPI entrypoint: create_app() + lifespan (api-websocket.md §2.1, BUILD_INDEX., Startup wiring (BUILD_INDEX.md §6), in order:      1. load settings;     2. buil, Construct the FastAPI app: lifespan, CORS, and mounted routers.      SKELETON —

### Community 30 - "Community 30"
Cohesion: 0.33
Nodes (4): Chunk, One row in an agent's flat index (data-model.md §2).      `embedding` is server-, _FakeBlock, _FakeMessage

### Community 31 - "Community 31"
Cohesion: 0.6
Nodes (5): list_chunks(), _load(), main(), Flip one chunk's visibility tier in a seed corpus, safely.  Avoids hand-editing, set_tier()

### Community 32 - "Community 32"
Cohesion: 0.5
Nodes (3): new_query_id(), query_id minting (api-websocket.md §2.4, BUILD_INDEX.md §2 core/ids.py).  Respon, Return a fresh opaque query id, e.g. "q_" + short hex.

### Community 33 - "Community 33"
Cohesion: 0.5
Nodes (3): Synthesis Claude call: final cited answer (orchestrator.md §3.1, BUILD_INDEX §2., Compose the final cited answer from verified full items (SYNTH_MODEL,     max_to, synthesize()

### Community 34 - "Community 34"
Cohesion: 0.5
Nodes (3): /ws/query WebSocket endpoint (api-websocket.md §2.8).  Responsibility: support B, Accept the socket, then loop on frames: `type:query` mints a run + acks +     st, ws_query()

### Community 35 - "Community 35"
Cohesion: 0.5
Nodes (3): POST /query handler (api-websocket.md §2.7).  Responsibility: resolve the asker, Mint a query_id, record run state, kick the fan-out, return immediately.     SKE, submit_query()

## Knowledge Gaps
- **216 isolated node(s):** `Return the AgentRegistry from request.app.state.`, `Return the Orchestrator from request.app.state.`, `Return the WSManager from request.app.state.`, `Return the RunRegistry from request.app.state.`, `Return the GrantAccessService from request.app.state (DI for the route).` (+211 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Chunk` connect `Community 30` to `Community 0`, `Community 3`, `Community 9`, `Community 13`, `Community 16`, `Community 22`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `AgentRegistry` connect `Community 16` to `Community 41`, `Community 42`, `Community 18`, `Community 22`, `Community 23`, `Community 25`, `Community 26`, `Community 27`, `Community 28`, `Community 30`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Why does `Relay Build Spec v2` connect `Community 3` to `Community 7`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `AgentRegistry` (e.g. with `hybrid_registry()` and `fixture_registry()`) actually correct?**
  _`AgentRegistry` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `redact()` (e.g. with `complete_text()` and `redaction_user()`) actually correct?**
  _`redact()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `verify_answer()` (e.g. with `call_tool()` and `verification_user()`) actually correct?**
  _`verify_answer()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `RuntimeAgent` (e.g. with `build_registry()` and `_agent()`) actually correct?**
  _`RuntimeAgent` has 9 INFERRED edges - model-reasoned connections that need verification._