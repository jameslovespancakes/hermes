// Home page scroll story: goal photo, data split, model training, quality cards, perspectives.
// One sticky scene follows the native scroll position.
import * as quality from './quality';
import { go } from './scroll';
import * as split from './split';
import { create } from './training';
import * as wall from './wall';
import { $, clamp, mix, onLink, ease, range, stickyTop } from './util';

const dataEnd = 0.58;

let outer: HTMLElement;
let comparison: HTMLElement;
let modelSection: HTMLElement;
let modelPin: HTMLElement;
let photo: HTMLElement;
let image: HTMLElement;
let intro: HTMLElement;
let curtain: HTMLElement;
let training: ReturnType<typeof create>;
let mobile = false;
let frame = 0;
const state = { story: 0, hero: 0 };
const target = { story: 0, hero: 0 };

function progress() {
  const distance = outer.offsetHeight - comparison.offsetHeight;
  return distance > 1 ? clamp((stickyTop(comparison) - outer.getBoundingClientRect().top) / distance) : 0;
}

function paintComparison(p: number) {
  const box = split.handoff();
  const flow = range(p, 0, dataEnd);
  const q = (box ? range(flow, 0, 0.42) : flow) * 0.43;
  const width = comparison.clientWidth;
  const height = comparison.clientHeight;
  const expand = ease(range(q, 0, 0.14));
  const shrink = ease(range(q, 0.2, 0.3));
  const lift = ease(range(q, 0.29, 0.43));
  const portraitWidth = mobile ? Math.min(width * 0.96, 360) : Math.min(400, width * 0.36);
  const portraitHeight = Math.min(mobile ? 470 : 500, height * 0.76);
  const w = mix(width, portraitWidth, shrink);
  const h = mix(Math.min(720, height * 0.9), portraitHeight, shrink);
  const dip = Math.sin(lift * Math.PI) * Math.min(180, Math.max(0, (height - portraitHeight) / 2 - 16));
  const shape = box ? ease(range(flow, 0.32, 0.46)) : 0;
  const blend = box ? ease(range(flow, 0.46, 0.51)) : 0;
  const end = box ?? { left: 0, top: 0, width: w, height: h, radius: 18 };
  // The photo becomes the data ribbon, then the ribbon takes over.
  photo.style.width = `${String(mix(w, end.width, shape))}px`;
  photo.style.height = `${String(mix(h, end.height, shape))}px`;
  photo.style.left = `${String(mix((width - w) / 2, end.left, shape))}px`;
  photo.style.top = `${String(mix((height - h) / 2 + dip, end.top, shape))}px`;
  photo.style.borderRadius = `${String(mix(mix(mobile ? 20 : 28, 18, shrink), end.radius, shape))}px`;
  photo.style.opacity = String(1 - blend);
  photo.style.visibility = blend < 1 ? 'visible' : 'hidden';
  photo.setAttribute('aria-hidden', String(blend >= 0.5));
  if (box) split.render(range(flow, 0.51, 1), blend, range(p, 0.56, 0.68));
  image.style.transform = `scale(${String(1.04 + expand * 0.08)}) translateX(${String(-q * 10)}px)`;
  const text = 1 - ease(range(q, 0.17, 0.27));
  intro.style.opacity = String(text);
  intro.style.translate = `0 ${String(-range(q, 0.17, 0.29) * 180)}px`;
  intro.style.visibility = text > 0 ? 'visible' : 'hidden';
  intro.setAttribute('aria-hidden', String(text < 0.5));
  curtain.style.transform = `translateY(${String(-ease(range(q, 0.27, 0.38)) * (height + 650))}px)`;
  curtain.style.borderRadius = `0 0 ${String(48 * lift)}px ${String(48 * lift)}px`;
  paintModel(p);
}

function paintModel(p: number) {
  const visibility = ease(range(p, 0.575, 0.6));
  modelSection.style.visibility = visibility > 0 ? 'visible' : 'hidden';
  modelSection.setAttribute('aria-hidden', String(visibility < 0.5));
  training.paint(range(p, 0.69, 0.98), visibility, {
    width: modelPin.clientWidth,
    height: modelPin.clientHeight,
    mobile,
    handoff: {
      source: split.trainingSource(),
      progress: ease(range(p, 0.6, 0.68)),
      content: ease(range(p, 0.68, 0.71)),
    },
  });
}

function paintStory(p: number) {
  const metrics = wall.metrics();
  const deck = Boolean(metrics?.quality);
  const distance = metrics ? p * metrics.total : 0;
  const core = metrics ? clamp(distance / metrics.core) : p;
  const entering = metrics && deck ? clamp((distance - metrics.core) / metrics.qualityEntrance) : 0;
  const cards =
    metrics && deck ? clamp((distance - metrics.core - metrics.qualityEntrance) / metrics.qualityTravel) : 0;
  const entrance = metrics ? clamp((distance - metrics.perspectivesStart) / metrics.entrance) : 0;
  const gallery = metrics
    ? clamp((distance - metrics.perspectivesStart - metrics.entrance) / metrics.travel)
    : 0;
  const leaving = deck ? ease(range(entering, 0.08, 0.55)) : ease(range(entrance, 0.08, 0.4));
  // Reset before drawing so reverse scrolling restores the exact geometry.
  modelSection.style.opacity = String(1 - leaving);
  modelSection.style.translate = `0 ${String(-leaving * (deck ? 110 : 32))}px`;
  modelSection.style.scale = String(1 - leaving * (deck ? 0.08 : 0.035));
  paintComparison(core);
  if (leaving > 0.5) modelSection.setAttribute('aria-hidden', 'true');
  if (leaving === 1) modelSection.style.visibility = 'hidden';
  if (deck) quality.render(entering, cards, entrance);
  if (metrics) wall.render(entrance, gallery);
}

function paint() {
  frame = 0;
  if (document.hidden) return;
  let moving = false;
  for (const key of ['story', 'hero'] as const) {
    const diff = target[key] - state[key];
    if (Math.abs(diff) > 0.0002) {
      state[key] += diff * 0.17;
      moving = true;
    } else state[key] = target[key];
  }
  paintStory(state.story);
  $('.hero-copy').style.translate = `0 ${-state.hero * (innerWidth < 680 ? 20 : 60)}px`;
  if (moving) frame = requestAnimationFrame(paint);
}

export function update() {
  target.story = progress();
  target.hero = clamp(scrollY / $('.hero').offsetHeight);
  frame ||= requestAnimationFrame(paint);
}

function layout() {
  mobile = innerWidth < 960;
  document.body.classList.toggle('cinema-mobile', mobile);
  training.invalidate();
  split.measure();
  update();
}

export function seekTimeline(p: number, smooth = false) {
  const top = scrollY + outer.getBoundingClientRect().top - stickyTop(comparison);
  go(top + clamp(p) * (outer.offsetHeight - comparison.offsetHeight), { immediate: !smooth });
  if (!smooth) state.story = clamp(p);
  update();
}

// Seek within the core chapters, before the quality cards and perspectives.
function seekCore(p: number, smooth = false) {
  const metrics = wall.metrics();
  seekTimeline(metrics ? (p * metrics.core) / metrics.total : p, smooth);
}

const seekData = (smooth = false) => seekCore(0.56 * dataEnd, smooth);
const seekModel = (smooth = false) => seekCore(0.73, smooth);

export function openHash() {
  if (location.hash === '#data-split') seekData();
  else if (location.hash === '#model-training') seekModel();
}

export function init() {
  outer = $('.comparison-scroll');
  comparison = $('.time-comparison');
  modelSection = $('#model-training');
  modelPin = $('.model-pin');
  photo = $('.film-photo');
  image = $('.film-photo-image');
  intro = $('.film-intro');
  document.body.classList.add('cinema-ready');

  curtain = document.createElement('div');
  curtain.className = 'film-curtain';
  curtain.setAttribute('aria-hidden', 'true');
  comparison.prepend(curtain);
  comparison.append(modelSection);
  modelSection.classList.add('model-linked');
  outer.classList.add('with-model');
  training = create(modelPin);

  onLink('a[href="#data-split"],a[href="#model-training"]', (hash) => {
    if (hash === '#data-split') seekData(true);
    else seekModel(true);
  });
  addEventListener('scroll', update, { passive: true });
  addEventListener('resize', layout);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) update();
  });
  addEventListener('hashchange', openHash);
}
