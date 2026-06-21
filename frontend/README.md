# Beacon — Frontend (`Ask the Network`)

The Beacon / Beacon query UI: ask the network an engineering question, watch the
party agents light up, and read a synthesized, attributed, permission-gated answer.

This is a faithful React port of the `Ask the Network` design (Claude Design project
`Engineering query synthesis interface`), built with the Beacon design system tokens.

## Run

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # production build (also a compile/lint check)
```

## What it does

A single full-viewport screen with an `empty → searching → results` flow:

- **Network constellation** — center "You" + three party agents (Atlas / Lyra / Vega)
  over a radar of reachable agents. Nodes pulse and packets travel while searching.
- **Synthesized answer** (top-left) — the cited answer + a per-source provenance list,
  plus a "Hand off to Claude Code" action.
- **Agents reached** (top-right) — one expandable row per party with its decision:
  `full` (green / verified), `redacted` (amber + **Request access**), `denied` (grey).
- **Grant-access beat** — "Request access" on Lyra resolves the redacted card to a full,
  verified answer (the demo's hero moment).

## Structure

```
src/
  components/   AskTheNetwork (state machine) + NetworkConstellation, AnswerPanel,
                AgentsReached, PromptPill, mockData
  styles/       tokens/ (Beacon design-system tokens, verbatim) + ask-network.css
```

## Status & next step (backend wiring)

Today the flow is driven by `setTimeout` mocks inside `AskTheNetwork.jsx` and the demo
content is hardcoded (`mockData.js` + the panels). To go live, swap the mocks for a
WebSocket client per `../shared/contracts/api-websocket.md`:

- `agent-activated` → node pulse · `response-item` → an agent row + decision badge ·
  `done` → the synthesized-answer panel.
- "Request access" → `POST /grant_access { chunk_id, query_id }`; the replay re-streams on
  the same `query_id` and flips Lyra grey → green.
- Design agents Atlas / Lyra / Vega map to backend `agent_northwind / helios / quanta`;
  the `full / redacted / denied` decisions already match the contract enum.
