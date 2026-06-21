// NetworkConstellation — the radar/constellation graph: center "You" + responder
// party nodes bound to hand-tuned slots, a beacon glow, curved edges. SVG, fills
// its positioned parent (absolute inset:0), so each cell gives it a sized stage.
import { NetworkConstellation } from 'beacon-frontend'

const nodes = [
  { agentId: 'a1', label: 'Payments Platform', letter: 'P', color: 'var(--active-500)', cards: [{ chunkId: 'c1', decision: 'full', color: 'var(--active-500)' }] },
  { agentId: 'a2', label: 'SRE On-Call', letter: 'S', color: 'var(--warn-500)', cards: [{ chunkId: 'c2', decision: 'redacted', color: 'var(--warn-500)' }] },
  { agentId: 'a3', label: 'Checkout Web', letter: 'C', color: 'var(--warm-mid)', cards: [{ chunkId: 'c3', decision: 'denied', color: 'var(--warm-mid)' }] },
]

// While searching every node/edge uses the live accent (electric blue).
const searchingNodes = nodes.map((n) => ({ ...n, color: 'var(--signal-500)' }))
const noop = () => {}

const Stage = ({ children }: any) => (
  <div style={{ position: 'relative', width: '100%', height: 420, background: 'var(--surface-page)', borderRadius: 12, overflow: 'hidden' }}>
    {children}
  </div>
)

// Results: each party node resolved to its decision color (green/amber/grey).
export const Results = () => (
  <Stage>
    <NetworkConstellation isResults nodes={nodes} subtitle="3 in range" focus={null} onClearFocus={noop} />
  </Stage>
)

// Searching: the signal propagates from You out to each agent.
export const Searching = () => (
  <Stage>
    <NetworkConstellation isSearching nodes={searchingNodes} subtitle="3 in range" focus={null} onClearFocus={noop} />
  </Stage>
)
