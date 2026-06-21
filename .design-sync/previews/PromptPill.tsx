// PromptPill — the always-present question dock (input + scope chip + ask button).
// It positions itself absolute/bottom, so each cell wraps it in a sized stage.
import { PromptPill } from 'beacon-frontend'

const Q = "We're seeing 429s on checkout. Who changed the rate limit on the payments path, and what is it now?"
const noop = () => {}

const Stage = ({ children }: any) => (
  <div style={{ position: 'relative', width: '100%', height: 132, background: 'var(--surface-page)', borderRadius: 12, overflow: 'hidden' }}>
    {children}
  </div>
)

export const Default = () => (
  <Stage><PromptPill question={Q} scopeLabel="team" onQ={noop} onKey={noop} onSubmit={noop} /></Stage>
)

export const Searching = () => (
  <Stage><PromptPill question={Q} scopeLabel="team" isSearching onQ={noop} onKey={noop} onSubmit={noop} /></Stage>
)

export const Empty = () => (
  <Stage><PromptPill question="" scopeLabel="org" onQ={noop} onKey={noop} onSubmit={noop} /></Stage>
)
