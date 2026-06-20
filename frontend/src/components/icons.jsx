// Shared inline-SVG icons — 2px stroke, round caps/joins, 24px grid, currentColor.
// Centralizing them keeps the layout components free of raw SVG markup.

export function SignalIcon({ size = 13, stroke = 'currentColor', dot = 2 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r={dot} fill={stroke} stroke="none" />
      <path d="M16.6 7.4a6.5 6.5 0 0 1 0 9.2M7.4 16.6a6.5 6.5 0 0 1 0-9.2" />
    </svg>
  )
}

export function CheckIcon({ size = 12, stroke = 'var(--active-500)' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12.5l4.2 4.2L19 7" />
    </svg>
  )
}

export function LockIcon({ size = 12, stroke = 'var(--signal-600)', width = 2.2 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth={width} strokeLinecap="round" strokeLinejoin="round">
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </svg>
  )
}

export function ChevronIcon({ open }) {
  const stroke = open ? 'var(--text-secondary)' : 'var(--text-muted)'
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d={open ? 'M18 15l-6-6-6 6' : 'M6 9l6 6 6-6'} />
    </svg>
  )
}

export function DocIcon({ size = 12, stroke = 'var(--text-muted)' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 3h11a2 2 0 0 1 2 2v15a1 1 0 0 0-1-1H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" />
      <path d="M6 16h13" />
    </svg>
  )
}

export function ShieldIcon({ size = 11 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />
    </svg>
  )
}

export function ArrowIcon({ size = 17 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  )
}

export function ResetIcon({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
      <path d="M3 4v4h4" />
    </svg>
  )
}

export function HandoffIcon({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 9l-3.5 3L8 15" />
      <path d="M16 9l3.5 3L16 15" />
      <path d="M13.5 6.5l-3 11" />
    </svg>
  )
}
