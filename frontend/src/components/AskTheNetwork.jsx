// "Ask the Network" — the main Beacon screen. Holds the empty → searching → results
// state machine (today driven by setTimeout mocks; later by the backend WebSocket) and
// lays out the constellation, answer panel, agents panel, prompt, and reset.

import { useEffect, useRef, useState } from 'react'
import NetworkConstellation from './NetworkConstellation.jsx'
import AnswerPanel from './AnswerPanel.jsx'
import AgentsReached from './AgentsReached.jsx'
import PromptPill from './PromptPill.jsx'
import { ResetIcon } from './icons.jsx'
import { CONFIG, DECISION_COLORS, DEFAULT_QUESTION } from './mockData.js'
import s from './AskTheNetwork.module.css'

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
      setExpanded((prev) => ({ ...prev, lyra: true }))
    }, 1150)
  }

  const handoff = () => {
    setHandedOff(true)
    clearTimeout(hRef.current)
    hRef.current = setTimeout(() => setHandedOff(false), 4500)
  }

  const toggle = (k) => setExpanded((prev) => ({ ...prev, [k]: !(prev[k] ?? autoExpand) }))

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
    <div className={s.app}>
      {/* ===== TOP BAR ===== */}
      <header className={s.topbar}>
        <img className={s.logo} src="/beacon-logo.png" alt="Beacon" />
        <span className={s.status}>
          <span className={s.statusDot} />
          <span className={s.statusOnline}>Online now</span>
          <span className={s.statusCount}>1,248 agents reachable</span>
        </span>
      </header>

      {/* ===== STAGE ===== */}
      <div className={s.stage}>
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
          <div className={s.statusPillDock}>
            <span className={s.statusPill}>
              {isSearching && <span className={s.searchDot} style={{ background: accent }} />}
              {statusLine}
            </span>
          </div>
        )}

        {/* prompt pill (always) */}
        <PromptPill question={question} onQ={onQ} onKey={onKey} onSubmit={submit} isSearching={isSearching} scopeLabel={scopeLabel} />

        {/* reset (results) */}
        {isResults && (
          <button className={s.reset} onClick={reset}>
            <ResetIcon />
            Reset
          </button>
        )}
      </div>
    </div>
  )
}
