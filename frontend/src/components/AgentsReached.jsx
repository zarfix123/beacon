// Top-right: the "Agents reached" list. One expandable row per party.
//   Atlas → full (verified)   Lyra → redacted → full (grant-access)   Vega → denied
// Appears in the results phase.

import { SignalIcon, CheckIcon, LockIcon, ChevronIcon, DocIcon } from './icons.jsx'
import s from './AgentsReached.module.css'

function Avatar({ children, muted }) {
  return <span className={`${s.avatar}${muted ? ` ${s.avatarMuted}` : ''}`}>{children}</span>
}

function RowHead({ color, letter, name, repo, mutedAvatar, children, onToggle }) {
  return (
    <div className={s.rowHead} onClick={onToggle}>
      <span className={s.dot} style={{ background: color }} />
      <Avatar muted={mutedAvatar}>{letter}</Avatar>
      <div className={s.rowMain}>
        <div className={s.rowTitle}>
          <span className={s.name}>{name}</span>
          <span className={s.repo}>{repo}</span>
        </div>
      </div>
      {children}
    </div>
  )
}

function DocChip({ children, withBorder = true }) {
  return (
    <span className={`${s.doc}${withBorder ? '' : ` ${s.docNoBorder}`}`}>
      <DocIcon />
      <span className={s.docLabel}>{children}</span>
    </span>
  )
}

const OVERLINE = {
  full: { cls: 'overlineFull', dot: 'var(--active-500)' },
  redacted: { cls: 'overlineRedacted', dot: 'var(--signal-500)' },
  denied: { cls: 'overlineDenied', dot: 'var(--warm-mid)' },
}

function Overline({ variant, children }) {
  const o = OVERLINE[variant]
  return (
    <span className={`${s.overline} ${s[o.cls]}`}>
      <span className={s.oDot} style={{ background: o.dot }} />{children}
    </span>
  )
}

export default function AgentsReached({
  colAtlas, colLyra, colVega, granted, requesting, requestLabel, showLatency, reachLine,
  expanded, onToggleAtlas, onToggleLyra, onToggleVega, onRequest,
}) {
  return (
    <div className={s.wrap}>
      <div className={s.card}>
        <div className={s.header}>
          <span className={s.headerLabel}><SignalIcon />Agents reached</span>
          <span className={s.reach}>{reachLine}</span>
        </div>

        {/* ATLAS — full */}
        <div className={s.row} style={{ borderLeftColor: colAtlas }}>
          <RowHead color={colAtlas} letter="A" name="Atlas" repo="billing-svc" onToggle={onToggleAtlas}>
            <ChevronIcon open={expanded.atlas} />
          </RowHead>
          {expanded.atlas && (
            <div className={s.expand}>
              <Overline variant="full">Full reply</Overline>
              <p className={s.reply}>Lowered the gateway limit to <b className={s.semibold}>60 req/min</b> while the retry queue refactors — intentional, reverts at 16:00.</p>
              <div className={s.metaRow}>
                <span className={s.verified}><CheckIcon size={12} stroke="currentColor" />Verified</span>
                {showLatency && <span className={s.latency}>142ms</span>}
                <DocChip>RetryPolicy.md</DocChip>
              </div>
            </div>
          )}
        </div>

        {/* LYRA — redacted → full */}
        <div className={s.row} style={{ borderLeftColor: colLyra }}>
          <RowHead color={colLyra} letter="L" name="Lyra" repo="auth-core" onToggle={onToggleLyra}>
            {!granted && (
              <button className={s.request} onClick={onRequest} disabled={requesting}>
                {requesting
                  ? <span className={s.spinner} />
                  : <LockIcon size={11} stroke="currentColor" width={2.2} />}
                {requestLabel}
              </button>
            )}
            <ChevronIcon open={expanded.lyra} />
          </RowHead>
          {expanded.lyra && (
            <div className={s.expand}>
              {granted ? (
                <div>
                  <Overline variant="full">Full reply</Overline>
                  <p className={s.reply}>Token issuance is capped at <b className={s.semibold}>30 req/min</b> per service. Raise it in the auth-core throttle config for headroom.</p>
                  <div className={s.metaRow}>
                    <span className={s.verified}><CheckIcon size={12} stroke="currentColor" />Granted by Diego</span>
                    <DocChip withBorder={false}>throttle.yaml</DocChip>
                  </div>
                </div>
              ) : (
                <>
                  <Overline variant="redacted">Redacted</Overline>
                  <p className={s.replyMuted}>auth-core throttles this same path, but the exact threshold is scoped to the security team.</p>
                  <div className={s.restrictedRow}>
                    <LockIcon size={12} stroke="currentColor" width={2.2} />
                    <span className={s.mono}>throttle.yaml · restricted</span>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* VEGA — denied */}
        <div className={s.row} style={{ borderLeftColor: colVega }}>
          <RowHead color={colVega} letter="V" name="Vega" repo="data-pipeline" mutedAvatar onToggle={onToggleVega}>
            <ChevronIcon open={expanded.vega} />
          </RowHead>
          {expanded.vega && (
            <div className={s.expand}>
              <Overline variant="denied">Denied</Overline>
              <p className={s.replySecondary}>A restricted runbook on this path exists, owned by the <b className={s.strong}>Data team</b>. Vega can't share it.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
