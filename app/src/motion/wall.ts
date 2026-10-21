// Perspective wall: fictional quotes drift past on the shared home scroll clock.
import * as cinema from './cinema';
import * as quality from './quality';
import { $, $$, clamp, ease, frames, isPaused, onLink, onPause, range } from './util';

export interface Metrics {
  core: number;
  quality: number;
  qualityEntrance: number;
  qualityTravel: number;
  perspectivesStart: number;
  entrance: number;
  travel: number;
  total: number;
}

let section: HTMLElement;
let stage: HTMLElement;
let heading: HTMLElement;
let layer: HTMLElement;
let controls: HTMLElement;
let background: HTMLElement;
let previous: HTMLElement;
let next: HTMLElement;
let output: HTMLOutputElement;
let cards: HTMLElement[];
let paused = false;
let value = 0;
let current = 0;
let positions: number[] = [];
let sizes: { width: number; height: number }[] = [];
let width = 0;
let mobile = false;
let measured: Metrics | undefined;

export const metrics = () => measured;
const last = () => positions[positions.length - 1];

function draw() {
  if (!positions.length) return;
  const focus = value * last();
  const centerY = stage.clientHeight / 2 + (mobile && (innerWidth < 600 || innerHeight >= 620) ? 8 : 20);
  let nearest = 0;
  let distance = Infinity;
  cards.forEach((card, i) => {
    const delta = positions[i] - focus;
    const relative = delta / width;
    const off = Math.min(1, Math.abs(relative));
    const x = stage.clientWidth / 2 + delta - sizes[i].width / 2;
    const y =
      centerY - delta * (mobile ? 0.18 : 0.4) + (!mobile && i === 0 ? off * 25 : 0) - sizes[i].height / 2;
    const turn = clamp(-relative * 4.3, -16, 16) - (i === 0 ? off * 5 : 0);
    card.style.transform = `translate(${x.toFixed(2)}px,${y.toFixed(2)}px) rotate(${turn.toFixed(2)}deg)`;
    card.style.zIndex = String(20 - Math.min(15, Math.round(Math.abs(relative))));
    if (Math.abs(delta) < distance) {
      nearest = i;
      distance = Math.abs(delta);
    }
  });
  current = nearest;
  cards.forEach((card, i) => {
    for (const link of $$('a', card)) link.tabIndex = i === current ? 0 : -1;
  });
  previous.setAttribute('aria-disabled', String(current === 0));
  next.setAttribute('aria-disabled', String(current === cards.length - 1));
  const pad = (n: number) => String(n).padStart(2, '0');
  output.textContent = `${pad(current + 1)} / ${pad(cards.length)}`;
}

export function render(entrance: number, progress: number, still: boolean) {
  if (!positions.length) return;
  const field = ease(range(entrance, 0.1, 0.44));
  const rise = ease(range(entrance, 0.28, 0.5));
  const title = rise * (1 - ease(range(entrance, 0.63, 0.81)));
  const arriving = ease(range(entrance, 0.76, 1));
  const lift = ease(range(entrance, 0.58, 0.86));
  section.style.visibility = entrance > 0.08 ? 'visible' : 'hidden';
  section.setAttribute('aria-hidden', String(title < 0.05 && arriving < 0.05));
  section.style.pointerEvents = arriving > 0.99 ? 'auto' : 'none';
  background.style.opacity = String(field);
  heading.style.opacity = String(title);
  heading.style.visibility = title > 0 ? 'visible' : 'hidden';
  heading.style.translate = `0 ${String((1 - rise) * 30 - lift * Math.min(260, innerHeight * 0.28))}px`;
  layer.style.opacity = String(arriving);
  layer.style.transform = `translateY(${String((1 - arriving) * 60)}px) scale(${String(0.96 + arriving * 0.04)})`;
  controls.style.opacity = String(ease(range(entrance, 0.92, 1)));
  stage.style.visibility = arriving > 0 ? 'visible' : 'hidden';
  stage.setAttribute('aria-hidden', String(arriving < 0.5));
  stage.inert = arriving < 0.99;
  stage.tabIndex = arriving >= 0.99 ? 0 : -1;
  section.classList.toggle('wall-active', arriving > 0);
  const before = value;
  value = arriving === 0 ? 0 : still ? positions[current] / last() : clamp(progress);
  if (arriving > 0 || value !== before) draw();
}

function seek(index: number, announce = true, smooth = false) {
  if (!measured) return;
  index = clamp(index, 0, cards.length - 1);
  const p = positions[index] / last();
  const moving = smooth && !paused;
  if (!moving) {
    current = index;
    value = p;
  }
  cinema.seekTimeline(
    (measured.perspectivesStart + measured.entrance + p * measured.travel) / measured.total,
    moving,
  );
  stage.scrollLeft = stage.scrollTop = 0;
  if (!moving) draw();
  if (announce)
    $('#wall-announcement').textContent =
      `${cards[index].getAttribute('aria-label') ?? ''}. ${String(index + 1)} of ${String(cards.length)}.`;
}

function seekIntro(smooth = false) {
  if (!measured) return;
  if (!smooth || paused) {
    current = value = 0;
    draw();
  }
  cinema.seekTimeline(
    (measured.perspectivesStart + measured.entrance * 0.58) / measured.total,
    smooth && !paused,
  );
}

export function layout() {
  mobile = innerWidth < 960;
  const compact = mobile && innerHeight < 620;
  section.classList.toggle('wall-compact', compact);
  width = mobile
    ? Math.min(390, innerWidth - 48)
    : Math.min(470, innerWidth * 0.326, Math.max(180, (innerHeight - 160) / 1.1));
  const height = mobile
    ? compact
      ? Math.max(240, innerHeight - (innerWidth >= 600 ? 140 : 220))
      : Math.min(470, innerHeight - 270)
    : width * 1.1;
  const type = mobile ? Math.min(32, Math.max(18, width * 0.087), height * 0.075) : width * 0.077;
  section.style.setProperty('--wall-width', `${String(width)}px`);
  section.style.setProperty('--wall-height', `${String(height)}px`);
  section.style.setProperty('--wall-type', `${String(type)}px`);
  sizes = cards.map((card) => ({ width: card.offsetWidth, height: card.offsetHeight }));
  const gap = mobile ? 65 : Math.min(140, innerWidth * 0.098);
  positions = [0];
  for (let i = 1; i < cards.length; i++)
    positions[i] = positions[i - 1] + sizes[i - 1].width / 2 + gap + sizes[i].width / 2;
  const travel = mobile ? (cards.length - 1) * Math.max(430, innerHeight * 0.64) : last() * 1.05;
  section.style.setProperty('--wall-travel', `${String(travel)}px`);

  // The home runway: core chapters, quality cards, then this wall.
  const story = $('.comparison-scroll');
  const entrance = Math.max(560, stage.clientHeight * 1.4);
  const deck = quality.metrics();
  const deckTotal = deck?.total ?? 0;
  story.style.setProperty('--quality-travel', `${String(deckTotal)}px`);
  story.style.setProperty('--perspectives-travel', `${String(entrance + travel)}px`);
  const total = story.offsetHeight - $('.time-comparison').offsetHeight;
  const core = total - deckTotal - entrance - travel;
  measured = {
    core,
    quality: deckTotal,
    qualityEntrance: deck?.entrance ?? 0,
    qualityTravel: deck?.travel ?? 0,
    perspectivesStart: core + deckTotal,
    entrance,
    travel,
    total,
  };
  cinema.update();
  draw();
}

export function openHash() {
  if (location.hash === '#perspectives-wall') seek(1, false);
  else if (location.hash === '#perspectives') seekIntro();
}

export function init() {
  section = $('.perspectives');
  stage = $('.wall-stage', section);
  heading = $('.center-head', section);
  layer = $('.wall-cards', section);
  controls = $('.wall-controls', section);
  cards = $$('.wall-card', section);
  previous = $('[data-wall-prev]', section);
  next = $('[data-wall-next]', section);
  output = $<HTMLOutputElement>('output', section);
  paused = isPaused();

  const scene = $('.time-comparison');
  scene.append(section);
  section.classList.add('perspectives-linked', 'wall-cinematic');
  $('.comparison').classList.add('has-perspectives');
  background = document.createElement('div');
  background.className = 'perspectives-background';
  background.setAttribute('aria-hidden', 'true');
  section.prepend(background);
  stage.tabIndex = -1;
  stage.setAttribute('aria-label', 'Delivery perspectives. Use left and right arrow keys to browse.');

  previous.addEventListener('click', () => seek(current - 1, true, true));
  next.addEventListener('click', () => seek(current + 1, true, true));
  stage.addEventListener('keydown', (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    const keys: Record<string, number> = {
      ArrowLeft: current - 1,
      ArrowRight: current + 1,
      Home: 0,
      End: cards.length - 1,
    };
    if (!(event.key in keys)) return;
    event.preventDefault();
    seek(keys[event.key], true, true);
  });
  stage.addEventListener('focusin', (event) => {
    const card = (event.target as Element).closest<HTMLElement>('.wall-card');
    if (card) seek(cards.indexOf(card), false);
  });
  onLink('a[href="#perspectives"]', () => seekIntro(true));
  addEventListener('resize', layout);
  addEventListener('hashchange', () => void frames(2).then(openHash));
  onPause((value) => {
    paused = value;
  });
}
