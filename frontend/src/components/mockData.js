// Demo fixture for the "Ask the Network" screen.
// These mirror the design's hardcoded demo. Later, agent rows + the synthesized
// answer come from the backend WebSocket events (see README / api-websocket.md).

// Design "props" (knobs). Easy to lift to real props/settings later.
export const CONFIG = {
  liveAccent: 'var(--signal-500)', // beacon signal (electric blue), used while searching
  scope: 'team',           // me | team | org  (prompt-pill chip)
}

// Decision → color (CSS vars so they track the token system). While searching,
// every edge/node uses the accent instead.
export const DECISION_COLORS = {
  full: 'var(--active-500)',   // green
  redacted: 'var(--warn-500)', // amber
  denied: 'var(--warm-mid)',   // grey
  idle: 'var(--stone-300)',    // empty state
}

export const DEFAULT_QUESTION =
  "We're seeing 429s on checkout. Who changed the rate limit on the payments path, and what is it now?"
