// Bottom-center prompt pill: the always-present question input, scope chip, and submit
// button (arrow → spinner while searching). Enter submits.

export default function PromptPill({ question, onQ, onKey, onSubmit, isSearching, scopeLabel }) {
  return (
    <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, display: 'flex', justifyContent: 'center', padding: '0 24px 28px', pointerEvents: 'none', zIndex: 7 }}>
      <div className="bc-prompt" style={{ pointerEvents: 'auto', display: 'flex', alignItems: 'center', gap: 11, width: 'min(660px,100%)', padding: '8px 8px 8px 18px', background: 'var(--surface-card)', border: '1px solid var(--border-subtle)', borderRadius: 999, boxShadow: '0 8px 28px rgba(15,14,13,.10)', transition: 'box-shadow 160ms, border-color 160ms' }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--signal-600)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flex: 'none' }}><circle cx="12" cy="12" r="2.4" fill="var(--signal-600)" stroke="none" /><path d="M16.6 7.4a6.5 6.5 0 0 1 0 9.2M7.4 16.6a6.5 6.5 0 0 1 0-9.2" /></svg>
        <input
          className="bc-q"
          value={question}
          onChange={onQ}
          onKeyDown={onKey}
          placeholder="Ask the network an engineering question…"
          style={{ flex: 1, minWidth: 0, border: 'none', background: 'none', fontFamily: 'var(--font-sans)', fontSize: 14.5, color: 'var(--text-primary)' }}
        />
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '5px 10px', borderRadius: 999, background: 'var(--surface-sunken)', color: 'var(--text-muted)', fontSize: 11.5, whiteSpace: 'nowrap', flex: 'none' }}>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" /></svg>
          {scopeLabel}
        </span>
        <button className="bc-iconbtn-ink" onClick={onSubmit} disabled={isSearching} aria-label="Ask" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 40, height: 40, border: 'none', borderRadius: 999, background: 'var(--ink)', color: 'var(--ivory)', cursor: isSearching ? 'default' : 'pointer', flex: 'none', transition: 'background 120ms, transform 120ms' }}>
          {isSearching ? (
            <span style={{ width: 15, height: 15, border: '2px solid rgba(250,250,249,.4)', borderTopColor: 'var(--ivory)', borderRadius: 999, display: 'inline-block', animation: 'bc-spin .7s linear infinite' }} />
          ) : (
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
          )}
        </button>
      </div>
    </div>
  )
}
