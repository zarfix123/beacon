// "Ask the Network" — the main Beacon screen. Holds the empty → searching → results
// state machine (today driven by setTimeout mocks; later by the backend WebSocket) and
// lays out the constellation, answer panel, agents panel, prompt, and reset.

import { useEffect, useRef, useState } from 'react'
import NetworkConstellation from './NetworkConstellation.jsx'
import AnswerPanel from './AnswerPanel.jsx'
import AgentsReached from './AgentsReached.jsx'
import PromptPill from './PromptPill.jsx'
import { CONFIG, DECISION_COLORS, DEFAULT_QUESTION } from './mockData.js'

export default function AskTheNetwork() {
  const { liveAccent: accent, showLatency, scope: scopeLabel, autoExpandAgents: autoExpand } = CONFIG

  const [phase, setPhase] = useState('empty') // empty | searching | results
  const [granted, setGranted] = useState(false)
  const [requesting, setRequesting] = useState(false)
  const [handedOff, setHandedOff] = useState(false)
  const [expanded, setExpanded] = useState({})
  const [question, setQuestion] = useState(DEFAULT_QUESTION)

  const tRef = useRef(), rRef = useRef(), hRef = useRef()
  const clearTimers = () => { clearTimeout(tRef.current); clearTimeout(rRef.current); clearTimeout(hRef.current) }
  useEffect(() => clearTimers, [])

  const isEmpty = phase === 'empty'
  const isSearching = phase === 'searching'
  const isResults = phase === 'results'

  const submit = () => {
    if (isSearching) return
    clearTimers()
    setPhase('searching'); setGranted(false); setRequesting(false); setHandedOff(false); setExpanded({})
    tRef.current = setTimeout(() => setPhase('results'), 1900)
  }

  const reset = () => {
    clearTimers()
    setPhase('empty'); setGranted(false); setRequesting(false); setHandedOff(false); setExpanded({})
  }

  const request = (e) => {
    if (e && e.stopPropagation) e.stopPropagation()
    if (requesting || granted) return
    setRequesting(true)
    clearTimeout(rRef.current)
    rRef.current = setTimeout(() => {
      setRequesting(false); setGranted(true)
      setExpanded((s) => ({ ...s, lyra: true }))
    }, 1150)
  }

  const handoff = () => {
    setHandedOff(true)
    clearTimeout(hRef.current)
    hRef.current = setTimeout(() => setHandedOff(false), 4500)
  }

  const toggle = (k) => setExpanded((s) => ({ ...s, [k]: !(s[k] ?? autoExpand) }))

  const onQ = (e) => setQuestion(e.target.value)
  const onKey = (e) => { if (e.key === 'Enter') { e.preventDefault(); submit() } }

  // decision → color (every edge/node goes accent while searching)
  const idle = DECISION_COLORS.idle
  const dec = (d) => (isSearching ? accent : isResults ? DECISION_COLORS[d] : idle)
  const colAtlas = dec('full')
  const colLyra = dec(granted ? 'full' : 'redacted')
  const colVega = dec('denied')

  const reachLine = granted ? '2 full · 1 denied' : '1 full · 1 scoped · 1 denied'
  const statusLine = isEmpty ? 'Ask a question to light up the network' : 'Querying agents across the network…'
  const requestLabel = requesting ? 'Requesting…' : 'Request access'
  const expandedOpen = {
    atlas: expanded.atlas ?? autoExpand,
    lyra: expanded.lyra ?? autoExpand,
    vega: expanded.vega ?? autoExpand,
  }

  return (
    <div style={{ width: '100%', height: '100vh', background: 'var(--ivory)', fontFamily: 'var(--font-sans)', color: 'var(--text-primary)', display: 'flex', flexDirection: 'column', boxSizing: 'border-box', overflow: 'hidden' }}>
      {/* ===== TOP BAR ===== */}
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 28px', borderBottom: '1px solid var(--border-subtle)', background: 'rgba(250,250,249,.8)', backdropFilter: 'blur(16px)', zIndex: 8, flex: 'none' }}>
        <img src="/beacon-logo.png" alt="Beacon" style={{ height: 28, width: 'auto', display: 'block' }} />
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '5px 11px', border: '1px solid var(--border-subtle)', borderRadius: 999, background: 'var(--surface-card)', whiteSpace: 'nowrap' }}>
          <span style={{ width: 6, height: 6, borderRadius: 999, background: 'var(--active-500)', animation: 'bc-glow 2s infinite ease-in-out' }} />
          <span style={{ fontSize: 12, letterSpacing: '.6px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Online now</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-secondary)' }}>1,248 agents reachable</span>
        </span>
      </header>

      {/* ===== STAGE ===== */}
      <div style={{ position: 'relative', flex: 1, minHeight: 0, overflow: 'hidden' }}>
        <NetworkConstellation isSearching={isSearching} accent={accent} colAtlas={colAtlas} colLyra={colLyra} colVega={colVega} />

        {isResults && <AnswerPanel granted={granted} handedOff={handedOff} onHandoff={handoff} />}

        {isResults && (
          <AgentsReached
            colAtlas={colAtlas} colLyra={colLyra} colVega={colVega}
            granted={granted} requesting={requesting} requestLabel={requestLabel}
            showLatency={showLatency} reachLine={reachLine} expanded={expandedOpen}
            onToggleAtlas={() => toggle('atlas')} onToggleLyra={() => toggle('lyra')} onToggleVega={() => toggle('vega')}
            onRequest={request}
          />
        )}

        {/* status pill (empty / searching) */}
        {!isResults && (
          <div style={{ position: 'absolute', bottom: 108, left: 0, right: 0, display: 'flex', justifyContent: 'center', pointerEvents: 'none', zIndex: 5 }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 9, padding: '7px 15px', borderRadius: 999, background: 'rgba(255,255,255,.85)', backdropFilter: 'blur(10px)', border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)', fontSize: 13 }}>
              {isSearching && <span style={{ width: 7, height: 7, borderRadius: 999, background: accent, animation: 'bc-glow 1s infinite ease-in-out' }} />}
              {statusLine}
            </span>
          </div>
        )}

        {/* prompt pill (always) */}
        <PromptPill question={question} onQ={onQ} onKey={onKey} onSubmit={submit} isSearching={isSearching} scopeLabel={scopeLabel} />

        {/* reset (results) */}
        {isResults && (
          <button className="bc-reset" onClick={reset} style={{ position: 'absolute', bottom: 36, right: 24, zIndex: 7, display: 'inline-flex', alignItems: 'center', gap: 7, height: 34, padding: '0 13px', border: '1px solid var(--border-default)', borderRadius: 999, background: 'rgba(255,255,255,.9)', backdropFilter: 'blur(10px)', color: 'var(--text-secondary)', fontFamily: 'var(--font-sans)', fontSize: 12.5, cursor: 'pointer', transition: 'border-color 120ms' }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 4v4h4" /></svg>
            Reset
          </button>
        )}
      </div>
    </div>
  )
}
