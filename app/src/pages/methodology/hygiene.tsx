// Data hygiene: eight steps, each a headline number over a faint chart of the saved simulation (Yantai and Jilin).

const steps = [
  {
    id: 'validate',
    heading: 'Clean|inputs.',
    caption: 'A cheap scanner app spreads to 60% of couriers, July to September.',
    name: 'Validate',
    number: '175/184',
    label: 'bad days caught by the daily data contract',
    desc: 'Share of repeated courier timestamps per day in the simulated cheap-app feed and in the clean feed. The daily data contract flagged 175 of 184 corrupted days across Yantai and Jilin, and 4 of 184 clean days.',
  },
  {
    id: 'clean',
    heading: 'Clean|inputs.',
    caption: 'A cheap scanner app spreads to 60% of couriers, July to September.',
    name: 'Clean',
    number: '100%',
    label: 'of re-sent copies removed, no real parcel lost',
    desc: 'Re-sent records per day in the simulated feed. The guard removed every injected copy and no real parcels. Address repairs are estimates, not verified locations.',
  },
  {
    id: 'weigh',
    heading: 'Clean|inputs.',
    caption: 'A cheap scanner app spreads to 60% of couriers, July to September.',
    name: 'Weigh',
    number: '0.11',
    label: 'how much a bad record counts in training; clean ones 1.00',
    desc: 'Average training weight per day of the cheap app’s records. Courier-days with same-minute bursts or impossible travel count for less, by a share learned from all couriers; nothing is deleted.',
  },
  {
    id: 'correct',
    heading: 'Clean|inputs.',
    caption: 'A cheap scanner app spreads to 60% of couriers, July to September.',
    name: 'Correct',
    number: '20 → 2.6',
    label: 'min of clock error after correcting fast devices',
    desc: 'Clock error per day on devices running 20 minutes fast. Deliveries stamped after the server received them reveal the offset, which is then removed using each device’s earlier uploads.',
  },
  {
    id: 'adapt',
    heading: 'Keep|watch.',
    caption: 'Late uploads, lost scans, frozen habits, no retraining. September 16 to 30.',
    name: 'Adapt',
    number: '53.4',
    label: 'min error with late uploads, from 62.2',
    desc: 'Minutes of error saved per day by the stale-feed model with uploads 60 minutes late, growing as more couriers go stale. Error falls from 62.2 to 53.4 minutes.',
  },
  {
    id: 'flag',
    heading: 'Keep|watch.',
    caption: 'Late uploads, lost scans, frozen habits, no retraining. September 16 to 30.',
    name: 'Flag',
    number: '13%',
    label: 'of lost-scan ETAs flagged, on the day of the miss',
    desc: 'Lost scans per day as up to 60% of couriers lose 30% of their scans. A parcel is flagged the day its courier visits its area and leaves without scanning it; the flag stops when the day ends, and the estimate is not repaired. 1.7% of genuinely pending parcels are flagged.',
  },
  {
    id: 'monitor',
    heading: 'Keep|watch.',
    caption: 'Late uploads, lost scans, frozen habits, no retraining. September 16 to 30.',
    name: 'Monitor',
    number: '94/94',
    label: 'corrupted days above the drift alarm',
    desc: 'Daily input drift for the corrupted and clean feeds. Every corrupted day crossed the alarm; clean days crossed it once in Yantai but every day in Jilin, whose operation grew four-fold.',
  },
  {
    id: 'retrain',
    heading: 'Keep|watch.',
    caption: 'Late uploads, lost scans, frozen habits, no retraining. September 16 to 30.',
    name: 'Retrain',
    number: '50.4',
    label: 'min error retrained monthly, from 56.7 never retrained',
    desc: 'Records per day in Jilin as its operation grows. A model trained on July data and never updated errs by 56.7 minutes in late September; retraining monthly brings it to 50.4.',
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
            <p className="method-context">
              A cheap scanner app spreads to 60% of couriers, July to September: bulk-synced times, 1 km GPS
              errors, re-sent records, clocks 20 min fast.
            </p>
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
