// Bottom-center prompt pill: the always-present question input, scope chip, and submit
// button (arrow → spinner while searching). Enter submits.

import { SignalIcon, ShieldIcon, ArrowIcon } from './icons.jsx'
import s from './PromptPill.module.css'

export default function PromptPill({ question, onQ, onKey, onSubmit, isSearching, scopeLabel }) {
  return (
    <div className={s.dock}>
      <div className={s.pill}>
        <span className={s.lead}><SignalIcon size={16} stroke="var(--signal-600)" dot={2.4} /></span>
        <input
          className={s.input}
          value={question}
          onChange={onQ}
          onKeyDown={onKey}
          placeholder="Ask the network an engineering question…"
        />
        <span className={s.scope}><ShieldIcon />{scopeLabel}</span>
        <button className={s.submit} onClick={onSubmit} disabled={isSearching} aria-label="Ask">
          {isSearching ? <span className={s.spinner} /> : <ArrowIcon />}
        </button>
      </div>
    </div>
  )
}
