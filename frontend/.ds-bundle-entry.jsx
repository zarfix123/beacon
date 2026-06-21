// design-sync bundle entry (a named-export barrel) — lives in the package root so
// the converter's --entry walk-up resolves PKG_DIR to frontend/ (package.json name
// "beacon-frontend").
//
// Beacon's components are `export default`, which the converter's synth-entry
// (`export * from <file>`) cannot surface into window.Beacon.<Name>. This barrel
// re-exports them as NAMED exports so the IIFE bundle exposes each component, and
// scopes the bundle to the reusable parts only (the live-backend screens
// AskTheNetwork / LiveQueryDebug are intentionally excluded).
//
// Repo source under src/ is untouched. Passed via `--entry frontend/.ds-bundle-entry.jsx`.

export { default as PromptPill } from './src/components/PromptPill.jsx'
export { default as AnswerPanel } from './src/components/AnswerPanel.jsx'
export { default as AgentsReached } from './src/components/AgentsReached.jsx'
export { default as NetworkConstellation } from './src/components/NetworkConstellation.jsx'

// Icon primitives (already named exports).
export * from './src/components/icons.jsx'
