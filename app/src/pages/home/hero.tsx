// Mixkit video 31346, free licence. Muted, looping background only.
export function Hero() {
  return (
    <section className="hero" id="top" aria-labelledby="hero-title">
      <div className="hero-backdrop" aria-hidden="true">
        <video
          className="hero-video"
          src="/assets/video/hero.mp4"
          poster="/assets/images/hero-poster.jpg"
          autoPlay
          muted
          loop
          playsInline
          preload="auto"
        />
      </div>
      <div className="hero-copy">
        <h1 id="hero-title">
          Predict the route.
          <br />
          <em>Update the ETA.</em>
        </h1>
      </div>
    </section>
  );
}
