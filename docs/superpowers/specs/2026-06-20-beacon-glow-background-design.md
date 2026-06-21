# Beacon Glow — Background Redesign

**Date:** 2026-06-20
**Component:** `frontend/src/components/NetworkConstellation.jsx` (+ module CSS), `frontend/src/components/AskTheNetwork.jsx`
**Status:** Approved, ready for implementation plan

## Problem

The constellation background currently has two layers behind the You + 3-agent graph:

- **`DOTS`** — 83 hand-placed cool-grey dots meant to imply a large reachable network (the "1,248 agents" scale cue), dimmed to opacity 0.45.
- **`RINGS`** — 4 static concentric radar rings centered on You.

Issues (all confirmed by the user): the dots read as **busy/noisy**, their positions are **visibly random/arbitrary**, the concentric rings feel like **generic stock network-viz**, and the overall desire is for something **cleaner**. The mock is also being changed from a **1,248-agent** network to a **3-agent** one, which removes the entire justification for a density/scale background.

## Solution: Beacon Glow (resting) + outward pulse (search)

Replace both layers with a single soft radial light bloom centered on **You** — the light a beacon casts. This swaps the metaphor from *radar range* (generic) to *emitted signal* (literally what Beacon is). Calm and atmospheric at rest; when a query searches, the glow intensifies and concentric pulse-rings radiate outward from You and wash over the agents.

### Behavior

- **At rest:** a faint, mostly-neutral luminous bloom on the ivory ground, with a hint of the `--signal` accent. A very slow, low-amplitude breathe keeps it subtly alive.
- **While searching:** the glow intensifies and shifts more clearly toward `--signal-500`; 2–3 concentric pulse-rings radiate outward from You and fade as they expand (a radar "ping" leaving the source). These coexist with the existing edge-flow signal lights and per-node arrival halos, completing a **depart → travel → arrive** story.

## Changes by file

### `frontend/src/components/NetworkConstellation.jsx`
- **Remove** the `DOTS` array (lines ~10–40) and its `<g opacity="0.45">` dot-render layer.
- **Remove** the `RINGS` array (lines ~42–44) and its concentric-ring `<g>`.
- **Add (defs):** `radialGradient#beaconGlow` centered on You.
- **Add (resting layer):** one `<circle cx="320" cy="235" r≈260 fill="url(#beaconGlow)" className={s.glow}>`, rendered **before** the `.scene` group so the bloom stays stable while the scene zooms into a focused node. Radius/stops chosen so it bathes You and softly reaches all three agents (~150–165px from center) while fading to transparent before the panel edges. The `s.glow` element receives an extra searching modifier (class or inline) when `isSearching`.
- **Add (search layer):** inside the existing `isSearching` block, 2–3 concentric `<circle cx="320" cy="235" className={s.pulse}>` rings with staggered `animationDelay`.
- **Edit:** `1,248 in range` → `3 in range` (line ~152).

### `frontend/src/components/NetworkConstellation.module.css`
- `.glow` — slow, low-amplitude idle breathe (`@keyframes bc-breathe`, opacity only); intensity increased while searching.
- `.pulse` + `@keyframes bc-pulse` — expand (animate `r`) from ~the You node radius outward, fading opacity to 0; thin stroke in the signal accent with a soft glow.
- Keyframes co-located in this module file (CSS Modules scopes animation names — consistent with the existing `bc-flow` / `bc-halo` pattern).

### `frontend/src/components/AskTheNetwork.jsx`
- **Edit:** `1,248 agents reachable` → `3 agents reachable` (line ~102).

## Kept untouched

Metallic nodes (`MetalNode`), curved edges + edge-flow signal animation (`.flow`), per-node arrival halos (`.halo`), focus-zoom transform, and all labels. The global `prefers-reduced-motion` guard in `ask-network.css` already neutralizes the new animations; the resting glow remains as a static gradient under reduced motion.

## Tint (tuned during build)

Resting bloom: faint cool/luminous wash, mostly neutral against ivory (`#f8f9fb`) with a hint of `--signal`. Searching: shift core toward `--signal-500` and raise opacity. Exact gradient stops are a build-time tuning detail, not a spec commitment.

## Verification

- Idle: dots and rings gone; a calm centered glow is visible; only 3 agents implied, counts read "3".
- Search: glow intensifies and pulse-rings radiate outward from You and reach the agents; edge-flow and arrival halos still play.
- Focus-zoom into a node: the resting glow stays stable (does not zoom with the scene).
- `prefers-reduced-motion`: no breathe/pulse motion; static glow remains.
- No remaining occurrences of `1,248` / `1248` in `frontend/src`.

## Out of scope

Directions A (nothing), C-alone, and D (structural field) from brainstorming. No changes to node count/positions, edges, panels, or state machine beyond the count-text edits.
