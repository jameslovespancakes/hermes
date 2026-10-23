// The tour figures: thin lines on a soft card. Parcels and times in the audit figures are invented.

// LaDe Table 4, each method's MAE averaged over the paper's three cities (Shanghai, Yantai, Chongqing).
const lanes = [
  { name: 'LightGBM', value: 21.59 },
  { name: 'FDNET', value: 21.25 },
  { name: 'RankETPA', value: 20.16 },
  { name: 'M2G4RTP', value: 14.47 },
];

export function Lanes() {
  return (
    <svg
      viewBox="0 0 400 300"
      role="img"
      aria-label="Published LaDe Table 4 results averaged over Shanghai, Yantai and Chongqing: LightGBM 21.59, FDNET 21.25, RankETPA 20.16, M2G4RTP 14.47 minutes mean absolute error, from zero. Lower is better."
    >
      {lanes.map((lane, i) => {
        const y = 60 + i * 62;
        const end = 24 + (lane.value / 25) * 300;
        return (
          <g
            key={lane.name}
            className={lane.name === 'M2G4RTP' ? 'paper-row lead' : 'paper-row'}
            data-value={lane.value}
          >
            <text x={24} y={y - 12}>
              {lane.name}
            </text>
            <path className="line" d={`M24 ${String(y)}H${String(end)}`} />
            <text className="value" x={end + 10} y={y + 5}>
              {lane.value}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// Minutes from now as angles on a clock face; the window covers the first two hours.
const dial = (minutes: number, r: number) => {
  const a = (minutes / 360) * 2 * Math.PI - Math.PI / 2;
  return [200 + r * Math.cos(a), 150 + r * Math.sin(a)] as const;
};

export function Clock() {
  const [x, y] = dial(120, 100);
  return (
    <svg
      viewBox="0 0 400 300"
      role="img"
      aria-label="Invented example on a clock face: from now, only parcels finished within two hours are kept. A box at 20 minutes and an envelope at 50 are kept; a bag at 180 minutes is dropped."
    >
      <circle className="faint" cx={200} cy={150} r={100} />
      <path className="line accent" d={`M200 50A100 100 0 0 1 ${x.toFixed(1)} ${y.toFixed(1)}`} />
      <text className="middle" x={200} y={38}>
        now
      </text>
      <text className="middle big" x={200} y={160}>
        ≤ 2 h
      </text>
      {(
        [
          ['benchmark-box', 20],
          ['benchmark-envelope', 50],
          ['benchmark-bag', 180],
        ] as const
      ).map(([icon, minutes]) => {
        const [px, py] = dial(minutes, 132);
        return (
          <use
            key={icon}
            className={minutes > 120 ? 'dropped' : undefined}
            href={`#${icon}`}
            x={px - 14}
            y={py - 14}
            width={28}
            height={28}
          />
        );
      })}
    </svg>
  );
}

export function Swap() {
  return (
    <svg
      viewBox="0 0 400 300"
      role="img"
      aria-label="Invented example: the envelope was predicted for 10:20 and the box for 10:50, but they arrived the other way round. Matching by time slot sees no error; matching by parcel sees 30 minutes each."
    >
      <text className="middle" x={120} y={40}>
        10:20
      </text>
      <text className="middle" x={280} y={40}>
        10:50
      </text>
      <use href="#benchmark-envelope" x={100} y={58} width={40} height={40} />
      <use href="#benchmark-box" x={260} y={58} width={40} height={40} />
      <path className="line" d="M120 112C120 160 280 150 280 196M280 112C280 160 120 150 120 196" />
      <use href="#benchmark-box" x={100} y={204} width={40} height={40} />
      <use href="#benchmark-envelope" x={260} y={204} width={40} height={40} />
    </svg>
  );
}

const rod = (minutes: number) => 250 - (minutes / 80) * 200;

export function Rods() {
  return (
    <svg
      viewBox="0 0 400 300"
      role="img"
      aria-label="On 149,263 matched Yantai predictions, M2G4RTP has a mean absolute error of 77.11 minutes and Hermes 58.64, 24% lower, drawn as two bars from zero."
    >
      <path className="faint" d="M60 250H340" />
      {(
        [
          ['M2G4RTP', 77.11, 140],
          ['Hermes', 58.64, 260],
        ] as const
      ).map(([name, value, x]) => (
        <g
          key={name}
          className={name === 'Hermes' ? 'matched-observation lead' : 'matched-observation'}
          data-value={value}
        >
          <path className="rod" d={`M${String(x)} 250V${rod(value).toFixed(1)}`} />
          <text className="middle value" x={x} y={rod(value) - 14}>
            {value}
          </text>
          <text className="middle" x={x} y={276}>
            {name}
          </text>
        </g>
      ))}
    </svg>
  );
}
