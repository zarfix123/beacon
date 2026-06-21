// HandoffIcon — "hand off to Claude Code" exchange glyph.
import { HandoffIcon } from 'beacon-frontend'

const Tile = ({ children }: any) => (
  <div style={{ display: 'flex', gap: 16, padding: 26, justifyContent: 'center', alignItems: 'center', color: 'var(--text-primary)' }}>{children}</div>
)
const Chip = ({ children }: any) => (
  <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 56, height: 56, borderRadius: 14, background: 'var(--surface-card)', border: '1px solid var(--border-subtle)' }}>{children}</div>
)

export const Sizes = () => (<Tile><Chip><HandoffIcon size={30} /></Chip><Chip><HandoffIcon size={20} /></Chip></Tile>)
