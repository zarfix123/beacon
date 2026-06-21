// "Ask the Network" — the main Beacon screen. Drives the constellation, answer panel,
// agents panel, and prompt from the live backend via useRelayQuery (one consumer; the
// visual children stay presentational). phase idle|searching|done → empty|searching|results.

import { useEffect, useState } from 'react'
import { useRelayQuery } from '../useRelayQuery.js'
import NetworkConstellation from './NetworkConstellation.jsx'
import AnswerPanel from './AnswerPanel.jsx'
import AgentsReached from './AgentsReached.jsx'
import PromptPill from './PromptPill.jsx'
import { ResetIcon } from './icons.jsx'
import { CONFIG, DECISION_COLORS, DEFAULT_QUESTION } from './mockData.js'
import s from './AskTheNetwork.module.css'

const decisionColor = (d) => DECISION_COLORS[d] || DECISION_COLORS.idle
const letterOf = (name) => ((name || '?').trim()[0] || '?').toUpperCase()

// A party can own several cards with mixed decisions. Node color = most-restricted
// UNRESOLVED state, so granting the last redacted card visibly flips the node to green.
function partyDecision(cards) {
  if (cards.some((c) => c.decision === 'redacted')) return 'redacted'
  if (cards.some((c) => c.decision === 'full')) return 'full'
  if (cards.some((c) => c.decision === 'denied')) return 'denied'
  return 'idle'
}

export default function AskTheNetwork() {
  const { liveAccent: accent, scope: scopeLabel } = CONFIG
  const r = useRelayQuery()

  const [question, setQuestion] = useState(DEFAULT_QUESTION)
  const [expanded, setExpanded] = useState({})            // by chunk_id
  const [focus, setFocus] = useState(null)                // zoomed agent_id (mirrors open row)
  const [requestingChunkId, setRequestingChunkId] = useState(null)

  const isEmpty = r.phase === 'idle'
  const isSearching = r.phase === 'searching'
  // 'synthesizing' = fan-out done, answer streaming → show the results panels and let r.answer grow live
  const isResults = r.phase === 'synthesizing' || r.phase === 'done'

  // clear the per-card "requesting" spinner once that card has flipped to full
  useEffect(() => {
    if (!requestingChunkId) return
    const c = r.cards.find((c) => c.chunk_id === requestingChunkId)
    if (c && c.decision === 'full') setRequestingChunkId(null)
  }, [r.cards, requestingChunkId])

  const submit = () => {
    if (isSearching || !question.trim()) return
    setExpanded({}); setFocus(null); setRequestingChunkId(null)
    r.submit(question)
  }
  const reset = () => {
    setExpanded({}); setFocus(null); setRequestingChunkId(null)
    r.reset()
  }
  const request = (chunkId) => {
    if (requestingChunkId) return
    const card = r.cards.find((c) => c.chunk_id === chunkId)
    setRequestingChunkId(chunkId)
    if (card) setFocus(card.source_agent_id) // zoom to the party as the request travels
    r.requestAccess(chunkId)
  }
  const toggle = (chunkId) => {
    const card = r.cards.find((c) => c.chunk_id === chunkId)
    const willOpen = !expanded[chunkId]
    setExpanded((prev) => ({ ...prev, [chunkId]: willOpen }))
    if (card) setFocus((f) => (willOpen ? card.source_agent_id : f === card.source_agent_id ? null : f))
  }
  // click the center "You" node while zoomed → collapse that party's rows + zoom out
  const clearFocus = () => {
    if (!focus) return
    const ids = r.cards.filter((c) => c.source_agent_id === focus).map((c) => c.chunk_id)
    setExpanded((prev) => { const n = { ...prev }; ids.forEach((id) => { n[id] = false }); return n })
    setFocus(null)
  }

  const onQ = (e) => setQuestion(e.target.value)
  const onKey = (e) => { if (e.key === 'Enter') { e.preventDefault(); submit() } }

  // ----- view-models derived from the live hook -----
  const cardsFor = (agentId) => r.cards.filter((c) => c.source_agent_id === agentId)
  const agents = [...r.agents].sort((a, b) => (a.agent_id < b.agent_id ? -1 : a.agent_id > b.agent_id ? 1 : 0))
  const nodes = agents.map((a) => {
    const pc = cardsFor(a.agent_id)
    return {
      agentId: a.agent_id,
      label: a.party_name,
      letter: letterOf(a.party_name),
      color: isResults ? decisionColor(partyDecision(pc)) : accent,
      // per-source breakdown for the mother-node satellites (one dot per card, decision-colored)
      cards: pc.map((c) => ({ chunkId: c.chunk_id, decision: c.decision, color: decisionColor(c.decision) })),
    }
  })
  const requestingAgentId = requestingChunkId
    ? r.cards.find((c) => c.chunk_id === requestingChunkId)?.source_agent_id ?? null
    : null

  const cards = r.cards
    .map((c) => ({
      chunkId: c.chunk_id,
      agentId: c.source_agent_id,
      party: c.source_party,
      letter: letterOf(c.source_party),
      decision: c.decision,
      answer: c.answer,
      docTitle: c.source_doc_title,
      verified: c.verified,
      color: decisionColor(c.decision),
    }))
    .sort((a, b) => (a.agentId < b.agentId ? -1 : a.agentId > b.agentId ? 1 : 0))

  const counts = r.cards.reduce((m, c) => ((m[c.decision] = (m[c.decision] || 0) + 1), m), {})
  const reachLine = cards.length
    ? [['full', 'full'], ['redacted', 'scoped'], ['denied', 'denied']]
        .filter(([k]) => counts[k]).map(([k, lbl]) => `${counts[k]} ${lbl}`).join(' · ')
    : 'no replies'

  const reached = nodes.length
  const statusCount = isEmpty ? 'Network online' : `${reached} ${reached === 1 ? 'agent' : 'agents'} reached`
  const subtitle = reached ? `${reached} in range` : ''
  const statusLine = isEmpty ? 'Ask a question to light up the network' : 'Querying agents across the network…'

  return (
    <div className={s.app}>
      {/* ===== TOP BAR ===== */}
      <header className={s.topbar}>
        <img className={s.logo} src="/beacon-logo.png" alt="Beacon" />
        <span className={s.status}>
          <span className={s.statusDot} style={r.connected ? undefined : { background: 'var(--warm-mid)', animation: 'none' }} />
          <span className={s.statusOnline}>{r.connected ? 'Online now' : 'Connecting…'}</span>
          <span className={s.statusCount}>{statusCount}</span>
        </span>
      </header>

      {/* ===== STAGE ===== */}
      <div className={s.stage}>
        <NetworkConstellation
          isSearching={isSearching} isResults={isResults} accent={accent}
          nodes={nodes} requestingAgentId={requestingAgentId} subtitle={subtitle}
          focus={focus} onClearFocus={clearFocus}
        />

        {isResults && <AnswerPanel answer={r.answer} provenance={r.provenance} cards={cards} question={question} />}

        {isResults && (
          <AgentsReached
            cards={cards} reachLine={reachLine} expanded={expanded}
            requestingChunkId={requestingChunkId} focus={focus}
            onToggle={toggle} onRequest={request}
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
