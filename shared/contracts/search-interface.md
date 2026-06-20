# Relay — Frozen Contract 2: `search()` Interface

> **Status: FROZEN (hour 0).** Changing this signature or the returned shape requires a 2-minute sync between Hao (implements) and Dennis (consumes / stubs). Derived from spec sections 9 and 15.

**Owner of the implementation:** Hao (retrieval substrate).
**Consumer:** Dennis (backend gate + orchestrator). Dennis builds against the keyword **stub** below until Hao's real retrieval lands at checkpoint H8, then swaps it in with zero call-site changes.

The contract is: `search` takes a query and an agent id, runs cosine top-k over **that one agent's** flat index, and returns a list of [Chunk](./data-model.md#2-chunk-one-row-in-an-agents-flat-index) rows ordered by descending relevance. **Retrieval happens here; the gate does NOT.** Per spec section 9: *retrieve first, gate second.* `search` returns chunks of every visibility tier — filtering/redaction is the backend's job downstream.

---

## Signature

```python
from typing import TypedDict, Literal, Optional

Visibility = Literal["public", "restricted", "private"]


class Chunk(TypedDict):
    """One row returned from search. Matches data-model.md §2.

    `embedding` is included because it lives on the index row, but the
    backend never serializes it past the gate. `score` is added by search
    on returned rows and is absent on stored rows.
    """
    chunk_id: str
    parent_doc_id: str
    doc_title: str
    owner: str            # an Agent.id; equals the searched agent_id
    visibility: Visibility
    text: str
    embedding: list[float]
    score: float          # cosine similarity to query, 0.0–1.0


def search(
    query: str,
    agent_id: str,
    top_k: int = 5,
) -> list[Chunk]:
    """Return the top-k most relevant chunks from a single agent's index.

    Args:
        query:    Natural-language query string. Embedded with the same model
                  used to embed the corpus at index time.
        agent_id: Which agent's isolated index to search. MUST be one of the
                  3 seeded agent ids. Searching one agent never reads another's
                  index (isolation = real separate parties, spec §6).
        top_k:    Max number of chunks to return. Default 5. See top-k behavior.

    Returns:
        A list of Chunk dicts (see schema above), ordered by descending
        `score` (cosine similarity). Length is between 0 and top_k.
        Every returned chunk has `owner == agent_id`. Chunks of ALL
        visibility tiers are returned — gating is done downstream by the
        backend, NOT here.

    Raises:
        KeyError: if agent_id is not a known seeded agent.
    """
    ...
```

> If the team prefers cleaner type hints, `Chunk` may be a `@dataclass` or a Pydantic model with identical fields — but the **wire/dict shape and key names are frozen** by [`data-model.md`](./data-model.md). Treat dict access as the contract.

---

## Parameter semantics

| Parameter | Semantics |
|-----------|-----------|
| `query` | The natural-language question. The orchestrator passes the user's question (or a per-agent reformulation) verbatim. Embedded at call time with the corpus embedding model so dimensions match `Chunk.embedding`. |
| `agent_id` | Selects exactly one agent's flat index. Real retrieval keys an in-memory index dict by this id. The stub keys its seeded fixtures by this id. **Isolation is enforced here:** results contain only chunks owned by `agent_id`. |
| `top_k` | Upper bound on returned chunks. Default `5`. The orchestrator may pass a smaller `top_k` to keep verification latency low (spec section 17). |

---

## Returned chunk shape

Each element is a `Chunk` exactly as defined in [data-model.md §2](./data-model.md#2-chunk-one-row-in-an-agents-flat-index), with the result-only `score` field present:

```json
{
  "chunk_id": "northwind_c014",
  "parent_doc_id": "northwind_d03",
  "doc_title": "Servo Jitter Postmortem — Q1",
  "owner": "agent_northwind",
  "visibility": "restricted",
  "text": "Root cause of the servo jitter was a PID integral windup under sustained load; we clamped the integral term and added a 5ms feed-forward.",
  "embedding": [0.0123, -0.0457, 0.2210, "...384 floats..."],
  "score": 0.83
}
```

Guarantees on every returned row:

- `owner == agent_id` (isolation).
- `visibility` is one of `public` / `restricted` / `private` — **unfiltered**; all tiers may appear.
- `score` is present and in `[0.0, 1.0]`.
- `embedding` is present (the backend ignores it past the gate; it is never sent to the frontend).

---

## Top-k behavior

- Returns **at most `top_k`** chunks, **ordered by descending `score`** (most relevant first).
- If the agent's index holds fewer than `top_k` chunks, returns all of them (still sorted).
- If nothing clears retrieval (empty index, or — implementation's choice — a minimum-score floor), returns `[]`. The backend treats an empty list as "this party had no relevant hit" (no response card, or a "no match" card — frontend's call).
- Ties broken arbitrarily but deterministically (stable sort on `score`). The MVP does not require a defined tiebreak beyond stability.
- No deduplication by `parent_doc_id` in the MVP: two chunks from the same doc may both appear. Small-to-big parent rollup is explicitly out of scope unless retrieval underperforms (spec section 9).

---

## Keyword STUB behavior (backend uses until real retrieval lands)

Dennis ships this stub on day one so the gate and orchestrator are never blocked on retrieval (spec section 15). It satisfies the exact signature and returns the exact `Chunk` shape, so swapping in Hao's real `search` at H8 is a drop-in replacement.

**Stub algorithm (deterministic, no embeddings):**

1. Load the seeded chunks for `agent_id` from a local fixture (the same seed corpus, JSON form, minus real vectors).
2. Lowercase and tokenize both `query` and each chunk's `text` (+ `doc_title`) on non-alphanumeric boundaries.
3. Score each chunk by keyword overlap — count of distinct query tokens present in the chunk, normalized to `[0.0, 1.0]` by dividing by the number of distinct query tokens. This becomes the chunk's `score`.
4. Drop chunks with `score == 0.0` (no keyword hit).
5. Sort by descending `score`, return the first `top_k`.

**Stub guarantees / notes:**

- Same return type and key names as real `search`, including `score`.
- `embedding` in the stub fixture may be a placeholder (`[]` or omitted-then-backfilled). The backend never reads `embedding`, so this is safe; real retrieval populates it for real.
- Stub `score` is keyword-overlap, not cosine — values are directionally sensible (higher = more query words matched) but not comparable to real cosine scores. Do not tune thresholds against stub scores.
- Deterministic for a given (query, agent_id, fixture): same input → same output, which keeps the demo query reproducible during backend development.
- The stub MUST return chunks of mixed visibility for the locked demo query — including at least one `restricted` chunk on one party — so the gate, redaction, and the live grant-access beat are all exercisable before real retrieval lands.

---

## Cross-file consistency notes

- The returned `Chunk` is the [data-model §2](./data-model.md#2-chunk-one-row-in-an-agents-flat-index) shape; `score` is the only result-only addition.
- `search` is **gate-free**. The mapping from `Chunk.visibility` to `ResponseItem.decision` happens in the backend gate, not here — consistent with [data-model.md](./data-model.md) and [api-websocket.md](./api-websocket.md).
- `agent_id` values are the `Agent.id`s defined in [data-model.md §1](./data-model.md#1-agent): `agent_northwind`, `agent_helios`, `agent_quanta`.
