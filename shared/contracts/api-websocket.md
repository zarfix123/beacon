# Relay — Frozen Contract 3: HTTP + WebSocket API

> **Status: FROZEN (hour 0).** Changing any endpoint, payload, or event requires a 2-minute sync between Dennis (serves) and Hao (renders). Derived from spec sections 6, 10, 12, and 15.

**Server:** Dennis (FastAPI, one service, 3 in-process agent contexts, WebSocket for live events — spec section 7).
**Client:** Hao (React + Tailwind + react-flow). Builds against a **mock JSON fixture matching this contract** so the frontend never waits on the backend (spec section 15).

All payloads are JSON, `snake_case`. Record shapes referenced here are defined in [`data-model.md`](./data-model.md) and are authoritative there. No production auth in the MVP (spec section 5).

Base URL (dev): `http://localhost:8000`. WebSocket: `ws://localhost:8000/ws/query`.

---

## Overview of the flow (maps to spec section 10)

1. Client opens the WebSocket, then sends the query frame (or POSTs `/query` and reads the stream — see "Two transport options" below).
2. Server fans out to the 3 party agents. For each agent it emits an **`agent-activated`** event (the node pulses).
3. As each party's gated chunk resolves, the server emits a **`response-item`** event (one card row).
4. When all parties are done and the synthesized answer is ready, the server emits a single **`done`** event carrying the synthesized answer + provenance.
5. The live grant-access beat: client calls **`POST /grant_access`**, server toggles the chunk's visibility and re-runs, streaming a fresh `agent-activated` → `response-item` → `done` cycle for the same `query_id`.

---

## HTTP endpoints

### 1. `POST /query`

Submit a public engineering question to the network. Kicks off the fan-out. Returns immediately with a `query_id`; live results stream over the WebSocket keyed by that id. (For a no-WebSocket fallback, see "Two transport options.")

**Request**

```http
POST /query
Content-Type: application/json
```

```json
{
  "query": "How do we stop servo jitter under sustained load?",
  "from_agent": "agent_helios"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `query` | `string` | yes | The natural-language question. |
| `from_agent` | `string` | no | Asking agent id (a `Agent.id`). Defaults to a fixed demo "asker" agent if omitted. Mirrors the [Cross-agent request](./data-model.md#3-cross-agent-request) shape. |

**Response** `200 OK`

```json
{
  "query_id": "q_8f3a2c",
  "from_agent": "agent_helios",
  "agents": ["agent_northwind", "agent_quanta"]
}
```

| Field | Type | Notes |
|-------|------|-------|
| `query_id` | `string` | Correlates all WebSocket events for this run. Also used by `grant_access`. |
| `from_agent` | `string` | Echoes the resolved asker id. |
| `agents` | `array<string>` | The party `Agent.id`s being fanned out to (the nodes that will pulse). Lets the frontend pre-render the graph. |

---

### 2. `POST /grant_access`

The one coupled feature (spec section 15 / hero beat 12). Toggles a single chunk's visibility (e.g. `restricted` → `public`), then re-runs the original query so the card animates from locked-grey to full-green with the verified answer.

**Request**

```http
POST /grant_access
Content-Type: application/json
```

```json
{
  "chunk_id": "northwind_c014",
  "query_id": "q_8f3a2c"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `chunk_id` | `string` | yes | The chunk to unlock — the `chunk_id` carried on the `redacted` response item. |
| `query_id` | `string` | yes | The original run to re-execute, so re-run results stream on the same correlation id. |

**Response** `200 OK`

```json
{
  "chunk_id": "northwind_c014",
  "new_visibility": "public",
  "query_id": "q_8f3a2c",
  "rerunning": true
}
```

| Field | Type | Notes |
|-------|------|-------|
| `chunk_id` | `string` | Echoes the toggled chunk. |
| `new_visibility` | `string` (enum) | The chunk's visibility after the toggle: `"public"` \| `"restricted"` \| `"private"`. For the demo this is `"public"`. |
| `query_id` | `string` | The run being re-executed. Fresh `agent-activated` → `response-item` → `done` events stream on this id. |
| `rerunning` | `boolean` | `true` once the re-run has been kicked off. |

---

## WebSocket: `ws://localhost:8000/ws/query`

Every frame is a JSON object with a `type` discriminator and a `query_id` for correlation. The client switches on `type`.

### Two transport options (both supported; pick one, frozen either way)

- **WS-driven (default):** client sends the query as the first WS frame; server replies with the `query_id` acknowledgement then streams events.
- **POST + WS:** client `POST /query`, gets `query_id`, then listens on the WS for events with that id.

Either way the **event shapes below are identical**. The frontend mock fixture is just an ordered list of these event frames.

**Client → server (WS-driven option) — submit frame**

```json
{ "type": "query", "query": "How do we stop servo jitter under sustained load?", "from_agent": "agent_helios" }
```

Server acks with the same body as the `POST /query` response, wrapped as `{ "type": "ack", ... }`.

---

### Event: `agent-activated` (node-pulse)

Emitted once per party agent the instant the orchestrator dispatches the query to it — drives the edge animation + node pulse on the network graph (spec section 12).

**When:** at fan-out, before that agent's search/gate completes; one per agent in the `/query` response's `agents` list. Also re-emitted per agent on a `grant_access` re-run.

```json
{
  "type": "agent-activated",
  "query_id": "q_8f3a2c",
  "agent_id": "agent_northwind",
  "party_name": "Northwind Robotics",
  "status": "searching"
}
```

| Field | Type | Notes |
|-------|------|-------|
| `type` | `string` | Literal `"agent-activated"`. |
| `query_id` | `string` | Correlation id. |
| `agent_id` | `string` | The pulsing node's `Agent.id`. |
| `party_name` | `string` | Display label for the node. |
| `status` | `string` | `"searching"`. (Single MVP value; field reserved so the node can show progress.) |

---

### Event: `response-item`

Emitted once per resolved gated chunk — one response card row per party (spec section 12). Carries the full [Response item](./data-model.md#4-response-item) shape plus the two frontend-wiring identifiers (`chunk_id`, `source_agent_id`) needed for the grant-access button.

**When:** after a party's chunk has passed through retrieve → gate → (redaction for `restricted`, verification for `full`). May arrive in any order across parties; client keys cards by `source_agent_id` (+ `chunk_id`).

```json
{
  "type": "response-item",
  "query_id": "q_8f3a2c",
  "chunk_id": "northwind_c014",
  "source_agent_id": "agent_northwind",
  "answer": "Northwind has a documented fix for servo jitter under load. Request access to view the resolution.",
  "source_party": "Northwind Robotics",
  "source_doc_title": "Servo Jitter Postmortem — Q1",
  "decision": "redacted",
  "verified": false
}
```

| Field | Type | Notes |
|-------|------|-------|
| `type` | `string` | Literal `"response-item"`. |
| `query_id` | `string` | Correlation id. |
| `chunk_id` | `string` | The cited chunk — the handle passed to `grant_access` when `decision == "redacted"`. |
| `source_agent_id` | `string` | The owning `Agent.id` (the chunk's `owner`). Keys the card to a graph node. |
| `answer` | `string` \| `null` | Payload to render. `full` → answer text; `redacted` → one-line gist; `denied` → `null`. (Data-model §4.) |
| `source_party` | `string` | Owning party display name. |
| `source_doc_title` | `string` \| `null` | Clickable citation title; `null` for `denied` items that show nothing. |
| `decision` | `string` (enum) | `"full"` (green) \| `"redacted"` (amber + lock + "Request access") \| `"denied"` (grey). |
| `verified` | `boolean` | `true` → render `verified ✓`; `false` → `unverifiable ✗` or no badge. `false` for `redacted`/`denied` (no content crossed). |

> The five canonical section-8 fields (`answer`, `source_party`, `source_doc_title`, `decision`, `verified`) are exactly as in [data-model.md §4](./data-model.md#4-response-item). `chunk_id` and `source_agent_id` are transport additions for frontend wiring.

---

### Event: `done`

Emitted once when all parties have returned and the asking agent has synthesized the final answer with citations (spec section 10, step 6 / panel in section 12).

**When:** after the last `response-item` for this `query_id`, once verification + synthesis complete. Exactly one per run (and one more per `grant_access` re-run).

```json
{
  "type": "done",
  "query_id": "q_8f3a2c",
  "synthesized_answer": "Servo jitter under sustained load is caused by PID integral windup. The fix is to clamp the integral term and add a ~5ms feed-forward, which eliminates the oscillation.",
  "provenance": [
    {
      "source_party": "Northwind Robotics",
      "source_doc_title": "Servo Tuning Guide",
      "decision": "full",
      "verified": true,
      "source_agent_id": "agent_northwind",
      "chunk_id": "northwind_c014"
    }
  ],
  "item_count": 2
}
```

| Field | Type | Notes |
|-------|------|-------|
| `type` | `string` | Literal `"done"`. |
| `query_id` | `string` | Correlation id. |
| `synthesized_answer` | `string` | Final answer with inline citations, rendered in the left panel. |
| `provenance` | `array<object>` | Per-fact source list for the provenance footer. Each entry is a [Response item](./data-model.md#4-response-item)-shaped object (its five canonical fields) plus `source_agent_id` and `chunk_id`. Typically the `full`/`redacted` items that contributed. |
| `item_count` | `number` | How many `response-item` events were emitted this run (sanity check for the client). |

---

## Decision → UI mapping (reference, spec section 12)

| `decision` | Badge | Card state |
|------------|-------|------------|
| `full` | green "Full" | answer shown, `verified ✓` if `verified`, clickable citation |
| `redacted` | amber "Redacted" | gist greyed + lock icon + **"Request access from [source_party]"** button → `POST /grant_access` with `chunk_id` |
| `denied` | grey "Denied" | existence-only or nothing; no payload, no citation |

---

## Cross-file consistency notes

- `response-item` and each `provenance` entry carry the exact five [Response item](./data-model.md#4-response-item) fields from data-model §4; `chunk_id` and `source_agent_id` are the frontend-wiring additions noted there.
- `decision` and `new_visibility` use the enums from [data-model.md](./data-model.md) (`full`/`redacted`/`denied` and `public`/`restricted`/`private` respectively).
- `agent_id` / `source_agent_id` / `from_agent` values are the `Agent.id`s from [data-model.md §1](./data-model.md#1-agent): `agent_northwind`, `agent_helios`, `agent_quanta`.
- The backend produces response items by mapping the [chunks returned by `search()`](./search-interface.md) through the gate; `embedding` is never serialized into any of these payloads.
