// Home motion: reveals, the cinema, split, card wall, quality cards and hero video.
import * as cinema from './cinema';
import * as hero from './hero';
import * as quality from './quality';
import * as reveal from './reveal';
import * as split from './split';
import * as wall from './wall';

export function init() {
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
