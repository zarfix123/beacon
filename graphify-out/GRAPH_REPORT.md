# Graph Report - /Users/hlin/Documents/badminton/code/beacon  (2026-06-20)

## Corpus Check
- Corpus is ~49,080 words - fits in a single context window. You may not need a graph.

## Summary
- 520 nodes · 603 edges · 53 communities detected
- Extraction: 72% EXTRACTED · 28% INFERRED · 0% AMBIGUOUS · INFERRED: 166 edges (avg confidence: 0.79)
- Token cost: 288,384 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Capability Gate & App Wiring|Capability Gate & App Wiring]]
- [[_COMMUNITY_WebSocket Manager & Config|WebSocket Manager & Config]]
- [[_COMMUNITY_Permission Gate Package|Permission Gate Package]]
- [[_COMMUNITY_Boundary Pipeline & Claude Helpers|Boundary Pipeline & Claude Helpers]]
- [[_COMMUNITY_API Endpoints & Frozen Contracts|API Endpoints & Frozen Contracts]]
- [[_COMMUNITY_Shared Data Models|Shared Data Models]]
- [[_COMMUNITY_Agent Isolation & Runtime|Agent Isolation & Runtime]]
- [[_COMMUNITY_Corpus Loading & Embeddings|Corpus Loading & Embeddings]]
- [[_COMMUNITY_Grant-Access & Wire Schemas|Grant-Access & Wire Schemas]]
- [[_COMMUNITY_Router Fan-Out & Events|Router Fan-Out & Events]]
- [[_COMMUNITY_Runtime Agent & Index|Runtime Agent & Index]]
- [[_COMMUNITY_App.state Dependency Accessors|App.state Dependency Accessors]]
- [[_COMMUNITY_WS Event Builders & Tests|WS Event Builders & Tests]]
- [[_COMMUNITY_Search (Stub + Cosine)|Search (Stub + Cosine)]]
- [[_COMMUNITY_API Wire Schemas|API Wire Schemas]]
- [[_COMMUNITY_Agent Registry|Agent Registry]]
- [[_COMMUNITY_Grant-Access Service|Grant-Access Service]]
- [[_COMMUNITY_Run Registry|Run Registry]]
- [[_COMMUNITY_Orchestrator|Orchestrator]]
- [[_COMMUNITY_Claude Client|Claude Client]]
- [[_COMMUNITY_Provenance Assembly|Provenance Assembly]]
- [[_COMMUNITY_Redaction Claude Call|Redaction Claude Call]]
- [[_COMMUNITY_Grant-Access Errors|Grant-Access Errors]]
- [[_COMMUNITY_Claude Prompt Templates|Claude Prompt Templates]]
- [[_COMMUNITY_Registry Builder|Registry Builder]]
- [[_COMMUNITY_Query ID Minting|Query ID Minting]]
- [[_COMMUNITY_Synthesis Claude Call|Synthesis Claude Call]]
- [[_COMMUNITY_WebSocket Endpoint|WebSocket Endpoint]]
- [[_COMMUNITY_POST query Handler|POST /query Handler]]
- [[_COMMUNITY_Responder Boundary Pipeline|Responder Boundary Pipeline]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
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
- [[_COMMUNITY_Community 52|Community 52]]

## God Nodes (most connected - your core abstractions)
1. `Relay Build Spec v2` - 15 edges
2. `AgentRegistry` - 14 edges
3. `Orchestrator` - 11 edges
4. `lifespan()` - 10 edges
5. `GrantAccessService` - 10 edges
6. `EventBus` - 10 edges
7. `redact` - 10 edges
8. `Frozen Contract 1: Data Model` - 10 edges
9. `RunRegistry` - 9 edges
10. `WSManager` - 9 edges

## Surprising Connections (you probably didn't know these)
- `Response Item Shape` --conceptually_related_to--> `ResponseItem`  [INFERRED]
  shared/contracts/data-model.md → app/models.py
- `Redaction Claude Call (restricted gist)` --conceptually_related_to--> `redact()`  [INFERRED]
  docs/relay-spec.md → app/claude/redaction.py
- `search(query, agent_id, top_k) Signature` --conceptually_related_to--> `search()`  [INFERRED]
  shared/contracts/search-interface.md → app/retrieval/search.py
- `Visibility / Decision Enums + Gate Mapping` --conceptually_related_to--> `decide()`  [INFERRED]
  shared/contracts/data-model.md → app/gate/policy.py
- `Chunk Record Shape` --conceptually_related_to--> `Chunk`  [INFERRED]
  shared/contracts/data-model.md → app/models.py

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

## Communities (53 total, 23 thin omitted)

### Community 0 - "Capability Gate & App Wiring"
Cohesion: 0.07
Nodes (43): Query loop (spec section 10), response-item WS event, EventBus, allows, Capability, CapabilityGrant, issue_grant, get_settings (+35 more)

### Community 1 - "WebSocket Manager & Config"
Cohesion: 0.05
Nodes (27): WSManager: bridge EventBus -> live sockets (api-websocket.md §2.6).  Responsibil, query_id -> set[WebSocket]; bridges EventBus frames to live sockets., Bind a socket to a query_id and start forwarding bus frames to it., Drop a socket from every query_id on disconnect., Send one event dict to all subscribers of query_id. Best-effort: a failed, WSManager, Config, get_settings() (+19 more)

### Community 2 - "Permission Gate Package"
Cohesion: 0.06
Nodes (28): GatedResult, Serialize to the EXACT frozen response-item payload (api-websocket.md)., Boundary-safe output of the gate for ONE chunk (permission-gate.md §2.1).      I, Visibility / Decision Enums + Gate Mapping, Exception, Flag, allows(), Capability (+20 more)

### Community 3 - "Boundary Pipeline & Claude Helpers"
Cohesion: 0.08
Nodes (34): H8 drop-in search swap, respond() gate seam, Retrieve-first, gate-second, cached_system_block, complete_text, get_client (AsyncAnthropic singleton), parse (structured output), Fail-Closed Principle (+26 more)

### Community 4 - "API Endpoints & Frozen Contracts"
Cohesion: 0.09
Nodes (29): done WS Event, POST /grant_access Endpoint, POST /query Endpoint, Verification Claude call: grounding check (provenance-verification.md §2.3).  Re, Ask Claude whether `answer` is supported by `source_text`.      Uses structured, verify_answer(), Frozen Contract 3: HTTP + WebSocket API, Frozen Contract 1: Data Model (+21 more)

### Community 5 - "Shared Data Models"
Cohesion: 0.08
Nodes (26): Agent, Chunk, CrossAgentRequest, GateDecision, GrantAccessRequest, GrantAccessResponse, ProvenancePointer, Shared record shapes — the single source of truth for the whole backend.  Respon (+18 more)

### Community 6 - "Agent Isolation & Runtime"
Cohesion: 0.11
Nodes (21): Agent Isolation Invariant (owner == agent_id), RuntimeAgent.respond, RuntimeAgent, RuntimeAgent.search, assert_isolation, load_corpus_chunks, embed_query, embed_texts (+13 more)

### Community 7 - "Corpus Loading & Embeddings"
Cohesion: 0.1
Nodes (16): assert_isolation(), load_corpus_chunks(), Corpus load helpers + isolation assert (agents-corpus-index.md §2.3).  Responsib, Read app/data/corpora/<agent_id>.json into a list of Chunk dicts.      Asserts t, Raise if any chunk's `owner != agent_id` (spec §6 isolation guarantee)., embed_query(), embed_texts(), Embedding function + model id + dimension (agents-corpus-index.md §2.2).  Respon (+8 more)

### Community 8 - "Grant-Access & Wire Schemas"
Cohesion: 0.1
Nodes (20): WSManager.emit, WSManager.subscribe, Grant-Access-Live Hero Beat, submit_query (POST /query), ChunkNotFoundError, AgentIndex.set_visibility, Deterministic Leak-Guard, _passes_leak_guard (+12 more)

### Community 9 - "Router Fan-Out & Events"
Cohesion: 0.12
Nodes (19): agent-activated WS event, done WS event, WSManager (emit-by-query_id), agent_activated_event builder, POST /grant_access (toggle + replay), GrantAccessService (toggle + replay-trigger), Replay trigger (re-run on same query_id), AgentIndex.set_visibility (mutation) (+11 more)

### Community 10 - "Runtime Agent & Index"
Cohesion: 0.11
Nodes (12): RuntimeAgent: identity + own AgentIndex + the gate seam (agents-corpus-index.md, One party agent: identity + its own isolated index only., Retrieve over OWN index only. Delegates to search.search(query, self.id,, Seam for the GATE subsystem. retrieve-first, gate-second, IN this agent, RuntimeAgent, AgentIndex, load_agent_index(), AgentIndex: one agent's isolated flat index (agents-corpus-index.md §2.3, grant- (+4 more)

### Community 11 - "App.state Dependency Accessors"
Cohesion: 0.12
Nodes (15): get_grant_access_service(), get_orchestrator(), get_orchestrator_ws(), get_registry(), get_run_registry(), get_ws_manager(), get_ws_manager_ws(), Request-time app.state accessors (api-websocket.md §2.9).  Responsibility: thin (+7 more)

### Community 12 - "WS Event Builders & Tests"
Cohesion: 0.14
Nodes (11): agent-activated WS Event, response-item WS Event, Response Item Shape, agent_activated_event(), Pure WS event builders (router.md §2.3, api-websocket.md).  Responsibility: pure, Build the frozen `agent-activated` frame:     {type, query_id, agent_id, party_n, Build the frozen `response-item` frame: {type:"response-item", query_id, ...item, response_item_event() (+3 more)

### Community 13 - "Search (Stub + Cosine)"
Cohesion: 0.17
Nodes (11): _cosine_search(), _keyword_stub(), Frozen search() interface + keyword stub + real cosine (agents-corpus-index.md §, Inject the AgentRegistry at startup so search() resolves the per-agent index., FROZEN signature (search-interface.md). Single dispatch point.      Returns ALL, Deterministic keyword-overlap stub (search-interface.md stub algorithm):     tok, Real retrieval: embed query -> cosine vs agent.index.matrix (own index only), search() (+3 more)

### Community 14 - "API Wire Schemas"
Cohesion: 0.27
Nodes (12): AgentActivatedEvent, DoneEvent, GrantAccessRequest, GrantAccessResponse, ProvenanceEntry, QueryRequest, QueryResponse, Pydantic WIRE models — verbatim from the frozen contract (api-websocket.md §2.5, (+4 more)

### Community 15 - "Agent Registry"
Cohesion: 0.18
Nodes (6): AgentRegistry, Holds the 3 RuntimeAgents; the only place agent_id -> Agent resolution lives., Resolve an agent by id. Raises KeyError on unknown id (search() contract)., Every registered agent id, in stable order., Resolve party_name (for agent-activated / ResponseItem.source_party)., Resolve (owning agent, chunk) by globally-unique chunk_id (grant_access).

### Community 16 - "Grant-Access Service"
Cohesion: 0.2
Nodes (6): GrantAccessService, Owns the two new behaviors: mutate one chunk's visibility, and trigger a     rep, Flip one chunk's stored visibility (restricted -> public for the demo)., Validate the query_id, toggle the chunk, and build the ACK. The replay is, Re-invoke the orchestrator for the stored query on the SAME query_id,         st, Tests for app/grant_access/ (BUILD_INDEX.md §2 / step 30).  TODO: assert toggle_

### Community 17 - "Run Registry"
Cohesion: 0.18
Nodes (7): Per-query_id run context for grant-access replay (grant-access.md §2.3, OQ-8)., The original request behind one query_id (grant-access.md §2.3)., In-memory map query_id -> RunContext. Single source of truth for     'what was t, Store run context at query mint time (/query happy path)., Look up the original request for a query_id; None if unknown., RunContext, RunRegistry

### Community 18 - "Orchestrator"
Cohesion: 0.18
Nodes (6): Orchestrator, Orchestrator.run: plan -> fan out -> collect -> verify -> synthesize (orchestrat, Drives one query run end-to-end. Transport-agnostic via an injected sink., Plan -> fan out -> collect -> verify -> synthesize.          Resolve asker, allo, Schedule run() as a fire-and-forget asyncio task and return immediately, Tests for app/orchestrator/orchestrator.py (BUILD_INDEX.md §2 / step 20).  TODO:

### Community 19 - "Claude Client"
Cohesion: 0.2
Nodes (9): cached_system_block(), complete_text(), get_client(), parse(), Shared AsyncAnthropic client + model ids + helpers (redaction.md §2.1, provenanc, Process-wide AsyncAnthropic singleton. Reads ANTHROPIC_API_KEY from env., Return a system block with an ephemeral cache breakpoint, so a byte-stable     s, One-shot text completion. Returns the first text block, or None on refusal. (+1 more)

### Community 20 - "Provenance Assembly"
Cohesion: 0.2
Nodes (7): build_response_item(), build_response_item: gate verdict + chunk -> ResponseItem (provenance-verificati, Turn one gated chunk into the canonical Response item.      `decision` is the ga, assemble_provenance(), Provenance pointer assembly — no Claude (provenance-verification.md §2.2).  Resp, Build the provenance pointer from a gated chunk (data-model §2 dict).      Resol, Tests for app/provenance/ (BUILD_INDEX.md §2 / step 16).  TODO: assert assemble_

### Community 21 - "Redaction Claude Call"
Cohesion: 0.22
Nodes (8): _passes_leak_guard(), Redaction Claude call: restricted text -> safe one-line gist (redaction.md §2.2), Return a safe one-line gist for a RESTRICTED chunk. Never returns chunk text., Deterministic content-free gist from owner-published doc_title only., Cheap deterministic backstop: reject if the gist shares a >=6-word verbatim, redact(), _safe_fallback(), Tests for app/claude/redaction.py (BUILD_INDEX.md §2 / step 13).  TODO: against

### Community 22 - "Grant-Access Errors"
Cohesion: 0.22
Nodes (8): ChunkNotFoundError, Raised by set_visibility when chunk_id is unknown (-> 404 upstream)., GrantResult, GrantAccessService: toggle + replay (grant-access.md §2.1).  Responsibility: the, Internal result of grant_and_rerun, shaped into GrantAccessResponse by the route, Raised when query_id has no stored RunContext (-> 404)., UnknownQueryError, KeyError

### Community 23 - "Claude Prompt Templates"
Cohesion: 0.25
Nodes (7): Frozen, byte-stable system/user prompt templates (cache-friendly).  Responsibili, Build the per-call redaction user message. SKELETON — no logic., Build the per-call verification user message (delimited tags). SKELETON., Build the per-call synthesis user message. Must contain NO restricted     payloa, redaction_user(), synthesis_user(), verification_user()

### Community 24 - "Registry Builder"
Cohesion: 0.5
Nodes (3): build_registry(), AgentRegistry: the single agent_id -> Agent resolution point (agents-corpus-inde, Build 3 isolated RuntimeAgents from AGENT_DEFS + seed files. Called once at

### Community 25 - "Query ID Minting"
Cohesion: 0.5
Nodes (3): new_query_id(), query_id minting (api-websocket.md §2.4, BUILD_INDEX.md §2 core/ids.py).  Respon, Return a fresh opaque query id, e.g. "q_" + short hex.

### Community 26 - "Synthesis Claude Call"
Cohesion: 0.5
Nodes (3): Synthesis Claude call: final cited answer (orchestrator.md §3.1, BUILD_INDEX §2., Compose the final cited answer from verified full items (SYNTH_MODEL,     max_to, synthesize()

### Community 27 - "WebSocket Endpoint"
Cohesion: 0.5
Nodes (3): /ws/query WebSocket endpoint (api-websocket.md §2.8).  Responsibility: support B, Accept the socket, then loop on frames: `type:query` mints a run + acks +     st, ws_query()

### Community 28 - "POST /query Handler"
Cohesion: 0.5
Nodes (3): POST /query handler (api-websocket.md §2.7).  Responsibility: resolve the asker, Mint a query_id, record run state, kick the fan-out, return immediately.     SKE, submit_query()

### Community 29 - "Responder Boundary Pipeline"
Cohesion: 0.5
Nodes (3): respond_for_agent: the boundary pipeline inside the responding agent (router.md,, Run the boundary pipeline for one agent and return already-gated items.      sea, respond_for_agent()

## Knowledge Gaps
- **207 isolated node(s):** `Request-time app.state accessors (api-websocket.md §2.9).  Responsibility: thin`, `Return the AgentRegistry from request.app.state.`, `Return the Orchestrator from request.app.state.`, `Return the WSManager from request.app.state.`, `Return the RunRegistry from request.app.state.` (+202 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Relay Build Spec v2` connect `API Endpoints & Frozen Contracts` to `Corpus Loading & Embeddings`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Why does `Frozen Contract 1: Data Model` connect `API Endpoints & Frozen Contracts` to `Permission Gate Package`, `WS Event Builders & Tests`, `Shared Data Models`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `Chunk` connect `Shared Data Models` to `Runtime Agent & Index`, `Grant-Access Errors`, `Agent Registry`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `AgentRegistry` (e.g. with `GrantResult` and `UnknownQueryError`) actually correct?**
  _`AgentRegistry` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `Orchestrator` (e.g. with `GrantResult` and `UnknownQueryError`) actually correct?**
  _`Orchestrator` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `lifespan()` (e.g. with `get_settings()` and `build_registry()`) actually correct?**
  _`lifespan()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `GrantAccessService` (e.g. with `AgentRegistry` and `Orchestrator`) actually correct?**
  _`GrantAccessService` has 4 INFERRED edges - model-reasoned connections that need verification._