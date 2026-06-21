# Beacon — Complete Build Spec v2 (Berkeley AI Hackathon 2026)

*Working name. Alternatives: Conduit, Quorum, Synapse.*

---

## 1. Thesis & wedge
- **What it is:** a permissioned knowledge-brokering network. Agents represent independent parties, query each other for already-solved problems, share only what they're authorized to, and attach verifiable provenance.
- **The wedge (no one combines all three):**
  1. **Cross-party** — not one expert (Delphi), not one org's search (Glean), not your own pooled memory (universal-memory tools).
  2. **Enforced permission at the owner's boundary** — full / redacted / denied, decided before anything leaves the owning agent.
  3. **Verified provenance** — every shared answer traces to a real source, and fabricated citations get caught.
- Both load-bearing pieces (2 and 3) are trust/security problems. That's the team's edge.

## 2. The two layers (same primitive, different boundary)
- A **scope** is just a visibility policy. Move the boundary, get a different topology:
- **Intra-workspace:** boundary is per-team. Teams inside one org broker knowledge, restricting what crosses team lines.
- **Inter-workspace (public layer):** boundary is per-org or per-person. Anyone can ask an engineering problem; each party exposes a **public scope**, a **restricted scope** (request-access), and a **private core** that never leaves.
- Same three tiers, same gate, same redaction and provenance logic. The public layer costs no extra engineering, only framing and seed data.
- **Primary demo = the public inter-org layer**, because it's the bigger swing and puts the scope decision center stage.

## 3. Permission model (the core product surface)
- **Provenance vs content split:**
  - *Provenance* = the pointer (source party, doc title, owner, timestamp). Travels even when content doesn't.
  - *Content* = the actual answer payload.
- **Three tiers:**
  - **Public** — pointer + payload.
  - **Restricted** — pointer + redacted gist + "request access." (Default for the demo, most compelling.)
  - **Private** — payload hidden; you choose whether even the pointer shows ("a restricted item exists, owned by X") or nothing at all.
- **Enforcement runs in the responding agent**, before content crosses the boundary, so a restricted payload physically cannot leak through the chain.
- Knowing *that* something was solved (and by whom) is itself graduated information. Modeling that gradient is the product.

## 4. What we're building (MVP)
- **3 agents**, each = a Claude brain + a private corpus + a scope policy, presented as 3 independent public-facing parties.
- A **query loop**: ask the network → each party's agent searches its corpus → returns per-tier results → asker verifies provenance and synthesizes.
- A **permission gate** returning full / redacted / denied per chunk.
- A **provenance + verification** pass (real source, grounding check).
- A **frontend** showing the network light up, the per-party decision, cited answers, and a **live grant-access** beat.

## 5. Out of scope (protect the 24h)
- No live hooks into real ChatGPT/Gemini/Claude accounts. Corpora are **seeded** (state this in the pitch).
- No login, accounts, real marketplace, or monetization.
- No production auth. Scoping is real and enforced in-demo, not hardened for prod.
- Small corpora (10–30 docs/agent).
- Fetch.ai Agentverse is a **stretch**, not core.
- No knowledge graph / GraphRAG / nested vectors. Flat index only.

## 6. Architecture
- **Agent (×3):** isolated corpus + flat vector index + permission gate. Isolation is what makes them genuinely separate parties.
- **Router:** lets the asking agent discover and query the others. In-process to start; WebSocket out to stream "agent activated" events to the UI.
- **Orchestrator:** lives in the asking agent — plan → fan out → collect → verify → synthesize.
- **Permission gate:** per-chunk policy check on every cross-agent request.
- **Provenance/verification:** Claude pass confirming each answer is grounded in its cited source.

## 7. Tech stack
- **Brains:** Claude (Anthropic API) for all 3 agents. Build everything with **Claude Code** (required for the Anthropic prize — say so on Devpost).
- **Backend:** Python + FastAPI, one service with 3 isolated agent contexts; WebSocket for live events.
- **Retrieval:** embeddings + cosine. Chroma or plain numpy over precomputed embeddings (corpora are tiny).
- **Permission gate:** plain Python policy functions keyed off per-chunk `visibility`. Capability-scoped requests (make this genuinely real — it's the wedge).
- **Frontend:** React + Tailwind + react-flow (or d3) for the network graph; WebSocket client for live updates.

## 8. Data model
- **Agent:** `{ id, party_name, scope_policy }`
- **Chunk (one row in an agent's flat index):**
  `{ chunk_id, parent_doc_id, owner, visibility: public|restricted|private, text, embedding }`
- **Cross-agent request:** `{ from_agent, query }`
- **Response item:** `{ answer, source_party, source_doc_title, decision: full|redacted|denied, verified: bool }`

## 9. Retrieval (how indexing actually works)
- **Mental model:** each agent's index is a **flat list of `{ text, vector, tags }`**. No nesting, no graph. Intelligence is in the tags and the gate, not the index shape.
- **Indexing time (once, before demo):**
  1. Seed raw docs (chat threads, wiki pages, code notes).
  2. Chunk by semantic unit — for chats, one question-plus-resolution; for docs, 200–500 token chunks.
  3. Embed each chunk → one vector.
  4. Store the row with `visibility` and `parent_doc_id` tags. Chunks inherit the doc's visibility.
- **Query time:** embed the query → cosine top-k over the agent's list → **then** run results through the gate. Retrieve first, gate second. That ordering is the product.
- Optional only if retrieval underperforms: small-to-big (embed small chunks, return parent thread). Not MVP-critical.

## 10. Query flow (the loop)
1. User submits a public engineering question.
2. Asking agent embeds it, fans out to the 3 party agents via the router.
3. Each party agent runs cosine top-k over its own index.
4. Each passes its hits through the **gate**: public → full + provenance; restricted → redacted gist + access-request + provenance; private → nothing or existence-only.
5. Asking agent collects responses, runs the **verification** pass on any content returned.
6. Asking agent synthesizes the final answer with citations and surfaces access requests.

## 11. The two Claude calls that make it real
- **Redaction** (restricted): hand Claude the restricted chunk, get a safe one-line gist conveying *that* a solution exists without leaking it. Real transform — content never crosses the boundary.
- **Verification** (returned content): hand Claude the answer + cited chunk, ask "is this supported, yes/no." Surface `verified ✓` / `unverifiable ✗`.

## 12. Frontend / UI-UX spec
- **Layout:** single screen. Left = query box + synthesized answer. Center = network graph (asker node + 3 party nodes). Right = per-party response cards.
- **Network graph:** nodes for asker + 3 parties. On submit, edges animate and party nodes **pulse** as they're searched.
- **Response card (per party):** party name, a **decision badge** (green Full / amber Redacted / grey Denied), the returned gist or answer, a clickable **citation** (doc title), and a `verified ✓` indicator.
- **Redacted state:** shows the gist greyed with a lock icon and a **"Request access from [Party]"** button.
- **Hero beat (live grant-access):** clicking the button toggles that chunk's visibility, re-runs the query, and the card animates from locked-grey to full-green with the real verified answer flowing in. The wall comes down on stage.
- **Synthesized answer panel:** final answer with inline citations and a small provenance list (which party each fact came from).
- **Visual tone:** clean, high-contrast, one accent color for "verified," amber for restricted, grey for denied. The badges and the graph are the demo's visual anchors — build them first.

## 13. Demo script (~3 min)
1. Show the 3-party public network.
2. Ask a public engineering question.
3. Nodes pulse; two parties return **full** public answers with working citations.
4. The third has the real fix but it's **restricted** → redacted gist + "Request access."  ← *the wow*
5. Click **Request access** → card resolves live to the full **verified** answer.
6. Synthesized answer shows provenance across parties.
7. Optional kicker: inject a fabricated source, show it fails verification (`✗`).
8. Close on the vision: a public library where any org or expert is a permissioned, queryable agent.

## 14. Prize alignment
- **Track:** Ddoski's World (democratizing access to knowledge = social impact). Most ambitious framing, best Anthropic fit.
- **Anthropic (primary):** Claude-native, built with Claude Code, economic-opportunity/education swing.
- **Fetch.ai (stretch):** router on Agentverse → multi-agent bounty.
- **Cheap stacks (if time):** Sentry (error monitoring), Arize (trace/eval the agent loop).

---

## 15. Two-person work split (designed to minimize conflicts)

**Principle:** split by codebase with a frozen interface so you almost never touch the same files. One seam = the contracts, agreed in hour 0.

### Ownership
- **Dennis — entire backend (the wedge):** permission gate, redaction, provenance/verification, orchestration loop, router, API + WebSocket endpoints. This is your edge; own it end to end.
- **Hao — retrieval substrate + entire frontend:** chunk/embed/store/search (first, ~2–3h), then the full React app (network graph, response cards, badges, citations, the live grant-access beat).
- **Joint, hour 0:** seed the 3 corpora and lock the exact demo query together. It touches both retrieval and the permission tiers, so do it once, together, up front.

### The three frozen contracts (write together in hour 0, then freeze)
1. **Chunk/record schema** (section 8) — so retrieval and the gate agree on shape.
2. **`search(query, agent_id) -> [chunk]` interface** — Hao implements, Dennis consumes (or stubs).
3. **API + WebSocket event shapes** — the JSON the frontend renders (response items, node-pulse events, grant-access endpoint signature).
- Changing any of the three requires a 2-minute sync. Otherwise they're untouchable.

### How you stay unblocked (build against mocks)
- Hao builds the **frontend against a mock JSON fixture** matching the contract, so he never waits on the backend.
- Dennis **stubs `search`** (return seeded chunks by keyword) so he never waits on retrieval, then swaps in Hao's real one at the first checkpoint.

### The one coupled feature
- **Grant-access-live** spans both: Dennis exposes a `grant_access(chunk_id)` endpoint that toggles visibility and re-runs; Hao builds the button + animation. Agree the endpoint signature early, then build the halves independently.

### Branch & merge discipline
- Separate folders: `backend/` (Dennis), `frontend/` (Hao), `shared/contracts` (edit only together).
- Feature branches per person, small frequent commits **within your own folder**.
- Integrate at **3 checkpoints, not continuously**: H8, H13, H18. Batch the merges there.
- Whoever scaffolds the repo (hour 0) sets the folder structure first so all paths are stable before parallel work starts.

---

## 16. Build timeline (24h, mapped to the split)
- **H0–1 (both):** repo scaffold, freeze the 3 contracts, seed corpora + lock demo query.
- **H1–3:** Hao builds retrieval behind the `search` interface, commits it. Dennis scaffolds backend + stubs search, starts the gate.
- **H3–8:** Dennis builds the 3-tier gate + redaction call. Hao builds frontend scaffold + network graph against the mock.
- **H8 — checkpoint:** integrate real search into the gate; first backend end-to-end test.
- **H8–13:** Dennis builds orchestration + provenance/verification. Hao builds query UI, response cards, badges, citations.
- **H13 — checkpoint:** wire frontend to live backend over WebSocket; first full vertical demo.
- **H13–18:** Dennis builds the `grant_access` endpoint (toggle + re-run). Hao builds the live grant-access animation.
- **H18–21 (both):** polish the hero beat, the public-layer framing in the UI, rehearse.
- **H21–23:** buffer + bugfix. **Devpost draft submitted by midnight Sat regardless.**
- **H23–24:** final rehearsal, rest.

## 17. Risks & mitigations
- **"Looks like 3 chatbots texting"** → the network graph + decision badges + the wall-coming-down animation are the anchors. Build them early.
- **Verification latency** → tiny corpora, cache embeddings, tight verify prompt.
- **Scope creep** → hard cap at 3 agents and one demo query.
- **Integration seams** → the 3 frozen contracts + mock-driven parallel work are the defense.
- **Multi-process complexity** → start in-process; only split services if time allows.

---

**Pitch positioning (one line):** Delphi clones one expert, Glean searches one org, universal-memory tools pool your own context. Beacon is the first to broker knowledge *between* parties, with enforced permission tiers and verifiable provenance.
