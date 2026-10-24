// Results: the simulated bad-data test, before and after the data-hygiene controls. Each step draws
// two columns on a zero-based scale, without and with the controls, against a clean-data line.
// Mean absolute error in minutes from evidence/baddata/results: Yantai and Jilin averaged (four conditions and new
// faults over 3 seeds; over time and the unseen fault from the first run).

const scale = 100;
const clean = 50.38;
const height = (minutes: number) => `${((minutes / scale) * 100).toFixed(2)}%`;

const conditions = [
  {
    id: 'reference',
    name: 'Clean data',
    before: 50.38,
    after: 50.21,
    label: 'min error on clean data, with or without controls',
  },
  {
    id: 'stale',
    name: 'Late uploads',
    before: 62.24,
    after: 53.41,
    label: 'min error with late uploads, 62.2 without',
  },
  {
    id: 'quality',
    name: 'Bad records',
    before: 71.57,
    after: 60.66,
    label: 'min error with bad records, 71.6 without',
  },
  {
    id: 'combined',
    name: 'Both at once',
    before: 81.09,
    after: 60.95,
    label: 'min error with both, 81.1 without',
  },
  {
    id: 'time',
    name: 'Three months on',
    before: 73.15,
    after: 65.39,
    label: 'min error after three monthly retrains on bad records, 73.2 without',
  },
  {
    id: 'unseen',
    name: 'An unseen fault',
    before: 61.94,
    after: 55.84,
    label: 'min error with timestamps randomly off by up to 30 min, 61.9 without',
  },
  {
    id: 'lost',
    name: 'Lost scans',
    before: 64.34,
    after: 63.56,
    label: 'min error when 30% of scans never arrive: flagged, not repaired',
  },
];

export function Results() {
  return (
    <section
      className="method-section outcome-section stepped"
      id="results"
      data-method-section="results"
      data-tone="cream"
      tabIndex={0}
      aria-labelledby="results-heading"
    >
      <div className="method-stage">
        <div className="method-composition">
          <header className="method-heading">
            <h2 id="results-heading">
              Hold the
              <br />
              <em>results.</em>
            </h2>
            <p className="method-context">Yantai and Jilin, 3 runs each, September 16 to 30.</p>
            <a className="dataset-source" href="/results">
              Every training, validation and test graph <span aria-hidden="true">→</span>
            </a>
          </header>
          <figure className="method-figure results-editorial">
            <div
              className="visual-surface results-surface steps"
              role="list"
              aria-label="Bad-data test results"
            >
              {conditions.map((c) => (
                <article
                  key={c.id}
                  className="step"
                  role="listitem"
                  aria-label={`${c.name}: mean absolute error ${c.before.toFixed(1)} minutes without the controls and ${c.after.toFixed(1)} with them, against ${clean.toFixed(1)} on clean data. Simulated corruption on real Yantai and Jilin records, not live operation.`}
                >
                  <div className="columns" aria-hidden="true">
                    <div className="reference" style={{ bottom: height(clean) }}>
                      <span>Clean data {clean.toFixed(1)}</span>
                    </div>
                    <div className="column other" style={{ height: height(c.before) }}>
                      <span>
                        {c.before.toFixed(1)}
                        <small>without</small>
                      </span>
                    </div>
                    <div className="column" style={{ height: height(c.after) }}>
                      <span>
                        {c.after.toFixed(1)}
                        <small>with controls</small>
                      </span>
                    </div>
                  </div>
                  <div className="step-copy" aria-hidden="true">
                    <strong className="step-number">{c.after.toFixed(1)}</strong>
                    <span className="step-label">{c.label}</span>
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
