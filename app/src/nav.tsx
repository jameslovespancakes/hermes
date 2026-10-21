import type { Page } from './routes';

export function Nav({ page }: { page: Page }) {
  return (
    <div className="nav-wrap">
      <header className="navbar has-nav-modes">
        <a className="brand" href="/" aria-label="Hermes home">
          <svg className="hermes-logo" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
            <use href="#hermes-boots" />
          </svg>
          Hermes
        </a>
        <fieldset className="nav-mode-toggle">
          <legend className="sr-only">Navigation area</legend>
          <label>
            <input
              type="radio"
              name="nav-area"
              value="deliver"
              aria-controls="deliver-links"
              defaultChecked={page === 'home'}
            />
            <span>Deliver</span>
          </label>
          <label>
            <input
              type="radio"
              name="nav-area"
              value="research"
              aria-controls="research-links"
              defaultChecked={page !== 'home'}
            />
            <span>Research</span>
          </label>
        </fieldset>
        <nav className="nav-links" aria-label="Main navigation">
          <div className="nav-panel" id="deliver-links" data-nav-area="deliver">
            <a href="/" aria-current={page === 'home' ? 'page' : undefined}>
              Overview
            </a>
          </div>
          <div className="nav-panel" id="research-links" data-nav-area="research">
            <a href="/benchmarks" aria-current={page === 'benchmarks' ? 'page' : undefined}>
              Benchmarks
            </a>
            <a href="/methodology" aria-current={page === 'methodology' ? 'page' : undefined}>
              Methodology
            </a>
          </div>
        </nav>
      </header>
    </div>
  );
}
