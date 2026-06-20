// Top-left: the synthesized answer with inline numbered citations, a per-source
// provenance list, and the "Hand off to Claude Code" action. Appears in the results phase.

import { CheckIcon, LockIcon, HandoffIcon } from './icons.jsx'
import s from './AnswerPanel.module.css'

const NBSP = ' '

function Cite({ children, lock }) {
  return lock ? (
    <span className={s.citeLock}><LockIcon size={8} stroke="currentColor" width={2.4} />{children}</span>
  ) : (
    <span className={s.cite}>{children}</span>
  )
}

export default function AnswerPanel({ granted, handedOff, onHandoff }) {
  return (
    <div className={s.wrap}>
      <div className={s.card}>
        <div className={s.eyebrowRow}>
          <span className={s.live} />
          <span className={s.eyebrow}>Synthesized answer</span>
        </div>

        <p className={s.prose}>
          The 429s trace to two throttles on the payments path. Atlas lowered the gateway limit to <b className={s.semibold}>60{NBSP}req/min</b> for the retry-queue refactor<Cite>1</Cite>, reverting at 16:00.
          {granted && <> auth-core caps token issuance at <b className={s.semibold}>30{NBSP}req/min</b> per service<Cite>2</Cite> — raise it for headroom.</>}
          {!granted && <> auth-core also throttles this path, but the threshold is <span className={s.muted}>access-scoped</span><Cite lock>2</Cite>.</>}
        </p>

        <div className={s.sources}>
          {/* source 1 — Atlas (always full) */}
          <div className={s.sourceRow}>
            <span className={s.num}>1</span>
            <span className={s.party}>Atlas</span>
            <span className={s.path}>billing-svc/RetryPolicy.md</span>
            <span className={s.right}><CheckIcon /></span>
          </div>

          {/* source 2 — Lyra (redacted → full when granted) */}
          <div className={s.sourceRow}>
            {granted ? (
              <>
                <span className={s.num}>2</span>
                <span className={s.party}>Lyra</span>
                <span className={s.path}>auth-core/throttle.yaml</span>
                <span className={s.right}><CheckIcon /></span>
              </>
            ) : (
              <>
                <span className={s.numLock}>2</span>
                <span className={s.partyMuted}>Lyra</span>
                <span className={s.pathRestricted}>auth-core · restricted</span>
                <span className={s.right}><LockIcon size={11} /></span>
              </>
            )}
          </div>
        </div>

        <div className={s.footer}>
          <button className={s.handoff} onClick={onHandoff}>
            <HandoffIcon />Hand off to Claude Code
          </button>
          {handedOff ? (
            <div className={s.confirm}>
              <span className={s.noShrink}><CheckIcon size={15} stroke="#2c5d40" /></span>
              <span className={s.confirmText}>Context packaged — opening in Claude Code.</span>
            </div>
          ) : (
            <p className={s.hint}>Carries this answer and its cited sources in as context.</p>
          )}
        </div>
      </div>
    </div>
  )
}
