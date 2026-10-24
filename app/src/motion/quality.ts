// Data-quality cards: a reversible paper deck inside the home scroll story.
import * as cinema from './cinema';
import * as wall from './wall';
import { $, clamp, ease, frames, onLink, range } from './util';

let section: HTMLElement;
let deck: HTMLElement;
let stage: HTMLElement;
let steps: HTMLElement[];
let previous: HTMLElement;
let next: HTMLElement;
let label: HTMLElement;
let announcement: HTMLElement;
let width = 0;
let height = 0;
let index = 0;
let travel = 0;
let measured: { entrance: number; travel: number; total: number } | undefined;

export const metrics = () => measured;

function draw(position: number) {
  index = Math.round(position);
  const mobile = innerWidth < 760;
  const left = (stage.clientWidth - width) / 2;
  const top = (stage.clientHeight - 80 - height) / 2;
  steps.forEach((step, i) => {
    const delta = i - position;
    const depth = clamp(delta, 0, 3);
    const out = Math.max(0, -delta);
    const visible = delta > -0.98 && delta < 2.7;
    const x = left + depth * (mobile ? 18 : 42) - out * (width * 0.9 + (mobile ? 40 : 100));
    const y = top + depth * (mobile ? 14 : 24) - out * height * 0.15;
    const scale = 1 - depth * 0.055 - out * 0.1;
    const turn = depth * (mobile ? 2.5 : 3) - out * (mobile ? 12 : 16);
    step.style.visibility = visible ? 'visible' : 'hidden';
    step.style.opacity = String(
      visible ? (1 - ease(range(out, 0.45, 0.98))) * (1 - ease(range(depth, 2, 2.7))) : 0,
    );
    step.style.transform = `translate(${x.toFixed(2)}px,${y.toFixed(2)}px) rotate(${turn.toFixed(2)}deg) scale(${scale.toFixed(4)})`;
    step.style.zIndex = String(40 - i);
    step.style.setProperty('--copy-reveal', String(1 - ease(range(depth, 0.25, 0.8))));
    step.style.setProperty('--photo-x', `${String(clamp(delta, -1, 1) * (mobile ? -7 : -14))}px`);
    step.setAttribute('aria-hidden', String(i !== index));
    step.inert = i !== index;
  });
  label.textContent = steps[index].dataset.name ?? '';
  previous.setAttribute('aria-disabled', String(index === 0));
  next.setAttribute('aria-disabled', String(index === steps.length - 1));
}

export function render(entrance: number, progress: number, departure: number) {
  const arrival = ease(range(entrance, 0.1, 0.82));
  const leaving = ease(range(departure, 0.06, 0.44));
  const shown = arrival * (1 - leaving);
  const interactive = arrival > 0.99 && leaving < 0.01;
  section.style.opacity = String(ease(range(arrival, 0, 0.15)) * (1 - leaving));
  section.style.visibility = shown > 0.001 ? 'visible' : 'hidden';
  section.style.pointerEvents = interactive ? 'auto' : 'none';
  section.setAttribute('aria-hidden', String(shown < 0.5));
  section.inert = !interactive;
  stage.tabIndex = interactive ? 0 : -1;
  stage.style.translate = `0 ${String((1 - arrival) * innerHeight * 0.84 - leaving * 48)}px`;
  stage.style.scale = String(0.94 + arrival * 0.06 - leaving * 0.04);
  const position = clamp(progress * (steps.length - 0.4) - 0.3, 0, steps.length - 1);
  draw(position);
}

function seek(target: number, announce = true, smooth = false) {
  const totals = wall.metrics();
  if (!totals) return;
  target = clamp(target, 0, steps.length - 1);
  const p = (target + 0.3) / (steps.length - 0.4);
  cinema.seekTimeline(
    (totals.core + totals.qualityEntrance + p * totals.qualityTravel) / totals.total,
    smooth,
  );
  if (!smooth) draw(target);
  if (announce) announcement.textContent = steps[target].dataset.name ?? '';
}

function layout() {
  const mobile = innerWidth < 760;
  travel = (steps.length - 0.4) * Math.max(400, innerHeight * 0.78);
  width = mobile ? Math.min(430, innerWidth - 56) : Math.min(1040, innerWidth * 0.82);
  height = Math.min(mobile ? 610 : 620, Math.max(230, stage.clientHeight - (mobile ? 110 : 128)));
  deck.style.setProperty('--chapter-travel', `${String(travel)}px`);
  deck.style.setProperty('--quality-card-width', `${String(width)}px`);
  deck.style.setProperty('--quality-card-height', `${String(height)}px`);
  const entrance = Math.max(620, innerHeight * 0.8);
  measured = { entrance, travel, total: entrance + travel };
  wall.layout();
}

export function openHash() {
  if (location.hash === '#data-quality') seek(0, false);
}

// Turn the six readable cards into a staged deck with controls.
function build() {
  deck.classList.add('chapter-runway', 'quality-chapter', 'photo-story', 'chapter-ready');
  deck.setAttribute('aria-label', 'Six potential data-quality failure modes');
  stage = document.createElement('div');
  stage.className = 'chapter-frame';
  stage.tabIndex = 0;
  stage.setAttribute('role', 'group');
  stage.setAttribute('aria-label', 'Six potential data-quality failure modes');
  const list = document.createElement('div');
  list.className = 'chapter-steps';
  steps = [...deck.children] as HTMLElement[];
  for (const step of steps) step.classList.add('chapter-step');
  list.append(...steps);
  const controls = document.createElement('div');
  controls.className = 'chapter-controls';
  controls.setAttribute('aria-label', 'Browse data-quality failure modes');
  controls.innerHTML =
    '<button type="button" data-previous aria-label="Previous failure mode">←</button><span data-current aria-live="off"></span><button type="button" data-next aria-label="Next failure mode">→</button>';
  announcement = document.createElement('span');
  announcement.className = 'sr-only chapter-announcement';
  announcement.setAttribute('aria-live', 'polite');
  stage.append(list, controls, announcement);
  deck.append(stage);
  previous = $('[data-previous]', controls);
  next = $('[data-next]', controls);
  label = $('[data-current]', controls);
}

export function init() {
  deck = $('[data-quality-story]');
  section = $('#data-quality');
  build();
  const scene = $('.time-comparison');
  scene.insertBefore(section, $('.perspectives-linked', scene));
  section.classList.add('quality-linked');
  section.inert = true;

  previous.addEventListener('click', () => seek(index - 1, true, true));
  next.addEventListener('click', () => seek(index + 1, true, true));
  stage.addEventListener('keydown', (event) => {
    if (event.target !== stage && !(event.target as Element).closest('.chapter-controls')) return;
    const keys: Record<string, number> = {
      ArrowLeft: index - 1,
      ArrowRight: index + 1,
      Home: 0,
      End: steps.length - 1,
    };
    if (!(event.key in keys)) return;
    event.preventDefault();
    seek(keys[event.key], true, true);
  });
  onLink('a[href="#data-quality"]', () => seek(0, false, true));
  addEventListener('hashchange', () => void frames(2).then(openHash));
  addEventListener('resize', layout);
  layout();
}
