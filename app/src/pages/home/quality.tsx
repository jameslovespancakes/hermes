const cards = [
  {
    kind: 'quality-city quality-poster',
    name: 'Outdated patterns',
    photo: 'Illustrative stock photograph of a city at dusk, not a dataset location',
    copy: 'Training data reflects courier habits that have since changed. Hermes retrains monthly and watches for drift.',
  },
  {
    kind: 'quality-feed',
    name: 'Frozen updates',
    photo:
      'Illustrative stock photograph of a courier moving parcels beside a van, not a dataset participant',
    copy: 'Courier and area habits stop refreshing. Hermes rebuilds them from the live log at every prediction.',
  },
  {
    kind: 'quality-late quality-poster',
    name: 'Late uploads',
    photo: 'Illustrative stock photograph of a courier in training, not a dataset participant',
    copy: 'Scans reach the system long after the delivery. A model built for stale feeds takes over, and the dispatcher sees it.',
  },
  {
    kind: 'quality-missing',
    name: 'Missing events',
    photo:
      'Illustrative stock photograph of a delivery handoff, not a dataset participant or a confirmed missing event',
    copy: 'A parcel is delivered, but the scan never arrives. Parcels left behind in a visited area are flagged.',
  },
  {
    kind: 'quality-bulk quality-poster',
    name: 'Bulk uploads',
    photo: 'Illustrative stock photograph of a shop counter, not a recorded data error',
    copy: 'A cheap app stamps many parcels with one time. Those records count for less in training and are flagged live.',
  },
  {
    kind: 'quality-values',
    name: 'Wrong values',
    photo: 'Illustrative stock photograph of hands packing a parcel, not a recorded data error',
    copy: 'A delivery has the wrong timestamp or location. Fast device clocks are corrected and far-off addresses repaired.',
  },
  {
    kind: 'quality-volume quality-poster',
    name: 'Duplicate records',
    photo: 'Illustrative stock photograph of people working among warehouse shelves, not the source dataset',
    copy: 'The same delivery event is recorded more than once. Copies are removed; no real parcel is lost.',
  },
  {
    kind: 'quality-future',
    name: 'Data leakage',
    photo: 'Illustrative stock photograph looking ahead along an office corridor',
    copy: 'A prediction uses delivery details that were only known later. Audited: hiding the future changes nothing.',
  },
];

export function Quality() {
  return (
    <section
      className="evidence-section data-quality"
      id="data-quality"
      aria-label="Eight data-quality failures Hermes handles, illustrated with stock photography"
    >
      <div className="quality-story" data-quality-story>
        {cards.map(({ kind, name, photo, copy }) => {
          const [first, second] = name.split(' ');
          return (
            <article key={name} className={`quality-card ${kind}`} data-name={name}>
              <div className="quality-photo" role="img" aria-label={photo}>
                <span aria-hidden="true">Illustrative scene</span>
              </div>
              <div className="quality-copy">
                <h3>
                  {first}
                  <br />
                  <em>{second}.</em>
                </h3>
                <p>{copy}</p>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
