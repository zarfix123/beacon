# Relay — Backend

The backend for **Relay**, a permissioned knowledge-brokering network built for the
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

## Run (planned)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set ANTHROPIC_API_KEY
python scripts/build_embeddings.py   # one-shot, index-once-before-demo (cosine mode)
uvicorn app.main:app --reload --port 8000
```

Base URL `http://localhost:8000`; WebSocket `ws://localhost:8000/ws/query`.
Embeddings use a local model (sentence-transformers `all-MiniLM-L6-v2`), NOT
Claude — Anthropic has no embeddings endpoint. The three Claude calls (redaction,
verification, synthesis) need `ANTHROPIC_API_KEY`.
```
