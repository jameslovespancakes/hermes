const cards = [
  {
    kind: 'quality-city quality-poster',
    name: 'Outdated patterns',
    photo: 'Illustrative stock photograph of a city at dusk, not a dataset location',
    copy: 'Training data reflects courier habits that have since changed.',
  },
  {
    kind: 'quality-feed',
    name: 'Frozen updates',
    photo:
      'Illustrative stock photograph of a courier moving parcels beside a van, not a dataset participant',
    copy: 'The courier keeps delivering, but the log stops updating.',
  },
  {
    kind: 'quality-values quality-poster',
    name: 'Wrong values',
    photo: 'Illustrative stock photograph of hands packing a parcel, not a recorded data error',
    copy: 'A delivery has the wrong timestamp or location.',
  },
  {
    kind: 'quality-missing',
    name: 'Missing events',
    photo:
      'Illustrative stock photograph of a delivery handoff, not a dataset participant or a confirmed missing event',
    copy: 'A parcel is delivered, but the event isn’t recorded.',
  },
  {
    kind: 'quality-volume quality-poster',
    name: 'Duplicate records',
    photo: 'Illustrative stock photograph of people working among warehouse shelves, not the source dataset',
    copy: 'The same delivery event is recorded more than once.',
  },
  {
    kind: 'quality-future',
    name: 'Data leakage',
    photo: 'Illustrative stock photograph looking ahead along an office corridor',
    copy: 'A prediction uses delivery details that were only known later.',
  },
];

export function Quality() {
  return (
    <section
      className="evidence-section data-quality"
      id="data-quality"
      aria-label="Six potential data-quality failures, illustrated with stock photography"
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
