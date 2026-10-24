// Benchmarks, laid out as a product story: a hero with handwritten sums, a dark statement over
// a faded bar chart, a sticky six-part tour and a closing video card.
import { Nav } from '../../nav';
import { Defs } from './defs';
import { Clock, Lanes, Rods, Spread, Swap, Window } from './figures';

// An unlabelled bar chart behind the statement, rising as it comes into view.
const bars = Array.from({ length: 32 }, (_, i) =>
  Math.round(30 + 22 * Math.sin(i * 0.55) + i * 1.3 + ((i * 37) % 11)),
);

const tour = [
  {
    id: 'comparison-story',
    nav: 'Published scores',
    title: ['The published', 'lead.'],
    text: "LaDe's Table 4 puts M2G4RTP first, averaged over Shanghai, Yantai and Chongqing. The paper's numbers, not our rerun.",
    number: '14.47 min',
    figure: <Lanes />,
  },
  {
    id: 'future-inputs',
    nav: 'Future inputs',
    title: ['The future', 'picks the inputs.'],
    text: 'Only parcels due within two hours are scored, using future delivery order. Neither is known at prediction time.',
    number: '2 hours',
    figure: <Clock />,
  },
  {
    id: 'parcel-scoring',
    nav: 'Parcel identity',
    title: ['Right time.', 'Wrong parcel.'],
    text: 'Times are matched by position, not parcel. Matching by parcel raises error from 12.47 to 22.19 min.',
    number: '+9.7 min',
    figure: <Swap />,
  },
  {
    id: 'matched-rerun',
    nav: 'A fair rerun',
    title: ['A fair', 'rerun.'],
    text: 'Their model retrained without the leaks, on the same 115,983 Yantai predictions, Sep 16–30. Hermes has 24% lower error.',
    number: '24% lower',
    figure: <Rods />,
  },
  {
    id: 'spread',
    nav: 'The spread',
    title: ['How far off,', 'and which way.'],
    text: 'Every Yantai ETA, Sep 16–30: where real arrivals fell. Most land close; the misses that remain run late more often than early.',
    number: '27 min',
    figure: <Spread />,
  },
  {
    id: 'customer-window',
    nav: 'What customers see',
    title: ['A window,', 'not a guess.'],
    text: 'Customers see the range where 80% of similar parcels really arrived. Set on Sep 1–15, checked on Sep 16–30 in all five cities.',
    number: '80.0%',
    figure: <Window />,
  },
];

export function Page() {
  return (
    <>
      <Defs />
      <a className="skip" href="#main">
        Skip to benchmarks
      </a>
      <Nav page="benchmarks" />
      <main id="main" className="bench">
        <section className="b-hero" aria-labelledby="cover-title">
          <div className="scribbles" aria-hidden="true" />
          <h1 id="cover-title">
            A number needs <em>its context.</em>
          </h1>
        </section>

        <section className="b-statement" aria-labelledby="statement-title">
          <div className="bars" aria-hidden="true">
            {bars.map((height, i) => (
              <span
                key={i}
                style={{ height: `${String(height)}%`, transitionDelay: `${String(i * 30)}ms` }}
              />
            ))}
          </div>
          <h2 id="statement-title">
            <em>M2G4RTP</em> leads. But how was it <em>scored?</em>
          </h2>
        </section>

        <section className="b-tour" aria-label="Inside the benchmark">
          <div className="tour-stage">
            <svg className="squiggle" viewBox="0 0 1200 800" preserveAspectRatio="none" aria-hidden="true">
              <path d="M-40 620C220 520 260 180 520 220S820 700 1000 520 1180 120 1260 160" pathLength={1} />
            </svg>
            <ol className="tour-nav">
              {tour.map((step, i) => (
                <li key={step.id}>
                  <a href={`#${step.id}`} data-step={i}>
                    {step.nav}
                  </a>
                </li>
              ))}
            </ol>
            {tour.map((step) => (
              <article key={step.id} className="tour-step" id={step.id} aria-labelledby={`${step.id}-title`}>
                <figure className="tour-card">{step.figure}</figure>
                <div className="tour-copy">
                  <h3 id={`${step.id}-title`}>
                    {step.title[0]} <em>{step.title[1]}</em>
                  </h3>
                  <p>{step.text}</p>
                  <strong className="tour-number">{step.number}</strong>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="b-voice" aria-labelledby="voice-title">
          <div className="voice-card">
            <video
              className="voice-video"
              src="/assets/video/accuracy.mp4"
              poster="/assets/images/accuracy-poster.jpg"
              aria-label="Illustrative stock video of a presenter"
              autoPlay
              muted
              loop
              playsInline
              preload="metadata"
            />
            <blockquote>
              <h2 id="voice-title">
                “A late parcel is forgiven. <em>A wrong promise isn’t.</em>”
              </h2>
              <p>Every minute of error is a minute someone waits.</p>
            </blockquote>
          </div>
        </section>
      </main>
    </>
  );
}
