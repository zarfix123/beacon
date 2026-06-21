// Top-left: the synthesized answer (live r.answer, streamed token-by-token) with inline
// numbered [n] citations that line up 1:1 with r.provenance, a collapsible source list
// (count pill → popover), and an Expand control that opens a right-half "reader" slide-over
// for long answers. Appears in the results phase.

import { useState, useEffect, useRef, useMemo, useId } from 'react'
import { createPortal } from 'react-dom'
import { CheckIcon, LockIcon, HandoffIcon, ExpandIcon, CloseIcon, CopyIcon } from './icons.jsx'
import s from './AnswerPanel.module.css'

// The contents of a citation popover: party, document, verified/lock badge, and the
// snippet of the actual cited reply (when we have one — null for denied items).
function SourceCard({ source }) {
  const badge = source.verified
    ? <CheckIcon size={12} />
    : source.decision === 'redacted'
      ? <LockIcon size={11} />
      : null
  return (
    <>
      <span className={s.citePopHead}>
        <span className={source.decision === 'denied' ? s.partyMuted : s.party}>{source.party}</span>
        {badge && <span className={s.citePopBadge}>{badge}</span>}
      </span>
      <span className={source.decision === 'redacted' ? s.pathRestricted : s.path}>
        {source.docTitle || (source.decision === 'redacted' ? 'restricted' : '—')}
      </span>
      {source.snippet && <span className={s.citeSnippet}>{source.snippet}</span>}
    </>
  )
}

// One inline [n] citation: a sleek footnote numeral that opens its source on click.
// The popover is portaled to <body> and viewport-positioned — it flips above the numeral
// when there's no room below, so the capped/scrolling prose box can never clip it. Esc closes
// it and returns focus to the numeral; opening one number bubbles a click that closes any other.
function Cite({ n, source, lock }) {
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState(null)
  const btnRef = useRef(null)
  const popId = useId()
  const cls = lock ? s.citeLock : s.cite
  const lockGlyph = lock ? <LockIcon size={8} stroke="currentColor" width={2.4} /> : null

  useEffect(() => {
    if (!open) return
    const place = () => {
      const el = btnRef.current
      if (!el) return
      const r = el.getBoundingClientRect()
      const half = 124                          // keep the 240px card on-screen near the panel
      const estH = source.snippet ? 168 : 80    // popover height estimate → flip decision
      const left = Math.min(Math.max(r.left + r.width / 2, half), window.innerWidth - half)
      const below = r.bottom + 6
      const flipUp = below + estH > window.innerHeight - 8   // no room below → open above
      const top = flipUp ? Math.max(8, r.top - 6 - estH) : below
      setPos({ top, left })
    }
    place()
    const onDocClick = (e) => { if (btnRef.current && !btnRef.current.contains(e.target)) setOpen(false) }
    const onKey = (e) => { if (e.key === 'Escape') { setOpen(false); btnRef.current?.focus() } }
    document.addEventListener('click', onDocClick)
    document.addEventListener('keydown', onKey)
    window.addEventListener('scroll', place, true)
    window.addEventListener('resize', place)
    return () => {
      document.removeEventListener('click', onDocClick)
      document.removeEventListener('keydown', onKey)
      window.removeEventListener('scroll', place, true)
      window.removeEventListener('resize', place)
    }
  }, [open, source?.snippet])

  // Citation whose provenance hasn't streamed in yet → a muted, non-interactive numeral.
  if (!source) return <span className={`${cls} ${s.citePending}`}>{lockGlyph}{n}</span>

  return (
    <>
      <button
        ref={btnRef}
        type="button"
        className={cls}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={open ? popId : undefined}
        aria-label={`Source ${n}: ${source.party}`}
      >
        {lockGlyph}{n}
      </button>
      {open && pos && createPortal(
        <span
          id={popId}
          role="tooltip"
          className={s.citePopover}
          style={{ top: pos.top, left: pos.left }}
          onClick={(e) => e.stopPropagation()}
        >
          <SourceCard source={source} />
        </span>,
        document.body,
      )}
    </>
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

function AnswerText({ answer, provenance, cardsByChunk }) {
  const sourceFor = (n) => {
    const p = provenance[n - 1]
    if (!p) return null
    const card = cardsByChunk[p.chunk_id]
    return {
      party: p.source_party,
      docTitle: p.source_doc_title,
      decision: p.decision,
      verified: p.verified,
      snippet: card ? card.answer : null, // the actual cited reply text (null for denied)
    }
  }
  return splitCitations(answer || '').map((part, i) =>
    part.t === 'text'
      ? <span key={i}>{part.v}</span>
      : <Cite key={i} n={part.n} source={sourceFor(part.n)} lock={provenance[part.n - 1]?.decision === 'redacted'} />
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

// Assemble the Claude Code hand-off prompt: the question, the synthesized answer, and each
// cited source (party · doc · status · snippet) — everything needed to keep working downstream.
function buildHandoffPrompt({ question, answer, provenance, cardsByChunk }) {
  const out = []
  if (question) out.push(`I asked my agent network: "${question}"`, '')
  out.push('Synthesized answer:', (answer || '').trim() || '(no answer)', '')
  if (provenance.length) {
    out.push('Cited sources:')
    provenance.forEach((p, i) => {
      const status = p.decision === 'denied' ? 'access denied'
        : p.decision === 'redacted' ? 'restricted'
        : p.verified ? 'verified' : 'unverified'
      const doc = p.source_doc_title ? ` — ${p.source_doc_title}` : ''
      out.push(`[${i + 1}] ${p.source_party}${doc} (${status})`)
      const snippet = cardsByChunk[p.chunk_id]?.answer?.trim()
      if (snippet) out.push(`    ${snippet.replace(/\s+/g, ' ')}`)
    })
    out.push('')
  }
  out.push('Help me act on this.')
  return out.join('\n')
}

export default function AnswerPanel({ answer, provenance = [], cards = [], question = '' }) {
  // chunk_id → card, so a citation can pull the snippet of its actual cited reply
  const cardsByChunk = useMemo(
    () => Object.fromEntries(cards.map((c) => [c.chunkId, c])),
    [cards],
  )
  const [showSources, setShowSources] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [handoff, setHandoff] = useState(false)   // copyable Claude Code prompt modal
  const [copied, setCopied] = useState(false)
  const [draft, setDraft] = useState('')
  const inlineRef = useRef(null)
  const readerRef = useRef(null)
  const draftRef = useRef(null)

  const openHandoff = () => {
    setDraft(buildHandoffPrompt({ question, answer, provenance, cardsByChunk }))
    setCopied(false)
    setHandoff(true)
  }
  const copyDraft = async () => {
    try {
      await navigator.clipboard.writeText(draft)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      draftRef.current?.select()   // clipboard blocked → let the user copy the selection manually
    }
  }

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

  // Esc closes the hand-off modal
  useEffect(() => {
    if (!handoff) return
    const onKey = (e) => { if (e.key === 'Escape') setHandoff(false) }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [handoff])

  // follow the streaming answer to the bottom — but only when already near the bottom, so a
  // user who scrolled up to re-read isn't yanked back down on every token.
  useEffect(() => {
    for (const el of [inlineRef.current, readerRef.current]) {
      if (el && el.scrollHeight - el.scrollTop - el.clientHeight < 60) el.scrollTop = el.scrollHeight
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
          <p className={s.prose}><AnswerText answer={answer} provenance={provenance} cardsByChunk={cardsByChunk} /></p>
        </div>

        <div className={s.footer}>
          <button className={s.handoff} onClick={openHandoff}>
            <HandoffIcon />Hand off to Claude Code
          </button>
          <p className={s.hint}>Carries this answer and its cited sources in as context.</p>
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
          <p className={s.readerProse}><AnswerText answer={answer} provenance={provenance} cardsByChunk={cardsByChunk} /></p>
          {provenance.length > 0 && (
            <div className={s.readerSources}>
              <div className={s.readerSourcesLabel}>Sources</div>
              <ProvenanceRows provenance={provenance} />
            </div>
          )}
        </div>
      </div>

      {handoff && createPortal(
        <div className={s.handoffOverlay} onClick={() => setHandoff(false)}>
          <div className={s.handoffModal} onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-label="Hand off to Claude Code">
            <div className={s.handoffHead}>
              <span className={s.eyebrow}>Hand off to Claude Code</span>
              <button className={s.readerClose} onClick={() => setHandoff(false)} aria-label="Close">
                <CloseIcon />
              </button>
            </div>
            <p className={s.handoffHint}>Copy this prompt and paste it into Claude Code to keep going with the answer and its sources as context.</p>
            <textarea
              ref={draftRef}
              className={s.handoffText}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              spellCheck={false}
            />
            <div className={s.handoffActions}>
              <button className={s.handoffCopy} onClick={copyDraft}>
                {copied
                  ? <><CheckIcon size={14} stroke="currentColor" />Copied</>
                  : <><CopyIcon size={14} />Copy prompt</>}
              </button>
            </div>
          </div>
        </div>,
        document.body,
      )}
    </div>
  )
}
