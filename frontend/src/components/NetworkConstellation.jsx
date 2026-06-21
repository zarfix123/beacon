// The radar/constellation network graph — center "You" (the asker) + N responder parties
// bound to hand-tuned SLOTS, a soft beacon glow cast from You, fluid curved edges, and
// (while searching) a propagating "signal": flow along the lines → node arrival glow.
// Nodes are tinted-metallic orbs; node/edge colors + the agent list come from props so the
// parent state machine (live useRelayQuery data) stays untouched. An SVG graphic.

import s from './NetworkConstellation.module.css'

const YOU = [320, 235]
const FOCUS_ZOOM = 2.4

// Hand-tuned node positions + their curved You→node edge paths. Live responders bind to
// these in order (demo = 2 → the two balanced side slots). Keep the bespoke geometry.
const SLOTS = [
  { pos: [181, 291], edge: 'M320 235 Q 238 276 181 291' }, // left
  { pos: [478, 286], edge: 'M320 235 Q 410 248 478 286' }, // right
  { pos: [367, 90], edge: 'M320 235 Q 372 172 367 90' },   // top
]

// A sleek metallic disc: flat status fill + a subtle satin sheen + a thin machined rim.
function MetalNode({ cx, cy, r, col, children, delay }) {
  return (
    <g>
      <circle cx={cx} cy={cy} r={r} fill={col} className={s.nodeBase} filter="url(#nodeShadow)" style={delay ? { transitionDelay: delay } : undefined} />
      <circle cx={cx} cy={cy} r={r} fill="url(#metalSheen)" />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="url(#metalRim)" strokeWidth="1" />
      {children}
    </g>
  )
}

export default function NetworkConstellation({
  isSearching, isResults, accent = 'var(--signal-500)',
  nodes = [], requestingAgentId = null, subtitle = '', focus = null, onClearFocus,
}) {
  // bind responder nodes to slots (in order); ignore extras beyond the slot count
  const placed = nodes.slice(0, SLOTS.length).map((n, i) => ({ ...n, pos: SLOTS[i].pos, edge: SLOTS[i].edge }))
  const reqNode = requestingAgentId ? placed.find((n) => n.agentId === requestingAgentId) : null

  // Smoothly zoom + center the whole scene on a focused node (identity when none).
  const focusNode = focus ? placed.find((n) => n.agentId === focus) : null
  const [fx, fy] = focusNode ? focusNode.pos : YOU
  const sceneStyle = {
    transform: `translate(320px, 235px) scale(${focusNode ? FOCUS_ZOOM : 1}) translate(${-fx}px, ${-fy}px)`,
  }

  return (
    <div className={s.stage}>
      <svg className={s.svg} viewBox="0 0 640 470" width="100%" preserveAspectRatio="xMidYMid meet">
        <defs>
          {/* sleek: a shallow soft shadow for a slight lift, not a floating ball */}
          <filter id="nodeShadow" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="1.5" stdDeviation="1.5" floodColor="#0d0e11" floodOpacity="0.18" />
          </filter>
          {/* satin sheen: faint light top → faint dark bottom (flat metal, no spherical volume) */}
          <linearGradient id="metalSheen" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#fff" stopOpacity="0.22" />
            <stop offset="46%" stopColor="#fff" stopOpacity="0" />
            <stop offset="100%" stopColor="#000" stopOpacity="0.14" />
          </linearGradient>
          {/* thin machined rim: bright top edge → faint dark bottom */}
          <linearGradient id="metalRim" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#fff" stopOpacity="0.5" />
            <stop offset="55%" stopColor="#fff" stopOpacity="0" />
            <stop offset="100%" stopColor="#000" stopOpacity="0.22" />
          </linearGradient>
          {/* beacon glow: a soft signal-tinted bloom cast from You, fading to ivory */}
          <radialGradient id="beaconGlow" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0%" stopColor="var(--signal-500)" stopOpacity="0.18" />
            <stop offset="35%" stopColor="var(--signal-500)" stopOpacity="0.09" />
            <stop offset="100%" stopColor="var(--signal-500)" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* resting beacon glow — outside .scene so it stays stable while the graph zooms */}
        <circle cx="320" cy="235" r="260" fill="url(#beaconGlow)" className={isSearching ? `${s.glow} ${s.glowSearching}` : s.glow} />

        <g className={s.scene} style={sceneStyle}>

          {/* fluid curved edges: soft glow underlay + crisp line */}
          {placed.map((n) => (
            <g key={n.agentId}>
              <path d={n.edge} fill="none" stroke={n.color} strokeOpacity="0.16" strokeWidth="5" strokeLinecap="round" className={s.edge} />
              <path d={n.edge} fill="none" stroke={n.color} strokeOpacity="0.55" strokeWidth="1.6" strokeLinecap="round" className={s.edge} />
            </g>
          ))}

          {/* request access: an amber signal "knocks" along You→party while requesting */}
          {reqNode && (
            <path d={reqNode.edge} pathLength="1" fill="none" stroke="currentColor" strokeWidth="3" className={s.flow} style={{ color: 'var(--warn-500)' }} />
          )}

          {isSearching && (
            <>
              {/* a blue light travels from You out to each node, looping (staggered) */}
              {placed.map((n, i) => (
                <path key={n.agentId} d={n.edge} pathLength="1" fill="none" stroke="currentColor" strokeWidth="3" className={s.flow} style={{ color: accent, animationDelay: `${i * 0.24}s` }} />
              ))}
              {/* arrival glow behind each agent node */}
              {placed.map((n, i) => (
                <circle key={n.agentId} cx={n.pos[0]} cy={n.pos[1]} r="17" fill={accent} className={s.halo} style={{ animationDelay: `${i * 0.5}s` }} />
              ))}
            </>
          )}

          {/* verdict landing: a one-shot glow as each node resolves, staggered left→right */}
          {isResults && placed.map((n, i) => (
            <circle key={n.agentId} cx={n.pos[0]} cy={n.pos[1]} r="17" fill={n.color} className={s.land} style={{ animationDelay: `${i * 110}ms` }} />
          ))}

          {/* YOU (center) — graphite metallic orb; click to zoom back out when focused */}
          <g onClick={onClearFocus} style={{ cursor: focus ? 'zoom-out' : 'default' }}>
            <MetalNode cx={320} cy={235} r={22} col="var(--ink)">
              <g transform="translate(304.4,219.4) scale(1.3)" fill="none" stroke="var(--ivory)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="2.4" fill="var(--ivory)" stroke="none" />
                <path d="M16.6 7.4a6.5 6.5 0 0 1 0 9.2M7.4 16.6a6.5 6.5 0 0 1 0-9.2" />
              </g>
            </MetalNode>
          </g>
          <text x="320" y="276" textAnchor="middle" fontFamily="Hanken Grotesk, sans-serif" fontSize="13" fontWeight="700" fill="var(--text-primary)">You</text>
          {subtitle && (
            <text x="320" y="291" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="9.5" fill="var(--text-muted)">{subtitle}</text>
          )}

          {/* responder parties (mother node + a decision-colored satellite per source when >1 card) */}
          {placed.map((n, i) => {
            const sats = n.cards && n.cards.length > 1 ? n.cards : []
            const dir = Math.atan2(n.pos[1] - 235, n.pos[0] - 320) // radiate outward, away from You
            return (
              <g key={n.agentId}>
                {sats.map((c, j) => {
                  const ang = dir + (j - (sats.length - 1) / 2) * 0.55
                  const x0 = n.pos[0] + 17 * Math.cos(ang), y0 = n.pos[1] + 17 * Math.sin(ang)
                  const x1 = n.pos[0] + 31 * Math.cos(ang), y1 = n.pos[1] + 31 * Math.sin(ang)
                  return (
                    <g key={c.chunkId} className={s.sat}>
                      <line x1={x0} y1={y0} x2={x1} y2={y1} stroke={c.color} strokeOpacity="0.55" strokeWidth="1.2" strokeLinecap="round" />
                      <circle cx={x1} cy={y1} r="4.5" fill={c.color} className={s.satDot} stroke="var(--ivory)" strokeWidth="1.2" />
                    </g>
                  )
                })}
                <MetalNode cx={n.pos[0]} cy={n.pos[1]} r={17} col={n.color} delay={isResults ? `${i * 110}ms` : undefined}>
                  <text x={n.pos[0]} y={n.pos[1]} textAnchor="middle" dominantBaseline="central" fontFamily="Hanken Grotesk, sans-serif" fontSize="15" fontWeight="600" fill="#fff">{n.letter}</text>
                </MetalNode>
                <text x={n.pos[0]} y={n.pos[1] + 34} textAnchor="middle" fontFamily="Hanken Grotesk, sans-serif" fontSize="12.5" fontWeight="600" fill="var(--text-primary)">{n.label}</text>
              </g>
            )
          })}
        </g>
      </svg>
    </div>
  )
}
