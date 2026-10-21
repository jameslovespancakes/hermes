// Data split chapter: three chronological bands, captions and photo reflections.
// Driven by the cinema clock; counts and membership never change.
import * as cinema from './cinema';
import type { Box } from './training';
import { $, $$, clamp, ease, isPaused, range } from './util';

const colors = [
  [3, 79, 70],
  [255, 169, 70],
  [157, 177, 141],
];
const muted = [228, 228, 208];

let section: HTMLElement;
let visual: HTMLElement;
let heading: HTMLElement;
let captions: HTMLElement;
let reflections: HTMLElement;
let pictures: HTMLElement[];
let labels: HTMLElement[];
let bands: SVGRectElement[];
let svg: SVGSVGElement;
let counts: number[];
let total = 0;
let paused = false;
let geometry:
  | {
      width: number;
      height: number;
      usable: number;
      gap: number;
      bar: number;
      starts: number[];
      handoff: Box;
      training: Box;
      lift: number;
      drift: number;
    }
  | undefined;

export const handoff = () => geometry?.handoff;
export const trainingSource = () => geometry?.training;

export function measure() {
  const width = visual.clientWidth;
  const height = visual.clientHeight;
  const mobile = innerWidth < 760;
  const gap = mobile ? 12 : 22;
  const bar = innerHeight <= 620 ? 30 : mobile ? 36 : 48;
  const usable = width - gap * 2 - 4;
  svg.setAttribute('viewBox', `0 0 ${String(width)} ${String(height)}`);
  let sum = 0;
  const starts = bands.map((band, i) => {
    const w = (usable * counts[i]) / total;
    const start = sum;
    sum += w;
    band.setAttribute('width', String(w));
    band.setAttribute('height', String(bar));
    return start;
  });
  const from = $('.time-comparison').getBoundingClientRect();
  const to = visual.getBoundingClientRect();
  const left = to.left - from.left + (width - usable) / 2;
  const top = to.top - from.top + (height - bar) / 2;
  geometry = {
    width,
    height,
    usable,
    gap,
    bar,
    starts,
    handoff: { left, top, width: usable, height: bar, radius: 2 },
    // Only the fitting band becomes the model surface; holdouts stay behind.
    training: { left: left - gap, top, width: (usable * counts[0]) / total, height: bar, radius: 5 },
    lift: innerHeight <= 620 ? 8 : mobile ? 10 : 14,
    drift: mobile ? 48 : 120,
  };
}

function paint(p: number) {
  if (!geometry) return;
  const { width, height, usable, gap, bar, starts, lift, drift } = geometry;
  const first = range(p, 0.27, 0.39);
  const second = range(p, 0.6, 0.72);
  const a = ease(first);
  const b = ease(second);
  const weights = paused ? [1, 1, 1] : [1 - a, a * (1 - b), b];
  const separation = paused ? 1 : ease(range(p, 0.02, 0.18));
  const left = (width - usable - gap * separation * 2) / 2;
  bands.forEach((band, i) => {
    const strength = 0.3 + 0.7 * weights[i];
    const rgb = colors[i].map((v, c) => Math.round(muted[c] + (v - muted[c]) * strength));
    band.setAttribute('x', String(left + starts[i] + i * gap * separation));
    band.setAttribute('y', String((height - bar) / 2 - (paused ? 0 : lift * weights[i] * separation)));
    band.setAttribute('rx', String(2 + 3 * separation));
    band.setAttribute('fill', `rgb(${rgb.join(',')})`);
  });
  // The outgoing caption leaves before the next one arrives.
  const outA = ease(range(first, 0, 0.46));
  const inA = ease(range(first, 0.54, 1));
  const outB = ease(range(second, 0, 0.46));
  const inB = ease(range(second, 0.54, 1));
  const opacity = [1 - outA, inA * (1 - outB), inB];
  const shift = [-28 * outA, 28 * (1 - inA) - 28 * outB, 28 * (1 - inB)];
  labels.forEach((label, i) => {
    label.style.opacity = String(paused ? 1 : opacity[i]);
    label.style.transform = `translateY(${String(paused ? 0 : shift[i])}px)`;
    label.style.filter = `blur(${String(paused ? 0 : (1 - opacity[i]) * 2.5)}px)`;
  });
  pictures.forEach((picture, i) => {
    const local = range(p, [0, 0.27, 0.6][i], [0.39, 0.72, 1][i]);
    picture.style.opacity = String(paused ? (i === 0 ? 1 : 0) : weights[i]);
    picture.style.transform = paused
      ? 'none'
      : `translate3d(${String((0.5 - local) * drift)}px,${String((0.5 - local) * 20)}px,0) scale(${String(1.04 + local * 0.025)})`;
  });
}

export function render(progress: number, entrance: number, exit: number) {
  const state = paused ? 1 : clamp(progress);
  paint(state);
  section.style.visibility = entrance > 0 && exit < 1 ? 'visible' : 'hidden';
  section.setAttribute('aria-hidden', String(entrance < 0.5 || exit >= 0.25));
  // The fitting band stays until the model surface covers it; holdouts fade in place.
  bands.forEach((band, i) => {
    band.style.opacity = String(i === 0 ? (exit < 1 / 3 ? 1 : 0) : 1 - ease(range(exit, 0, 1 / 3)));
  });
  const copy = entrance * (1 - ease(range(exit, 0, 0.25)));
  heading.style.opacity = String(copy);
  captions.style.opacity = String(copy);
  reflections.style.opacity = String(copy * (paused ? 0.32 : ease(range(state, 0, 0.1))));
}

export function setPaused(value: boolean) {
  paused = value;
  section.classList.toggle('split-still', paused);
  measure();
}

export function init() {
  section = $('#data-split');
  visual = $('.split-visual', section);
  heading = $('.split-heading', section);
  captions = $('.split-groups', section);
  reflections = $('.split-reflections', section);
  pictures = $$('.split-reflection', reflections);
  labels = $$('.split-group', section);
  counts = labels.map((label) => Number(label.dataset.count));
  total = counts.reduce((sum, count) => sum + count, 0);
  paused = isPaused();

  svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.classList.add('split-motion');
  svg.setAttribute('aria-hidden', 'true');
  svg.innerHTML = counts.map(() => '<rect class="split-band"/>').join('');
  visual.append(svg);
  bands = $$<SVGRectElement>('.split-band', svg);

  const scene = $('.time-comparison');
  scene.insertBefore(section, $('.model-linked', scene));
  section.classList.add('split-ready', 'split-linked');
  section.classList.toggle('split-still', paused);
  $('.comparison-scroll').classList.add('with-data');

  addEventListener('resize', () => {
    measure();
    cinema.update();
  });
  measure();
  cinema.update();
}
