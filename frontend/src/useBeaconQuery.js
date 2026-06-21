/**
 * useBeaconQuery — the live data layer for Beacon (Phase 4).
 *
 * Owns one WebSocket to the backend, reduces the real event stream
 * (ack -> agent-activated -> response-item -> done) into the shape the UI renders, and
 * exposes submit()/requestAccess()/reset(). Built straight to the frozen contract
 * (shared/contracts/api-websocket.md + backend app/api/schemas.py) — no mock parser.
 *
 * This hook is the CONTRACT between the data layer and the visual components: swap a
 * component's mock source for these fields and it renders live.
 *
 * Returned state:
 *   phase       'idle' | 'searching' | 'synthesizing' | 'done'   ('synthesizing' = answer streaming)
 *   connected   bool
 *   queryId     string | null
 *   agents      [{ agent_id, party_name, status }]      // from agent-activated (the nodes)
 *   cards       [{ chunk_id, source_agent_id, source_party, decision, answer,
 *                  source_doc_title, verified }]         // from response-item (upserted by chunk_id)
 *   answer      string | null                            // done.synthesized_answer
 *   provenance  [{ source_party, source_doc_title, decision, verified, source_agent_id, chunk_id }]
 *   itemCount   number | null
 *   rawEvents   [frame, ...]                             // every frame, for debugging
 *   submit(question)        send a fresh query on the socket
 *   requestAccess(chunkId)  POST /grant_access; the targeted re-stream upserts the flipped card
 *   reset()                 POST /demo/reset (re-arm tiers) + clear local state
 */
import { useCallback, useEffect, useMemo, useReducer, useRef } from 'react'

const WS_URL = 'ws://localhost:8000/ws/query'
const HTTP = 'http://localhost:8000'

const INITIAL = {
  phase: 'idle',
  connected: false,
  queryId: null,
  agentsById: {},
  cardsById: {},
  answer: null,
  provenance: [],
  itemCount: null,
  rawEvents: [],
}

function reducer(state, action) {
  switch (action.type) {
    case 'connected':
      return { ...state, connected: action.value }
    case 'submit':
      // fresh query: clear last run, keep the connection
      return { ...INITIAL, connected: state.connected, phase: 'searching' }
    case 'reset':
      return { ...INITIAL, connected: state.connected }
    case 'frame': {
      const f = action.frame
      const rawEvents = [...state.rawEvents, f]
      switch (f.type) {
        case 'ack':
          // ack only fires on a fresh query (not on a grant-access replay) -> start clean
          return { ...INITIAL, connected: state.connected, phase: 'searching',
                   queryId: f.query_id, rawEvents }
        case 'agent-activated':
          return { ...state, rawEvents,
                   agentsById: { ...state.agentsById,
                     [f.agent_id]: { agent_id: f.agent_id, party_name: f.party_name, status: f.status } } }
        case 'response-item':
          // upsert by chunk_id so a grant-access re-stream flips the ONE card in place
          return { ...state, rawEvents,
                   cardsById: { ...state.cardsById, [f.chunk_id]: f } }
        case 'synthesizing':
          // fan-out done; the answer is about to stream. Reset answer (also covers the
          // grant-access re-stream re-composing the answer on the same query_id).
          return { ...state, rawEvents, phase: 'synthesizing', answer: '' }
        case 'answer-delta':
          // append streamed tokens -> r.answer grows live, no component change needed
          return { ...state, rawEvents, phase: 'synthesizing',
                   answer: (state.answer || '') + (f.delta || '') }
        case 'done':
          return { ...state, rawEvents, phase: 'done',
                   answer: f.synthesized_answer, provenance: f.provenance || [],
                   itemCount: f.item_count }
        default:
          return { ...state, rawEvents }
      }
    }
    default:
      return state
  }
}

export function useBeaconQuery() {
  const [state, dispatch] = useReducer(reducer, INITIAL)
  const wsRef = useRef(null)
  const pendingRef = useRef(null) // question queued until the socket opens

  useEffect(() => {
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws
    ws.onopen = () => {
      dispatch({ type: 'connected', value: true })
      if (pendingRef.current != null) {
        ws.send(JSON.stringify({ type: 'query', query: pendingRef.current }))
        pendingRef.current = null
      }
    }
    ws.onmessage = (ev) => dispatch({ type: 'frame', frame: JSON.parse(ev.data) })
    ws.onclose = () => dispatch({ type: 'connected', value: false })
    ws.onerror = () => dispatch({ type: 'connected', value: false })
    return () => ws.close()
  }, [])

  const submit = useCallback((question) => {
    dispatch({ type: 'submit' })
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'query', query: question }))
    } else {
      pendingRef.current = question // sent in onopen
    }
  }, [])

  const requestAccess = useCallback(async (chunkId) => {
    if (!state.queryId) return
    await fetch(`${HTTP}/grant_access`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chunk_id: chunkId, query_id: state.queryId }),
    }).catch(() => {})
    // the targeted re-stream arrives on the SAME socket and upserts the flipped card
  }, [state.queryId])

  const reset = useCallback(async () => {
    await fetch(`${HTTP}/demo/reset`, { method: 'POST' }).catch(() => {})
    dispatch({ type: 'reset' })
  }, [])

  const agents = useMemo(() => Object.values(state.agentsById), [state.agentsById])
  const cards = useMemo(() => Object.values(state.cardsById), [state.cardsById])

  return {
    phase: state.phase,
    connected: state.connected,
    queryId: state.queryId,
    agents,
    cards,
    answer: state.answer,
    provenance: state.provenance,
    itemCount: state.itemCount,
    rawEvents: state.rawEvents,
    submit,
    requestAccess,
    reset,
  }
}
