export function Cover() {
  return (
    <section
      className="research-intro benchmark-intro"
      id="top"
      aria-labelledby="cover-title"
      data-cover
      data-atelier-cover
    >
      <div className="intro-layout wrap">
        <div className="intro-copy">
          <h1 id="cover-title">
            <span className="hero-line">
              <span>A number needs</span>
            </span>{' '}
            <span className="hero-line">
              <em>its context.</em>
            </span>
          </h1>
        </div>
        <div
          className="intro-scene"
          role="img"
          aria-label="Illustrative stock photograph of a city at sunset, not a benchmark location"
        >
          <div className="intro-photo" aria-hidden="true" />
          <div className="intro-veil" aria-hidden="true" />
        </div>
      </div>
    </section>
  );
}
