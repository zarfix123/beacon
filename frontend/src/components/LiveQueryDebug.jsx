/**
 * LiveQueryDebug — the walking skeleton (Phase 4 step 4a).
 *
 * Barebones, real client over useBeaconQuery: ask the locked query, watch the live frame
 * stream (ack -> agent-activated -> response-item -> done) drive cards + the synthesized
 * answer, and hit "Request access" to fire the grant-access targeted re-stream and watch the
 * one redacted card flip to full+verified. Ugly on purpose — this is the "the demo exists"
 * milestone and the guaranteed-working fallback. Mounted via App.jsx at ?debug.
 */
import { useState } from 'react'
import { useBeaconQuery } from '../useBeaconQuery.js'
import { DEFAULT_QUESTION } from './mockData.js'

const COLORS = { full: '#3f7d57', redacted: '#b9802f', denied: '#8f8b85' }
const mono = { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 13 }

export default function LiveQueryDebug() {
  const [q, setQ] = useState(DEFAULT_QUESTION)
  const r = useBeaconQuery()

  return (
    <div style={{ padding: 24, maxWidth: 920, margin: '0 auto', ...mono, color: '#1c1b19' }}>
      <h2 style={{ margin: '0 0 4px' }}>Beacon — live wire (walking skeleton)</h2>
      <div style={{ color: '#666' }}>
        {r.connected ? '🟢 connected' : '🔴 disconnected'} · phase <b>{r.phase}</b> · query_id {r.queryId || '—'}
      </div>

      <div style={{ display: 'flex', gap: 8, margin: '12px 0' }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} style={{ flex: 1, padding: 8, ...mono }} />
        <button onClick={() => r.submit(q)} disabled={r.phase === 'searching'}>Ask</button>
        <button onClick={r.reset}>Reset</button>
      </div>

      <h3 style={{ marginBottom: 4 }}>Nodes ({r.agents.length})</h3>
      {r.agents.map((a) => (
        <div key={a.agent_id}>● {a.party_name} <span style={{ color: '#888' }}>({a.agent_id})</span> — {a.status}</div>
      ))}

      <h3 style={{ marginBottom: 4 }}>Cards ({r.cards.length})</h3>
      {r.cards.map((c) => (
        <div key={c.chunk_id} style={{ borderLeft: `4px solid ${COLORS[c.decision] || '#ccc'}`,
                                       padding: '8px 12px', margin: '8px 0', background: '#faf9f7' }}>
          <div>
            <b style={{ color: COLORS[c.decision] }}>{c.decision.toUpperCase()}</b>
            {c.verified ? ' ✓ verified' : ''} · {c.source_party} · {c.source_doc_title || '—'}
          </div>
          <div style={{ color: '#333', marginTop: 2 }}>{c.answer || <i>(no answer)</i>}</div>
          {c.decision === 'redacted' && (
            <button onClick={() => r.requestAccess(c.chunk_id)} style={{ marginTop: 8 }}>🔒 Request access</button>
          )}
        </div>
      ))}

      <h3 style={{ marginBottom: 4 }}>Synthesized answer</h3>
      <div style={{ background: '#f1efea', padding: 12, whiteSpace: 'pre-wrap', minHeight: 28 }}>
        {r.answer || <i style={{ color: '#999' }}>(pending)</i>}
      </div>
      {r.provenance.length > 0 && (
        <ol style={{ marginTop: 8 }}>
          {r.provenance.map((p, i) => (
            <li key={i}>{p.source_party} · {p.source_doc_title || '—'} · {p.decision}{p.verified ? ' ✓' : ''}</li>
          ))}
        </ol>
      )}
      <div style={{ color: '#999' }}>item_count: {r.itemCount ?? '—'}</div>

      <details style={{ marginTop: 16 }}>
        <summary style={{ cursor: 'pointer', color: '#666' }}>raw frames ({r.rawEvents.length})</summary>
        <pre style={{ maxHeight: 320, overflow: 'auto', fontSize: 11, background: '#1c1b19', color: '#d6d3cd', padding: 10 }}>
          {r.rawEvents.map((f) => JSON.stringify(f)).join('\n')}
        </pre>
      </details>
    </div>
  )
}
