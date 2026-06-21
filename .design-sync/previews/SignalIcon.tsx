// SignalIcon — the beacon/broadcast mark used in headers and the prompt lead.
import { SignalIcon } from 'beacon-frontend'

const Tile = ({ children }: any) => (
  <div style={{ display: 'flex', gap: 16, padding: 26, justifyContent: 'center', alignItems: 'center', color: 'var(--signal-600)' }}>{children}</div>
)
const Chip = ({ children }: any) => (
  <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 56, height: 56, borderRadius: 14, background: 'var(--surface-card)', border: '1px solid var(--border-subtle)' }}>{children}</div>
)

export const Sizes = () => (<Tile><Chip><SignalIcon size={30} /></Chip><Chip><SignalIcon size={20} /></Chip></Tile>)
