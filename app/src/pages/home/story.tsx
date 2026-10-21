export function Story() {
  return (
    <div className="dark-foundation">
      <div className="city-strip wrap">
        <div className="cities" aria-label="Shanghai, Hangzhou, Chongqing, Yantai, and Jilin">
          <span>Shanghai</span>
          <span>Hangzhou</span>
          <span>Chongqing</span>
          <span>YANTAI</span>
          <span>Jilin.</span>
        </div>
      </div>
      <section className="comparison" id="delivery-film" aria-labelledby="comparison-title">
        <div className="wrap">
          <div className="time-comparison">
            <div
              className="film-photo"
              role="img"
              aria-label="Soft-focus photograph of a courier carrying parcels beside a delivery van"
            >
              <div className="film-photo-image" />
              <div className="film-photo-shade" />
            </div>
            <div className="film-intro">
              <h2 id="comparison-title">
                Train for the
                <br />
                <em>most accurate ETA.</em>
              </h2>
              <p>Learn from past deliveries to reduce arrival-time error.</p>
            </div>
          </div>
        </div>
      </section>
      <section className="data-split" id="data-split" aria-labelledby="data-split-title">
        <div className="split-runway">
          <div className="split-stage wrap">
            <div className="split-reflections" aria-hidden="true">
              <div className="split-reflection shop" />
              <div className="split-reflection street" />
              <div className="split-reflection doorstep" />
            </div>
            <header className="split-heading">
              <h2 id="data-split-title">
                One history.
                <br />
                <em>Three different jobs.</em>
              </h2>
            </header>
            <div
              className="split-visual"
              role="img"
              aria-label="One ribbon separates into training, validation and evaluation queries, in chronological order"
              aria-describedby="split-note"
            />
            <ol className="split-groups">
              <li className="split-group" data-split-group="train" data-count={800000}>
                <span className="split-date">Before Sep 1</span>
                <h3>Train.</h3>
                <p>Earlier checkpoints teach the model its patterns.</p>
              </li>
              <li className="split-group" data-split-group="validate" data-count={181388}>
                <span className="split-date">Sep 1–15</span>
                <h3>Validate.</h3>
                <p>A later slice helps choose when to stop training.</p>
              </li>
              <li className="split-group" data-split-group="evaluate" data-count={155296}>
                <span className="split-date">Sep 16–30</span>
                <h3>Evaluate.</h3>
                <p>Later checkpoints measure ETA error, without fitting to them.</p>
              </li>
            </ol>
            <p className="sr-only" id="split-note">
              The Yantai development split, not a live training process. The changing delivery reflections are
              decorative stock imagery, not examples from these groups. Ribbon widths reflect saved counts:
              800,000 fitting queries, 181,388 early-stopping queries, and 155,296 evaluation queries. These
              are checkpoint queries, not unique parcels. Only the fitting band continues into the model
              illustration; the later groups remain separate. The fitting sample is capped at 800,000.
              Training uses events and outcomes before September 1. Early stopping uses September 1–15 events
              with outcomes known before September 16. September 16–30 is development evaluation; no October
              test is shown.
            </p>
          </div>
        </div>
      </section>
      <section className="model-section" id="model-training" aria-label="Offline model training">
        <div className="model-runway">
          <div className="model-pin wrap" />
        </div>
        <p className="model-fallback wrap">
          LightGBM learns from past checkpoints, combining trees to refine the ETA.
        </p>
      </section>
    </div>
  );
}
