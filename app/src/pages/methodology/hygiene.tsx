// Data hygiene: the actual rules (from server/quality), and what they caught in the saved simulation.
import { Spec } from './spec';

type Step = {
  id: string;
  heading: string;
  caption: string;
  name: string;
  number: string;
  label: string;
  desc: string;
  spec?: readonly (readonly [string, string])[];
};

const steps: Step[] = [
  {
    id: 'load',
    heading: 'Clean|inputs.',
    caption: 'Bad records are checked and repaired before training.',
    name: 'Load',
    number: '4',
    label: 'rules drop records with no usable time',
    desc: 'Records are dropped only when their times cannot be used: no order id, a repeated order id, an unreadable time, or delivered before accepted. Across all five cities this removed 3 records.',
    spec: [
      ['No order id', 'dropped'],
      ['Repeated order id', 'every copy dropped'],
      ['Unreadable time', 'dropped'],
      ['Delivered before accepted', 'dropped (3 records in five cities)'],
    ],
  },
  {
    id: 'guard',
    heading: 'Clean|inputs.',
    caption: 'Bad records are checked and repaired before training.',
    name: 'Repair',
    number: '3',
    label: 'repairs before any model sees a record',
    desc: 'Re-sent copies of a scan are removed; an address more than 1.5 km from its area is moved to the area centre; courier-days where 30% or more scans share a timestamp are left out of training and flagged when live.',
    spec: [
      ['Re-sent copy', 'same courier, times, area and spot: removed'],
      ['Address 1.5+ km off its area', 'moved to the area centre'],
      ['30%+ scans share a timestamp', 'left out of training, flagged live'],
    ],
  },
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
    id: 'flags',
    heading: 'Keep|watch.',
    caption: 'Live feeds are watched for delays and drift.',
    name: 'Flag',
    number: '7',
    label: 'dashboard flags, each a fixed rule',
    desc: 'Every icon on the dashboard is a fixed threshold, not a model: scans 45 minutes late, no scans for 45 minutes, bulk-synced scans, a moved address, a removed copy, an ETA that jumped 60 minutes earlier or sits 15 km from its courier, and an ETA that slipped 90 minutes in an hour.',
    spec: [
      ['Lagging', 'scans reach us 45+ min late'],
      ['Silent', 'no scans from the courier for 45+ min'],
      ['Bulk', "30%+ of today's scans share a timestamp"],
      ['Moved', 'address was repaired'],
      ['Resent', 'a copy was removed'],
      ['Suspect', 'ETA 60+ min earlier in an hour, or 15+ km away'],
      ['Late', 'ETA slipped 90+ min in an hour'],
    ],
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
            <div className="visual-surface guard-surface steps" role="list" aria-label="Data hygiene steps">
              {steps.map((step) => (
                <article
                  key={step.id}
                  className="step"
                  role="listitem"
                  data-heading={step.heading}
                  data-caption={step.caption}
                  aria-label={`${step.name}. ${step.desc}`}
                >
                  {!step.spec && (
                    <svg
                      className="step-chart"
                      viewBox="0 0 640 440"
                      preserveAspectRatio="none"
                      aria-hidden="true"
                    >
                      <use href={`#hygiene-${step.id}-art`} />
                    </svg>
                  )}
                  <div className="step-copy" aria-hidden="true">
                    <strong className="step-number">{step.number}</strong>
                    <span className="step-label">{step.label}</span>
                  </div>
                  {step.spec && <Spec rows={step.spec} />}
                </article>
              ))}
            </div>
          </figure>
        </div>
      </div>
    </section>
  );
}
