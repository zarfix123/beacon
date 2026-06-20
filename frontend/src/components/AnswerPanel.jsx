// Top-left: the synthesized answer with inline numbered citations, a per-source
// provenance list, and the "Hand off to Claude Code" action. Appears in the results phase.

const NBSP = ' '

// numbered citation chip rendered inline in the prose / sources list
function NumChip({ children, variant = 'ink' }) {
  if (variant === 'ink') {
    return (
      <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', minWidth: 15, height: 15, padding: '0 3px', borderRadius: 4, background: 'var(--ink)', color: 'var(--ivory)', fontFamily: 'var(--font-mono)', fontSize: 9.5, verticalAlign: '3px', margin: '0 1px' }}>{children}</span>
    )
  }
  // locked / access-scoped chip
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 2, minWidth: 15, height: 15, padding: '0 3px', borderRadius: 4, background: 'var(--signal-50)', color: 'var(--signal-700)', fontFamily: 'var(--font-mono)', fontSize: 9.5, verticalAlign: '3px', margin: '0 1px' }}>
      <LockIcon size={8} stroke="currentColor" width={2.4} />{children}
    </span>
  )
}

function CheckIcon({ size = 12, stroke = 'var(--active-500)' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.5l4.2 4.2L19 7" /></svg>
  )
}

function LockIcon({ size = 12, stroke = 'var(--signal-600)', width = 2.2 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth={width} strokeLinecap="round" strokeLinejoin="round"><rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></svg>
  )
}

export default function AnswerPanel({ granted, handedOff, onHandoff }) {
  return (
    <div style={{ position: 'absolute', top: 24, left: 24, width: 360, maxWidth: 'calc(100% - 48px)', zIndex: 6 }}>
      <div style={{ background: 'rgba(255,255,255,.95)', backdropFilter: 'blur(16px)', border: '1px solid var(--border-subtle)', borderRadius: 14, padding: 18, boxShadow: '0 10px 34px rgba(15,14,13,.12)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <span style={{ width: 6, height: 6, borderRadius: 999, background: 'var(--active-500)' }} />
          <span style={{ fontSize: 11.5, letterSpacing: '.6px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Synthesized answer</span>
        </div>

        <p style={{ fontFamily: 'var(--font-serif)', fontSize: 16.5, lineHeight: 1.5, letterSpacing: '-.1px', margin: '0 0 14px', color: 'var(--text-primary)', textWrap: 'pretty' }}>
          The 429s trace to two throttles on the payments path. Atlas lowered the gateway limit to <b style={{ fontWeight: 600 }}>60{NBSP}req/min</b> for the retry-queue refactor<NumChip>1</NumChip>, reverting at 16:00.
          {granted && (
            <> auth-core caps token issuance at <b style={{ fontWeight: 600 }}>30{NBSP}req/min</b> per service<NumChip>2</NumChip> — raise it for headroom.</>
          )}
          {!granted && (
            <> auth-core also throttles this path, but the threshold is <span style={{ color: 'var(--text-muted)' }}>access-scoped</span><NumChip variant="lock">2</NumChip>.</>
          )}
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 7, padding: '11px 12px', background: 'var(--surface-sunken)', borderRadius: 8 }}>
          {/* source 1 — Atlas (always full) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 16, height: 16, borderRadius: 4, background: 'var(--ink)', color: 'var(--ivory)', fontFamily: 'var(--font-mono)', fontSize: 10, flex: 'none' }}>1</span>
            <span style={{ fontSize: 12.5, color: 'var(--text-secondary)', fontWeight: 500 }}>Atlas</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>billing-svc/RetryPolicy.md</span>
            <span style={{ marginLeft: 'auto', flex: 'none', display: 'inline-flex' }}><CheckIcon /></span>
          </div>

          {/* source 2 — Lyra (redacted → full when granted) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {granted ? (
              <>
                <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 16, height: 16, borderRadius: 4, background: 'var(--ink)', color: 'var(--ivory)', fontFamily: 'var(--font-mono)', fontSize: 10, flex: 'none' }}>2</span>
                <span style={{ fontSize: 12.5, color: 'var(--text-secondary)', fontWeight: 500 }}>Lyra</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>auth-core/throttle.yaml</span>
                <span style={{ marginLeft: 'auto', flex: 'none', display: 'inline-flex' }}><CheckIcon /></span>
              </>
            ) : (
              <>
                <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 16, height: 16, borderRadius: 4, background: 'var(--signal-50)', color: 'var(--signal-700)', fontFamily: 'var(--font-mono)', fontSize: 10, flex: 'none' }}>2</span>
                <span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>Lyra</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--signal-700)' }}>auth-core · restricted</span>
                <span style={{ marginLeft: 'auto', flex: 'none', display: 'inline-flex' }}><LockIcon size={11} /></span>
              </>
            )}
          </div>
        </div>

        <div style={{ marginTop: 15, paddingTop: 15, borderTop: '1px solid var(--border-subtle)' }}>
          <button className="bc-btn-ink" onClick={onHandoff} style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8, width: '100%', height: 40, border: 'none', borderRadius: 8, background: 'var(--ink)', color: 'var(--ivory)', fontFamily: 'var(--font-sans)', fontWeight: 500, fontSize: 13.5, cursor: 'pointer', transition: 'background 120ms, transform 120ms' }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M8 9l-3.5 3L8 15" /><path d="M16 9l3.5 3L16 15" /><path d="M13.5 6.5l-3 11" /></svg>
            Hand off to Claude Code
          </button>
          {handedOff ? (
            <div style={{ marginTop: 11, display: 'flex', alignItems: 'center', gap: 9, padding: '9px 11px', border: '1px solid rgba(63,125,87,.28)', background: 'var(--active-50)', borderRadius: 8 }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2c5d40" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" style={{ flex: 'none' }}><path d="M5 12.5l4.2 4.2L19 7" /></svg>
              <span style={{ fontSize: 12.5, color: '#2c5d40' }}>Context packaged — opening in Claude Code.</span>
            </div>
          ) : (
            <p style={{ margin: '9px 0 0', fontSize: 11.5, lineHeight: 1.45, color: 'var(--text-muted)' }}>Carries this answer and its cited sources in as context.</p>
          )}
        </div>
      </div>
    </div>
  )
}
