# Beacon — Backend

The backend for **Beacon**, a permissioned knowledge-brokering network built for the
Berkeley AI Hackathon 2026. Three independent party agents query each other's
isolated corpora and share only what the owner authorizes — the wedge is
**enforced permission at the owner's boundary** (full / redacted / denied, decided
before content crosses the boundary) plus **verified provenance** (every shared
answer traces to a real source; fabricated citations get caught).

## Start here

- **[BUILD_INDEX.md](./BUILD_INDEX.md)** — the single entry point: canonical
  directory tree, the merged ordered build plan (mapped to checkpoints H1–H18),
  consolidated dependencies, the FastAPI startup-wiring plan, and the open
  contract questions to settle in a 2-minute sync.

## The frozen contracts (the seam — edit only with a 2-minute sync)

- [`../shared/contracts/data-model.md`](../shared/contracts/data-model.md) — Agent / Chunk / Cross-agent request / Response item.
- [`../shared/contracts/search-interface.md`](../shared/contracts/search-interface.md) — `search(query, agent_id, top_k=5) -> list[Chunk]`.
- [`../shared/contracts/api-websocket.md`](../shared/contracts/api-websocket.md) — `POST /query`, `POST /grant_access`, `ws://localhost:8000/ws/query`.

## Per-subsystem build docs

See [`docs/`](./docs/) — agents/corpus/index, permission gate, redaction,
provenance/verification, router, orchestrator, FastAPI app, grant-access. The
canonical reading order is listed in BUILD_INDEX.md §3.

## MVP scope (spec §5)

Flat in-memory index, 3 in-process agents, seeded corpora (10–30 chunks each), one
locked demo query, no production auth, no database, no GraphRAG. Scoping is real
and enforced in-demo, not hardened for prod.

## Search backends (`BEACON_SEARCH`)

The frozen `search(query, agent_id, top_k)` dispatches on the `BEACON_SEARCH` env var:

| Mode | Engine | Needs |
|------|--------|-------|
| `stub` (default) | keyword token-overlap | nothing — no model, no torch |
| `cosine` | dense only (model2vec static embeddings) | `model2vec` + `embeddings.npz` |
| `hybrid` | BM25 + dense, fused with Reciprocal Rank Fusion (RRF, k=60) | `model2vec` + `rank-bm25` + `embeddings.npz` |

- **Embeddings are model2vec static** (`minishlab/potion-retrieval-32M`, pinned in
  `app/agents/embeddings.py`) — numpy-only inference, no torch, instant cold start.
- **`hybrid`** runs a per-agent BM25 lexical channel beside the dense channel and fuses
  by rank, so exact identifiers (`429`, `RetryPolicy`) and paraphrase (`throttle` ↔
  `rate limit`) both land. It falls back to whichever channel is available.
- All modes keep the frozen shape: own-agent only, all tiers **ungated**, descending
  score in (0,1], `<= top_k`, `KeyError` on unknown agent. Retrieve-first, gate-second.
- `cosine`/`hybrid` load `app/data/corpora/embeddings.npz` (built once via
  `python -m scripts.build_embeddings`); any chunk missing from the cache is embedded
  on the fly at startup.

Quick check (no server, no gate):

```bash
BEACON_SEARCH=hybrid python -c "from app.agents.registry import build_registry; \
from app.retrieval import search as S; r=build_registry(with_embeddings=True); \
S.set_registry(r); print([(c['chunk_id'], round(c['score'],3)) for c in \
S.search('how do we stop the service getting overloaded','agent_helios',3)])"
```

> Note: server startup currently builds the embedding matrix for `cosine` only. To run
> `hybrid` over the live server, widen `main.py`'s `with_embeddings` check to include
> `hybrid` — otherwise it falls back to BM25-only (no dense channel).

## Run (planned)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set ANTHROPIC_API_KEY
python -m scripts.build_embeddings   # one-shot embeddings cache (cosine/hybrid; stub needs none)
uvicorn app.main:app --reload --port 8000
```

Base URL `http://localhost:8000`; WebSocket `ws://localhost:8000/ws/query`.
Embeddings use **model2vec static** (`minishlab/potion-retrieval-32M`) — local,
numpy-only, no torch, NOT Claude (Anthropic has no embeddings endpoint). See
**Search backends** above for the `BEACON_SEARCH` modes. The three Claude calls
(redaction, verification, synthesis) need `ANTHROPIC_API_KEY`.
```
