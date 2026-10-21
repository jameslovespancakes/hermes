// Benchmarks reel: one sticky full-screen stage. Each photo wipes up over the last as you scroll,
// the outgoing one slowly zooms and dims, and the next figure draws in.
import { go } from './scroll';
import { $, $$, clamp, ease, isPaused, onPause } from './util';

export function init() {
  const reel = $('.reel');
  const scenes = $$('.reel-scene', reel);
  const last = scenes.length - 1;
  let enabled = false;
  let paused = isPaused();
  let frame = 0;

  function paint() {
    frame = 0;
    if (!enabled) return;
    const rect = reel.getBoundingClientRect();
    const p = clamp(-rect.top / (rect.height - innerHeight)) * last;
    scenes.forEach((scene, i) => {
      const raw = i === 0 ? 1 : clamp(p - i + 1);
      const reveal = paused ? Math.round(raw) : ease(raw);
      const leave = paused ? 0 : ease(clamp(p - i));
      scene.style.clipPath = `inset(${((1 - reveal) * 100).toFixed(2)}% 0 0 0)`;
      scene.style.setProperty('--reveal', reveal.toFixed(4));
      scene.style.setProperty('--leave', leave.toFixed(4));
      scene.style.setProperty('--draw', ease(clamp(raw * 1.4 - 0.4)).toFixed(4));
    });
  }

  const request = () => (frame ||= requestAnimationFrame(paint));

  function layout() {
    enabled = innerWidth >= 760 && innerHeight >= 520;
    reel.classList.toggle('reel-enhanced', enabled);
    reel.style.setProperty('--scenes', String(scenes.length));
    if (!enabled) for (const scene of scenes) scene.removeAttribute('style');
    request();
  }

  function openHash() {
    const index = scenes.findIndex((s) => `#${s.id}` === location.hash);
    if (index < 0) return;
    const top = scrollY + reel.getBoundingClientRect().top;
    go(enabled ? top + (index / last) * (reel.offsetHeight - innerHeight) : top + scenes[index].offsetTop, {
      immediate: true,
      done: paint,
    });
  }

  addEventListener('scroll', request, { passive: true });
  addEventListener('resize', layout);
  addEventListener('hashchange', openHash);
  onPause((value) => {
    paused = value;
    request();
  });
  layout();
  return openHash;
}
