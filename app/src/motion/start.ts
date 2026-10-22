// Start the scroll engines for one page, once per document.
import type { Page } from '../routes';
import * as scroll from './scroll';
import { frames } from './util';

let started = false;

// Each page's motion loads with it, so other pages' engines are never downloaded.
const pages: Record<Exclude<Page, 'dashboard'>, () => Promise<{ init: () => () => void }>> = {
  home: () => import('./home'),
  benchmarks: () => import('./benchmarks'),
  methodology: () => import('./flow'),
};

export async function start(page: Exclude<Page, 'dashboard'>) {
  if (started) return;
  started = true;
  scroll.init();
  const [motion] = await Promise.all([pages[page](), document.fonts.ready]);
  const openHash = motion.init();
  dispatchEvent(new Event('resize'));
  await frames(2);
  openHash();
  await frames(2);
  // Research pages stay hidden until their first scroll pose is drawn (see index.html).
  delete document.documentElement.dataset.boot;
}
