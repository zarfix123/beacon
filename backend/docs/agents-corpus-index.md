# BUILD DOC — Subsystem: Agents, Isolated Corpus & Flat Vector Index

> Status: PLAN / INDEX (not an implementation). Scope locked to spec section 5 (MVP).
> Owner: Dennis (backend). Consumes the three frozen contracts under `shared/contracts/`.
>
> Sibling backend subsystems (separate build docs / files, do NOT build them here):
> permission gate, redaction/verification Claude passes, orchestrator (fan-out / collect /
> synthesize), router, FastAPI HTTP + WebSocket endpoints. This doc is the substrate they sit on.

---

## 1. Purpose & where it sits in the query flow

This subsystem is the **data + retrieval substrate** for the 3 party agents. It owns:

1. **The Agent abstraction** — `{ id, party_name, scope_policy }` (data-model §1), plus each agent's
   **isolated in-memory state**: its own flat list of `Chunk` rows with precomputed embeddings.
2. **Genuine party isolation** — 3 agents constructed as separate parties with **no shared chunk
   memory**. One agent's index is unreachable from another's; isolation is what makes them real
   distinct parties (spec §6, §4).
3. **Retrieval** — embed the query, cosine top-k over **one** agent's index (numpy; Chroma optional),
   returning `Chunk` rows of **all visibility tiers, unfiltered**.
4. **The frozen `search(query, agent_id, top_k)` boundary** (search-interface.md) — this subsystem is
   the backend-side **consumer** of that interface AND ships the **keyword STUB** behind it until
   Hao's real cosine retrieval lands at checkpoint H8, then drop-in swaps with zero call-site changes.
5. **Startup loading** — where seeded corpora + their embeddings are loaded into the per-agent indexes.

### Position in spec section 10 (the query loop)

```
  User question
        │
        ▼
  [API /query]  ── orchestrator ──┐                         (sibling subsystems)
                                  │ fan-out CrossAgentRequest per agent
                                  ▼
            ┌─────────────── THIS SUBSYSTEM ───────────────┐
            │  search(query, agent_id, top_k) -> [Chunk]    │  step 3: cosine top-k
            │  • embed query                                │  over ONE agent's
            │  • cosine over agent_id's flat index ONLY     │  isolated index
            │  • return ALL tiers, with score, UNGATED      │
            └───────────────────────────────────────────────┘
                                  │ raw Chunk rows (public + restricted + private)
                                  ▼
  [permission gate]  step 4  ── public→full, restricted→redacted, private→denied
        │                        (gate + redaction/verification = sibling subsystems)
        ▼
  [orchestrator: collect → verify → synthesize]  steps 5–6
        │
        ▼
  WebSocket: agent-activated / response-item / done
```

**RETRIEVE-FIRST, GATE-SECOND (spec §9, hard constraint).** This subsystem performs *retrieval only*.
`search()` returns raw hits of every tier. It **does NOT gate, redact, filter by visibility, or strip
`text`/`embedding`**. The gate is a strictly downstream sibling subsystem. Mixing gating in here would
violate the contract and the product thesis.

> **Boundary note on the hard constraint "gate runs inside the responding agent before content
> crosses the boundary" (spec §3, §6):** In the MVP everything is in-process, so the "boundary" is a
> Python call boundary, not a network one. This subsystem deliberately keeps `search()` gate-free
> (per search-interface.md). The *enforcement* still happens "inside the responding agent" in the
> sense that the gate executes on the owning agent's raw chunks **before** the orchestrator emits any
> `response-item` — i.e. before content leaves the backend toward the frontend. We expose a thin
> per-agent `respond()` seam (see §3, `agent.py`) that the gate subsystem plugs into so the
> retrieve→gate sequence is anchored to the owning agent object, making the "enforced at the owner"
> story literal in code. The seam calls the gate; it does not implement it.

---

## 2. Files / modules to create under `backend/app/`

All paths are under the single package `backend/app/`. Names are chosen to **not collide** with the
sibling subsystems' files (gate → `gate.py`, redaction/verification → `verify.py`, orchestrator →
`orchestrator.py`, router → `router.py`, API/WS → `api.py`/`ws.py`, Claude client → `llm.py`). This
subsystem owns only the files listed here.

| File | Responsibility |
|------|----------------|
| `backend/app/models.py` | Shared typed record shapes (`Chunk`, `Agent`, `CrossAgentRequest`, `ResponseItem`) as `TypedDict`s matching the frozen data-model. Single import source for every subsystem so shapes can't drift. (Shared utility; this subsystem authors it because it needs it first. If a sibling already created it, extend, don't duplicate.) |
| `backend/app/embeddings.py` | One embedding function + the model id + dimension constant. Used to embed both corpus (offline/startup) and queries (real `search`). Isolated so the stub path never imports a heavy client. |
| `backend/app/corpus.py` | Loads seeded corpora from `backend/app/seed/*.json` into per-agent in-memory structures at startup. Builds the embedding matrix per agent. Owns the `AgentIndex` dataclass and the isolation guarantee. |
| `backend/app/agent.py` | The `Agent` runtime object: identity (`id`, `party_name`, `scope_policy`) + a handle to *its own* `AgentIndex` and nothing else. Provides `agent.search(...)` (delegates to retrieval over its own index) and the `respond()` seam the gate plugs into. |
| `backend/app/registry.py` | Constructs the 3 agents once at startup, holds them in an `AgentRegistry`, enforces that each agent only ever touches its own index. The single place `agent_id → Agent` resolution happens. |
| `backend/app/search.py` | The frozen `search(query, agent_id, top_k)` entry point + the **keyword STUB** + the **real cosine** implementation behind one selectable backend. This is the drop-in-swap point at H8. |
| `backend/app/seed/agent_northwind.json` | Seeded corpus for Northwind (10–30 chunks, mixed tiers). |
| `backend/app/seed/agent_helios.json` | Seeded corpus for Helios. |
| `backend/app/seed/agent_quanta.json` | Seeded corpus for Quanta. |
| `backend/app/seed/embeddings.npz` | (Optional, generated) precomputed corpus embeddings cache, keyed by `chunk_id`, so startup doesn't re-embed every boot. Built by `scripts/build_embeddings.py`. |
| `backend/scripts/build_embeddings.py` | One-shot offline script: read seed JSONs → embed each chunk → write `embeddings.npz`. Run once before the demo (spec §9 "indexing time, once, before demo"). |

### 2.1 `models.py` — shared record shapes

Matches data-model.md exactly. `embedding`/`score` are present on the in-memory `Chunk` but the gate/API
strip them before the wire (never serialized — data-model §note, search-interface guarantees).

```python
from typing import TypedDict, Literal, Optional, NotRequired

Visibility = Literal["public", "restricted", "private"]
Decision   = Literal["full", "redacted", "denied"]

class Chunk(TypedDict):
    chunk_id: str
    parent_doc_id: str
    doc_title: str
    owner: str                       # an Agent.id; == the searched agent_id
    visibility: Visibility
    text: str
    embedding: NotRequired[list[float]]   # server-side only; stub may omit
    score: NotRequired[float]             # result-only, 0.0–1.0, added by search

class Agent(TypedDict):
    id: str
    party_name: str
    scope_policy: str                # "three_tier" for MVP

class CrossAgentRequest(TypedDict):
    from_agent: str
    query: str

class ResponseItem(TypedDict):       # produced downstream by the gate, defined here for one source
    answer: Optional[str]
    source_party: str
    source_doc_title: Optional[str]
    decision: Decision
    verified: bool
    chunk_id: str                    # transport addition (frontend wiring)
    source_agent_id: str             # transport addition (owning Agent.id)
```

### 2.2 `embeddings.py` — embedding function

```python
import numpy as np

EMBED_MODEL = "voyage-3-lite"     # or sentence-transformers/all-MiniLM-L6-v2 (local, no key)
EMBED_DIM   = 512                 # MUST be uniform across all agents (data-model §2)

def embed_texts(texts: list[str]) -> np.ndarray:
    """Return an (n, EMBED_DIM) float32 matrix. Used for corpus (startup) and query (search)."""
    ...

def embed_query(query: str) -> np.ndarray:
    """Convenience: embed_texts([query])[0]  -> shape (EMBED_DIM,)."""
    ...
```

> **Embedding provider is NOT Claude.** Anthropic does not ship a public embeddings endpoint, so do not
> call `claude-*` for vectors. Use Voyage (Anthropic's recommended embeddings partner) **or** a local
> `sentence-transformers` model. For a 24h hackathon with tiny corpora, prefer the **local
> `all-MiniLM-L6-v2`** (no API key, no latency, deterministic, `EMBED_DIM=384`) unless a key is already
> wired. Whatever is chosen, the **same model embeds corpus and query** (search-interface param
> semantics) and `EMBED_DIM` is fixed once. This is the one detail Hao and Dennis must agree on at H8
> so the swap is clean — note it in the H8 sync.

### 2.3 `corpus.py` — load seeded corpora into isolated per-agent indexes

```python
from dataclasses import dataclass, field
import json, pathlib
import numpy as np
from .models import Chunk

SEED_DIR = pathlib.Path(__file__).parent / "seed"

@dataclass
class AgentIndex:
    """One agent's isolated flat index. Holds ONLY this agent's chunks."""
    agent_id: str
    chunks: list[Chunk]                 # stored rows (no `score`)
    matrix: np.ndarray | None = None    # (n, EMBED_DIM) row i ↔ chunks[i]; None in stub mode

    def __post_init__(self) -> None:
        assert all(c["owner"] == self.agent_id for c in self.chunks)  # isolation invariant

def load_agent_index(agent_id: str, *, with_embeddings: bool) -> AgentIndex:
    """Read seed/<agent_id>.json, optionally attach precomputed/freshly-built embeddings.

    with_embeddings=False  -> stub mode (keyword overlap, no vectors).
    with_embeddings=True   -> load embeddings.npz cache, or embed_texts() on miss.
    The returned AgentIndex contains ONLY rows whose owner == agent_id (enforced).
    """
    ...
```

Key points:
- Each `AgentIndex` is a **separate object** holding a **separate list**. No agent holds a reference
  to another agent's `chunks` or `matrix`. This is the isolation guarantee (spec §6).
- The matrix row order is pinned to `chunks` order so `score` maps back by index.
- Stub mode skips the matrix entirely (keyword overlap needs no vectors), per search-interface stub notes.

### 2.4 `agent.py` — the runtime Agent object (identity + own index + gate seam)

```python
from dataclasses import dataclass
from .corpus import AgentIndex
from .models import Chunk, ResponseItem

@dataclass
class RuntimeAgent:
    id: str
    party_name: str
    scope_policy: str            # "three_tier"
    index: AgentIndex            # THIS agent's index only

    def search(self, query: str, top_k: int = 5) -> list[Chunk]:
        """Retrieve over OWN index only. Delegates to search.search(query, self.id, top_k).
        Returns ALL tiers, ungated, with score. (retrieve-first)"""
        ...

    def respond(self, query: str, top_k, gate_fn) -> list[ResponseItem]:
        """Seam for the GATE subsystem (sibling). retrieve-first, gate-second, IN this agent
        before anything crosses outward:
            hits = self.search(query, top_k)          # raw, all tiers
            return [gate_fn(h, self) for h in hits]    # gate provided by sibling subsystem
        This subsystem provides the seam + ordering; it does NOT implement gate_fn."""
        ...
```

> `respond()` exists so the "enforcement runs inside the responding agent before content crosses the
> boundary" requirement is literal: the gate is invoked through the owning agent, on its own raw hits,
> before the orchestrator ever sees a `ResponseItem`. The gate function is injected by the sibling gate
> subsystem — this file must not contain visibility→decision logic.

### 2.5 `registry.py` — construct the 3 agents once, resolve by id

```python
from .agent import RuntimeAgent
from .corpus import load_agent_index

AGENT_DEFS = [
    ("agent_northwind", "Northwind Robotics", "three_tier"),
    ("agent_helios",    "Helios Dynamics",    "three_tier"),
    ("agent_quanta",    "Quanta Systems",     "three_tier"),
]

class AgentRegistry:
    def __init__(self, agents: dict[str, RuntimeAgent]) -> None:
        self._agents = agents

    def get(self, agent_id: str) -> RuntimeAgent:
        if agent_id not in self._agents:
            raise KeyError(agent_id)            # matches search() contract: KeyError on unknown id
        return self._agents[agent_id]

    def all_ids(self) -> list[str]: ...
    def party_name(self, agent_id: str) -> str: ...   # for ResponseItem.source_party / WS payloads

def build_registry(*, with_embeddings: bool) -> AgentRegistry:
    """Called once at FastAPI startup. Builds 3 isolated RuntimeAgents from AGENT_DEFS + seed files."""
    agents = {
        aid: RuntimeAgent(aid, name, policy, load_agent_index(aid, with_embeddings=with_embeddings))
        for (aid, name, policy) in AGENT_DEFS
    }
    return AgentRegistry(agents)
```

- The registry is the **only** place `agent_id → Agent` resolution lives. The orchestrator/router and
  `search()` resolve through it; nothing reaches into another agent's index.
- `party_name` lookups for `agent-activated` and `ResponseItem.source_party` come from here.

### 2.6 `search.py` — the frozen interface + STUB + real cosine (drop-in swap point)

```python
from .models import Chunk
from .registry import AgentRegistry
from . import embeddings
import numpy as np, os, re

_REGISTRY: AgentRegistry | None = None   # set at startup by build_registry() wiring
SEARCH_BACKEND = os.getenv("RELAY_SEARCH", "stub")   # "stub" until H8, then "cosine"

def search(query: str, agent_id: str, top_k: int = 5) -> list[Chunk]:
    """FROZEN signature (search-interface.md). Single dispatch point.
    Returns ALL visibility tiers, ungated, ordered by descending score, <= top_k, [] on no hit.
    Raises KeyError on unknown agent_id. NEVER gates/filters by visibility."""
    agent = _REGISTRY.get(agent_id)              # KeyError on unknown id (contract)
    if SEARCH_BACKEND == "cosine":
        return _cosine_search(query, agent, top_k)
    return _keyword_stub(query, agent, top_k)

def _keyword_stub(query, agent, top_k) -> list[Chunk]:
    """Deterministic keyword-overlap (search-interface stub algorithm):
       tokenize query + chunk text/title on \\W+, score = |distinct query tokens in chunk| /
       |distinct query tokens|, drop score==0, sort desc, take top_k. No embeddings read."""
    q = {t for t in re.split(r"\W+", query.lower()) if t}
    scored = []
    for c in agent.index.chunks:
        toks = set(re.split(r"\W+", (c["text"] + " " + c["doc_title"]).lower()))
        s = len(q & toks) / max(len(q), 1)
        if s > 0.0:
            scored.append({**c, "score": round(s, 4)})   # carries all tiers, with score
    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored[:top_k]

def _cosine_search(query, agent, top_k) -> list[Chunk]:
    """Real retrieval (Hao's substrate or numpy fallback). embed query -> cosine vs agent.index.matrix
       -> argsort desc -> attach score in [0,1] -> top_k. Same Chunk shape, all tiers."""
    qv = embeddings.embed_query(query)                       # (D,)
    M = agent.index.matrix                                   # (n, D), own index only
    sims = (M @ qv) / (np.linalg.norm(M, axis=1) * np.linalg.norm(qv) + 1e-9)
    order = np.argsort(-sims)[:top_k]
    return [{**agent.index.chunks[i], "score": float((sims[i] + 1) / 2)} for i in order if sims[i] > 0]
```

> **H8 swap:** flip `RELAY_SEARCH=cosine` (or replace `_cosine_search`'s body with a call into Hao's
> module). Call sites in the orchestrator/gate never change — they only ever import `search()`.
> If Hao delivers his own `search()` module, this file's `search()` becomes a one-line delegate to his,
> preserving the KeyError-on-unknown-id and all-tiers guarantees.

---

## 3. Claude (Anthropic API) calls in THIS subsystem

**None.** This subsystem is pure retrieval + data loading. Its only LLM-adjacent dependency is the
**embedding** model, which is **not** a Claude model (Anthropic has no public embeddings endpoint — see
§2.2; use Voyage or a local sentence-transformers model).

The two Claude calls the product needs (spec §11) live in **sibling subsystems**, not here, and are
documented for cross-reference / the H8–H13 integration:

| Call | Owner subsystem | Purpose (spec §11) | Model | Output shape (spec §11 / data-model §4) |
|------|-----------------|--------------------|-------|------------------------------------------|
| **Redaction** | gate / `verify.py` | Turn a `restricted` chunk into a one-line gist that conveys a solution *exists* without leaking it. Real transform; content never crosses. | `claude-opus-4-8` (gist quality + leak-safety is the wedge; tiny token count makes Opus affordable). Acceptable downgrade: `claude-haiku-4-5` if latency in the live grant-access beat matters. | `{ "answer": str }` → becomes `ResponseItem.answer` for `decision="redacted"`, `verified=false`. |
| **Verification** | orchestrator / `verify.py` | Given a returned answer + its cited chunk text, decide if the answer is supported. | `claude-opus-4-8` (grounding judgment is load-bearing for the provenance story). | `{ "verified": bool }` → sets `ResponseItem.verified`. |
| **Synthesis** | orchestrator | Compose `done.synthesized_answer` with inline citations from the `full`/`redacted` items. | `claude-opus-4-8` (final on-stage answer; one call per run). | `{ "synthesized_answer": str }` plus `provenance[]` assembled from items. |

Tight prompt sketches (for the sibling owners; included so this doc is self-contained at the seam):

- **Redaction (input = restricted chunk text + doc_title):**
  *"A solution to the user's problem exists in this restricted document. In ONE sentence, state THAT a
  solution exists and its general area, revealing no specifics, numbers, or steps. Return JSON
  `{"answer": "..."}`."*
- **Verification (input = answer + cited chunk text):**
  *"Is every claim in ANSWER directly supported by SOURCE? Answer strictly. Return JSON
  `{"verified": true|false}`."*
- **Synthesis (input = list of full/redacted items + the question):**
  *"Synthesize a single answer to QUESTION using only the SUPPORTED items below, with inline
  `[party]` citations. Return JSON `{"synthesized_answer": "..."}`."*

These are listed under `claude_calls` in the structured summary as **out-of-subsystem references**, so
the orchestrator owner knows the expected shapes; none are implemented in the files in §2.

---

## 4. Dependencies

### Other backend modules
- `models.py` (this subsystem authors it; consumed by every sibling).
- Sibling **gate** subsystem provides `gate_fn` injected into `RuntimeAgent.respond()` — a runtime
  dependency direction (gate depends on this subsystem's seam, not vice-versa).
- Sibling **orchestrator/router** consumes `registry.get()` and `search()`.
- FastAPI app startup wires `build_registry()` and sets `search._REGISTRY` (in `api.py`, a sibling file).

### pip packages
- `numpy` — cosine math + embedding matrices. (Required.)
- `fastapi`, `uvicorn[standard]`, `websockets` — owned by the API sibling, listed for the shared
  `requirements.txt` only.
- Embedding provider (pick ONE, see §2.2):
  - `sentence-transformers` (+ `torch`) for the local `all-MiniLM-L6-v2` path (no API key) — **recommended for the hackathon**, or
  - `voyageai` for the hosted Voyage path (needs `VOYAGE_API_KEY`).
- `chromadb` — **optional only.** Tiny corpora make plain numpy simpler and dependency-light; add Chroma
  only if Hao's substrate already uses it. Not required by this subsystem.
- `anthropic` — needed by sibling Claude subsystems, not by this one.

> Add a `backend/requirements.txt` (shared, owned by whoever scaffolds first). This subsystem's hard
> lines: `numpy`, plus the chosen embedding lib.

---

## 5. Ordered build steps

1. **Scaffold the package.** Create `backend/app/__init__.py`, `backend/app/seed/`,
   `backend/scripts/`, and a shared `backend/requirements.txt` with `numpy` + the embedding lib.
2. **`models.py`.** Add the `TypedDict`s from §2.1 verbatim against data-model.md. This unblocks every
   sibling immediately.
3. **Seed corpora (joint, hour 0 — spec §15).** With Hao, author `seed/agent_*.json`: 10–30 chunks per
   agent, fields exactly = data-model §2 minus `embedding` (backfilled later). **The locked demo query
   MUST hit mixed tiers** — at least one `restricted` chunk on one party (so gate + redaction + the
   grant-access beat are exercisable on stub data; search-interface stub requirement). Keep one
   `private` chunk somewhere for the `denied` badge.
4. **`corpus.py` (stub mode first).** Implement `load_agent_index(agent_id, with_embeddings=False)`:
   read JSON, assert the isolation invariant (`owner == agent_id` for every row), build `AgentIndex`
   with `matrix=None`.
5. **`registry.py`.** Implement `build_registry(with_embeddings=False)` and `AgentRegistry` (with the
   `KeyError`-on-unknown-id contract). Confirm 3 separate `AgentIndex` objects, no shared lists.
6. **`agent.py`.** Implement `RuntimeAgent` with `.search()` delegating to `search.search()` and the
   `respond()` seam (ordering only; no gate logic).
7. **`search.py` — STUB path.** Implement `search()` dispatch + `_keyword_stub()` per the
   search-interface algorithm. Wire `_REGISTRY`. **Now the gate/orchestrator can build against a real,
   deterministic `search()`** without waiting on embeddings or Hao.
8. **Smoke test the stub.** Run the locked demo query through `search()` for all 3 agents; assert: only
   own-agent chunks returned, all tiers present, descending `score`, `<= top_k`, `KeyError` on a bogus
   id, `[]` on a no-keyword query. (Hand to `/tests` sibling or a quick `scripts/` check.)
9. **`embeddings.py`.** Pick the provider (§2.2), pin `EMBED_MODEL` + `EMBED_DIM`, implement
   `embed_texts` / `embed_query`.
10. **`scripts/build_embeddings.py`.** Embed every seed chunk once → write `seed/embeddings.npz` keyed
    by `chunk_id`. (Spec §9: index once, before demo. Caching avoids re-embedding every boot — spec §17
    "cache embeddings.")
11. **`corpus.py` — embeddings mode.** Extend `load_agent_index(..., with_embeddings=True)` to load the
    `.npz` (or embed on cache miss) and attach `matrix` in `chunks` order.
12. **`search.py` — cosine path.** Implement `_cosine_search()` (numpy) behind `RELAY_SEARCH=cosine`.
13. **H8 checkpoint swap.** Either flip the env flag to `cosine` (numpy fallback) or delegate
    `search()` to Hao's real module if delivered. Verify identical shape/guarantees; re-run step-8 tests.
    Sync with Hao on `EMBED_MODEL`/`EMBED_DIM` so query and corpus vectors match.
14. **Startup wiring (coordination with API sibling).** In `api.py` startup: call `build_registry()`
    and set `search._REGISTRY`. Document that `grant_access` mutates `registry.get(owner).index.chunks`
    visibility in place (the chunk is found by `chunk_id`), then the orchestrator re-runs — the mutate
    lives in the gate/orchestrator sibling but operates on this subsystem's in-memory chunk; expose a
    helper `registry.find_chunk(chunk_id) -> (RuntimeAgent, Chunk)` for it.

---

## 6. Integration points with frozen contracts & sibling subsystems

| Contract / subsystem | This subsystem's obligation |
|----------------------|------------------------------|
| **data-model §1 (Agent)** | `RuntimeAgent` / `AgentRegistry` carry `id`, `party_name`, `scope_policy="three_tier"`; locked ids `agent_northwind`, `agent_helios`, `agent_quanta`. |
| **data-model §2 (Chunk)** | `seed/*.json` rows + `AgentIndex.chunks` use exactly these keys. `embedding` server-side only; `score` added only on `search()` results. |
| **search-interface.md** | `search(query, agent_id, top_k=5) -> list[Chunk]`, descending score, `<= top_k`, `[]` on no hit, `KeyError` on unknown id, **all tiers unfiltered**, `owner == agent_id`. STUB matches signature + shape for drop-in swap at H8. |
| **api-websocket.md** | This subsystem feeds the gate, which feeds `response-item`/`done`. We provide `registry.party_name(agent_id)` for `agent-activated.party_name` and `ResponseItem.source_party`, and `registry.find_chunk(chunk_id)` for `grant_access`. We never serialize `embedding`/`score`/`text` onto the wire — the gate strips them. |
| **gate subsystem** | Receives raw `search()` hits via `RuntimeAgent.respond(gate_fn=...)`; this subsystem guarantees retrieve-first ordering and never gates. |
| **orchestrator/router** | Resolve agents via `registry`, fan out by calling `search()`/`agent.search()` per agent. We guarantee isolation so a fan-out to agent A cannot read B's chunks. |
| **grant_access (coupled feature)** | We expose `registry.find_chunk(chunk_id)` and the chunks are mutable in place (`visibility` flip); the orchestrator does the toggle + re-run. New `search()` after the flip naturally returns the now-`public` chunk. |

---

## 7. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| **Cross-party leakage** (one agent reading another's chunks) — the product's core security claim. | Hard isolation invariant: each `AgentIndex` owns its own list; `__post_init__` asserts every row's `owner == agent_id`; `search()`/`agent.search()` only ever touch `registry.get(agent_id).index`. No global chunk list. Add a unit test that searching agent A returns zero chunks owned by B/C. |
| **Gating leaking into retrieval** (violates retrieve-first, §9). | `search()` and `_keyword_stub`/`_cosine_search` contain **no** visibility checks; all tiers returned with `text` intact. Gate is a separate file injected via `respond()`. Code review gate: grep these files for `visibility ==` should return nothing. |
| **`embedding` / `text` of restricted chunks crossing the wire.** | This subsystem never serializes; the gate strips `embedding`/`score` and (for restricted/denied) replaces `text` with gist/null before any WS emit. Documented as the gate's job; this subsystem only hands raw chunks to the in-process gate, never to the transport layer. |
| **Verification / embedding latency in the live grant-access beat** (spec §17). | Tiny corpora (10–30 chunks). Precompute corpus embeddings (`embeddings.npz`) so startup/re-run never re-embeds the corpus; only the query is embedded (one vector). Local MiniLM removes network latency entirely. Numpy cosine over <100 rows is microseconds. |
| **Embedding-model mismatch at H8** (query embedded with a different model than the corpus → garbage cosine). | Pin `EMBED_MODEL` + `EMBED_DIM` in one constant; same function embeds corpus and query; explicit H8 sync line with Hao. Stub path is model-free so dev is never blocked on this. |
| **Stub scores aren't comparable to cosine** (threshold tuning against stub misleads). | Documented in search-interface; do not set score floors against stub numbers. Stub used only for shape/wiring, not relevance tuning. |
| **Non-determinism breaking the rehearsed demo.** | Stub is fully deterministic; cosine over fixed precomputed vectors is deterministic; stable sort on score. Lock the demo query in seed data so the same chunks always surface. |
| **`grant_access` re-run not reflecting the toggle.** | Visibility is mutated in place on the in-memory chunk before re-run; `search()` reads live `chunks`, so the next retrieval sees `public`. No cache between toggle and re-run. (Re-run/emit owned by orchestrator; this subsystem just keeps chunks mutable + findable.) |
| **`models.py` ownership collision** with a sibling also creating it. | Whoever scaffolds first authors it; others import. Flagged in build step 1; single source prevents shape drift. |
| **Gap noticed (not a contradiction):** contracts don't define a min-score floor for cosine, and the stub may surface low-relevance noise chunks. | Left to `top_k` only for the MVP (search-interface explicitly makes a floor implementation's choice). If noise hurts the demo, add an optional floor in `_cosine_search` ONLY — never in the stub, and never as a visibility filter. Noted here rather than inventing a contract field. |

---

## 8. Summary of the contract-safe boundaries this subsystem holds

- Returns **raw, all-tier** `Chunk` rows. Never gates, redacts, filters, or strips.
- Enforces **single-agent isolation** at construction and on every search.
- Ships a **deterministic keyword stub** that is a drop-in for real cosine at H8.
- Loads **seeded corpora + precomputed embeddings** once at startup.
- Provides the `respond()` seam so the gate runs **inside the owning agent, before content crosses the
  boundary** (spec §3/§6) — while keeping the gate logic itself out of this subsystem.
