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

// Where real arrivals fell around the ETA, every Yantai ETA on Sep 16-30: the distribution of (arrival - ETA) from
// -180 to +240 min in 5-minute steps, rebuilt from each distance band's measured percentiles and weighted by its
// share. Shaded: P50 and P80, the ranges either side of the ETA holding half and 80% of arrivals.
const curve = [
  0.005, 0.009, 0.011, 0.013, 0.015, 0.017, 0.02, 0.023, 0.027, 0.03, 0.032, 0.035, 0.038, 0.041, 0.046,
  0.053, 0.064, 0.081, 0.101, 0.122, 0.144, 0.164, 0.182, 0.201, 0.23, 0.269, 0.316, 0.374, 0.444, 0.524,
  0.608, 0.7, 0.798, 0.898, 0.977, 0.999, 0.947, 0.841, 0.719, 0.606, 0.508, 0.426, 0.363, 0.314, 0.268,
  0.228, 0.201, 0.18, 0.157, 0.135, 0.118, 0.106, 0.098, 0.093, 0.092, 0.088, 0.08, 0.068, 0.057, 0.05, 0.048,
  0.048, 0.048, 0.048, 0.048, 0.048, 0.048, 0.048, 0.048, 0.048, 0.048, 0.048, 0.047, 0.046, 0.044, 0.042,
  0.04, 0.038, 0.036, 0.034, 0.032, 0.03, 0.027, 0.022, 0.014,
];
const P50 = 27;
const P80 = 71;
const minute = (m: number) => 30 + ((m + 180) / 420) * 340;
const BASE = 200;
const HEIGHT = 140;

export function Spread() {
  const points = curve.map((v, k) => [minute(-180 + k * 5), BASE - v * HEIGHT] as const);
  const line = points.map(([x, y], k) => `${k ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join('');
  const area = (from: number, to: number) => {
    const inside = points.filter((_, k) => -180 + k * 5 >= from && -180 + k * 5 <= to);
    return `M${inside[0][0].toFixed(1)} ${String(BASE)}${inside.map(([x, y]) => `L${x.toFixed(1)} ${y.toFixed(1)}`).join('')}L${inside[inside.length - 1][0].toFixed(1)} ${String(BASE)}Z`;
  };
  return (
    <svg
      viewBox="0 0 400 300"
      role="img"
      aria-label="Every Yantai ETA, September 16 to 30: how far real arrivals fell from the ETA, as one curve peaking just before the ETA with a longer late tail. Half arrived within 27 minutes of the ETA (P50), 80% within 71 minutes (P80)."
    >
      <path className="spread-fill wide" d={area(-P80, P80)} data-value={P80} />
      <path className="spread-fill" d={area(-P50, P50)} data-value={P50} />
      <path className="line" d={line} />
      <path className="faint" d={`M${minute(-180).toFixed(1)} ${String(BASE)}H${minute(240).toFixed(1)}`} />
      <path className="faint" d={`M${minute(0).toFixed(1)} ${String(BASE)}V${String(BASE - HEIGHT - 8)}`} />
      {[-120, -60, 0, 60, 120, 180].map((m) => (
        <text key={m} className="middle" x={minute(m)} y={BASE + 18}>
          {m === 0 ? 'ETA' : `${m > 0 ? '+' : '−'}${String(Math.abs(m) / 60)} h`}
        </text>
      ))}
      <text className="middle" x={200} y={BASE + 50}>
        P50 ±27 min
      </text>
      <text className="middle" x={200} y={BASE + 72}>
        P80 ±71 min
      </text>
    </svg>
  );
}

// What a customer sees for a parcel the ETA puts 20 minutes away (Yantai window: 13 min early to 52 min late).
export function Window() {
  const x = (m: number) => 60 + (m + 20) * 3.6;
  return (
    <svg
      viewBox="0 0 400 300"
      role="img"
      aria-label="Invented example: the ETA says 10:20, twenty minutes from now. The customer sees 'Arrives between 10:07 and 11:12', the window where 80% of parcels with an ETA like this really arrived."
    >
      <text className="middle" x={200} y={58}>
        Arrives between
      </text>
      <text className="middle big" x={200} y={108}>
        10:07 – 11:12
      </text>
      <path className="faint" d={`M${String(x(-20))} 200H${String(x(70))}`} />
      <path className="line accent" d={`M${String(x(-13))} 200H${String(x(52))}`} />
      <circle className="link-dot" cx={x(0)} cy={200} r={5} />
      <text className="middle" x={x(0)} y={180}>
        ETA 10:20
      </text>
      <text className="middle" x={x(-13)} y={232}>
        10:07
      </text>
      <text className="middle" x={x(52)} y={232}>
        11:12
      </text>
    </svg>
  );
}
