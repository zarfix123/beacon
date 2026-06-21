// Top-right: the "Agents reached" list. One expandable row per response card (live
// r.cards, multiple per party). full = green verified · redacted = amber + lock + Request
// access · denied = grey. Appears in the results phase.

import { SignalIcon, CheckIcon, LockIcon, ChevronIcon } from './icons.jsx'
import s from './AgentsReached.module.css'

function Avatar({ children, muted, focused }) {
  return (
    <span className={`${s.avatar}${muted ? ` ${s.avatarMuted}` : ''}${focused ? ` ${s.avatarFocused}` : ''}`}>
      {children}
    </span>
  )
}

function RowHead({ letter, name, repo, mutedAvatar, focused, children, onToggle }) {
  return (
    <div className={s.rowHead} onClick={onToggle}>
      <Avatar muted={mutedAvatar} focused={focused}>{letter}</Avatar>
      <div className={s.rowMain}>
        <div className={s.rowTitle}>
          <span className={s.name}>{name}</span>
          {repo && <span className={s.repo}>{repo}</span>}
        </div>
      </div>
      {children}
    </div>
  )
}

const OVERLINE = {
  full: { cls: 'overlineFull', dot: 'var(--active-500)', label: 'Full reply' },
  redacted: { cls: 'overlineRedacted', dot: 'var(--warn-500)', label: 'Redacted' },
  denied: { cls: 'overlineDenied', dot: 'var(--warm-mid)', label: 'Denied' },
}

function Overline({ variant }) {
  const o = OVERLINE[variant] || OVERLINE.denied
  return (
    <span className={`${s.overline} ${s[o.cls]}`}>
      <span className={s.oDot} style={{ background: o.dot }} />{o.label}
    </span>
  )
}

function CardBody({ decision, answer, verified }) {
  if (decision === 'full') {
    return (
      <div className={s.expand}>
        <Overline variant="full" />
        <p className={s.reply}>{answer}</p>
        {verified && (
          <div className={s.metaRow}>
            <span className={s.verified}><CheckIcon size={12} stroke="currentColor" />Verified against source</span>
          </div>
        )}
      </div>
    )
  }
  if (decision === 'redacted') {
    return (
      <div className={s.expand}>
        <Overline variant="redacted" />
        <p className={s.replyMuted}>{answer}</p>
        <div className={s.restrictedRow}>
          <LockIcon size={12} stroke="currentColor" width={2.2} />
          <span className={s.mono}>restricted · request access to view</span>
        </div>
      </div>
    )
  }
  return (
    <div className={s.expand}>
      <Overline variant="denied" />
      <p className={s.replySecondary}>{answer || 'A relevant item exists here but was not shared.'}</p>
    </div>
  )
}

export default function AgentsReached({ cards, reachLine, expanded, requestingChunkId, focus, onToggle, onRequest }) {
  return (
    <div className={s.wrap}>
      <div className={s.card}>
        <div className={s.header}>
          <span className={s.headerLabel}><SignalIcon />Agents reached</span>
          <span className={s.reach}>{reachLine}</span>
        </div>

        {cards.length === 0 && (
          <p className={s.empty}>No party returned a shareable answer to this question.</p>
        )}

        {cards.map((c) => {
          const open = !!expanded[c.chunkId]
          const requesting = requestingChunkId === c.chunkId
          return (
            <div key={c.chunkId} className={s.row} style={{ borderLeftColor: c.color }}>
              <RowHead
                letter={c.letter} name={c.party} repo={c.docTitle}
                mutedAvatar={c.decision === 'denied'} focused={focus === c.agentId}
                onToggle={() => onToggle(c.chunkId)}
              >
                {c.decision === 'redacted' && (
                  <button
                    className={s.request}
                    onClick={(e) => { e.stopPropagation(); onRequest(c.chunkId) }}
                    disabled={requesting}
                  >
                    {requesting
                      ? <span className={s.spinner} />
                      : <LockIcon size={11} stroke="currentColor" width={2.2} />}
                    {requesting ? 'Requesting…' : 'Request access'}
                  </button>
                )}
                <ChevronIcon open={open} />
              </RowHead>
              <div className={`${s.drawer}${open ? ` ${s.drawerOpen}` : ''}`}>
                <div className={s.drawerInner}>
                  <CardBody decision={c.decision} answer={c.answer} verified={c.verified} />
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
