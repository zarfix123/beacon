// AnswerPanel — the synthesized answer with inline [n] citations, a sources
// popover, and a hand-off action. Anchored top-left; wrapped in a sized stage.
import { AnswerPanel } from 'beacon-frontend'

const provenance = [
  { source_party: 'Payments Platform', source_doc_title: 'payments/rate-limit.yaml', decision: 'full', verified: true, source_agent_id: 'a1', chunk_id: 'c1' },
  { source_party: 'SRE On-Call', source_doc_title: 'incident-4471 runbook', decision: 'redacted', verified: false, source_agent_id: 'a2', chunk_id: 'c2' },
  { source_party: 'Checkout Web', source_doc_title: '', decision: 'denied', verified: false, source_agent_id: 'a3', chunk_id: 'c3' },
]

const cards = [
  { chunkId: 'c1', agentId: 'a1', party: 'Payments Platform', letter: 'P', decision: 'full', answer: 'Lowered the payments-path limit from 1000 to 600 req/min on Jun 18 (commit a3f9c2) to shed load during the checkout incident.', docTitle: 'payments/rate-limit.yaml', verified: true, color: 'var(--active-500)' },
  { chunkId: 'c2', agentId: 'a2', party: 'SRE On-Call', letter: 'S', decision: 'redacted', answer: 'Rollback + paging steps for the 429 incident — access-restricted.', docTitle: 'incident-4471 runbook', verified: false, color: 'var(--warn-500)' },
  { chunkId: 'c3', agentId: 'a3', party: 'Checkout Web', letter: 'C', decision: 'denied', answer: '', docTitle: '', verified: false, color: 'var(--warm-mid)' },
]

const answer = "The 429s trace to a deliberate change: the payments path was lowered from 1000 to 600 req/min on Jun 18 [1]. It shipped during the active checkout incident [2]; the checkout service itself surfaced no relevant config [3]. The current limit on /payments is 600 req/min."

const noop = () => {}

const Stage = ({ children }: any) => (
  <div style={{ position: 'relative', width: 408, maxWidth: '100%', height: 440, margin: '0 auto', background: 'var(--surface-page)', borderRadius: 12, overflow: 'hidden' }}>
    {children}
  </div>
)

export const Default = () => (
  <Stage><AnswerPanel answer={answer} provenance={provenance} cards={cards} onHandoff={noop} /></Stage>
)

export const HandedOff = () => (
  <Stage><AnswerPanel answer={answer} provenance={provenance} cards={cards} handedOff onHandoff={noop} /></Stage>
)
