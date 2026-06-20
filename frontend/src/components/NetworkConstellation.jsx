// The radar/constellation network graph — center "You" + 3 agents (Atlas/Lyra/Vega),
// concentric rings, a scattered background of reachable agents, and (while searching)
// travelling packets + node pulses. Ported faithfully from the design's inline SVG.

// Background "reachable agents": [cx, cy, r, fillOpacity]. All fill #bbb6ae.
const DOTS = [
  [394.3, 283.4, 2.5, 0.35], [426, 131.2, 1.7, 0.75], [424, 308.5, 2.8, 0.73],
  [295.6, 180.5, 1.5, 0.69], [491.5, 176.1, 2.1, 0.73], [75.7, 274, 3.3, 0.66],
  [241.8, 124.1, 1.6, 0.46], [335.1, 33.8, 2.7, 0.51], [269.7, 206.7, 4.1, 0.59],
  [445.5, 319.3, 1.6, 0.78], [150.1, 270.8, 2.2, 0.73], [463, 347.9, 1.6, 0.42],
  [382.6, 270.1, 2.8, 0.59], [337.9, 375.2, 2.1, 0.46], [90.2, 278.9, 2.4, 0.69],
  [383, 197.5, 2.2, 0.3], [437.4, 159.3, 1.5, 0.55], [391.5, 234, 3.3, 0.43],
  [281.4, 166.5, 3.8, 0.79], [437.4, 143.1, 1.6, 0.62], [195.9, 331.5, 1.7, 0.29],
  [291.7, 103.9, 2.7, 0.71], [366, 378.1, 2.5, 0.44], [256.9, 98.2, 1.7, 0.32],
  [246.1, 355.7, 2.5, 0.51], [294.5, 293.1, 1.9, 0.65], [210.6, 255.3, 2.1, 0.55],
  [334.9, 285.2, 1.4, 0.61], [179.2, 355.9, 2.6, 0.71], [304.6, 335.9, 1.7, 0.38],
  [106.1, 184.6, 1.5, 0.53], [154.2, 171, 2.8, 0.6], [198.4, 187.2, 2.6, 0.43],
  [121.8, 344.7, 1.5, 0.31], [556.8, 227.5, 2.4, 0.37], [225.7, 341, 2.6, 0.5],
  [117.2, 242, 1.7, 0.35], [306.9, 432, 3.4, 0.37], [266.3, 412.7, 2.5, 0.28],
  [154, 389.2, 1.6, 0.4], [429, 362.2, 2.8, 0.43], [256.7, 182.8, 2.3, 0.39],
  [191.9, 242.1, 2.7, 0.43], [324.5, 156.6, 1.7, 0.62], [241.9, 215.6, 2.2, 0.76],
  [255.7, 244.4, 2.5, 0.5], [223.9, 238.5, 3.1, 0.39], [259, 339.2, 2.4, 0.6],
  [127, 224.8, 3.7, 0.59], [535.5, 279, 1.5, 0.29], [144.2, 190.3, 2.7, 0.31],
  [349.5, 33, 1.7, 0.34], [237.9, 74.3, 2.6, 0.78], [205.9, 130.7, 4, 0.38],
  [142, 232.9, 2.5, 0.44], [362.6, 149.2, 2.3, 0.53], [360.2, 282.3, 1.6, 0.57],
  [230.6, 394.1, 2.6, 0.52], [519, 277, 2.7, 0.45], [154.1, 253.9, 3.8, 0.4],
  [267.7, 374.3, 2.1, 0.63], [236.4, 250.4, 2.6, 0.6], [374.2, 308.6, 2.8, 0.37],
  [253.4, 137.8, 1.9, 0.76], [229.5, 162.2, 1.4, 0.32], [251.7, 229.6, 2.2, 0.4],
  [259.9, 306.9, 2.4, 0.33], [518.2, 290.5, 2.6, 0.51], [299, 150.5, 1.5, 0.69],
  [172.8, 259.8, 2.4, 0.42], [69.3, 205.1, 2.3, 0.64], [313.4, 106.6, 1.8, 0.56],
  [543.8, 300.4, 3.6, 0.83], [232.5, 199.6, 3.5, 0.49], [255, 285.6, 2.1, 0.34],
  [517.9, 181.1, 1.7, 0.61], [208.1, 102.8, 2.4, 0.72], [441.9, 343.5, 1.6, 0.69],
  [330.6, 313.4, 2.2, 0.72], [364.5, 258.9, 1.6, 0.82], [498.9, 383.9, 2.4, 0.31],
  [403.3, 330, 1.7, 0.7],
]

const RINGS = [
  [72, 0.8], [124, 0.6], [178, 0.45], [232, 0.3],
]

export default function NetworkConstellation({ isSearching, accent, colAtlas, colLyra, colVega }) {
  return (
    <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
      <svg viewBox="0 0 640 470" width="100%" style={{ maxWidth: 720, maxHeight: '100%', overflow: 'visible' }} preserveAspectRatio="xMidYMid meet">
        {/* radar rings */}
        {RINGS.map(([r, op], i) => (
          <circle key={i} cx="320" cy="235" r={r} fill="none" stroke="var(--border-default)" strokeOpacity={op} />
        ))}

        {/* background network (scales to many) */}
        <g>
          {DOTS.map(([cx, cy, r, op], i) => (
            <circle key={i} cx={cx} cy={cy} r={r} fill="#bbb6ae" fillOpacity={op} />
          ))}
        </g>

        {/* edges to the three relevant agents */}
        <path id="e-atlas" d="M320 235 L367 90" fill="none" stroke={colAtlas} strokeOpacity="0.55" strokeWidth="1.6" />
        <path id="e-lyra" d="M320 235 L478 286" fill="none" stroke={colLyra} strokeOpacity="0.55" strokeWidth="1.6" />
        <path id="e-vega" d="M320 235 L181 291" fill="none" stroke={colVega} strokeOpacity="0.55" strokeWidth="1.6" />

        {isSearching && (
          <>
            <circle r="3.5" fill={accent}><animateMotion dur="1s" repeatCount="indefinite"><mpath href="#e-atlas" /></animateMotion></circle>
            <circle r="3.5" fill={accent}><animateMotion dur="1s" begin="0.18s" repeatCount="indefinite"><mpath href="#e-lyra" /></animateMotion></circle>
            <circle r="3.5" fill={accent}><animateMotion dur="1s" begin="0.36s" repeatCount="indefinite"><mpath href="#e-vega" /></animateMotion></circle>
            <circle cx="367" cy="90" r="18" fill={accent} style={{ transformBox: 'fill-box', transformOrigin: 'center', animation: 'bc-pulse 1.7s infinite ease-out' }} />
            <circle cx="478" cy="286" r="18" fill={accent} style={{ transformBox: 'fill-box', transformOrigin: 'center', animation: 'bc-pulse 1.7s .28s infinite ease-out' }} />
            <circle cx="181" cy="291" r="18" fill={accent} style={{ transformBox: 'fill-box', transformOrigin: 'center', animation: 'bc-pulse 1.7s .56s infinite ease-out' }} />
          </>
        )}

        {/* YOU (center) */}
        <circle cx="320" cy="235" r="22" fill="var(--ink)" />
        <g transform="translate(304.4,219.4) scale(1.3)" fill="none" stroke="var(--ivory)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="2.4" fill="var(--ivory)" stroke="none" />
          <path d="M16.6 7.4a6.5 6.5 0 0 1 0 9.2M7.4 16.6a6.5 6.5 0 0 1 0-9.2" />
        </g>
        <text x="320" y="276" textAnchor="middle" fontFamily="Hanken Grotesk, sans-serif" fontSize="13" fontWeight="700" fill="var(--text-primary)">You</text>
        <text x="320" y="291" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="9.5" fill="var(--text-muted)">1,248 in range</text>

        {/* ATLAS */}
        <circle cx="367" cy="90" r="17" fill={colAtlas} />
        <text x="367" y="90" textAnchor="middle" dominantBaseline="central" fontFamily="Hanken Grotesk, sans-serif" fontSize="15" fontWeight="600" fill="#fff">A</text>
        <text x="367" y="124" textAnchor="middle" fontFamily="Hanken Grotesk, sans-serif" fontSize="12.5" fontWeight="600" fill="var(--text-primary)">Atlas</text>
        <text x="367" y="139" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="10" fill="var(--text-muted)">billing-svc</text>

        {/* LYRA */}
        <circle cx="478" cy="286" r="17" fill={colLyra} />
        <text x="478" y="286" textAnchor="middle" dominantBaseline="central" fontFamily="Hanken Grotesk, sans-serif" fontSize="15" fontWeight="600" fill="#fff">L</text>
        <text x="478" y="320" textAnchor="middle" fontFamily="Hanken Grotesk, sans-serif" fontSize="12.5" fontWeight="600" fill="var(--text-primary)">Lyra</text>
        <text x="478" y="335" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="10" fill="var(--text-muted)">auth-core</text>

        {/* VEGA */}
        <circle cx="181" cy="291" r="17" fill={colVega} />
        <text x="181" y="291" textAnchor="middle" dominantBaseline="central" fontFamily="Hanken Grotesk, sans-serif" fontSize="15" fontWeight="600" fill="#fff">V</text>
        <text x="181" y="325" textAnchor="middle" fontFamily="Hanken Grotesk, sans-serif" fontSize="12.5" fontWeight="600" fill="var(--text-primary)">Vega</text>
        <text x="181" y="340" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="10" fill="var(--text-muted)">data-pipeline</text>
      </svg>
    </div>
  )
}
