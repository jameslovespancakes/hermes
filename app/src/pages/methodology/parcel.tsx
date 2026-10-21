export function Parcel() {
  return (
    <section className="method-opening" id="top" aria-labelledby="cover-title">
      <header className="opening-copy">
        <h1 id="cover-title">
          Unpack the
          <br />
          <em>estimate.</em>
        </h1>
        <p className="method-context">Data. Models. Cleaning.</p>
      </header>
      <figure className="method-figure parcel-figure">
        <div className="visual-surface parcel-surface">
          <svg
            className="parcel-scene"
            viewBox="180 -380 1080 1540"
            role="img"
            aria-labelledby="parcel-title"
            aria-describedby="parcel-desc"
          >
            <title id="parcel-title">A folding parcel reveals the layers behind an estimate</title>
            <desc id="parcel-desc">
              Four hinged cardboard flaps open beneath three sheets that rise vertically in a single stack,
              retaining the carton's isometric angle instead of turning toward the viewer. Each carries one
              icon: a database for data, a tree of nodes for models and a shield with a check for cleaning.
              Cleaning remains fully above the carton beneath Models and Data. The data sheet unfolds into the
              data chapter. This rendered parcel and its spacing are a visual metaphor, not study records,
              processing steps or quantitative measurements.
            </desc>
            <defs>
              <linearGradient id="parcel-shadow-fade-ramp" x2="1" y2="0.4">
                <stop offset="0.6" stopColor="#fff" />
                <stop offset="0.85" stopColor="#000" />
              </linearGradient>
              <mask id="parcel-shadow-fade" maskContentUnits="objectBoundingBox">
                <rect width={1} height={1} fill="url(#parcel-shadow-fade-ramp)" />
              </mask>
              <image
                id="parcel-flap-texture"
                href="/assets/images/method-parcel-lid.png"
                width={1440}
                height={1120}
              />
              <linearGradient id="parcel-inner-kraft" x2=".3" y2={1}>
                <stop stopColor="#c6a477" />
                <stop offset={1} stopColor="#a98559" />
              </linearGradient>
              <clipPath id="parcel-clip-left">
                <polygon />
              </clipPath>
              <clipPath id="parcel-clip-back">
                <polygon />
              </clipPath>
              <clipPath id="parcel-clip-right">
                <polygon />
              </clipPath>
              <clipPath id="parcel-clip-front">
                <polygon />
              </clipPath>
            </defs>
            <g id="parcel-assembly">
              <g id="parcel-ground" transform="matrix(.68 0 0 .68 230.4 436)">
                <image
                  href="/assets/images/method-parcel-shadow.png"
                  width={1440}
                  height={1120}
                  mask="url(#parcel-shadow-fade)"
                />
              </g>
              <g id="parcel-guides" className="parcel-guides">
                <path d="M415 -187V940M1025 -182V990" />
              </g>
              <g id="parcel-back" transform="matrix(.68 0 0 .68 230.4 436)">
                <image href="/assets/images/method-parcel-body.png" width={1440} height={1120} />
              </g>
              <g id="parcel-flaps-back" transform="matrix(.68 0 0 .68 230.4 436)">
                <g
                  className="flap-fallback"
                  fill="url(#parcel-inner-kraft)"
                  stroke="#967347"
                  strokeWidth="1.5"
                >
                  <polygon points="630.5,279.4 369.2,412.1 269.6,266.1 530.9,133.3" />
                  <polygon points="630.5,279.4 1070.8,413.2 1163.2,227.4 722.9,93.6" />
                </g>
                <g data-parcel-flap="left" style={{ visibility: 'hidden' }}>
                  <g clipPath="url(#parcel-clip-left)">
                    <use className="flap-outside" href="#parcel-flap-texture" />
                    <polygon className="flap-inside" fill="url(#parcel-inner-kraft)" />
                  </g>
                  <polygon className="flap-edge" fill="none" stroke="#967347" strokeWidth="1.5" />
                </g>
                <g data-parcel-flap="back" style={{ visibility: 'hidden' }}>
                  <g clipPath="url(#parcel-clip-back)">
                    <use className="flap-outside" href="#parcel-flap-texture" />
                    <polygon className="flap-inside" fill="url(#parcel-inner-kraft)" />
                  </g>
                  <polygon className="flap-edge" fill="none" stroke="#967347" strokeWidth="1.5" />
                </g>
              </g>
              <g
                id="parcel-sheet-checks"
                className="parcel-sheet"
                transform="matrix(.60796 .18475 -.55428 .28165 636.31124 340)"
              >
                <rect className="parcel-sheet-edge" y={9} width={640} height={400} rx={18} />
                <rect className="parcel-sheet-face" width={640} height={400} rx={18} />
                <g className="sheet-art checks" aria-hidden="true">
                  <rect className="sheet-panel" x={24} y={24} width={592} height={352} rx={14} />
                  <path
                    className="sheet-icon"
                    d="M320 82 430 120v80c0 70-50 110-110 130-60-20-110-60-110-130v-80Z"
                  />
                  <path className="sheet-icon" d="m268 204 36 36 70-74" />
                  <path className="sheet-icon thin" d="M470 96v32m-16-16h32M168 268v28m-14-14h28" />
                </g>
              </g>
              <g
                id="parcel-sheet-models"
                className="parcel-sheet"
                transform="matrix(.60796 .18475 -.55428 .28165 636.31124 20)"
              >
                <rect className="parcel-sheet-edge" y={9} width={640} height={400} rx={18} />
                <rect className="parcel-sheet-face" width={640} height={400} rx={18} />
                <g className="sheet-art models" aria-hidden="true">
                  <rect className="sheet-panel" x={24} y={24} width={592} height={352} rx={14} />
                  <path
                    className="sheet-icon thin"
                    d="M320 112C320 160 200 150 200 200M320 112v88M320 112C320 160 440 150 440 200M200 200c0 44-50 40-50 90M200 200c0 44 50 40 50 90M440 200c0 44-50 40-50 90M440 200c0 44 50 40 50 90"
                  />
                  {[
                    [320, 112, 20],
                    [200, 200, 15],
                    [320, 200, 15],
                    [440, 200, 15],
                    [150, 290, 11],
                    [250, 290, 11],
                    [390, 290, 11],
                    [490, 290, 11],
                  ].map(([cx, cy, r]) => (
                    <circle key={`${cx}-${cy}`} className="sheet-node" cx={cx} cy={cy} r={r} />
                  ))}
                </g>
              </g>
              <g
                id="parcel-sheet-data"
                className="parcel-sheet"
                transform="matrix(.60796 .18475 -.55428 .28165 636.31124 -300)"
              >
                <rect className="parcel-sheet-edge" y={9} width={640} height={400} rx={18} />
                <rect className="parcel-sheet-face" width={640} height={400} rx={18} />
                <g className="sheet-art data" aria-hidden="true">
                  <rect className="sheet-panel" x={24} y={24} width={592} height={352} rx={14} />
                  <ellipse className="sheet-icon" cx={320} cy={118} rx={118} ry={34} />
                  <path
                    className="sheet-icon"
                    d="M202 118v164c0 19 53 34 118 34s118-15 118-34V118M202 172c0 19 53 34 118 34s118-15 118-34M202 227c0 19 53 34 118 34s118-15 118-34"
                  />
                </g>
              </g>
              <g id="parcel-front" transform="matrix(.68 0 0 .68 230.4 436)">
                <image href="/assets/images/method-parcel-front.png" width={1440} height={1120} />
              </g>
              <g id="parcel-lid" transform="matrix(.68 0 0 .68 230.4 436)">
                <g
                  className="flap-fallback"
                  fill="url(#parcel-inner-kraft)"
                  stroke="#967347"
                  strokeWidth="1.5"
                >
                  <polygon points="1070.8,413.2 809.5,545.9 908.9,460.4 1170.4,327.6" />
                  <polygon points="369.2,412.1 809.5,545.9 702.5,487.6 262.2,353.8" />
                </g>
                <g data-parcel-flap="right" style={{ visibility: 'hidden' }}>
                  <g clipPath="url(#parcel-clip-right)">
                    <use className="flap-outside" href="#parcel-flap-texture" />
                    <polygon className="flap-inside" fill="url(#parcel-inner-kraft)" />
                  </g>
                  <polygon className="flap-edge" fill="none" stroke="#967347" strokeWidth="1.5" />
                </g>
                <g data-parcel-flap="front" style={{ visibility: 'hidden' }}>
                  <g clipPath="url(#parcel-clip-front)">
                    <use className="flap-outside" href="#parcel-flap-texture" />
                    <polygon className="flap-inside" fill="url(#parcel-inner-kraft)" />
                  </g>
                  <polygon className="flap-edge" fill="none" stroke="#967347" strokeWidth="1.5" />
                </g>
              </g>
              <g id="parcel-label-data" className="parcel-layer-label" transform="translate(1078 -155)">
                <path d="M-46-10H-12" />
                <text>Data</text>
              </g>
              <g id="parcel-label-models" className="parcel-layer-label" transform="translate(1078 165)">
                <path d="M-46-10H-12" />
                <text>Models</text>
              </g>
              <g id="parcel-label-checks" className="parcel-layer-label" transform="translate(1078 485)">
                <path d="M-46-10H-12" />
                <text>Cleaning</text>
              </g>
            </g>
          </svg>
        </div>
      </figure>
    </section>
  );
}
