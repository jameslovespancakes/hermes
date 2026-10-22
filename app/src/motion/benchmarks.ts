// Benchmarks motion: handwritten sums, the closing video and the scroll tour.
import * as hero from './hero';
import * as scribble from './scribble';
import * as tour from './tour';

export function init() {
  scribble.init();
  hero.init('.voice-video');
  return tour.init();
}
