# Beacon — Final Technical Specification

> **Status:** near-final. This is the authoritative technical spec for Beacon as built. It
> supersedes the running notes in `CHECKPOINT.md` for anything technical. Where the two disagree,
> trust this document. Last substantive change: MCP federation (Phase 5) + the Relay→Beacon rename.

---

## 0. What Beacon is (in one paragraph)

**Beacon is a permissioned knowledge-brokering network.** An *asking* agent poses a natural-language
question; Beacon fans it out to multiple independent *parties*, each of which searches **only its
own** private knowledge and decides — at its own boundary — what may cross: the full answer, a
redacted "this exists but is locked" stub, or nothing. Each crossing answer is **verified against
its own source**, and the asker **synthesizes** one cited answer from what came back. The
differentiator is not retrieval — it's the **gate**: permissioning, structural non-leakage, and
verified provenance enforced *inside each party* before any content leaves it. A restricted item
surfaces as **"request access"**, and granting it live re-streams just that one answer.

The corpora are seeded from real exported account data for the demo; the **gate + verified
provenance is the engineered product.**

---

## 1. Table of contents

1. Core concepts & invariants
2. System architecture (the layers)
3. Data model (the canonical record shapes)
4. Retrieval engine
5. The gate — the wedge (visibility, capability, redaction, verification)
6. The spine — router, orchestrator, events
7. Synthesis
8. Grant-access (the hero beat)
9. MCP federation (Phase 5) — inbound & outbound
10. Frontend
11. API surface (HTTP + WebSocket)
12. Configuration & models
13. Running it / deployment topology
14. The demo scenario
15. Testing
16. Repository map
17. Security & data handling
18. Build history (phases)
19. Known limitations & future work

---

## 2. Core concepts & invariants

- **Party (agent).** One independent knowledge holder with its **own isolated index**. Three exist:
  `agent_northwind` (Northwind Robotics), `agent_helios` (Helios Dynamics), `agent_quanta`
  (Quanta Systems). The asker is `agent_you` — the "You" node, **not** a party, so it is excluded
  from the fan-out and all three parties respond.
- **Isolation invariant.** Each party's `AgentIndex` holds *only* chunks it owns (asserted at
  construction: every row's `owner == agent_id`). No party can read another's chunks or matrix.
- **Visibility tiers** (per chunk, the data's own label): `public`, `restricted`, `private`.
- **Decision** (what the gate emits, per chunk): `full`, `redacted`, `denied`.
- **Retrieve-first, gate-second.** `search()` returns **all** tiers, ungated, ranked. Gating
  happens *after* retrieval, inside the owning party. Retrieval never filters by visibility.
- **Structural no-leak invariant.** The gate's output object (`GatedResult`) is `frozen` and has
  **no field that can carry raw restricted text**. For `redacted`/`denied` there is no `text` to
  leak because the type literally cannot hold it. This is enforced by *shape*, not by discipline.
- **Fail-closed.** Verification defaults to `verified=False` on any error, refusal, or parse
  failure. An unverifiable answer is never presented as verified.
- **The gate runs inside the responder.** All policy + the redaction/verification Claude calls
  happen on the owning party's side, before any item is handed back — including across the MCP
  boundary (the party server runs the same pipeline in its own process).

---

## 3. System architecture (the layers)

```
                         ┌──────────────────────────────────────────────┐
   Browser UI  ◄── WS ──►│  FastAPI app (uvicorn :8000)                  │
   (React/Vite :5173)    │                                              │
                         │   API layer: /ws/query, /query, /grant_access│
                         │              /health, /agents, /demo/reset   │
                         │   ───────────────────────────────────────    │
                         │   Orchestrator  ── drives one run end-to-end  │
                         │      │  fan-out + synthesize + one `done`     │
                         │      ▼                                        │
                         │   Router  ── event clock + concurrent fan-out │
                         │      │  injected ResponderFn(agent_id, query) │
                         │      ▼                                        │
                         │   Responder (per party) ── THE WEDGE:         │
                         │      search → gate → redact → verify          │
                         │      ▼                                        │
                         │   Registry (3 isolated AgentIndex objects)    │
                         │   EventBus ──► WSManager ──► sockets          │
                         └──────────────────────────────────────────────┘
                                    │ (one party optionally federated)
                                    ▼  MCP (streamable-HTTP :9100)
                         ┌──────────────────────────────────────────────┐
                         │  Helios party MCP server (own process)        │
                         │  same search→gate→redact→verify, own corpus   │
                         └──────────────────────────────────────────────┘

   Outbound:  Claude Desktop / Claude Code  ──MCP──►  Beacon outbound server (:9200 / stdio)
              one `query(question)` tool → runs the SAME orchestrator → gated, cited answer
```

The seam that makes all of this composable is a single injected function:

```python
ResponderFn = Callable[[str, str], Awaitable[list[ResponseItem]]]   # (agent_id, query) -> gated items
```

The Router calls one `ResponderFn`. In-process that's `respond_for_agent`. Federated, it's a
**dispatcher** that routes some parties to an MCP responder and the rest to local — and nothing
upstream (orchestrator, synthesis, events, UI) changes.

---

## 4. Data model (`app/models.py` — the single source of truth)

All record shapes live in one flat module so they cannot drift across subsystems.

### Chunk (one row in a party's index)
```python
class Chunk(TypedDict):
    chunk_id: str            # globally unique
    parent_doc_id: str
    doc_title: str
    owner: str               # an agent_id; == the searched party
    visibility: Visibility   # "public" | "restricted" | "private"
    text: str
    embedding: NotRequired[list[float]]   # server-side ONLY — never crosses the boundary
    score: NotRequired[float]             # result-only, added by search(), 0.0–1.0
```
**Boundary rule:** `embedding` is the only field that never serializes past the gate; `score` is
result-only. Outbound wire shapes omit both.

### ResponseItem (one party's gated answer for one chunk — the wire shape)
```python
class ResponseItem(TypedDict):
    answer: Optional[str]            # full: the answer | redacted: gist | denied: None
    source_party: str                # party_name of the owner
    source_doc_title: Optional[str]  # provenance; None for fully-hidden denied
    decision: Decision               # "full" | "redacted" | "denied"
    verified: bool                   # full+verified only; else False
    chunk_id: str                    # grant_access handle
    source_agent_id: str             # owning agent_id
    transport: NotRequired[Literal["mcp","fallback","local"]]   # federation badge (Phase 5)
```
This is the **7-key contract** (+ the additive `transport` tag). The router/orchestrator/UI all
consume exactly these keys.

### GatedResult (boundary-safe output of the gate — `@dataclass(frozen=True)`)
Carries `decision`, `answer`, `source_party`, `source_doc_title`, `verified`, `chunk_id`,
`source_agent_id`, `access_requestable` (internal-only, True only for redacted). **It has no raw
`text` field** — the no-leak invariant is structural. `to_wire()` serializes exactly the 7 wire
keys (drops `access_requestable`).

### Other shapes
- `Visibility = Literal["public","restricted","private"]`, `Decision = Literal["full","redacted","denied"]`.
- `GateDecision(Enum)` — `FULL/REDACTED/DENIED`, values match `Decision` verbatim.
- `Capability(Flag)` — `PUBLIC_READ`, `RESTRICTED_REQUEST`, `PRIVATE_READ`; `CapabilityGrant`.
- `ProvenancePointer`, `VerifyResult(verified, reason)`.
- `GrantAccessRequest(chunk_id, query_id)`, `GrantAccessResponse(chunk_id, new_visibility, query_id, rerunning)`.
- `RunContext(query_id, query, from_agent)` — what's needed to replay a run.

---

## 5. Retrieval engine (`app/retrieval/search.py`, `app/agents/`)

### Frozen interface
```python
def search(query: str, agent_id: str, top_k: int = 5) -> list[Chunk]:
    # Returns ALL visibility tiers, UNGATED, descending score, <= top_k, [] on no hit.
    # Raises KeyError on unknown agent_id. NEVER gates/filters by visibility.
```
Single dispatch point selected by `BEACON_SEARCH`: `stub` (keyword overlap), `cosine`
(pure dense), or **`hybrid`** (the production engine).

### Hybrid = BM25 (lexical) + dense (static embeddings), fused with RRF
- **Lexical:** `rank_bm25.BM25Okapi` over each party's own chunks (tokenized text + title, with term
  frequencies). Per-agent, lazily built and cached.
- **Dense:** `model2vec` static embeddings (model `minishlab/potion-retrieval-32M`, ~512-dim,
  **CPU-only, no GPU, no torch**). Query embedded once; cosine vs the party's matrix.
- **Fusion:** Reciprocal Rank Fusion, `RRF_K = 60`, scores max-normalized to (0, 1].
- **Relevance floor** (`BEACON_MIN_SIM`, demo = 0.35): drop any result whose absolute dense cosine
  is below the floor. This is what produces clean **no-hit** (off-topic → `[]`) and **single-hit**
  (only the relevant party surfaces) behaviors.

### Measured numbers (real corpora, re-ingested at volume)
- **~4,335 chunks** total (Northwind 1,240 · Helios 1,519 · Quanta 1,576), each party isolated.
- Latency per search: cosine ~4 ms · **hybrid ~10–18 ms** · keyword stub ~112 ms (all CPU).
- Accuracy (self-retrieval): hybrid **recall@5 ≈ 97%**, recall@1 ≈ 85%, MRR ≈ 0.90.
- Embeddings are a one-time **~4 s** offline step, cached to `embeddings.npz`; startup loads the
  cache + pre-warms BM25 so the first live query is snappy.

---

## 6. The gate — the wedge (`app/gate/`, `app/claude/`)

For each retrieved chunk, the responder runs the gate. **Two independent gates must both say yes**
for content to cross:

1. **Visibility policy** — the chunk's tier vs the party's scope policy (`three_tier`).
2. **Capability** — an unforgeable in-process `CapabilityGrant` issued by the responder for the
   asker. MVP issuer grants `PUBLIC_READ | RESTRICTED_REQUEST`, **never `PRIVATE_READ`**. The asker
   cannot widen its own scope.

Mapping (after both gates):
- `public` + PUBLIC_READ → **full** (answer = the public payload, then verified).
- `restricted` + RESTRICTED_REQUEST → **redacted** (answer = a safe *gist*, `access_requestable=True`).
- `private` (or any tier the capability disallows) → **denied** (answer = None, title hidden).

### Redaction (`app/claude/redaction.py`)
- For restricted chunks, Claude (`REDACT_MODEL` = `claude-opus-4-8`, `max_tokens≈80`) produces a
  short existence-only **gist** — never the raw secret.
- A **leak-guard** checks the gist doesn't echo distinctive source tokens; on refusal/error/leak →
  a deterministic safe fallback. The gist is what's allowed to cross; the raw text never is.

### Verification (`app/claude/verification.py`)
- For **full** items only, Claude (`VERIFY_MODEL` = `claude-haiku-4-5`) checks the answer is grounded
  in its source chunk, via **forced tool-use** (a structured `{verified: bool}` tool call).
- **Fail-closed:** any API error / refusal / parse failure → `verified=False`. Redacted/denied never
  verify (their `verified` stays False).

### Concurrency
`respond_for_agent` fans the per-chunk gate work out with `asyncio.gather`, so the redaction and
verification Claude calls for a party run **in parallel**, not serially behind the spinner.

---

## 7. The spine — router, orchestrator, events

### Router (`app/router/router.py`)
- Resolves the target party set (asker excluded; optionally narrowed to `only_agents` for targeted
  replay).
- **Phase 1:** emits `agent-activated` for *all* targets *before* awaiting any responder, so the
  graph lights up at once.
- **Phase 2:** runs responders concurrently; emits one `response-item` per resolved item.
- Returns the flat item list. Holds the injected `ResponderFn` — the single swap point for MCP.

### Orchestrator (`app/orchestrator/orchestrator.py`)
- Drives one run end-to-end: fan-out (or targeted replay) → collect → synthesize → emit exactly one
  `done`. **Transport-agnostic** via an injected `emit` sink.
- Never sees raw restricted/private text — only already-gated, already-verified items.
- Builds provenance as `[verified-full …, redacted …]` so synthesis's `[n]` citations line up 1:1
  with `done.provenance`.
- Streams synthesis: emits `synthesizing`, then `answer-delta` per token, then `done`.
- `run_guarded` wraps `run` so any mid-stream error still emits a terminal `done` — the client (and
  the hero beat) never hangs on a silent spinner.

### Event path (`app/events/bus.py`, `app/api/events.py`)
- **EventBus:** tiny in-process async pub/sub keyed by `query_id`, with a bounded per-`query_id`
  history. `emit` is non-blocking per subscriber (`put_nowait`, drop-never-block). History replay
  means a socket that subscribes a beat late still gets earlier frames, and a grant-access replay
  streams onto the still-open socket with no special handling.
- **WSManager:** subscribes per `query_id` and pumps frames to sockets.

### WS event sequence for one query
```
ack → agent-activated (×N parties) → response-item (×M items) → synthesizing → answer-delta (×T) → done
```

---

## 8. Synthesis (`app/claude/synthesis.py`)

- Composes the final cited answer from verified-full items, with redacted items surfaced as
  **existence-only** ("request access"). `SYNTH_MODEL` = `claude-opus-4-8`, **`max_tokens = 512`**.
- Streams when given an `on_delta` callback (the live path); single-shot otherwise (tests).
- Empty input → a graceful guard string ("No party returned a verified answer…"); refusal/error → a
  deterministic fallback. The answer carries `[n]` citations aligned to `done.provenance`.

---

## 9. Grant-access — the hero beat (`app/grant_access/`)

The money moment. **Local and bulletproof by design — it never crosses MCP.**

1. `POST /grant_access {chunk_id, query_id}` → validate the `query_id` has a stored `RunContext`
   (else 404) → **toggle the chunk's visibility in the live in-memory index** via
   `AgentIndex.set_visibility(chunk_id, "public")` (resolves the owning party from the globally
   unique `chunk_id`, mutates only that row — isolation preserved). ACK immediately.
2. Background **targeted replay**: the orchestrator re-runs the *stored* query on the *same*
   `query_id`, but re-dispatches **only the granted chunk's party** (`changed_chunk_id`); every
   other party's items are reused from the per-`query_id` cache in `RunRegistry`. The answer is
   re-synthesized.
3. Net effect on the UI: that **one card flips redacted 🔒 → full ✓** and the answer updates — only
   that card re-streams. Near-instant; no full re-run, no dead spinner.

**Reset between demo takes:** `POST /demo/reset` re-applies the locked demo tiers to the live index
(re-arming the granted chunk to restricted) without a server restart. A fresh `run.sh` is the
can't-fail hard reset.

**Why it stays local:** routing the flip over MCP would put the single most important demo beat on
the network and forfeit the local fallback. The grant is the party's own decision; in production it
would be an out-of-band request (an email / in-platform approval), not a synchronous tool call.

---

## 10. MCP federation (Phase 5)

Beacon speaks MCP in **two directions**, both additive and feature-flagged. Inbound proves "a party
is its own independent service"; outbound makes Beacon queryable from any MCP client.

### 10.1 Inbound — one party served over a real MCP server
- **`backend/scripts/mcp_party.py`** — a standalone process (`python -m scripts.mcp_party
  --agent-id agent_helios --port 9100`). Builds a **single-party** registry (Helios's corpus only),
  wires search + responder against it, and exposes one tool `respond(query) -> JSON list[ResponseItem]`
  over **streamable-HTTP** (`/mcp`). The full retrieve→gate→redact→verify runs **inside this
  process**; only gated items cross. **Faithfulness:** a test proves no raw restricted `text` ever
  appears in the served JSON (the doc *title* is provenance and legitimately crosses).
- **`backend/app/mcp/client.py`** — the backend's MCP client:
  - `connect_mcp(stack, url)` — opens an initialized streamable-HTTP `ClientSession`, kept alive by
    an `AsyncExitStack` (closed on lifespan shutdown).
  - `make_mcp_responder(session, agent_id)` — a `ResponderFn` that calls the party's `respond` tool,
    **wrapped in `asyncio.wait_for(…, BEACON_MCP_TIMEOUT≈8s)`** so a *hang* (server alive but
    stalled) falls back fast, and `_coerce_items` keeps only the 7 wire keys (a second structural
    no-leak guard at the client edge).
  - `make_dispatch_responder(local, mcp_map)` — routes each party to its MCP responder if configured,
    else local; **any MCP error/timeout falls back to `local(agent_id, query)`**. Tags every item's
    `transport`: `"mcp"` (success), `"fallback"` (MCP failed → local), `"local"` (never MCP).
- **Wiring** (`app/main.py` lifespan): if `BEACON_MCP_AGENTS` + `BEACON_MCP_URL` are set (and
  `BEACON_MCP != off`), connect and pass the **dispatcher** as the Router's responder; on connect
  failure, keep the in-process responder (all-local). `BEACON_MCP=off` forces all-local.
- **Visibility of the beat:** `GET /agents` returns a static `transport: "mcp"|"local"` per party
  (the config-level badge), and each `response-item` carries the *live* `transport` (which flips to
  `"fallback"` if you kill the MCP server mid-run). The demo is visually identical to all-local until
  you look at the badge.

### 10.2 Outbound — Beacon itself as an MCP server
- **`backend/scripts/mcp_beacon_server.py`** — a standalone, **query-only** server. One tool,
  `query(question) -> str`, runs the **existing** orchestrator fan-out (reuses it verbatim — no
  pipeline rebuild) and returns the synthesized cited answer + the per-party gated summary
  (full ✓ / redacted 🔒 / denied ⛔) as markdown. Restricted items show as **exists-but-locked, no
  content**, so the permissioning is visible even in plain text.
  - Reuse mechanics: a throwaway `EventBus` (the Router requires one) + an `emit` that captures the
    `done` event; per-party items read from `RunRegistry.get_items()`.
  - Transports: **stdio** (default; Claude Desktop spawns it) or **streamable-HTTP** (`--transport
    http --port 9200`, started by `run.sh` for terminal/URL clients). stdout is the stdio protocol
    channel — all logging is on stderr and heavy init is `redirect_stdout`-guarded.
  - **Opt-in gating:** the tool is described so a consuming assistant only calls it when the user's
    message starts with the `/beacon` flag; the flag is also stripped server-side. A `/beacon` MCP
    **prompt** surfaces the flag as a slash command. A **presentation directive** is prepended to
    every result (and reinforced in the tool description) so assistants keep the gating visible
    rather than paraphrasing it away — *instruction-level, not a hard lock*.
- **`backend/scripts/beacon_ask.py`** — a tiny terminal client for the HTTP instance, used by the
  Claude Code `/beacon` slash command.
- **No grant tool.** Outbound is query-only; granting access stays in the UI, local.

### 10.3 Consumer setup (captured in `integrations/`)
- **Claude Desktop:** stdio entry in `~/.config/Claude/claude_desktop_config.json`. Must use a
  `bash -c "cd <backend> && exec python -m scripts.mcp_beacon_server"` wrapper — Claude Desktop does
  **not** honor the config's `cwd`, so a plain `-m` invocation dies with `No module named 'scripts'`.
  Requires a full app restart to load. (Template + the cwd gotcha documented in `integrations/`.)
- **Claude Code:** `~/.claude/commands/beacon.md` — a `/beacon <question>` slash command that runs
  `beacon_ask.py` and renders the cold output verbatim, then a short "My read:".

---

## 11. Frontend (`frontend/`, React + Vite)

- **`src/useBeaconQuery.js`** — the live data layer (the one consumer of the WebSocket). Opens
  `ws://…/ws/query`, sends `{type:"query", query}`, and reduces the frame stream to a stable shape:
  `{phase, agents, cards, answer, provenance, submit, requestAccess, reset}`. `phase` includes
  `synthesizing`; `answer-delta` frames accumulate into a streaming `answer`.
- **Components:** `AskTheNetwork.jsx` (the shell + prompt + agents panel), `NetworkConstellation.jsx`
  (the SVG node graph; lights up on `agent-activated`, carries the per-node transport chip),
  `LiveQueryDebug.jsx` (the **walking skeleton** at `/?debug` — a raw event-stream client, the
  guaranteed-working fallback).
- The UI is driven entirely by the live WS; nodes pulse, cards arrive per party, the answer streams,
  and clicking **Request access** on a redacted card triggers the targeted re-stream.

---

## 12. API surface

### WebSocket — `/ws/query` (one endpoint, two transport options)
- `{type:"query", query, from_agent?}` → mint a run, send `ack {query_id, from_agent, agents}`,
  subscribe this socket, start the orchestrator. Events then stream on this socket. The handler
  stays in its receive loop so a later grant-access replay re-streams here.
- `{type:"subscribe", query_id}` → bind this socket to an existing run (the POST+WS path); the bus
  replays any frames already emitted.

### HTTP
- `POST /query` — mint a run (POST+WS transport; subscribe over the WS for frames).
- `POST /grant_access {chunk_id, query_id}` → `{chunk_id, new_visibility, query_id, rerunning}`;
  schedules the targeted replay. `ChunkNotFoundError`/`UnknownQueryError` → 404.
- `GET /health` → `{status:"ok"}` (readiness probe).
- `GET /agents` → `[{id, party_name, transport}]` — real party names + the federation badge.
- `POST /demo/reset` → re-applies the locked demo tiers to the live index (re-arm between takes).

### WS frames (canonical shapes)
- `ack {type, query_id, from_agent, agents[]}`
- `agent-activated {type, query_id, agent_id, party_name, status:"searching"}`
- `response-item {type, query_id, …ResponseItem}` (the 7 keys + optional `transport`)
- `synthesizing {type, query_id}`
- `answer-delta {type, query_id, delta}`
- `done {type, query_id, synthesized_answer, provenance[], item_count}`

---

## 13. Configuration & models

### Environment variables (`BEACON_` prefix; read at import time → set in `run.sh`)
| Var | Demo value | Meaning |
|---|---|---|
| `BEACON_SEARCH` | `hybrid` | retrieval backend: `stub` / `cosine` / `hybrid` |
| `BEACON_TOP_K` | `2` | results per party (clean cards) |
| `BEACON_MIN_SIM` | `0.35` | relevance floor (off-topic → no-hit; one-party → single-hit) |
| `BEACON_DEFAULT_ASKER` | `agent_you` | the asker; excluded from fan-out → all 3 respond |
| `BEACON_MCP` | `on` | `off` forces all-local (no inbound federation) |
| `BEACON_MCP_AGENTS` / `BEACON_MCP_URL` | `agent_helios` / `…:9100/mcp` | inbound federation target |
| `BEACON_MCP_TIMEOUT` | `8.0` | MCP call timeout (hang → fast fallback) |
| `BEACON_OUTBOUND` / `BEACON_OUTBOUND_PORT` | `on` / `9200` | outbound MCP server |
| `ANTHROPIC_API_KEY` | (in `backend/.env`, git-ignored) | Claude calls |

### Models (`app/claude/client.py`)
| Role | Model | Notes |
|---|---|---|
| Redaction | `claude-opus-4-8` | restricted → safe gist, `max_tokens≈80`, leak-guarded |
| Verification | `claude-haiku-4-5` | full grounding check, forced tool-use, fail-closed |
| Synthesis | `claude-opus-4-8` | streamed, `max_tokens=512`, cited |

No `thinking` and no sampling params on these calls (Opus 4.8 rejects sampling params; the tasks are
structured/short). SDK: `anthropic` (forced tool-use + `messages.stream`).

---

## 14. Running it / deployment topology

```bash
cd backend && ./scripts/run.sh        # Ctrl-C stops everything
```
Starts four processes:

| service | port | role |
|---|---|---|
| frontend (Vite) | 5173 | the visual demo (`/?debug` = walking skeleton) |
| backend (uvicorn) | 8000 | main app; Helios federated over MCP, others local |
| Helios party MCP server | 9100 | inbound federation (streamable-HTTP `/mcp`) |
| Beacon outbound MCP server | 9200 | outbound `query` tool (streamable-HTTP `/mcp`) |

Escape hatches: `BEACON_MCP=off` (all-local parties), `BEACON_OUTBOUND=off` (no outbound server).

---

## 15. The demo scenario (`app/demo.py`, `scripts/demo_seed.py`)

The three real corpora are domain-disjoint, so a coherent cross-party "money" query is **planted**
(synthetic, sanctioned for the demo). `demo.py` is the single source of truth; `demo_seed.py` writes
the planted chunks into the (git-ignored) corpora + embeds them; `POST /demo/reset` re-applies tiers
live. Every planted chunk overlaps the query's distinctive tokens so it ranks top-2 under hybrid.

**The hero query** (surfaces all three decisions — the right demo/test prompt):
> We're seeing 429s on checkout — who changed the rate limit on the payments path, and what is it now?
- **Northwind** → `billing-svc/RetryPolicy.md` **full ✓** (gateway lowered to 60 req/min, reverts
  16:00) + `payments/incident-runbook.md` **denied ⛔**.
- **Helios** → `observability/checkout-429-dashboard.md` **full ✓**.
- **Quanta** → `auth-core/throttle.yaml` **redacted 🔒** (30 req/min, security-scoped) +
  `auth-core/README.md` **full ✓**.
- **Hero:** click **Request access** on the throttle card → targeted re-stream → that one card flips
  redacted → full ✓ and the answer updates.

Two more behaviors from the relevance floor: a **single-hit** query (only one party answers) and a
**no-hit** query (nodes pulse, no cards, "No party returned a verified answer." — no hallucination).

---

## 16. Testing

- **93 tests** pass (`python -m pytest -q -m "not live"`), plus a `live` smoke set.
- Coverage spans: frozen search interface + isolation, the gate (visibility/capability/leakage),
  redaction + verification (mocked Claude via `conftest.patch_claude`), router + orchestrator (done
  shape, targeted replay, never-hang, streaming deltas), the API (meta + grant-access), the MCP
  federation (faithfulness — no raw restricted text crosses; dispatcher routing + fallback + timeout;
  shape parity; transport tagging), and the outbound server (`_format` rendering + flag stripping +
  a mocked `query` run).
- Live verification done: full stack via `run.sh`; inbound Helios round-trip (server log shows the
  `respond` tool call, item arrives `transport="mcp"`); outbound stdio + HTTP round-trips returning
  the gated answer.

---

## 17. Repository map

```
backend/
  app/
    models.py                # canonical record shapes (the one source of truth)
    config.py                # Settings + .env loader (stdlib, no pydantic-settings)
    main.py                  # FastAPI app + lifespan wiring (incl. MCP dispatcher)
    agents/                  # AgentIndex, AgentRegistry, embeddings, corpus loading
    retrieval/search.py      # frozen search() — stub / cosine / hybrid + relevance floor
    gate/                    # visibility policy + capability grants
    claude/                  # client, redaction, verification, synthesis (the boundary Claude calls)
    router/                  # Router (fan-out + event clock) + responder (the wedge) + events
    orchestrator/            # Orchestrator (coordinate + synthesize + done + targeted replay)
    events/bus.py            # EventBus
    api/                     # ws.py, http.py, events.py (WSManager), meta.py, schemas.py
    grant_access/            # service (toggle + replay) + routes
    run_registry.py          # per-query RunContext + item cache (targeted-replay)
    mcp/client.py            # MCP client + dispatcher (inbound federation)
    demo.py                  # the planted demo scenario (single source of truth)
  scripts/
    run.sh                   # one-command launcher (4 processes)
    mcp_party.py             # inbound: serve one party over MCP
    mcp_beacon_server.py     # outbound: Beacon-as-MCP-server (the query tool)
    beacon_ask.py            # terminal client for the outbound server
    ingest.py, demo_seed.py  # corpus ingest + demo planting (git-ignored outputs)
  tests/                     # 93 unit tests + live smokes
  docs/                      # per-subsystem design docs
frontend/                    # React/Vite UI (useBeaconQuery + components)
shared/contracts/            # the frozen cross-cutting contracts (data-model, api, search)
integrations/                # Claude Desktop config + Claude Code /beacon command (reference copies)
DEMO.md, HANDOFF.md, CHECKPOINT.md, TECHNICAL_SPEC.md   # runbook / handoff / state / this spec
```

---

## 18. Security & data handling

- **Real private data is git-ignored and never committed:** `data/raw/`, `backend/app/data/corpora/*.json`,
  `**/embeddings.npz`, `backend/.env`. Regenerate corpora with `scripts/ingest.py`/`demo_seed.py`.
- **The no-leak invariant is structural** (`GatedResult` carries no raw text for non-full items) and
  re-guarded at the MCP client edge (`_coerce_items` keeps only the 7 wire keys). A faithfulness test
  proves no raw restricted text crosses the MCP boundary.
- **Outbound MCP is query-only** — no grant/visibility mutation tool is exposed.
- **API key:** lives only in `backend/.env` (git-ignored). The current key is flagged for rotation.
- Commit messages are kept nameless; a pre-commit secret-scan pattern lives in `scripts/ingest.py`.

---

## 19. Build history (phases)

| Phase | What landed |
|---|---|
| 1 | Registry + isolated indices + the frozen `search()` interface + the record shapes. |
| 1.5 | Hybrid retrieval (BM25 + model2vec dense + RRF) + the relevance floor; scaled to ~4.3k chunks. |
| 2 | The gate (visibility + capability), structural no-leak, redaction (Opus + leak-guard), verification (Haiku, forced tool-use, fail-closed). |
| 3 | The spine: Router + Orchestrator + EventBus/WSManager + grant-access (toggle + targeted replay). |
| 4 | "Make the demo real": live UI data layer (`useBeaconQuery`) + walking skeleton, token-streamed synthesis, the planted scenario + no-hit/single-hit, dev tooling (`run.sh`, `/demo/reset`). |
| 5 | MCP federation — inbound (Helios party server + client dispatcher + transport badge + timeout/fallback) and outbound (Beacon-as-MCP-server, the `query` tool + `/beacon` gating + Claude Desktop/Code integrations). Project renamed **Relay → Beacon**. |

---

## 20. Known limitations & future work

- **Planted demo scenario.** The cross-party "money" query is synthetic (the real corpora are
  domain-disjoint). Everything else runs on real data. A production deployment would rely on
  genuinely overlapping party corpora.
- **MCP presentation gating is instruction-level.** The outbound server can't *force* a consuming
  assistant (e.g. Claude Desktop) to render the gating verbatim — it strongly instructs it. The web
  UI is the guaranteed-visible surface.
- **Grant-access is in-memory + local.** Flips live index state in-process; not persisted, and
  deliberately never federated over MCP. Production = out-of-band approval (email / in-platform).
- **Single-client demo.** EventBus/WSManager and the persistent MCP session assume one client; fine
  for the demo, not yet hardened for concurrency.
- **Capability issuer is uniform.** Every asker currently gets `PUBLIC_READ | RESTRICTED_REQUEST`;
  per-asker/per-party policies are the obvious next step.
- **Inbound federation is one party (Helios).** The seam supports more, but the demo federates one to
  keep the grant-access party (Quanta) local and the hero beat bulletproof.
```
