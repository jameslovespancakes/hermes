// Start the scroll engines for one page, once per document.
import type { Page } from '../routes';
import * as cinema from './cinema';
import * as flow from './flow';
import * as hero from './hero';
import * as reel from './reel';
import * as quality from './quality';
import * as reveal from './reveal';
import * as scroll from './scroll';
import * as split from './split';
import * as wall from './wall';
import { frames } from './util';

let started = false;

function home() {
  reveal.init();
  cinema.init();
  split.init();
  wall.init();
  quality.init();
  hero.init();
  return () => {
    cinema.openHash();
    wall.openHash();
    quality.openHash();
  };
}

const pages: Record<Page, () => () => void> = { home, benchmarks: reel.init, methodology: flow.init };

export async function start(page: Page) {
  if (started) return;
  started = true;
  scroll.init();
  await document.fonts.ready;
  const openHash = pages[page]();
  dispatchEvent(new Event('resize'));
  await frames(2);
  openHash();
  await frames(2);
  // Research pages stay hidden until their first scroll pose is drawn (see index.html).
  delete document.documentElement.dataset.boot;
}
