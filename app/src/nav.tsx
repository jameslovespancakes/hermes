import { Link } from 'react-router';
import type { Page } from './routes';

// Story pages run document-wide scroll engines, so links between them load a fresh document.

export function Nav({ page }: { page: Page }) {
  return (
    <div className="nav-wrap">
      <header className="navbar has-nav-modes">
        <Link reloadDocument className="brand" to="/" aria-label="Hermes home">
          <svg className="hermes-logo" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
            <use href="#hermes-boots" />
          </svg>
          Hermes
        </Link>
        <fieldset className="nav-mode-toggle">
          <legend className="sr-only">Navigation area</legend>
          <label>
            <input
              type="radio"
              name="nav-area"
              value="deliver"
              aria-controls="deliver-links"
              defaultChecked={page === 'home' || page === 'dashboard'}
            />
            <span>Deliver</span>
          </label>
          <label>
            <input
              type="radio"
              name="nav-area"
              value="research"
              aria-controls="research-links"
              defaultChecked={page === 'benchmarks' || page === 'methodology'}
            />
            <span>Research</span>
          </label>
        </fieldset>
        <nav className="nav-links" aria-label="Main navigation">
          <div className="nav-panel" id="deliver-links" data-nav-area="deliver">
            <Link reloadDocument to="/dashboard" aria-current={page === 'dashboard' ? 'page' : undefined}>
              Overview
            </Link>
          </div>
          <div className="nav-panel" id="research-links" data-nav-area="research">
            <Link reloadDocument to="/benchmarks" aria-current={page === 'benchmarks' ? 'page' : undefined}>
              Benchmarks
            </Link>
            <Link reloadDocument to="/methodology" aria-current={page === 'methodology' ? 'page' : undefined}>
              Methodology
            </Link>
          </div>
        </nav>
      </header>
    </div>
  );
}
