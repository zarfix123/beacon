// AgentsReached — the "Agents reached" list: one expandable row per response card.
// full = green verified · redacted = amber + Request access · denied = grey.
// Anchored top-right; wrapped in a sized stage.
import { AgentsReached } from 'beacon-frontend'

const cards = [
  { chunkId: 'c1', agentId: 'a1', party: 'Payments Platform', letter: 'P', decision: 'full', answer: 'Lowered the payments-path limit from 1000 to 600 req/min on Jun 18 (commit a3f9c2) to shed load during the checkout incident.', docTitle: 'payments/rate-limit.yaml', verified: true, color: 'var(--active-500)' },
  { chunkId: 'c2', agentId: 'a2', party: 'SRE On-Call', letter: 'S', decision: 'redacted', answer: 'Rollback + paging steps for the 429 incident — access-restricted.', docTitle: 'incident-4471 runbook', verified: false, color: 'var(--warn-500)' },
  { chunkId: 'c3', agentId: 'a3', party: 'Checkout Web', letter: 'C', decision: 'denied', answer: '', docTitle: '', verified: false, color: 'var(--warm-mid)' },
]

const reachLine = '1 full · 1 scoped · 1 denied'
const noop = () => {}

// The card has an `opacity: 0 → 1` entrance animation (bc-rise); a static
// screenshot would capture it at opacity 0. Neutralize animations so the card
// paints at its final state.
const Stage = ({ children, h = 380 }: any) => (
  <div style={{ position: 'relative', width: 408, maxWidth: '100%', height: h, margin: '0 auto', background: 'var(--surface-page)', borderRadius: 12, overflow: 'hidden' }}>
    <style>{`*{animation:none!important}`}</style>
    {children}
  </div>
)

// First (full) row expanded → shows the verified reply; redacted row shows the
// Request-access affordance; denied row is muted.
export const Replies = () => (
  <Stage h={420}>
    <AgentsReached cards={cards} reachLine={reachLine} expanded={{ c1: true }} focus={null} onToggle={noop} onRequest={noop} />
  </Stage>
)

export const Collapsed = () => (
  <Stage>
    <AgentsReached cards={cards} reachLine={reachLine} expanded={{}} focus={null} onToggle={noop} onRequest={noop} />
  </Stage>
)
