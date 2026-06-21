# Relay — Demo Runbook

The one-page reference for running and narrating the demo. Relay is a permissioned
knowledge-brokering network: an asking agent fans a question out to other parties, each
party's **gate** decides what may cross its boundary (full / redacted / denied), answers are
**verified** against their source, and the asker **synthesizes** one cited answer.

## Run it

```bash
cd backend && ./scripts/run.sh          # backend :8000 + frontend :5173, Ctrl-C stops both
```

`run.sh` exports the demo env before launch (these are read at import time, so they must be
set in the environment, not just `.env`):

| var | value | why |
|---|---|---|
| `RELAY_SEARCH` | `hybrid` | real engine: BM25 + dense (model2vec) + RRF |
| `RELAY_TOP_K` | `2` | each party returns only its top-2 (clean cards) |
| `RELAY_MIN_SIM` | `0.35` | relevance floor → off-topic = no-hit, one-party = single-hit |

- **UI:** http://localhost:5173 (the visual shell) — or http://localhost:5173/?debug for the
  walking-skeleton client (raw event stream; the guaranteed-working fallback).
- **Asker:** `agent_helios` (excluded from fan-out) → responders are **Northwind** + **Quanta**.

## Reset between takes

Grant-access flips a chunk to public in the *live* index. To re-arm the redacted card:

```bash
curl -X POST http://localhost:8000/demo/reset     # instant, no restart (re-applies tiers)
```

A fresh `run.sh` (server restart) is the can't-fail hard reset (reloads disk tiers).
`python -m scripts.demo_seed` re-plants + re-embeds the corpus from scratch (disk truth).

## The retrieval, by the numbers

Real data, re-ingested at volume (`scripts/ingest.py`, deduped): **~1,440 chunks** indexed
(Northwind 439, Quanta 437, Helios 561). Each party searches its own index, isolated.

| engine | latency (per search) | notes |
|---|---|---|
| cosine (dense) | ~4 ms | brute-force numpy, no GPU |
| **hybrid (used)** | **~16 ms** | BM25 + dense + RRF; paraphrase-robust |
| keyword stub | ~112 ms | Phase-1 placeholder, not used |

Accuracy (self-retrieval): hybrid **recall@5 ≈ 97%**, recall@1 ≈ 85%, MRR ≈ 0.90.
Embedding all chunks is a one-time **~3 s** offline step (cached to `embeddings.npz`); startup
loads the cache + pre-warms BM25 so the first live query is snappy. **"1,440 docs searched in
~16 ms, no GPU."**

## The three demo scenarios (all verified live)

A **relevance floor** (cosine ≥ 0.35) separates a real hit (sim 0.43+) from noise (0.20–0.25),
which gives three distinct behaviors:

### 1. Multi-hit — the hero beat
> **We're seeing 429s on checkout — who changed the rate limit on the payments path, and what is it now?**

- **Northwind** → `billing-svc/RetryPolicy.md` **full ✓** (gateway lowered to 60 req/min, reverts 16:00) + `payments/incident-runbook.md` **denied** (Data team owns it).
- **Quanta** → `auth-core/throttle.yaml` **redacted** (30 req/min, security-scoped) + `auth-core/README.md` **full ✓**.
- Synthesis answers who/what-now and surfaces the restricted item as "request access."
- **Hero:** click **Request access** on the throttle card → targeted re-stream → that one card flips **redacted → full ✓** and the answer updates. (Only that card re-streams.)

> Note: this scenario is a **planted** synthetic story (`app/demo.py`) — the real corpora are
> domain-disjoint, so the money moment is seeded for reliability. Everything else is real data.

### 2. Single-hit — one party has it
> **Next.js authentication flow for teachers and students in the Tolus app**  → only **Northwind** answers (real auth chunks); Quanta stays silent.

> **evaluate my Harvard college admissions supplemental essay**  → only **Quanta** answers (real essay chunks); Northwind stays silent.

### 3. No-hit — nobody has it
> **what is the best recipe for chocolate chip cookies**  (or *cheapest flights to Tokyo*) → nodes pulse, **no cards**, answer = *"No party returned a verified answer to this question."* No hallucination.

## What's where

- Backend: `backend/app/` (gate, claude boundary calls, router/orchestrator, retrieval).
- Planted demo scenario: `backend/app/demo.py` (single source of truth; `demo_seed.py` writes it to the gitignored corpora).
- Live client contract: `frontend/src/useRelayQuery.js` (the hook the components consume).
- Walking skeleton: `frontend/src/components/LiveQueryDebug.jsx` (at `?debug`).
- Tuning: `RELAY_MIN_SIM` (floor), `RELAY_TOP_K` (cards per party) — tune in `run.sh` during rehearsal.
