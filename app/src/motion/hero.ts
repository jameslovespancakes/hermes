// A background video plays only while visible.
import { $ } from './util';

export function init(selector = '.hero-video') {
  const video = $<HTMLVideoElement>(selector);
  let visible = true;
  const sync = () => {
    if (visible && !document.hidden) void video.play().catch(() => undefined);
    else video.pause();
  };
  new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
    sync();
  }).observe(video);
  document.addEventListener('visibilitychange', sync);
  sync();
}
