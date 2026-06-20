// Demo fixture for the "Ask the Network" screen.
// These mirror the design's hardcoded demo. Later, agent rows + the synthesized
// answer come from the backend WebSocket events (see README / api-websocket.md).

// Design "props" (knobs). Easy to lift to real props/settings later.
export const CONFIG = {
  liveAccent: '#b9802f',   // beacon amber, used while searching
  showLatency: true,
  scope: 'team',           // me | team | org  (prompt-pill chip)
  autoExpandAgents: false, // default open-state of agent rows
}

// Decision → color. While searching, every edge/node uses the accent instead.
export const DECISION_COLORS = {
  full: '#3f7d57',     // green
  redacted: '#b9802f', // amber
  denied: '#8f8b85',   // grey
  idle: '#cfccc7',     // empty state
}

// Lightweight labels shared by the constellation nodes and the agent rows.
export const AGENTS = {
  atlas: { letter: 'A', name: 'Atlas', repo: 'billing-svc' },
  lyra: { letter: 'L', name: 'Lyra', repo: 'auth-core' },
  vega: { letter: 'V', name: 'Vega', repo: 'data-pipeline' },
}

export const DEFAULT_QUESTION =
  "We're seeing 429s on checkout — who changed the rate limit on the payments path, and what is it now?"
