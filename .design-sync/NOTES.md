# design-sync notes — Beacon

Beacon is a Vite **app** (`frontend/`), not a packaged component library. It is synced
as the `package` shape via a few deliberate workarounds (below). Scope = the reusable
parts only: `PromptPill`, `AnswerPanel`, `AgentsReached`, `NetworkConstellation`, and 10
icons. The live-backend screens `AskTheNetwork` and `LiveQueryDebug` are **intentionally
excluded** (they call `useRelayQuery` → a WebSocket backend).

## Build command (reproducible)

```bash
NODE_OPTIONS=--max-old-space-size=8192 node .ds-sync/package-build.mjs \
  --config .design-sync/config.json --node-modules ./frontend/node_modules \
  --entry frontend/.ds-bundle-entry.jsx --out ./ds-bundle
node .ds-sync/package-validate.mjs ./ds-bundle
```

## Gotchas (why the workarounds exist)

- **Named-export barrel `frontend/.ds-bundle-entry.jsx`** (`--entry`, committed). The
  components are `export default`; the converter's synth-entry uses `export *`, which
  drops default exports, so the IIFE would expose nothing. The barrel re-exports them as
  NAMED so `window.Beacon.<Name>` is populated, and scopes the bundle to the in-scope
  parts. It lives *inside* `frontend/` so the `--entry` walk-up resolves PKG_DIR to
  `frontend/` (its `package.json` name `beacon-frontend`); anywhere else and PKG_DIR
  falls back to `/`.
- **Heap bump required.** ts-morph OOMs (>4 GB) resolving the ~1500-icon
  `@phosphor-icons/react` type graph. Always build with `--max-old-space-size=8192`.
  Also mitigated by `cfg.dtsPropsFor` — hand-written prop bodies for all 14 components
  short-circuit per-component type extraction (and give better contracts than the `any`
  auto-extraction would). **These are hand-maintained**: if a component's props change in
  source, update `dtsPropsFor` (it won't auto-update).
- **`css.mjs` fork** (`.design-sync/overrides/css.mjs`, declared in `cfg.libOverrides`).
  Upstream `copyTokens` only globs tokens inside a tokens *npm package*; Beacon ships
  tokens as plain CSS in `src/styles/tokens/`. The fork makes a package-relative
  `tokensGlob` work with no `tokensPkg` (base = the package dir). Re-reads the real source
  files every build (no rot). On re-sync, diff it against the staged `lib/css.mjs`.
- **`@types/react not found` warning is harmless** — extraction is short-circuited by
  `dtsPropsFor`, so empty-body emission never happens.

## Fonts

`[FONT_REMOTE]` — fonts load at runtime via a Google Fonts `@import` in
`tokens/fonts.css`. The families (Hanken Grotesk / Newsreader / JetBrains Mono) are
**open substitutes** for the real proprietary brand fonts (`HarveySerifFont`,
`HarveySansFont`), which are unavailable — see the note in `frontend/src/styles/tokens/
fonts.css`. Tokens/colors apply offline; the webfonts need network (so headless
screenshots may show fallback text — not a regression).

## Preview specifics

- The four panel components are `position: absolute` overlays; their previews wrap them
  in a `position: relative` sized stage. `NetworkConstellation` fills `inset:0`.
- **AgentsReached** `.card` has an `opacity:0→1` entrance animation (`bc-rise`); a static
  screenshot captures it at opacity 0. The preview injects
  `<style>*{animation:none!important}</style>` so it paints at its final state.
- **AnswerPanel** uses `cardMode: single` — its always-mounted `position: fixed` reader
  slide-over escapes the cell (GRID_OVERFLOW) in column/grid mode.

## Known render warns

None — render check is clean (0 thin, 0 bad).

## Re-sync risks (watch-list)

- **New components**: a component added under `frontend/src/components/` is NOT synced
  unless added to all three of: the barrel, `cfg.componentSrcMap`, and `cfg.dtsPropsFor`.
- **dtsPropsFor / barrel are hand-maintained** — they don't track source prop changes.
- **Brand fonts are substitutes** (proprietary originals absent).
- **The `css.mjs` fork** may drift from upstream — re-diff on re-sync.
- **This run OVERWROTE** a pre-existing, richer "Beacon Design System" project (it held
  Button/Input/Card/Dialog/Tabs/etc. + a `beacon-app` ui_kit, from a *different* source —
  not this repo). Per the user's explicit choice (no backup), that content was replaced by
  this repo's 14 components. The project now reflects `frontend/` only.
