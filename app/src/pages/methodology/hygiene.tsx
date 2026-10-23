// Data hygiene: four steps, each a headline number over a faint chart of the saved simulation.

const steps = [
  {
    id: 'validate',
    heading: 'Clean|inputs.',
    caption: 'Bad records are checked and repaired before training.',
    name: 'Validate',
    number: '88/92',
    label: 'corrupted days flagged',
    desc: 'Share of repeated courier timestamps per day rises in the simulated corrupted feed and stays near zero in the clean feed. The data contract flagged 88 of 92 corrupted days and no clean days.',
  },
  {
    id: 'clean',
    heading: 'Clean|inputs.',
    caption: 'Bad records are checked and repaired before training.',
    name: 'Clean',
    number: '100%',
    label: 're-sent copies removed',
    desc: 'Re-sent records per day in the simulated corrupted feed. DataGuard removed every injected copy and no real parcels. GPS repairs are estimates, not verified locations.',
  },
  {
    id: 'adapt',
    heading: 'Keep|watch.',
    caption: 'Live feeds are watched for delays and drift.',
    name: 'Adapt',
    number: '60.0',
    label: 'min error with late uploads, from 63.3',
    desc: 'Minutes of error saved per day by the delay-aware controls with uploads simulated 60 minutes late, growing as more couriers go stale. Overall error falls from 63.3 to 60.0 minutes.',
  },
  {
    id: 'monitor',
    heading: 'Keep|watch.',
    caption: 'Live feeds are watched for delays and drift.',
    name: 'Monitor',
    number: '47/47',
    label: 'corrupted days above the drift alert',
    desc: 'Daily input drift for the simulated corrupted and clean feeds. The corrupted feed passed the action threshold on all 47 monitored days; the clean feed on 3.',
  },
];

export function Hygiene() {
  return (
    <section
      className="method-section guard-section stepped"
      id="data-safeguards"
      data-method-section="guard"
      data-tone="peach"
      data-photo="0.3"
      tabIndex={0}
      aria-labelledby="guard-heading"
    >
      <div className="method-stage">
        <div className="method-composition">
          <header className="method-heading">
            <h2 id="guard-heading">
              <span>Clean</span>
              <br />
              <em>inputs.</em>
            </h2>
            <p className="method-context">Bad records are checked and repaired before training.</p>
          </header>
          <figure className="method-figure guard-mechanism">
            <div
              className="visual-surface guard-surface steps"
              role="list"
              aria-label="Four data hygiene steps"
            >
              {steps.map((step) => (
                <article
                  key={step.id}
                  className="step"
                  role="listitem"
                  data-heading={step.heading}
                  data-caption={step.caption}
                  aria-label={`${step.name}. ${step.desc}`}
                >
                  <svg
                    className="step-chart"
                    viewBox="0 0 640 440"
                    preserveAspectRatio="none"
                    aria-hidden="true"
                  >
                    <use href={`#hygiene-${step.id}-art`} />
                  </svg>
                  <div className="step-copy" aria-hidden="true">
                    <strong className="step-number">{step.number}</strong>
                    <span className="step-label">{step.label}</span>
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
