// Small shared helpers for the scroll engines.

export const clamp = (v: number, min = 0, max = 1) => Math.max(min, Math.min(max, v));
export const range = (v: number, a: number, b: number) => clamp((v - a) / (b - a));
export const ease = (v: number) => v * v * (3 - 2 * v);
export const mix = (a: number, b: number, t: number) => a + (b - a) * t;

export const $ = <T extends Element = HTMLElement>(selector: string, root: ParentNode = document) =>
  root.querySelector(selector) as T;
export const $$ = <T extends Element = HTMLElement>(selector: string, root: ParentNode = document) => [
  ...root.querySelectorAll<T>(selector),
];

export const isPaused = () => document.body.classList.contains('motion-paused');

// Programmatic pause: dispatch `arrival:motion` with `{ paused }`.
export function onPause(handler: (paused: boolean) => void) {
  window.addEventListener('arrival:motion', (event) => {
    handler(event.detail.paused);
  });
}

// Plain left clicks on in-page links, ignoring modified clicks.
export function onLink(selector: string, handler: (hash: string) => void) {
  document.addEventListener('click', (event) => {
    const link = (event.target as Element | null)?.closest(selector);
    if (!link || event.defaultPrevented || event.button !== 0) return;
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    const hash = link.getAttribute('href') ?? '';
    if (location.hash !== hash) history.pushState(null, '', hash);
    handler(hash);
  });
}

export const frames = (count = 1): Promise<void> =>
  new Promise((resolve) => {
    const next = (left: number) => {
      requestAnimationFrame(() => {
        if (left > 1) next(left - 1);
        else resolve();
      });
    };
    next(count);
  });

export const stickyTop = (node: Element) => parseFloat(getComputedStyle(node).top) || 0;
