// ChevronIcon — a single caret that rotates 180° on toggle (row expand/collapse).
import { ChevronIcon } from 'beacon-frontend'

const Tile = ({ children }: any) => (
  <div style={{ display: 'flex', gap: 16, padding: 26, justifyContent: 'center', alignItems: 'center' }}>{children}</div>
)
const Chip = ({ children }: any) => (
  <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 56, height: 56, borderRadius: 14, background: 'var(--surface-card)', border: '1px solid var(--border-subtle)' }}>{children}</div>
)

export const Closed = () => (<Tile><Chip><ChevronIcon open={false} /></Chip></Tile>)
export const Open = () => (<Tile><Chip><ChevronIcon open={true} /></Chip></Tile>)
