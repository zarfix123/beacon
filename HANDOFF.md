# Handoff → Frontend integration

Read this first if you're wiring the Relay UI to the real backend. TL;DR: **the backend and
the live data layer are done. The job is to render the EXISTING components from one hook
(`useRelayQuery`) instead of the `setTimeout`/`mockData.js` mocks.** Don't rebuild visuals,
don't touch the backend.

## What's already built (so you don't redo it)

- **Backend** (`backend/`): the whole pipeline runs — fan-out, gate (full/redacted/denied),
  redaction + verification (Claude), synthesis, grant-access replay, live WebSocket events.
  Endpoints: `POST /query`, `WS /ws/query`, `POST /grant_access`, `GET /agents`, `GET /health`,
  `POST /demo/reset`.
- **Live data layer** (`frontend/src/useRelayQuery.js`): owns the WebSocket, parses the real
  event stream into the shape the components need. **This hook is the contract — consume it.**
- **Working reference** (`frontend/src/components/LiveQueryDebug.jsx`): a barebones client at
  `http://localhost:5173/?debug` that already drives the full flow (query → cards → grant flip)
  off the hook. **Copy its consumption pattern.** This is the proven-correct example.

## The 3 files to read (in order)

1. `frontend/src/useRelayQuery.js` — the hook + its exact output shape (docstring at top).
2. `frontend/src/components/LiveQueryDebug.jsx` — how to consume it, end to end.
3. `shared/contracts/api-websocket.md` — the frozen wire shapes (source of truth). Also
   `DEMO.md` (repo root) for the demo scenarios and run instructions.

## The hook's output (what you render from)

```js
const r = useRelayQuery()
// r.phase        'idle' | 'searching' | 'done'
// r.connected    bool
// r.agents       [{ agent_id, party_name, status }]      // the nodes that lit up
// r.cards        [{ chunk_id, source_agent_id, source_party, decision, answer,
//                   source_doc_title, verified }]        // one per response-item, upserted by chunk_id
// r.answer       string | null                           // synthesized answer
// r.provenance   [{ source_party, source_doc_title, decision, verified, source_agent_id, chunk_id }]
// r.itemCount    number | null
// r.submit(question)        // ask
// r.requestAccess(chunkId)  // grant-access on a redacted card
// r.reset()                 // clear + re-arm demo tiers
```

## Component-by-component swap (the visual files stay yours)

| component | today (mock) | swap to |
|---|---|---|
| `AskTheNetwork.jsx` | `setTimeout` phase machine | `useRelayQuery()`; map `r.phase` → empty/searching/results; `submit`/`reset`/`requestAccess` |
| `AgentsReached.jsx` | 3 hardcoded rows | render dynamic cards from `r.cards` (key by `chunk_id`); keep the decision→visual logic (full=green✓ / redacted=amber+lock+Request / denied=grey) |
| `AnswerPanel.jsx` | hardcoded prose | `r.answer` + `r.provenance` (the `[n]` citations already line up 1:1 with `provenance` order — backend guarantees it) |
| `NetworkConstellation.jsx` | Atlas/Lyra/Vega | map `r.agents` (+ `GET /agents`) → nodes; show real `party_name`; asker = "You" center |
| `PromptPill.jsx` | already clean | wire `onSubmit` → `r.submit(question)` |

## Gotchas (these will bite if you miss them)

- **Party names are Northwind / Helios / Quanta**, not Atlas/Lyra/Vega. Use `party_name` from
  the hook (it comes from `GET /agents` + the `agent-activated` events). The asker is
  `agent_helios` and is NOT a responder — it's "You".
- **Grant-access re-streams ONLY the changed card.** When the user clicks Request access, the
  backend targeted-replays just that party: a fresh `agent-activated → response-item → done`
  for the granted party on the same socket. The hook upserts `cards` by `chunk_id`, so the one
  card flips redacted→full✓ in place. **Animate only the changed card — do NOT treat it as a
  full restart.** `r.provenance` from the new `done` is the source of truth for the answer panel.
- **Handle the empty state.** Some queries return **zero cards** (no-hit) — nodes pulse, no
  cards, `r.answer` = "No party returned a verified answer…". Don't assume cards always exist.
- **No mock parser to reconcile** — build straight to the live hook shape. Cleaner than diffing
  against the old mock.

## How to test it

The backend needs the (gitignored) corpora + an API key, which live on the backend host. Two ways:

1. **Combine on one machine** (the backend host): `cd backend && ./scripts/run.sh` launches
   backend `:8000` + frontend `:5173`. Open `:5173/?debug` to confirm the live pipe works, then
   load `:5173` and check the wired components against it.
2. **Build against the contract first** (no backend locally): wire to the hook's shape +
   `api-websocket.md`; verify live when you combine. The hook + `LiveQueryDebug` define the
   exact shapes, so this is safe.

The three demo scenarios the UI must handle (see `DEMO.md` for exact prompts): multi-hit
(full + redacted + denied, grant flip), single-hit (one party), no-hit (zero cards).

## After you pull

`git pull` gets `useRelayQuery.js`, `LiveQueryDebug.jsx`, this file, and `DEMO.md`. The
existing components are untouched — they're yours to swap. Coordinate to run the combined
stack when you want to see it live.
