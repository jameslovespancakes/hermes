// Benchmarks as a reel: each chapter is a full-screen panel, in colour or one stock photograph, that
// wipes up over the last, with a headline number and one thin line figure.

const lanes = [
  { name: 'LightGBM', value: 23.32 },
  { name: 'FDNET', value: 22.41 },
  { name: 'RankETPA', value: 21.36 },
  { name: 'M2G4RTP', value: 17.21 },
];

// Clock face for the look-ahead window: minutes from now become angles, 180 min = half a turn.
const dial = (minutes: number, r = 150) => {
  const a = (minutes / 360) * 2 * Math.PI - Math.PI / 2;
  return [300 + r * Math.cos(a), 200 + r * Math.sin(a)] as const;
};
const [arcX, arcY] = dial(120);

const rod = (minutes: number) => 360 - (minutes / 80) * 320;

export function Reel() {
  return (
    <section className="reel" aria-label="How the published benchmark compares with a fair test">
      <div className="reel-stage">
        <article className="reel-scene tone-cream" id="comparison-story" aria-labelledby="comparison-title">
          <div className="reel-copy">
            <h2 id="comparison-title">
              The published <em>lead.</em>
            </h2>
            <p className="reel-stat">
              <strong>17.21</strong>
              <span>min error, M2G4RTP</span>
            </p>
          </div>
          <svg
            className="reel-figure"
            viewBox="0 0 600 400"
            role="img"
            aria-label="Published LaDe Table 4 Yantai results: LightGBM 23.32, FDNET 22.41, RankETPA 21.36, M2G4RTP 17.21 minutes mean absolute error, from zero. Lower is better."
          >
            {lanes.map((lane, i) => {
              const y = 70 + i * 90;
              const end = (lane.value / 25) * 520;
              return (
                <g
                  key={lane.name}
                  className={lane.name === 'M2G4RTP' ? 'paper-row lead' : 'paper-row'}
                  data-value={lane.value}
                >
                  <text x={0} y={y - 14}>
                    {lane.name}
                  </text>
                  <path className="draw" d={`M0 ${String(y)}H${String(end)}`} pathLength={1} />
                  <text className="value" x={end + 14} y={y + 7}>
                    {lane.value}
                  </text>
                </g>
              );
            })}
          </svg>
        </article>

        <article className="reel-scene photo-courier" id="future-inputs" aria-labelledby="future-title">
          <div className="reel-photo" aria-hidden="true" />
          <div className="reel-copy">
            <h2 id="future-title">
              The future <em>picks the inputs.</em>
            </h2>
            <p className="reel-stat">
              <strong>2 hours</strong>
              <span>of future data decided which parcels were scored</span>
            </p>
          </div>
          <svg
            className="reel-figure"
            viewBox="0 0 600 400"
            role="img"
            aria-label="Invented example on a clock face: from now, the pipeline only keeps parcels finished within two hours. A box at 20 minutes and an envelope at 50 are kept; a bag at 180 minutes is dropped. Fictional parcels."
          >
            <circle className="faint" cx={300} cy={200} r={150} />
            <path
              className="draw thick"
              d={`M300 50A150 150 0 0 1 ${arcX.toFixed(1)} ${arcY.toFixed(1)}`}
              pathLength={1}
            />
            <text className="middle" x={300} y={36}>
              now
            </text>
            {(
              [
                ['benchmark-box', 20],
                ['benchmark-envelope', 50],
                ['benchmark-bag', 180],
              ] as const
            ).map(([icon, minutes]) => {
              const [x, y] = dial(minutes, 200);
              return (
                <g key={icon} className={minutes > 120 ? 'dropped' : undefined}>
                  <use href={`#${icon}`} x={x - 18} y={y - 18} width={36} height={36} />
                  <text className="middle" x={x} y={y + 40}>
                    {minutes} min
                  </text>
                </g>
              );
            })}
            <text className="middle big" x={300} y={212}>
              ≤ 2 h
            </text>
          </svg>
        </article>

        <article className="reel-scene tone-green" id="parcel-scoring" aria-labelledby="identity-title">
          <div className="reel-copy">
            <h2 id="identity-title">
              Right time. <em>Wrong parcel.</em>
            </h2>
            <p className="reel-stat">
              <strong>+9.7 min</strong>
              <span>more error once scored by parcel, not route position</span>
            </p>
          </div>
          <svg
            className="reel-figure"
            viewBox="0 0 600 400"
            role="img"
            aria-label="Invented example: the envelope was predicted for 10:20 and the box for 10:50, but they arrived the other way round. Scoring by time slot sees no error; scoring by parcel sees 30 minutes each. On the published pipeline, scoring by parcel raises error from 12.47 to 22.19 minutes."
          >
            <text className="middle" x={150} y={60}>
              10:20
            </text>
            <text className="middle" x={450} y={60}>
              10:50
            </text>
            <use href="#benchmark-envelope" x={120} y={90} width={60} height={60} />
            <use href="#benchmark-box" x={420} y={90} width={60} height={60} />
            <path className="draw" d="M150 170C150 250 450 230 450 300" pathLength={1} />
            <path className="draw" d="M450 170C450 250 150 230 150 300" pathLength={1} />
            <use href="#benchmark-box" x={120} y={310} width={60} height={60} />
            <use href="#benchmark-envelope" x={420} y={310} width={60} height={60} />
          </svg>
        </article>

        <article className="reel-scene tone-peach" id="matched-rerun" aria-labelledby="outcome-title">
          <div className="reel-copy">
            <h2 id="outcome-title">
              A fair <em>rerun.</em>
            </h2>
            <p className="reel-stat">
              <strong>24%</strong>
              <span>lower error on the same 149,263 predictions</span>
            </p>
          </div>
          <svg
            className="reel-figure"
            viewBox="0 0 600 400"
            role="img"
            aria-label="On 149,263 matched Yantai predictions, M2G4RTP has a mean absolute error of 77.11 minutes and Hermes 58.64, 24% lower, drawn as two rods from zero. A development rerun, not the published protocol."
          >
            <path className="faint" d="M60 360H540" />
            {(
              [
                ['M2G4RTP', 77.11, 200],
                ['Hermes', 58.64, 400],
              ] as const
            ).map(([name, value, x]) => (
              <g
                key={name}
                className={name === 'Hermes' ? 'matched-observation lead' : 'matched-observation'}
                data-value={value}
              >
                <path className="draw rod" d={`M${String(x)} 360V${rod(value).toFixed(1)}`} pathLength={1} />
                <text className="middle value" x={x} y={rod(value) - 18}>
                  {value}
                </text>
                <text className="middle" x={x} y={390}>
                  {name}
                </text>
              </g>
            ))}
          </svg>
        </article>
      </div>
    </section>
  );
}
