// Hero video plays only while visible and motion is not paused.
import { $, isPaused, onPause } from './util';

export function init() {
  const video = $<HTMLVideoElement>('.hero-video');
  let paused = isPaused();
  let visible = true;
  const sync = () => {
    if (!paused && visible && !document.hidden) void video.play().catch(() => undefined);
    else video.pause();
  };
  new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
    sync();
  }).observe(video);
  onPause((value) => {
    paused = value;
    document.body.classList.toggle('motion-paused', paused);
    sync();
  });
  document.addEventListener('visibilitychange', sync);
  sync();
}
