// Faint Robinhood-style charts for the data-hygiene steps, from the saved simulated-corruption
// experiment (evidence/baddata/results). Corrupted or uncontrolled series first, comparison second.
import series from './hygiene.json';

const width = 640;
const top = 20;
const bottom = 420;

// Light 3-day smoothing keeps the line clean without changing its trend.
const smooth = (values: number[]) =>
  values.map((_, i) => {
    const near = values.slice(Math.max(0, i - 1), i + 2);
    return near.reduce((sum, v) => sum + v, 0) / near.length;
  });

type Kind = 'bars' | 'line' | 'area' | 'stems';

// Each chart fills the frame: lowest value bottom-left, highest top-right.
function Chart({ id, kind, data }: { id: string; kind: Kind; data: number[] }) {
  const values = kind === 'bars' ? data : smooth(data);
  const [min, max] = [Math.min(...values), Math.max(...values)];
  const xy = values.map((v, i) => [
    (i / (values.length - 1)) * width,
    bottom - ((v - min) / (max - min)) * (bottom - top),
  ]);
  const line = xy.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join('');
  const step = width / values.length;
  return (
    <g id={`hygiene-${id}-art`} className="step-art">
      {kind === 'bars' &&
        xy.map(([x, y], i) => (
          <rect
            key={i}
            className="step-bar"
            x={x - step * 0.3}
            y={y}
            width={step * 0.6}
            height={bottom + 40 - y}
            rx={1}
          />
        ))}
      {kind === 'area' && (
        <path className="step-fill" d={`${line}L${width} ${bottom + 40}L0 ${bottom + 40}Z`} />
      )}
      {kind === 'stems' &&
        xy.map(([x, y], i) => (
          <g key={i}>
            <path className="step-stem" d={`M${x.toFixed(1)} ${bottom + 40}V${y.toFixed(1)}`} />
            <circle className="step-dot" cx={x} cy={y} r={3.5} />
          </g>
        ))}
      {(kind === 'line' || kind === 'area') && <path className="step-line" d={line} pathLength={1} />}
    </g>
  );
}

// Late uploads: minutes saved per day by the delay-aware controls.
const [late, controlled] = series.adapt;
const saved = late.map((v, i) => v - controlled[i]);

export function Figures() {
  return (
    <>
      <Chart id="validate" kind="bars" data={series.validate[0]} />
      <Chart id="clean" kind="line" data={series.clean[0]} />
      <Chart id="weigh" kind="area" data={series.weigh[0]} />
      <Chart id="correct" kind="bars" data={series.correct[0]} />
      <Chart id="adapt" kind="area" data={saved} />
      <Chart id="flag" kind="stems" data={series.flag[0]} />
      <Chart id="monitor" kind="stems" data={series.monitor[0]} />
      <Chart id="retrain" kind="line" data={series.retrain[0]} />
    </>
  );
}
