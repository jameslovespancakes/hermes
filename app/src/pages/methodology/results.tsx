// Results: the simulated bad-data test, before and after the data-hygiene controls. Each step draws
// two columns on a zero-based scale, without and with the controls, against a clean-data line.
// Mean absolute error in minutes from evidence/baddata/results (four_conditions).

const scale = 100;
const clean = 58.45;
const height = (minutes: number) => `${((minutes / scale) * 100).toFixed(2)}%`;

const conditions = [
  {
    id: 'reference',
    name: 'Clean data',
    before: 58.45,
    after: 58.48,
    label: 'min error on clean data, with or without controls',
  },
  {
    id: 'stale',
    name: 'Late uploads',
    before: 63.34,
    after: 60.01,
    label: 'min error with late uploads, 63.3 without',
  },
  {
    id: 'quality',
    name: 'Bad records',
    before: 80.07,
    after: 66.66,
    label: 'min error with bad records, 80.1 without',
  },
  {
    id: 'combined',
    name: 'Both at once',
    before: 83.98,
    after: 66.87,
    label: 'min error with both, 84.0 without',
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
            <p className="method-context">Simulated bad data, before and after the controls.</p>
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
                  aria-label={`${c.name}: mean absolute error ${c.before.toFixed(1)} minutes without the controls and ${c.after.toFixed(1)} with them, against ${clean.toFixed(1)} on clean data. Simulated corruption on real Yantai records, not live operation.`}
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
