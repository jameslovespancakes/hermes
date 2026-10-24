// Stepped chapters: scrolling crossfades a section's steps and redraws the faint chart behind each.
// A step may carry data-heading ("Keep|watch.") and data-caption to retitle its section.
import { $, $$, clamp, ease, range } from './util';

export function state(progress: number, count: number) {
  const position = clamp(progress * count, 0, count - 1);
  const base = Math.floor(position);
  const turn = ease(range(position - base, 0.65, 1));
  return { base, turn, active: turn >= 0.5 ? Math.min(count - 1, base + 1) : base };
}

// How much of step `index` is showing: the current step fades out as the next fades in.
export function shown(index: number, progress: number, count: number) {
  const { base, turn } = state(progress, count);
  if (index === base) return 1 - turn;
  if (index === base + 1) return turn;
  return 0;
}

// A stepped section's sticky heading leaves before the next heading arrives, so they never overlap.
export function headingOpacity(scene: number, t: number, own: number) {
  if (scene === own) return 1 - ease(range(t, 0, 0.46));
  if (scene === own - 1) return ease(range(t, 0.54, 1));
  return 0;
}

export function create(section: HTMLElement) {
  const steps = $$('.step', section);
  const deck = $('.steps', section);
  const word = section.querySelector('h2 span');
  const accent = section.querySelector('h2 em');
  const caption = section.querySelector('.method-heading .method-context');
  const first = steps[0].dataset;

  function retitle(step: DOMStringMap) {
    if (!step.heading || !word || !accent) return;
    [word.textContent, accent.textContent] = step.heading.split('|');
    if (caption && step.caption) caption.textContent = step.caption;
  }

  return {
    count: steps.length,
    render(progress: number, enhanced: boolean) {
      deck.classList.toggle('deck-enhanced', enhanced);
      steps.forEach((step, i) => {
        const v = enhanced ? shown(i, progress, steps.length) : 1;
        step.style.opacity = String(v);
        step.style.setProperty('--draw', String(v));
        step.inert = enhanced && v < 0.5;
      });
      retitle(enhanced ? steps[state(progress, steps.length).active].dataset : first);
    },
  };
}
