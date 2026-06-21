# Beacon Glow Background Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the constellation's 83 random background dots + 4 static radar rings with a single soft "beacon glow" bloom cast from You — calm at rest, intensifying with outward pulse-rings while searching — and change the network counts from 1,248 to 3.

**Architecture:** All changes live in the existing `NetworkConstellation` SVG component and its CSS Module, plus a one-line count edit in `AskTheNetwork`. The glow is a `radialGradient`-filled circle rendered *outside* the zoomable `.scene` group so it stays stable during focus-zoom; its overall intensity is driven by the circle's `opacity` (a CSS-class modifier when searching) while the gradient defines hue/shape. Search-state pulse-rings are SVG circles whose `r` and `opacity` animate via co-located keyframes, mirroring the existing `.flow`/`.halo` animation pattern.

**Tech Stack:** React 19, Vite 5, CSS Modules. No new dependencies. No test runner exists in this project — verification is by structural grep, `npm run build`, and visual observation via `npm run dev`.

## Global Constraints

- React 19 + CSS Modules; **no new dependencies** (package.json deps stay: react, react-dom, @phosphor-icons/react).
- Animation `@keyframes` MUST be co-located in the `*.module.css` that references them (CSS Modules scopes animation names — global keyframes won't resolve). Existing names in `NetworkConstellation.module.css`: `bc-flow`, `bc-halo`.
- Single accent only: the Beacon "signal" color comes from the `accent` prop (default `var(--signal-500)`); do not introduce other hues.
- Light theme on ivory ground (`--ivory` `#f8f9fb`). Glow must fade to fully transparent at its edge.
- The global `prefers-reduced-motion` guard (in `frontend/src/styles/ask-network.css`) already neutralizes animation; new animations must degrade to a static, still-visible glow (no motion) under reduced motion — achieved by animating `opacity`/`r` only.
- Verify each task with: `cd frontend && npm run build` (must succeed) plus the task's grep checks. Visual checks via `cd frontend && npm run dev`.

---

### Task 1: Strip the old background (dots + rings) and fix the counts

**Files:**
- Modify: `frontend/src/components/NetworkConstellation.jsx` (remove `DOTS` const + dot layer; remove `RINGS` const + ring layer; edit count text)
- Modify: `frontend/src/components/AskTheNetwork.jsx:102` (edit count text)

**Interfaces:**
- Consumes: nothing new.
- Produces: a constellation with an empty background (clean ivory behind the graph) and counts reading "3". Tasks 2–3 add the glow back into the now-empty background.

- [ ] **Step 1: Remove the `DOTS` constant and its leading comment**

In `frontend/src/components/NetworkConstellation.jsx`, delete the comment line and the entire `DOTS` array (the block currently spanning the `// Background "reachable agents":` comment through the closing `]` — lines ~10–40):

```jsx
// Background "reachable agents": [cx, cy, r, fillOpacity]. All fill #b9bdc4 (cool grey).
const DOTS = [
  [394.3, 283.4, 2.5, 0.35], [426, 131.2, 1.7, 0.75], [424, 308.5, 2.8, 0.73],
  // ... all rows ...
  [403.3, 330, 1.7, 0.7],
]
```

Delete the whole thing (comment + `const DOTS = [` … `]`).

- [ ] **Step 2: Remove the `RINGS` constant**

In the same file, delete (lines ~42–44):

```jsx
const RINGS = [
  [72, 0.8], [124, 0.6], [178, 0.45], [232, 0.3],
]
```

- [ ] **Step 3: Remove the ring + dot render layers**

In the same file, delete both render blocks inside the `<g className={s.scene}>` group:

```jsx
        {/* radar rings */}
        {RINGS.map(([r, op], i) => (
          <circle key={i} cx="320" cy="235" r={r} fill="none" stroke="var(--border-default)" strokeOpacity={op} />
        ))}

        {/* background network — dimmed so the three real nodes dominate */}
        <g opacity="0.45">
          {DOTS.map(([cx, cy, r, op], i) => (
            <circle key={i} cx={cx} cy={cy} r={r} fill="#b9bdc4" fillOpacity={op} />
          ))}
        </g>
```

Leave a single blank line where they were; the next element (`{EDGES.map(...)}` curved edges) stays.

- [ ] **Step 4: Change the center count text**

In the same file, edit the line currently reading:

```jsx
        <text x="320" y="291" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="9.5" fill="var(--text-muted)">1,248 in range</text>
```

to:

```jsx
        <text x="320" y="291" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="9.5" fill="var(--text-muted)">3 in range</text>
```

- [ ] **Step 5: Change the topbar count text**

In `frontend/src/components/AskTheNetwork.jsx`, edit the line currently reading:

```jsx
          <span className={s.statusCount}>1,248 agents reachable</span>
```

to:

```jsx
          <span className={s.statusCount}>3 agents reachable</span>
```

- [ ] **Step 6: Verify removals and counts via grep**

Run: `cd frontend && grep -rn "DOTS\|RINGS\|#b9bdc4\|1,248\|1248" src/`
Expected: **no output** (all gone).

- [ ] **Step 7: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors (no references to removed `DOTS`/`RINGS`).

- [ ] **Step 8: Visual check**

Run: `cd frontend && npm run dev`, open the app.
Expected: the scattered grey dots and concentric rings are gone; You + 3 agents sit on clean ivory; the center reads "3 in range" and the topbar reads "3 agents reachable". (Background looks bare — the glow comes next.)

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/NetworkConstellation.jsx frontend/src/components/AskTheNetwork.jsx
git commit -m "feat(constellation): remove random dots + rings, set counts to 3"
```

---

### Task 2: Add the resting beacon glow

**Files:**
- Modify: `frontend/src/components/NetworkConstellation.jsx` (add `radialGradient#beaconGlow` to `<defs>`; add glow `<circle>` before the `.scene` group)
- Modify: `frontend/src/components/NetworkConstellation.module.css` (add `.glow` + `bc-breathe` keyframe)

**Interfaces:**
- Consumes: the empty background from Task 1; the existing `<defs>` block and the `s` CSS-module import.
- Produces: a `radialGradient` with `id="beaconGlow"` and a `.glow` circle centered at (320, 235). Task 3 adds a `.glowSearching` modifier class consumed by the same circle's `className`.

- [ ] **Step 1: Add the beacon-glow gradient to `<defs>`**

In `frontend/src/components/NetworkConstellation.jsx`, inside the `<defs>` block, after the `metalRim` `<linearGradient>` (just before `</defs>`), add:

```jsx
          {/* beacon glow: a soft signal-tinted bloom cast from You, fading to ivory */}
          <radialGradient id="beaconGlow" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0%" stopColor="var(--signal-500)" stopOpacity="0.18" />
            <stop offset="35%" stopColor="var(--signal-500)" stopOpacity="0.09" />
            <stop offset="100%" stopColor="var(--signal-500)" stopOpacity="0" />
          </radialGradient>
```

- [ ] **Step 2: Add the resting glow circle outside `.scene`**

In the same file, between `</defs>` and the `<g className={s.scene} style={sceneStyle}>` line, add the glow circle (rendered first, and outside the zoom group so it stays put during focus-zoom):

```jsx
        {/* resting beacon glow — outside .scene so it stays stable while the graph zooms */}
        <circle cx="320" cy="235" r="260" fill="url(#beaconGlow)" className={s.glow} />

```

- [ ] **Step 3: Add `.glow` + `bc-breathe` to the CSS module**

In `frontend/src/components/NetworkConstellation.module.css`, append:

```css
/* resting beacon glow: a calm centered bloom that breathes slowly.
   opacity-only animation so it degrades to a still, visible glow under reduced motion */
.glow {
  opacity: 0.5;
  animation: bc-breathe 6s ease-in-out infinite;
}

@keyframes bc-breathe { 0%, 100% { opacity: .42 } 50% { opacity: .6 } }
```

- [ ] **Step 4: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Visual check (idle + zoom stability)**

Run: `cd frontend && npm run dev`, open the app.
Expected:
- A calm, soft blue-tinted bloom is centered on You and gently breathes; it fades out before the edges.
- Click an agent row (or node) to focus-zoom: the graph zooms but **the glow stays put** (it is outside `.scene`).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/NetworkConstellation.jsx frontend/src/components/NetworkConstellation.module.css
git commit -m "feat(constellation): add resting beacon glow"
```

---

### Task 3: Add search-state intensify + outward pulse rings

**Files:**
- Modify: `frontend/src/components/NetworkConstellation.jsx` (add `glowSearching` modifier to the glow circle's `className`; add pulse-ring circles inside the existing `isSearching` block)
- Modify: `frontend/src/components/NetworkConstellation.module.css` (add `.glowSearching`, `.pulse`, and `bc-breathe-on` + `bc-pulse` keyframes)

**Interfaces:**
- Consumes: the `.glow` circle and `radialGradient#beaconGlow` from Task 2; the existing `isSearching` prop and `accent` prop; the existing `isSearching && ( <> … </> )` fragment.
- Produces: final search-state visuals. No further tasks depend on this.

- [ ] **Step 1: Make the glow intensify while searching**

In `frontend/src/components/NetworkConstellation.jsx`, change the glow circle added in Task 2 from:

```jsx
        <circle cx="320" cy="235" r="260" fill="url(#beaconGlow)" className={s.glow} />
```

to:

```jsx
        <circle cx="320" cy="235" r="260" fill="url(#beaconGlow)" className={isSearching ? `${s.glow} ${s.glowSearching}` : s.glow} />
```

- [ ] **Step 2: Add pulse-ring circles inside the `isSearching` block**

In the same file, inside the `isSearching && ( <> … </> )` fragment, add the pulse rings as the **first** children (before the `{EDGES.map(...)}` flow paths), so they emanate from behind You:

```jsx
            {/* signal ping: rings of light radiate outward from You as the query propagates */}
            {[0, 1, 2].map((i) => (
              <circle
                key={`pulse-${i}`}
                cx="320"
                cy="235"
                r="22"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                className={s.pulse}
                style={{ color: accent, animationDelay: `${i * 0.9}s` }}
              />
            ))}
```

- [ ] **Step 3: Add `.glowSearching`, `.pulse`, and keyframes to the CSS module**

In `frontend/src/components/NetworkConstellation.module.css`, append:

```css
/* searching: the bloom swells brighter (defined after .glow so it wins the cascade) */
.glowSearching { animation: bc-breathe-on 1.9s ease-in-out infinite; }
@keyframes bc-breathe-on { 0%, 100% { opacity: .8 } 50% { opacity: 1 } }

/* a ring of signal light expands outward from You and dissipates */
.pulse {
  filter: drop-shadow(0 0 4px currentColor);
  animation: bc-pulse 2.7s ease-out infinite;
}
@keyframes bc-pulse {
  0%   { r: 22px; opacity: 0 }
  15%  { opacity: .55 }
  100% { r: 200px; opacity: 0 }
}
```

- [ ] **Step 4: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Visual check (search state)**

Run: `cd frontend && npm run dev`, open the app, submit a question (or use the prompt) to enter the searching state.
Expected:
- The central glow visibly brightens.
- Three staggered rings of signal-blue light expand outward from You and fade as they grow, washing past the agent nodes (~150–165px out).
- The existing edge-flow lights and per-node arrival halos still play.
- On results/reset, the glow settles back to its calm resting breathe and the rings stop.

- [ ] **Step 6: Reduced-motion check**

In the browser/OS, enable "reduce motion" (or DevTools → Rendering → Emulate `prefers-reduced-motion: reduce`) and reload.
Expected: no breathing or pulsing motion; the glow remains visible as a still bloom; no rings animate.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/NetworkConstellation.jsx frontend/src/components/NetworkConstellation.module.css
git commit -m "feat(constellation): intensify glow + outward pulse rings while searching"
```

---

## Self-Review

**Spec coverage:**
- Remove `DOTS` + dot layer → Task 1, Steps 1, 3 ✓
- Remove `RINGS` + ring layer → Task 1, Steps 2, 3 ✓
- Counts 1,248 → 3 (both files) → Task 1, Steps 4–5 ✓
- `radialGradient#beaconGlow` in defs → Task 2, Step 1 ✓
- Resting glow circle before `.scene`, stable on zoom → Task 2, Steps 2, 5 ✓
- `.glow` idle breathe → Task 2, Step 3 ✓
- Searching intensify → Task 3, Steps 1, 3 ✓
- 2–3 outward pulse rings in `isSearching` block → Task 3, Steps 2, 3 ✓
- Coexist with edge-flow + arrival halos (kept untouched) → Task 3, Step 5 ✓
- `prefers-reduced-motion` degrades to static glow → Task 3, Step 6 ✓
- No `1,248`/`1248` remain → Task 1, Step 6 ✓

**Placeholder scan:** No TBD/TODO; every code step shows complete JSX/CSS. ✓

**Type/name consistency:** Gradient `id="beaconGlow"` referenced as `url(#beaconGlow)` (Task 2). CSS classes `s.glow` (Task 2) and `s.glowSearching` (Task 3) match the `.glow`/`.glowSearching` rules. `s.pulse` matches `.pulse`. Keyframes `bc-breathe`, `bc-breathe-on`, `bc-pulse` each defined in the same module that references them. `accent` prop and `isSearching` prop already exist on the component signature. ✓
