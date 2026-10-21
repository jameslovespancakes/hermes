import { createRoot, hydrateRoot } from 'react-dom/client';
import { App } from './app';
import { pages, route } from './routes';

const page = route(location.pathname);
const styles = {
  home: () => import('./styles/home.css'),
  benchmarks: () => import('./styles/benchmarks.css'),
  methodology: () => import('./styles/methodology.css'),
};
await styles[page]();
document.title = pages[page].title;
document.body.className = pages[page].body;
const root = document.getElementById('root') as HTMLElement;
const app = <App page={page} />;
// Built pages are pre-rendered; the dev server starts empty.
if (root.hasChildNodes()) hydrateRoot(root, app);
else createRoot(root).render(app);
