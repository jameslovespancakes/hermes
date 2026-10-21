// Data: four steps. First the whole dataset as five faint city maps of real drop-off points, then
// the daily record volume with each time window it serves: learn, decide when to stop, measure,
// and October, held back untouched.
import daily from './daily.json';
import points from './points.json';

const width = 640;
const top = 40;
const bottom = 420;
const max = Math.max(...daily.records);
const x = (i: number) => (i / (daily.days.length - 1)) * width;
const at = (day: string) => x(daily.days.indexOf(day));
const volume =
  daily.records
    .map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${(bottom - (v / max) * (bottom - top)).toFixed(1)}`)
    .join('') + `L${width} ${bottom + 40}L0 ${bottom + 40}Z`;

const windows = [
  {
    id: 'learn',
    from: '0501',
    to: '0831',
    number: '800,000',
    label: 'checkpoints to learn from, before Sep 1',
    desc: 'Checkpoints before September 1 train the models.',
  },
  {
    id: 'stop',
    from: '0901',
    to: '0915',
    number: '181,388',
    label: 'checkpoints to decide when to stop, Sep 1–15',
    desc: 'Checkpoints from September 1 to 15 choose when boosting stops.',
  },
  {
    id: 'measure',
    from: '0916',
    to: '0930',
    number: '155,296',
    label: 'held-out checkpoints to measure error, Sep 16–30',
    desc: 'Checkpoints from September 16 to 30 are held out and only used to measure error.',
  },
  {
    id: 'untouched',
    from: '1001',
    to: '1031',
    number: '1.1M',
    label: 'October records, untouched, kept for a final test',
    desc: 'No model has seen October. It is held back so a final check can use data that never influenced development.',
  },
];

export function Dataset() {
  return (
    <section
      className="method-section split-section stepped"
      id="data-split"
      data-method-section="split"
      data-tone="cream"
      tabIndex={0}
      aria-labelledby="split-heading"
    >
      <div className="method-stage">
        <div className="method-composition">
          <header className="method-heading">
            <h2 id="split-heading">
              Start with
              <br />
              <em>the data.</em>
            </h2>
            <p className="method-context">Every LaDe-D delivery record, across five cities.</p>
            <a
              className="dataset-source"
              href="https://huggingface.co/datasets/Cainiao-AI/LaDe/tree/be2cec02775cafc8d52230303f32134382bcc50b"
              target="_blank"
              rel="noopener noreferrer"
            >
              View the dataset on Hugging Face <span aria-hidden="true">↗</span>
            </a>
          </header>
          <figure className="method-figure dataset-figure">
            <div
              className="visual-surface dataset-surface steps"
              role="list"
              aria-label="How the data is used"
            >
              <article
                className="step"
                role="listitem"
                aria-label="Faint maps of sampled drop-off points for Shanghai, Hangzhou, Chongqing, Yantai and Jilin, each sized by its share of LaDe-D's 4,514,661 delivery records. Coordinates are as published and privacy-perturbed; the maps are context, not routes."
              >
                <svg className="data-map" viewBox="0 0 720 420" aria-hidden="true">
                  <g id="dataset-artwork" className="data-points">
                    {points.map(([px, py], i) => (
                      <circle key={i} cx={px} cy={py} r={1.2} />
                    ))}
                  </g>
                </svg>
                <div className="step-copy" aria-hidden="true">
                  <strong className="step-number">4.5M</strong>
                  <span className="step-label">delivery records in LaDe-D</span>
                </div>
              </article>
              {windows.map((w) => (
                <article
                  key={w.id}
                  className="step"
                  role="listitem"
                  aria-label={`${w.number} ${w.label}. ${w.desc} Shown over daily record volume, May to October.`}
                >
                  <svg
                    className="step-chart"
                    viewBox="0 0 640 440"
                    preserveAspectRatio="none"
                    aria-hidden="true"
                  >
                    <defs>
                      <clipPath id={`window-${w.id}`}>
                        <rect x={at(w.from)} width={at(w.to) - at(w.from)} height={480} />
                      </clipPath>
                    </defs>
                    <g className="step-art">
                      <path className="volume" d={volume} />
                      <path className="volume active" d={volume} clipPath={`url(#window-${w.id})`} />
                    </g>
                  </svg>
                  <div className="step-copy" aria-hidden="true">
                    <strong className="step-number">{w.number}</strong>
                    <span className="step-label">{w.label}</span>
                  </div>
                </article>
              ))}
            </div>
          </figure>
        </div>
      </div>
    </section>
  );
}
