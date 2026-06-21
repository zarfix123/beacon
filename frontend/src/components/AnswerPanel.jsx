// Top-left: the synthesized answer (live r.answer, streamed token-by-token) with inline
// numbered [n] citations that line up 1:1 with r.provenance, a collapsible source list
// (count pill → popover), and an Expand control that opens a right-half "reader" slide-over
// for long answers. Appears in the results phase.

import { useState, useEffect, useRef } from 'react'
import { CheckIcon, LockIcon, HandoffIcon, ExpandIcon, CloseIcon } from './icons.jsx'
import s from './AnswerPanel.module.css'

function Cite({ children, lock }) {
  return lock ? (
    <span className={s.citeLock}><LockIcon size={8} stroke="currentColor" width={2.4} />{children}</span>
  ) : (
    <span className={s.cite}>{children}</span>
  )
}

// Split a synthesized answer string into text + citation tokens on [n] markers.
function splitCitations(text) {
  const parts = []
  const re = /\[(\d+)\]/g
  let last = 0, m
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push({ t: 'text', v: text.slice(last, m.index) })
    parts.push({ t: 'cite', n: Number(m[1]) })
    last = m.index + m[0].length
  }
  if (last < text.length) parts.push({ t: 'text', v: text.slice(last) })
  return parts
}

function AnswerText({ answer, provenance }) {
  return splitCitations(answer || '').map((part, i) =>
    part.t === 'text'
      ? <span key={i}>{part.v}</span>
      : <Cite key={i} lock={provenance[part.n - 1]?.decision === 'redacted'}>{part.n}</Cite>
  )
}

function ProvenanceRows({ provenance }) {
  return provenance.map((p, i) => (
    <div key={i} className={s.sourceRow}>
      <span className={p.decision === 'redacted' ? s.numLock : s.num}>{i + 1}</span>
      <span className={p.decision === 'denied' ? s.partyMuted : s.party}>{p.source_party}</span>
      <span className={p.decision === 'redacted' ? s.pathRestricted : s.path}>
        {p.source_doc_title || (p.decision === 'redacted' ? 'restricted' : '—')}
      </span>
      <span className={s.right}>
        {p.verified ? <CheckIcon /> : p.decision === 'redacted' ? <LockIcon size={11} /> : null}
      </span>
    </div>
  ))
}

export default function AnswerPanel({ answer, provenance = [], handedOff, onHandoff }) {
  const [showSources, setShowSources] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const inlineRef = useRef(null)
  const readerRef = useRef(null)

  // close the citations popover on any outside click
  useEffect(() => {
    if (!showSources) return
    const close = () => setShowSources(false)
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [showSources])

  // Esc closes the reader
  useEffect(() => {
    if (!expanded) return
    const onKey = (e) => { if (e.key === 'Escape') setExpanded(false) }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [expanded])

  // follow the streaming answer to the bottom (inline + reader)
  useEffect(() => {
    for (const el of [inlineRef.current, readerRef.current]) {
      if (el) el.scrollTop = el.scrollHeight
    }
  }, [answer, expanded])

  return (
    <div className={s.wrap}>
      <div className={s.card}>
        <div className={s.eyebrowRow}>
          <span className={s.eyebrow}>Synthesized answer</span>
          <div className={s.eyebrowActions}>
            {provenance.length > 0 && (
              <div className={s.citeAnchor} onClick={(e) => e.stopPropagation()}>
                <button className={s.sourcesPill} onClick={() => setShowSources((v) => !v)} aria-expanded={showSources}>
                  {provenance.length} {provenance.length === 1 ? 'source' : 'sources'}
                </button>
                {showSources && <div className={s.popover}><ProvenanceRows provenance={provenance} /></div>}
              </div>
            )}
            <button className={s.expandBtn} onClick={() => setExpanded(true)} aria-label="Expand answer">
              <ExpandIcon />
            </button>
          </div>
        </div>

        <div className={s.proseScroll} ref={inlineRef}>
          <p className={s.prose}><AnswerText answer={answer} provenance={provenance} /></p>
        </div>

        <div className={s.footer}>
          <button className={s.handoff} onClick={onHandoff}>
            <HandoffIcon />Hand off to Claude Code
          </button>
          {handedOff ? (
            <div className={s.confirm}>
              <span className={s.noShrink}><CheckIcon size={15} stroke="var(--active-700)" /></span>
              <span className={s.confirmText}>Context packaged. Opening in Claude Code.</span>
            </div>
          ) : (
            <p className={s.hint}>Carries this answer and its cited sources in as context.</p>
          )}
        </div>
      </div>

      {/* right-half slide-over reader for long answers (always mounted; slides via class) */}
      <div className={`${s.reader}${expanded ? ` ${s.readerOpen}` : ''}`} aria-hidden={!expanded}>
        <div className={s.readerHead}>
          <span className={s.eyebrow}>Synthesized answer</span>
          <button className={s.readerClose} onClick={() => setExpanded(false)} aria-label="Close reader">
            <CloseIcon />
          </button>
        </div>
        <div className={s.readerBody} ref={readerRef}>
          <p className={s.readerProse}><AnswerText answer={answer} provenance={provenance} /></p>
          {provenance.length > 0 && (
            <div className={s.readerSources}>
              <div className={s.readerSourcesLabel}>Sources</div>
              <ProvenanceRows provenance={provenance} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
