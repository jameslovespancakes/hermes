// Smooth wheel and navigation scrolling on the real document scroll position.
// Touch, nested scrollers and modified gestures stay native.
import { isPaused, onPause } from './util';

interface Options {
  immediate?: boolean;
  done?: () => void;
}

let root: HTMLElement;
let fine: MediaQueryList;
const limit = () => Math.max(0, root.scrollHeight - innerHeight);
const fit = (y: number) => Math.max(0, Math.min(limit(), y));

let frame = 0;
let kind: '' | 'wheel' | 'navigation' = '';
let target = 0;
let written = 0;
let last = 0;
let start = 0;
let origin = 0;
let duration = 0;
let done: (() => void) | undefined;
let paused = false;

function stop() {
  cancelAnimationFrame(frame);
  frame = 0;
  kind = '';
  done = undefined;
  target = written = scrollY;
  root.classList.remove('hermes-scroll-active');
}

function write(y: number) {
  scrollTo({ top: y, behavior: 'instant' });
  written = scrollY;
}

function finish() {
  const callback = done;
  stop();
  callback?.();
}

function tick(now: number) {
  frame = 0;
  if (document.hidden || paused) {
    stop();
    return;
  }
  target = fit(target);
  if (kind === 'wheel') {
    const dt = Math.min(40, Math.max(1, now - last));
    last = now;
    if (Math.abs(target - scrollY) < 1) {
      write(target);
      finish();
      return;
    }
    const next = scrollY + (target - scrollY) * (1 - Math.exp(-dt / 85));
    // Avoid a subpixel stall at the end of a wheel step.
    write(Math.abs(next - scrollY) < 0.6 ? scrollY + Math.sign(target - scrollY) : next);
  } else {
    const p = Math.min(1, (now - start) / duration);
    write(fit(origin + (target - origin) * (1 - (1 - p) ** 4)));
    if (p === 1) {
      write(target);
      finish();
      return;
    }
  }
  frame = requestAnimationFrame(tick);
}

export function go(y: number, { immediate = false, done: callback }: Options = {}) {
  stop();
  target = fit(y);
  done = callback;
  if (immediate || paused || document.hidden || Math.abs(target - scrollY) < 1) {
    write(target);
    finish();
    return;
  }
  kind = 'navigation';
  origin = scrollY;
  start = last = performance.now();
  duration = Math.min(1100, Math.max(380, 340 + Math.abs(target - origin) * 0.12));
  root.classList.add('hermes-scroll-active');
  frame = requestAnimationFrame(tick);
}

// True when a nested element should scroll instead of the page.
function nested(event: WheelEvent, delta: number) {
  for (const node of event.composedPath()) {
    if (!(node instanceof Element) || node === document.body || node === root) break;
    if (node.matches('input,textarea,select,dialog[open],[contenteditable],[data-native-scroll]'))
      return true;
    const style = getComputedStyle(node);
    if (!/(auto|scroll|overlay)/.test(style.overflowY)) continue;
    if (/contain|none/.test(style.overscrollBehaviorY)) return true;
    const room = delta < 0 ? node.scrollTop > 0 : node.scrollTop + node.clientHeight < node.scrollHeight - 1;
    if (node.scrollHeight > node.clientHeight + 1 && room) return true;
  }
  return false;
}

function wheel(event: WheelEvent) {
  const modified = event.ctrlKey || event.metaKey || event.altKey || event.shiftKey;
  const sideways = Math.abs(event.deltaX) > Math.abs(event.deltaY);
  if (paused || document.hidden || !fine.matches || !event.cancelable || modified || sideways) {
    stop();
    return;
  }
  const scale = event.deltaMode === 1 ? 24 : event.deltaMode === 2 ? innerHeight * 0.9 : 1;
  const delta = event.deltaY * scale;
  if (!delta) return;
  if (nested(event, delta)) {
    stop();
    return;
  }
  const y = scrollY;
  if ((delta < 0 && y <= 0) || (delta > 0 && y >= limit() - 1)) {
    stop();
    return;
  }
  const base = kind === 'wheel' && Math.sign(target - y) === Math.sign(delta) ? target : y;
  const next = fit(base + delta);
  if (next === y && !frame) return;
  event.preventDefault();
  if (kind !== 'wheel') {
    stop();
    kind = 'wheel';
    last = performance.now();
  }
  target = next;
  root.classList.add('hermes-scroll-active');
  frame ||= requestAnimationFrame(tick);
}

export function init() {
  root = document.documentElement;
  fine = matchMedia('(hover: hover) and (pointer: fine)');
  paused = isPaused();
  target = written = scrollY;
  addEventListener('wheel', wheel, { passive: false });
  // Any other scroll source takes over immediately.
  addEventListener(
    'scroll',
    () => {
      if (frame && Math.abs(scrollY - written) > 2) stop();
    },
    { passive: true },
  );
  for (const type of ['pointerdown', 'touchstart', 'keydown'] as const) addEventListener(type, stop, true);
  for (const type of ['resize', 'pageshow', 'pagehide'] as const) addEventListener(type, stop);
  document.addEventListener('visibilitychange', stop);
  onPause((value) => {
    paused = value;
    root.toggleAttribute('data-scroll-paused', paused);
    stop();
  });
  root.toggleAttribute('data-scroll-paused', paused);
}
