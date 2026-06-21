// Icons — Phosphor, one family + one weight (taste skill §3.C: no hand-rolled SVG).
// Thin wrappers keep call sites stable: `size` + `stroke`→`color`. Legacy props
// (dot, width) are accepted by the caller and harmlessly ignored here.

import {
  Broadcast, Check, Lock, CaretDown, Shield,
  ArrowRight, ArrowClockwise, ArrowsLeftRight, ArrowsOutSimple, X,
} from '@phosphor-icons/react'

const W = 'bold' // single global weight

export function SignalIcon({ size = 13, stroke = 'currentColor' }) {
  return <Broadcast size={size} color={stroke} weight={W} />
}

export function CheckIcon({ size = 12, stroke = 'var(--active-500)' }) {
  return <Check size={size} color={stroke} weight={W} />
}

export function LockIcon({ size = 12, stroke = 'var(--warn-600)' }) {
  return <Lock size={size} color={stroke} weight={W} />
}

export function ChevronIcon({ open }) {
  // One caret that rotates 180° on toggle — smoother than swapping glyphs.
  return (
    <CaretDown
      size={16}
      weight={W}
      color={open ? 'var(--text-secondary)' : 'var(--text-muted)'}
      style={{
        transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
        transition: 'transform 240ms var(--ease-out), color 240ms var(--ease-out)',
      }}
    />
  )
}

export function ShieldIcon({ size = 11 }) {
  return <Shield size={size} color="currentColor" weight={W} />
}

export function ArrowIcon({ size = 17 }) {
  return <ArrowRight size={size} color="currentColor" weight={W} />
}

export function ResetIcon({ size = 13 }) {
  return <ArrowClockwise size={size} color="currentColor" weight={W} />
}

export function HandoffIcon({ size = 15 }) {
  return <ArrowsLeftRight size={size} color="currentColor" weight={W} />
}

export function ExpandIcon({ size = 14, stroke = 'currentColor' }) {
  return <ArrowsOutSimple size={size} color={stroke} weight={W} />
}

export function CloseIcon({ size = 16, stroke = 'currentColor' }) {
  return <X size={size} color={stroke} weight={W} />
}
