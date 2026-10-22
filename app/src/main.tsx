import { lazy, type ComponentType } from 'react';
import { createRoot, hydrateRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import { App, type Views } from './app';
import { pages, route, type Page } from './routes';

const loaders: Record<Page, () => Promise<ComponentType>> = {
  home: () => import('./pages/home').then((m) => m.Page),
  benchmarks: () => import('./pages/benchmarks').then((m) => m.Page),
  methodology: () => import('./pages/methodology').then((m) => m.Page),
  dashboard: () => import('./pages/dashboard').then((m) => m.Dashboard),
};
const styles = {
  home: () => import('./styles/home.css'),
  benchmarks: () => import('./styles/benchmarks.css'),
  methodology: () => import('./styles/methodology.css'),
  dashboard: () => import('./styles/dashboard.css'),
};

const page = route(location.pathname);
// Built pages already link their stylesheet; the dev server loads it here.
if (!document.querySelector('link[rel="stylesheet"]')) await styles[page]();
document.title = pages[page].title;
document.body.className = pages[page].body;

// The current page is loaded before hydration so it renders straight away; others stay lazy.
const deferred = (name: Page) => lazy(() => loaders[name]().then((View) => ({ default: View })));
const views: Views = {
  home: deferred('home'),
  benchmarks: deferred('benchmarks'),
  methodology: deferred('methodology'),
  dashboard: deferred('dashboard'),
};
views[page] = await loaders[page]();

const root = document.getElementById('root') as HTMLElement;
const app = (
  <BrowserRouter>
    <App views={views} />
  </BrowserRouter>
);
// Built pages are pre-rendered; the dev server starts empty.
if (root.hasChildNodes()) hydrateRoot(root, app);
else createRoot(root).render(app);
