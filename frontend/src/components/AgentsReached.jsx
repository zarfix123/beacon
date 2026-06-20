// Top-right: the "Agents reached" list. One expandable row per party.
//   Atlas → full (verified)   Lyra → redacted → full (grant-access)   Vega → denied
// Appears in the results phase.

function Chevron({ open }) {
  return open ? (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flex: 'none' }}><path d="M18 15l-6-6-6 6" /></svg>
  ) : (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flex: 'none' }}><path d="M6 9l6 6 6-6" /></svg>
  )
}

function Avatar({ children, muted }) {
  return (
    <span style={{ width: 27, height: 27, borderRadius: 999, background: 'var(--surface-sunken)', border: '1px solid var(--border-subtle)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600, fontSize: 12, color: muted ? 'var(--text-muted)' : 'var(--text-secondary)', flex: 'none' }}>{children}</span>
  )
}

function RowHead({ color, letter, name, repo, mutedAvatar, children, onToggle }) {
  return (
    <div onClick={onToggle} style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
      <span style={{ width: 8, height: 8, borderRadius: 999, background: color, flex: 'none' }} />
      <Avatar muted={mutedAvatar}>{letter}</Avatar>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontWeight: 600, fontSize: 13.5 }}>{name}</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, color: 'var(--text-muted)' }}>{repo}</span>
        </div>
      </div>
      {children}
    </div>
  )
}

function DocChip({ children, withBorder = true }) {
  return (
    <span className="bc-doc" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginLeft: 'auto', padding: '4px 8px', border: withBorder ? '1px solid var(--border-subtle)' : 'none', borderRadius: 6, background: withBorder ? 'var(--surface-card)' : 'transparent', cursor: 'pointer', transition: 'all 120ms' }}>
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 3h11a2 2 0 0 1 2 2v15a1 1 0 0 0-1-1H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" /><path d="M6 16h13" /></svg>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, color: 'var(--text-secondary)' }}>{children}</span>
    </span>
  )
}

const overline = (color) => ({ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 10.5, letterSpacing: '.5px', textTransform: 'uppercase', color, fontWeight: 600, marginBottom: 8 })
const rowCard = (color) => ({ background: 'var(--surface-card)', border: '1px solid var(--border-subtle)', borderLeft: `3px solid ${color}`, borderRadius: 10, padding: '11px 13px', transition: 'border-color 120ms' })
const expandWrap = { marginTop: 11, paddingTop: 11, borderTop: '1px solid var(--border-subtle)' }

export default function AgentsReached({
  colAtlas, colLyra, colVega, granted, requesting, requestLabel, showLatency, reachLine,
  expanded, onToggleAtlas, onToggleLyra, onToggleVega, onRequest,
}) {
  return (
    <div style={{ position: 'absolute', top: 24, right: 24, width: 360, maxWidth: 'calc(100% - 48px)', zIndex: 6 }}>
      <div style={{ background: 'rgba(255,255,255,.95)', backdropFilter: 'blur(16px)', border: '1px solid var(--border-subtle)', borderRadius: 14, padding: 14, boxShadow: '0 10px 34px rgba(15,14,13,.12)', display: 'flex', flexDirection: 'column', gap: 9 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 2px' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, fontSize: 11.5, letterSpacing: '.6px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="2" fill="currentColor" stroke="none" /><path d="M16.6 7.4a6.5 6.5 0 0 1 0 9.2M7.4 16.6a6.5 6.5 0 0 1 0-9.2" /></svg>
            Agents reached
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11.5, color: 'var(--text-muted)' }}>{reachLine}</span>
        </div>

        {/* ATLAS — full */}
        <div className="bc-row" style={rowCard(colAtlas)}>
          <RowHead color={colAtlas} letter="A" name="Atlas" repo="billing-svc" onToggle={onToggleAtlas}>
            <Chevron open={expanded.atlas} />
          </RowHead>
          {expanded.atlas && (
            <div style={expandWrap}>
              <span style={overline('#2c5d40')}><span style={{ width: 5, height: 5, borderRadius: 999, background: 'var(--active-500)' }} />Full reply</span>
              <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5, color: 'var(--text-primary)' }}>Lowered the gateway limit to <b style={{ fontWeight: 600 }}>60 req/min</b> while the retry queue refactors — intentional, reverts at 16:00.</p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginTop: 10 }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, color: 'var(--active-500)', fontSize: 11.5, fontWeight: 500 }}>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.5l4.2 4.2L19 7" /></svg>Verified
                </span>
                {showLatency && <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, color: 'var(--text-muted)' }}>142ms</span>}
                <DocChip>RetryPolicy.md</DocChip>
              </div>
            </div>
          )}
        </div>

        {/* LYRA — redacted → full */}
        <div className="bc-row" style={rowCard(colLyra)}>
          <RowHead color={colLyra} letter="L" name="Lyra" repo="auth-core" onToggle={onToggleLyra}>
            {!granted && (
              <button className="bc-btn-request" onClick={onRequest} disabled={requesting} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: 27, padding: '0 10px', border: '1px solid var(--signal-200)', borderRadius: 7, background: 'var(--signal-50)', color: 'var(--signal-700)', fontFamily: 'var(--font-sans)', fontWeight: 500, fontSize: 11.5, cursor: requesting ? 'default' : 'pointer', flex: 'none', transition: 'background 120ms, transform 120ms' }}>
                {requesting ? (
                  <span style={{ width: 10, height: 10, border: '2px solid rgba(155,110,40,.35)', borderTopColor: 'var(--signal-600)', borderRadius: 999, display: 'inline-block', animation: 'bc-spin .7s linear infinite' }} />
                ) : (
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></svg>
                )}
                {requestLabel}
              </button>
            )}
            <Chevron open={expanded.lyra} />
          </RowHead>
          {expanded.lyra && (
            <div style={expandWrap}>
              {granted ? (
                <div style={{ borderRadius: 8 }}>
                  <span style={overline('#2c5d40')}><span style={{ width: 5, height: 5, borderRadius: 999, background: 'var(--active-500)' }} />Full reply</span>
                  <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5, color: 'var(--text-primary)' }}>Token issuance is capped at <b style={{ fontWeight: 600 }}>30 req/min</b> per service. Raise it in the auth-core throttle config for headroom.</p>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginTop: 10 }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, color: 'var(--active-500)', fontSize: 11.5, fontWeight: 500 }}>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.5l4.2 4.2L19 7" /></svg>Granted by Diego
                    </span>
                    <DocChip withBorder={false}>throttle.yaml</DocChip>
                  </div>
                </div>
              ) : (
                <>
                  <span style={overline('var(--signal-700)')}><span style={{ width: 5, height: 5, borderRadius: 999, background: 'var(--signal-500)' }} />Redacted</span>
                  <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5, color: 'var(--text-muted)' }}>auth-core throttles this same path, but the exact threshold is scoped to the security team.</p>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginTop: 9, color: 'var(--signal-700)', fontSize: 11.5 }}>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></svg>
                    <span style={{ fontFamily: 'var(--font-mono)' }}>throttle.yaml · restricted</span>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* VEGA — denied */}
        <div className="bc-row" style={rowCard(colVega)}>
          <RowHead color={colVega} letter="V" name="Vega" repo="data-pipeline" mutedAvatar onToggle={onToggleVega}>
            <Chevron open={expanded.vega} />
          </RowHead>
          {expanded.vega && (
            <div style={expandWrap}>
              <span style={overline('var(--deep-gray)')}><span style={{ width: 5, height: 5, borderRadius: 999, background: 'var(--warm-mid)' }} />Denied</span>
              <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5, color: 'var(--text-secondary)' }}>A restricted runbook on this path exists, owned by the <b style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Data team</b>. Vega can't share it.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
