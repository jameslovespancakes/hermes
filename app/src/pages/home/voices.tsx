// Hugeicons ArrowRight02 (MIT, see /licenses).
function Arrow({ left = false }: { left?: boolean }) {
  return (
    <svg
      className="hermes-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path transform={left ? 'rotate(180 12 12)' : undefined} d="M18.5 12H5M13 18s6-4.42 6-6-6-6-6-6" />
    </svg>
  );
}

export function Voices() {
  return (
    <section className="perspectives" id="perspectives" aria-labelledby="perspectives-title">
      <div className="center-head">
        <h2 id="perspectives-title">
          One delivery.
          <br />
          <em>More than one story.</em>
        </h2>
        <p className="sr-only" id="wall-disclaimer">
          Six fictional perspectives, then a real interview: Gerry McGowan, Executive Director, US Network at
          Asendia, quoted with permission.
        </p>
      </div>
      <div className="wall-runway" id="perspectives-wall">
        <div
          className="wall-stage"
          role="group"
          aria-label="Delivery perspectives"
          aria-describedby="wall-disclaimer"
        >
          <div className="wall-cards">
            <article className="wall-card portrait" aria-label="The courier, fictional perspective">
              <div
                className="wall-photo courier"
                role="img"
                aria-label="Illustrative stock photograph of colleagues sharing a friendly team meeting"
              />
              <div className="wall-photo-copy">
                <blockquote>“Predict my next stop. Don’t choose it for me.”</blockquote>
                <div className="wall-signature">
                  <div>
                    <strong>The courier</strong>
                  </div>
                </div>
              </div>
            </article>
            <article className="wall-card" aria-label="Gerry McGowan, interview">
              <blockquote>
                “If I had to pick one data point: compare what we promised with what the customer got. Give
                them a range of times.”
              </blockquote>
              <p className="wall-tie">
                Hermes promises an arrival window, and checks it against real arrivals.
              </p>
              <div className="wall-signature">
                <span className="wall-mark photo" role="img" aria-label="Gerry McGowan" />
                <div>
                  <strong>Gerry McGowan</strong>
                  <small>Executive Director, US Network, Asendia</small>
                </div>
              </div>
            </article>
            <article className="wall-card landscape" aria-label="The sender, fictional perspective">
              <div className="wall-copy">
                <blockquote>“How many stops come before my parcel?”</blockquote>
              </div>
              <div
                className="wall-photo sender"
                role="img"
                aria-label="Illustrative stock photograph of colleagues collaborating at a shared workspace"
              />
            </article>
            <article className="wall-card olive" aria-label="Gerry McGowan, interview">
              <blockquote>
                “When it’s late, trace the life of the order. When did it drop, when was it processed, when
                did it get out?”
              </blockquote>
              <p className="wall-tie">
                Every scan is checked for time, place and duplicates before the model uses it.
              </p>
              <div className="wall-signature">
                <span className="wall-mark photo" role="img" aria-label="Gerry McGowan" />
                <div>
                  <strong>Gerry McGowan</strong>
                  <small>Executive Director, US Network, Asendia</small>
                </div>
              </div>
            </article>
            <article
              className="wall-card landscape green"
              aria-label="The operations team, fictional perspective"
            >
              <div className="wall-copy">
                <blockquote>“One stop done. Which parcels are still on the van?”</blockquote>
              </div>
              <div
                className="wall-photo team"
                role="img"
                aria-label="Illustrative stock photograph of a team reviewing work together around a table"
              />
            </article>
            <article className="wall-card" aria-label="Gerry McGowan, interview">
              <blockquote>“The goal is to know there’s a problem before the customer calls.”</blockquote>
              <p className="wall-tie">
                The dashboard flags slipping and unreliable ETAs for a dispatcher first.
              </p>
              <div className="wall-signature">
                <span className="wall-mark photo" role="img" aria-label="Gerry McGowan" />
                <div>
                  <strong>Gerry McGowan</strong>
                  <small>Executive Director, US Network, Asendia</small>
                </div>
              </div>
            </article>
          </div>
          <div className="wall-controls" aria-label="Browse perspectives">
            <button type="button" data-wall-prev aria-label="Previous perspective">
              <Arrow left />
            </button>
            <output aria-label="Current perspective" aria-live="off">
              01 / 06
            </output>
            <button type="button" data-wall-next aria-label="Next perspective">
              <Arrow />
            </button>
          </div>
          <span className="sr-only" id="wall-announcement" aria-live="polite" />
        </div>
      </div>
    </section>
  );
}
