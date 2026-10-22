// Models: the boosting fan (early trees miss widely, later ones correct the remaining error), the
// stop-order model feeding the ETA model (illustrative, not fitted trees), then what is actually trained
// per city and what goes in (from server/models and server/config).
import { Spec } from './spec';

const chain = [
  ['Next zone', 'LightGBM classifier, 16 inputs: which group of about 10 buildings comes next'],
  ['Stop order', "LightGBM regressor, 47 inputs: each parcel's place in the coming stops"],
  ['ETA x 3', 'LightGBM regressor, 94 inputs, 3 seeds averaged: minutes until delivery'],
  ['Later day x 2', 'classifier and regressor: will it slip to another day, and when'],
  ['Stale feed', 'LightGBM regressor, 96 inputs: replaces the ETA when uploads lag'],
  ['Risk', 'LightGBM regressor: expected error size, flags the riskiest 10%'],
] as const;

const inputs = [
  ['The parcel', 'area, address, region, distance from pickup, hour accepted'],
  ['Past days', 'usual delivery times for this courier and area, shift end, area-to-area moves'],
  ['Right now', 'parcels held, pace today, distance from the courier, area activity in the last hour'],
  ['Stop order', "stops predicted ahead, and those stops times today's pace"],
] as const;

const width = 720;
const trees = 48;
const target = (x: number) => 380 - 330 * (x / width) ** 1.4;

function fanLine(k: number) {
  const amplitude = 150 * 0.93 ** k;
  const frequency = 0.006 + (k % 7) * 0.0015;
  const phase = k * 1.7;
  return Array.from({ length: 49 }, (_, i) => {
    const x = (i / 48) * width;
    const y = target(x) + amplitude * Math.sin(x * frequency + phase);
    return `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join('');
}

const fan = Array.from({ length: trees }, (_, k) => fanLine(k));

// Two horizontal trees: the order model's leaves funnel into the ETA model's root.
type Branch = { x1: number; y1: number; x2: number; y2: number };
function grow(
  x: number,
  y: number,
  spread: number,
  step: number,
  depth: number,
  out: Branch[],
  leaves: number[][],
) {
  if (depth === 0) {
    leaves.push([x, y]);
    return;
  }
  for (const side of [-1, 1]) {
    const nx = x + step;
    const ny = y + side * spread;
    out.push({ x1: x, y1: y, x2: nx, y2: ny });
    grow(nx, ny, spread / 2, step, depth - 1, out, leaves);
  }
}
const orderBranches: Branch[] = [];
const orderLeaves: number[][] = [];
grow(40, 290, 72, 85, 3, orderBranches, orderLeaves);
const eta = { x: 400, y: 210 };
const etaBranches: Branch[] = [];
const etaLeaves: number[][] = [];
grow(eta.x, eta.y, 64, 85, 3, etaBranches, etaLeaves);
const finish = { x: 760, y: 170 };
const curve = ([x, y]: number[], to: { x: number; y: number }) =>
  `M${x} ${y}C${x + 40} ${y} ${to.x - 40} ${to.y} ${to.x} ${to.y}`;
const branch = (b: Branch) => `M${b.x1} ${b.y1}C${b.x1 + 40} ${b.y1} ${b.x2 - 40} ${b.y2} ${b.x2} ${b.y2}`;

export function Models() {
  return (
    <section
      className="method-section stack-section stepped"
      id="model-stack"
      data-method-section="stack"
      data-tone="green"
      data-photo="0.22"
      tabIndex={0}
      aria-labelledby="stack-heading"
    >
      <div className="method-stage">
        <div className="method-composition">
          <header className="method-heading">
            <h2 id="stack-heading">
              Order first.
              <br />
              <em>Then time.</em>
            </h2>
            <p className="method-context">Fixed models. Fresh context.</p>
          </header>
          <figure className="method-figure model-mechanism">
            <div
              className="visual-surface model-surface model-stage steps"
              role="list"
              aria-label="How the trees build an ETA"
            >
              <article
                className="step"
                role="listitem"
                aria-label="Each LightGBM model adds trees until its error on held-out August days stops falling, up to 3,000. The faint lines illustrate boosting: early trees miss widely and each later tree corrects the remaining error, converging on one estimate. Illustrative, not fitted trees. Models train offline and stay fixed during replay."
              >
                <svg
                  className="ensemble fan"
                  viewBox="0 0 720 440"
                  preserveAspectRatio="none"
                  aria-hidden="true"
                >
                  <g id="model-artwork">
                    {fan.map((d, k) => (
                      <path
                        key={k}
                        className="ensemble-tree"
                        d={d}
                        pathLength={1}
                        data-model-line="transfer"
                        style={{ opacity: 0.08 + (k / trees) * 0.3 }}
                      />
                    ))}
                    <path
                      className="ensemble-estimate"
                      d={fanLine(trees * 4)}
                      pathLength={1}
                      data-model-line="transfer"
                    />
                  </g>
                </svg>
                <div className="step-copy" aria-hidden="true">
                  <strong className="step-number">3,000</strong>
                  <span className="step-label">trees at most, each correcting the last</span>
                </div>
              </article>
              <article
                className="step"
                role="listitem"
                aria-label="Two models in sequence. A stop-order model predicts each courier's next stops, getting the next three right 69.2% of the time across five cities; every branch of its output feeds the ETA model, which predicts minutes remaining. Illustrative tree shapes, not fitted trees."
              >
                <svg className="ensemble" viewBox="0 0 800 440" aria-hidden="true">
                  {orderBranches.map((b, i) => (
                    <path key={`o${i}`} className="link-branch" d={branch(b)} />
                  ))}
                  {orderLeaves.map((leaf, i) => (
                    <path key={`m${i}`} className="link-merge" d={curve(leaf, eta)} />
                  ))}
                  {etaBranches.map((b, i) => (
                    <path key={`e${i}`} className="link-branch strong" d={branch(b)} />
                  ))}
                  {etaLeaves.map((leaf, i) => (
                    <path key={`f${i}`} className="link-merge" d={curve(leaf, finish)} />
                  ))}
                  {[...orderLeaves, ...etaLeaves].map(([x, y], i) => (
                    <circle key={`d${i}`} className="link-dot" cx={x} cy={y} r={3} />
                  ))}
                  <circle className="link-root" cx={40} cy={290} r={7} />
                  <circle className="link-root" cx={eta.x} cy={eta.y} r={9} />
                  <circle className="link-root" cx={finish.x} cy={finish.y} r={11} />
                  <text className="link-label start" x={40} y={150}>
                    Stop-order model
                  </text>
                  <text className="link-label" x={eta.x} y={eta.y + 110}>
                    ETA model
                  </text>
                  <text className="link-label" x={finish.x} y={finish.y - 24}>
                    Minutes
                  </text>
                </svg>
                <div className="step-copy" aria-hidden="true">
                  <strong className="step-number">69.2%</strong>
                  <span className="step-label">
                    of next three stops right across five cities, fed to the ETA
                  </span>
                </div>
              </article>
              <article
                className="step"
                role="listitem"
                aria-label={`What is trained for each city: ${chain.map(([n, d]) => `${n}, ${d}`).join('; ')}.`}
              >
                <div className="step-copy" aria-hidden="true">
                  <strong className="step-number">9</strong>
                  <span className="step-label">models trained per city, in one chain</span>
                </div>
                <Spec rows={chain} />
              </article>
              <article
                className="step"
                role="listitem"
                aria-label={`The ETA model's 94 inputs, in four groups: ${inputs.map(([n, d]) => `${n}, ${d}`).join('; ')}.`}
              >
                <div className="step-copy" aria-hidden="true">
                  <strong className="step-number">94</strong>
                  <span className="step-label">inputs to every ETA, all known at that moment</span>
                </div>
                <Spec rows={inputs} />
              </article>
            </div>
          </figure>
        </div>
      </div>
    </section>
  );
}
