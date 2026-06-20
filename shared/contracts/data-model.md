# Relay — Frozen Contract 1: Data Model

> **Status: FROZEN (hour 0).** Changing any shape here requires a 2-minute sync between Dennis (backend) and Hao (retrieval + frontend). Until then, treat these record shapes as untouchable. Derived from spec section 8.

This file is the single source of truth for the four core record shapes. The other two contracts ([`search-interface.md`](./search-interface.md) and [`api-websocket.md`](./api-websocket.md)) reference these shapes and MUST stay consistent with them.

---

## Conventions

- All records are plain JSON objects (Python `dict` on the backend, JSON over the wire to the frontend).
- `snake_case` keys everywhere, on the wire and in code.
- IDs are opaque strings; do not parse them. Format conventions below are for seed-data readability only.
- `embedding` is the only field that never crosses the API/WebSocket boundary — it stays server-side in the index.
- MVP scope (spec section 5): flat index, 3 in-process agents, seeded corpora, no production auth. No nested vectors, no graph.

### Shared enums

| Enum | Field | Allowed values | Meaning |
|------|-------|----------------|---------|
| **Visibility** | `Chunk.visibility` | `"public"` \| `"restricted"` \| `"private"` | The owner's policy tier for a chunk. Set at index time; chunks inherit their parent doc's visibility. Mutable only via `grant_access` (see API contract). |
| **Decision** | `ResponseItem.decision` | `"full"` \| `"redacted"` \| `"denied"` | The gate's per-chunk verdict, produced by mapping visibility through the permission gate at query time. |

**Visibility → Decision mapping (the gate, for reference — defined in backend, not here):**

| `visibility` | `decision` | What crosses the boundary |
|--------------|------------|---------------------------|
| `public` | `full` | pointer + full payload |
| `restricted` | `redacted` | pointer + one-line redacted gist + access-request |
| `private` | `denied` | nothing, or existence-only pointer (no payload) |

---

## 1. Agent

One of the 3 independent parties. Each owns an isolated corpus, a flat index, and a scope policy.

### Fields

| Field | Type | Required | Allowed values / format | Description |
|-------|------|----------|-------------------------|-------------|
| `id` | `string` | yes | opaque; seed convention `"agent_<slug>"` | Stable agent identifier. Used as `agent_id` in `search()` and as `from_agent` in requests. |
| `party_name` | `string` | yes | human-readable | Display name shown on the network graph node and response card header. |
| `scope_policy` | `string` | yes | `"three_tier"` for MVP | Names the policy the gate applies. MVP uses one policy (`public`/`restricted`/`private`). Kept as a field so topology can move per spec section 2 without reshaping the record. |

### JSON example

```json
{
  "id": "agent_northwind",
  "party_name": "Northwind Robotics",
  "scope_policy": "three_tier"
}
```

> The 3 seeded agents (ids locked at hour 0) are: `agent_northwind`, `agent_helios`, `agent_quanta`. Party names are illustrative and may be tuned during seeding without touching this shape.

---

## 2. Chunk (one row in an agent's flat index)

The atomic unit of retrieval. Produced at index time by chunking + embedding seed docs. Chunks inherit their parent doc's `visibility`.

### Fields

| Field | Type | Required | Allowed values / format | Description |
|-------|------|----------|-------------------------|-------------|
| `chunk_id` | `string` | yes | opaque; seed convention `"<agent_slug>_c<NNN>"` | Globally unique chunk identifier. This is the handle `grant_access` toggles. |
| `parent_doc_id` | `string` | yes | opaque; seed convention `"<agent_slug>_d<NN>"` | Identifies the source document the chunk came from. Multiple chunks share one `parent_doc_id`. |
| `doc_title` | `string` | yes | human-readable | Title of the parent document. Surfaced to the frontend as the clickable citation (`ResponseItem.source_doc_title`). Carried on the chunk so retrieval need not join. |
| `owner` | `string` | yes | an `Agent.id` | The owning agent/party. Equals the `agent_id` whose index holds this chunk. Used to populate `ResponseItem.source_party`. |
| `visibility` | `string` (enum) | yes | `"public"` \| `"restricted"` \| `"private"` | Permission tier. Drives the gate decision. Mutable only via `grant_access`. |
| `text` | `string` | yes | the chunk payload | The actual content — one question-plus-resolution for chats, or a 200–500 token slice for docs. Never leaves the owning agent for `restricted`/`private`. |
| `embedding` | `array<number>` | yes (server-side only) | fixed-length float vector; uniform dimension across all agents | Precomputed embedding for cosine top-k. **Server-side only — never serialized over the API/WebSocket boundary.** |
| `score` | `number` | no | `0.0`–`1.0`, present only on search results | Cosine similarity to the query. Added by `search()` on returned rows; absent on stored index rows. See search-interface contract. |

### JSON example (stored index row)

```json
{
  "chunk_id": "northwind_c014",
  "parent_doc_id": "northwind_d03",
  "doc_title": "Servo Jitter Postmortem — Q1",
  "owner": "agent_northwind",
  "visibility": "restricted",
  "text": "Root cause of the servo jitter was a PID integral windup under sustained load; we clamped the integral term and added a 5ms feed-forward. Resolved the oscillation entirely.",
  "embedding": [0.0123, -0.0457, 0.2210, "...384 floats total..."]
}
```

### JSON example (search result row — adds `score`, see search contract)

```json
{
  "chunk_id": "northwind_c014",
  "parent_doc_id": "northwind_d03",
  "doc_title": "Servo Jitter Postmortem — Q1",
  "owner": "agent_northwind",
  "visibility": "restricted",
  "text": "Root cause of the servo jitter was a PID integral windup...",
  "embedding": [0.0123, -0.0457, 0.2210, "...384 floats total..."],
  "score": 0.83
}
```

---

## 3. Cross-agent request

The minimal envelope one agent sends to another (or the orchestrator sends to each party) to ask its index a question. In-process for the MVP (spec section 6).

### Fields

| Field | Type | Required | Allowed values / format | Description |
|-------|------|----------|-------------------------|-------------|
| `from_agent` | `string` | yes | an `Agent.id` | The asking agent's id. The orchestrator lives in the asking agent (spec section 6). |
| `query` | `string` | yes | natural-language question | The engineering question being fanned out to the party agents. |

### JSON example

```json
{
  "from_agent": "agent_helios",
  "query": "How do we stop servo jitter under sustained load?"
}
```

---

## 4. Response item

One party's gated answer for one chunk, after retrieval → gate → (redaction/verification). This is the shape the orchestrator collects and the frontend renders (also emitted as the `response-item` WebSocket event payload — see API contract). The fields here are exactly those in spec section 8, plus identifiers the frontend needs to wire the live grant-access beat.

### Fields

| Field | Type | Required | Allowed values / format | Description |
|-------|------|----------|-------------------------|-------------|
| `answer` | `string` \| `null` | yes | text, or `null` | The payload to display. For `full`: the answer text. For `redacted`: the Claude-generated one-line gist (content does NOT cross the boundary). For `denied`: `null` (or existence-only — payload is hidden regardless). |
| `source_party` | `string` | yes | a `party_name` | The responding party's display name (resolved from the chunk's `owner` agent). |
| `source_doc_title` | `string` \| `null` | yes | text, or `null` | The cited document title (`Chunk.doc_title`). May be `null` for `denied` items that show nothing at all. |
| `decision` | `string` (enum) | yes | `"full"` \| `"redacted"` \| `"denied"` | The gate verdict for this chunk. |
| `verified` | `boolean` | yes | `true` \| `false` | Result of the verification Claude pass: `true` = answer is grounded in its cited source, `false` = unsupported/fabricated. For `redacted`/`denied` (no content crossed), this is `false` (nothing was verified). |

> **Frontend-needed identifiers (carried alongside the section-8 fields):** to wire the "Request access from [Party]" button and the live re-render, each response item also carries `chunk_id` (string, the handle for `grant_access`) and `source_agent_id` (string, the owning `Agent.id`). These are transport conveniences; the five fields above are the canonical section-8 payload. See [`api-websocket.md`](./api-websocket.md) for the exact emitted shape.

### JSON example — `full`

```json
{
  "answer": "Clamp the PID integral term and add a 5ms feed-forward; that eliminates windup-driven oscillation under sustained load.",
  "source_party": "Northwind Robotics",
  "source_doc_title": "Servo Tuning Guide",
  "decision": "full",
  "verified": true
}
```

### JSON example — `redacted`

```json
{
  "answer": "Northwind has a documented fix for servo jitter under load. Request access to view the resolution.",
  "source_party": "Northwind Robotics",
  "source_doc_title": "Servo Jitter Postmortem — Q1",
  "decision": "redacted",
  "verified": false
}
```

### JSON example — `denied`

```json
{
  "answer": null,
  "source_party": "Quanta Systems",
  "source_doc_title": null,
  "decision": "denied",
  "verified": false
}
```

---

## Cross-file consistency notes

- `Chunk.visibility` and `ResponseItem.decision` use the enums in the shared-enums table; no other values are legal.
- `ResponseItem.source_party` is the `party_name` of the agent whose `id == Chunk.owner`.
- `ResponseItem.source_doc_title` equals the `Chunk.doc_title` of the cited chunk.
- The search contract returns lists of **Chunk** rows (with `score`); the API contract emits **Response item** payloads. The gate is the transform between the two and lives entirely in the backend.
