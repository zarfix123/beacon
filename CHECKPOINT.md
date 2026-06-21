# Relay — Full Checkpoint

A single, detailed snapshot of the entire project: what it is, every phase, the architecture,
the UI, the demo, the data, the tooling, and what's left. (See also `DEMO.md` for the run
script + prompts, `HANDOFF.md` for frontend integration, `backend/BUILD_INDEX.md` for the
original build plan.)

---

## 1. What Relay is

**Relay is a permissioned knowledge-brokering network.** An asking agent ("You") fans a
question out to other party agents; each party's **gate** decides what may cross its boundary
(`full` / `redacted` / `denied`); full answers are **verified** against their source; and the
asker **synthesizes** one cited answer from what comes back. The product thesis — "the wedge" —
is **enforced permission at the owner's boundary + verified provenance**: sensitive content
never leaves a party except as the owner allows, and nothing is presented as trustworthy unless
it's grounded in a real source.

**Current state:** backend feature-complete and tested (78 mock + 4 live tests green); the
frontend is wired to the live backend (the redesigned UI renders from real WebSocket data); the
end-to-end demo runs — a 3-party fan-out over ~4,335 real documents, streaming answers, and the
grant-access "wall comes down" hero beat. Everything is on `main`.

The three parties (real exported Claude data, fictional names):
- **Northwind Robotics** = `agent_northwind` (Dennis's data — coding/infra)
- **Helios Dynamics** = `agent_helios` (Hao's data — security audits)
- **Quanta Systems** = `agent_quanta` (third account — admissions essays + CTF)
- **You** = `agent_you` (the asker; not a party, so all three respond)

---

## 2. The build, phase by phase

| phase | name | what it delivered |
|---|---|---|
| **1** | Retrieval foundation | ingestion → 3 isolated corpora; `AgentIndex`/`AgentRegistry`; the frozen `search()` seam (keyword stub) |
| **1.5** | Hybrid retrieval (Hao) | BM25 + static `model2vec` embeddings fused with RRF, behind the same seam (`RELAY_SEARCH=hybrid`) |
| **2** | The wedge | the gate (policy + capability), redaction + verification (Claude), provenance, the per-party responder |
| **3** | The spine | router fan-out + live WebSocket events + orchestrator + synthesis + grant-access replay |
| **4** | Make the demo real | planted demo scenario + tiering, relevance floor, the live UI data layer (`useRelayQuery`) + walking skeleton, dev tooling |
| **post-4** | Polish + scale + integration | **streamed** synthesis; corpus scaled to ~4,335; **3-party** fan-out; **Hao wired the redesigned UI** to the live backend |

---

## 3. Architecture — three layers + two boundary Claude calls

### Layer 1 — Retrieval foundation ("find the right text")
- **`app/agents/`** — each party is a `RuntimeAgent` owning an **isolated** `AgentIndex` (its own
  chunks + a `(n, 512)` embedding matrix). `__post_init__` asserts every chunk's `owner ==
  agent_id`, so cross-contamination crashes the boot. `AgentRegistry` is the single
  `agent_id → agent` resolver (`all_ids`, `party_name`, `find_chunk`).
- **`app/retrieval/search.py`** — the **frozen** `search(query, agent_id, top_k) → list[Chunk]`.
  Returns **all tiers, ungated** (gating is downstream). Three backends behind one dispatch:
  `stub` (keyword overlap), `cosine` (dense), `hybrid` (BM25 + dense + RRF). Plus the
  **relevance floor** (`RELAY_MIN_SIM`) that drops off-topic results → enables no-hit / single-hit.
- **`app/agents/embeddings.py`** — `model2vec` static embeddings (`minishlab/potion-retrieval-32M`,
  512-dim), numpy-only, **no GPU/torch**. `embeddings.npz` is the offline cache.

### Layer 2 — The wedge ("decide what's allowed to cross") — `app/gate/`, `app/claude/`, `app/provenance/`
- **Gate** (`gate/gate.py`): two independent checks — **policy** (`public→FULL`,
  `restricted→REDACTED`, `private→DENIED`, fail-closed on unknown) and **capability** (the asker's
  grant; down-ranks to DENIED if not entitled). Produces a frozen **`GatedResult`** that has **no
  `text`/`embedding` field** — leakage is structurally impossible, not filtered.
- **Redaction** (`claude/redaction.py`): turns a restricted chunk into one safe sentence inside the
  owner's boundary, with a deterministic **leak-guard** (reject ≥6-word verbatim runs / >240 chars)
  + content-free fallback. Model: `claude-opus-4-8`.
- **Verification** (`claude/verification.py`): "is this answer grounded in its source?" via **forced
  tool-use** (SDK 0.64.0 has no `messages.parse`), on **`claude-haiku-4-5`** for live-path latency,
  **fail-closed** (any error → `verified=False`).
- **Responder** (`router/responder.py`): per-chunk `gate.evaluate → build_response_item`, fanned out
  with `asyncio.gather` so the boundary Claude calls fire concurrently.

### Layer 3 — The spine ("ask everyone, stream it, answer once") — `app/router/`, `app/orchestrator/`, `app/events/`, `app/api/`
- **Router** (`router/router.py`): fans out to every party except the asker (`only_agents` narrows
  it for targeted replay); emits all `agent-activated` first (nodes pulse together), then one
  `response-item` per resolved item.
- **Orchestrator** (`orchestrator/orchestrator.py`): calls the router, splits verified-full /
  redacted, **streams** synthesis, emits exactly one `done`. `start_run`/`run_guarded` guarantee a
  terminal `done` even on error (never-hang). **Targeted replay**: grant-access re-runs only the
  flipped chunk's party, reuses cached items for the rest → near-instant, one-card flip.
- **Synthesis** (`claude/synthesis.py`): one cited answer over verified-full items (`[n]` citations
  aligned 1:1 with `done.provenance`); restricted items surfaced as "request access" without their
  content; empty-input guard; **streams token-by-token** (`stream_text` → `answer-delta` events).
  Model: `claude-opus-4-8`.
- **Event path** (`events/bus.py` + `api/events.py`): a pure `EventBus` (pub/sub keyed by
  `query_id`, with history replay so a late subscriber misses nothing) + a `WSManager` that bridges
  the bus to live WebSockets and prunes dead sockets.
- **API** (`app/api/`, `app/main.py`): `POST /query`, `WS /ws/query`, `POST /grant_access`,
  `GET /agents`, `GET /health`, `POST /demo/reset`. Lifespan wires registry → search → responder →
  bus → router → orchestrator → grant-access, and **pre-warms** BM25 + the model so the first live
  query is snappy.

### The live query, end to end
```
You ask → WS {type:query} → ack → agent-activated ×3 (nodes pulse)
  → each party: search (10–18ms) → gate → redact/verify (Claude, parallel) → response-item (card)
  → synthesizing → answer-delta… (answer streams in) → done (cited answer + provenance)
Click "Request access" on a redacted card → POST /grant_access → targeted replay
  → only that party re-streams → the one card flips redacted→full✓ → answer re-streams
```

---

## 4. Retrieval, in numbers (the "cool tech" beat)

- **~4,335 real documents** indexed (Northwind 1,240 · Helios 1,519 · Quanta 1,576), each party's
  index isolated.
- **Latency per search:** cosine ~4ms, **hybrid ~10–18ms**, keyword stub ~112ms — all numpy, **no GPU**.
- **Accuracy** (self-retrieval): hybrid **recall@5 ≈ 97%**, recall@1 ≈ 85%, MRR ≈ 0.90.
- **Embedding** all chunks: one-time **~4s** offline (cached to `embeddings.npz`); startup loads the
  cache. → *"4,300+ documents searched in ~15ms, no GPU."*
- **Relevance floor** (`RELAY_MIN_SIM=0.35`): on-topic hits sit at 0.43+, off-domain at 0.20–0.25,
  so the floor cleanly separates multi-hit / single-hit / no-hit.
- **`top_k=2`** (measured the right call): on the demo query it's identical to higher k (floor drops
  the rest); on broad queries higher k is ~2× slower per added card and adds clutter.

---

## 5. The UI (Hao's, now wired to the live backend)

- **Components** (`frontend/src/components/`): `NetworkConstellation` (the 3-node graph + "You"
  center, pulses while searching), `AgentsReached` (the agent cards — full=green✓ /
  redacted=amber+lock+"request access" / denied=grey), `AnswerPanel` (synthesized answer +
  provenance citations + "hand off to Claude Code"), `PromptPill` (the query input).
- **The live data layer** — `frontend/src/useRelayQuery.js` (Dennis): one hook owns the WebSocket
  and reduces the real event stream into `{phase, agents, cards, answer, provenance, submit,
  requestAccess, reset}`. `phase` includes `'synthesizing'` so the UI shows a live state while the
  answer streams. **`AskTheNetwork.jsx` is the single consumer** — Hao swapped his mock source for
  this hook, no contract changes.
- **Walking skeleton** — `frontend/src/components/LiveQueryDebug.jsx` at `http://localhost:5173/?debug`:
  a barebones client (raw frame stream + all controls) that's the guaranteed-working fallback demo.
- **Redesign** — Hao's "beacon-glow" visual pass (color/spacing tokens, `@phosphor-icons/react`,
  design docs in `docs/superpowers/`).

---

## 6. The demo

**The data is mostly real, with one planted scenario.** The real corpora are domain-disjoint (no
query answers coherently across parties), so a coherent **rate-limit/429s scenario** is *planted*
(`app/demo.py`, the single source of truth; `demo_seed.py` writes it to the gitignored corpora).
Synthetic, sanctioned for the demo; everything else is real.

**Three behaviors (all verified live):**
1. **Multi-hit — the hero beat:** *"We're seeing 429s on checkout — who changed the rate limit on
   the payments path, and what is it now?"* → all 3 nodes pulse; Northwind full+denied, Helios full,
   Quanta redacted+full; the answer streams in cited; **click Request access** → the throttle card
   flips redacted→full✓ and the answer re-streams with the 30 req/min value.
2. **Single-hit:** *"Next.js authentication flow…"* → only Northwind answers (real auth chunks).
3. **No-hit:** *"chocolate chip cookies"* / *"Taylor Swift lyrics"* → nodes pulse, **no cards**,
   *"No party returned a verified answer"* — no hallucination.

**Latency UX:** answers **stream** (first token ~3s, builds over ~2.3s) instead of a dead spinner;
grant-access is a **targeted** replay so only the one card re-streams.

---

## 7. Data model & frozen contracts (`shared/contracts/`)

- **`Chunk`**: `chunk_id, parent_doc_id, doc_title, owner, visibility, text, embedding, score`.
  `embedding`/`text` are server-side only — never on the wire.
- **`ResponseItem`** (the wire shape): `answer, source_party, source_doc_title, decision, verified,
  chunk_id, source_agent_id`.
- **WS events**: `ack` → `agent-activated` → `response-item` → `synthesizing` → `answer-delta`* →
  `done` (`synthesized_answer` + `provenance[]` + `item_count`). (`synthesizing`/`answer-delta` are
  additive — the hook handles them; `done` is unchanged + authoritative.)
- **Enums**: `visibility = public|restricted|private`, `decision = full|redacted|denied`.

---

## 8. Tooling & ops

- **`scripts/run.sh`** — one command: backend `:8000` + frontend `:5173`, sets the demo env
  (`RELAY_SEARCH=hybrid`, `RELAY_TOP_K=2`, `RELAY_MIN_SIM=0.35`), waits on `/health`.
- **`scripts/ingest.py`** — real raw data → corpora (`--loose`/`--max-per-title` for a fuller corpus;
  noise + secret filters always on).
- **`scripts/demo_seed.py`** — plants the demo scenario + tiers + embeds (idempotent; disk truth).
- **`scripts/build_embeddings.py`** — (re)build `embeddings.npz`.
- **`scripts/tier.py`** — flip one chunk's visibility.
- **`POST /demo/reset`** — re-arm the demo tiers in the live index between rehearsal takes (no restart).
- **Data sharing**: corpora/embeddings/raw are **gitignored** (real private data). `relay-hao-bundle.zip`
  (corpora + embeddings + setup) is how a teammate gets a working backend without the raw data.

---

## 9. Testing

- **78 mock tests** (no API key): gate policy/leakage, redaction, verification, provenance,
  responder, router, orchestrator (incl. streaming + targeted replay), bus, synthesis, grant-access,
  the API integration (httpx + WS), hybrid search, isolation, and the **deterministic demo-retrieval
  guard** (the locked query surfaces the planted needles top-2).
- **4 live tests** (`@pytest.mark.live`, needs key): real redaction no-leak, verification true/false,
  synthesis citations, and streamed synthesis.

---

## 10. What's done vs. what's left

**Done:** all 4 phases + streaming + scale + 3-party fan-out + the live UI integration. The
end-to-end demo runs on real data with the hero beat, on Hao's redesigned UI.

**Optional / deferred:**
- **MCP scale substrate** (the "parties connect live knowledge at scale" pitch) — Phase 5, only once
  the demo is rehearsed with time to spare. `search()` is the drop-in seam for it.
- **Fabricated-source ✗ kicker** — behind `RELAY_VERIFY_SYNTHESIS` (default off); grant-access is the
  rock-solid hero, flip the kicker on only if rehearsal proves it reliable.
- **Polish**: floor tuning for crisper scenarios, faster models if latency bites, demo rehearsal.

**Known notes:**
- The Anthropic API key lives in `backend/.env` (gitignored) — **rotate it** before/after the event.
- Asker is `agent_you` (3-party fan-out); `top_k=2`, floor `0.35` — all tunable via env/`run.sh`.
