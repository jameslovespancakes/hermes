// Benchmarks tour: one stage holds while scroll moves through its steps; the squiggle behind it draws
// as you go. Leaving the hero, its copy lifts and fades while the dark statement widens to full bleed;
// the statement's bar chart rises once it is in view.
import { go } from './scroll';
import { $, $$, clamp, onPause } from './util';

export function init() {
  const hero = $('.b-hero');
  const copy = $$(':scope > :not(.scribbles)', hero);
  const scribbles = $('.scribbles', hero);
  const statement = $('.b-statement');
  const tour = $('.b-tour');
  const steps = $$('.tour-step', tour);
  const links = $$<HTMLAnchorElement>('.tour-nav a', tour);
  const squiggle = $<SVGPathElement>('.squiggle path', tour);
  let enabled = false;
  let frame = 0;

  // Scroll position of step i in the enhanced tour.
  const stepTop = (i: number) => {
    const top = scrollY + tour.getBoundingClientRect().top;
    return top + ((i + 0.5) / steps.length) * (tour.offsetHeight - innerHeight);
  };

  function intro() {
    const out = clamp(scrollY / hero.offsetHeight);
    for (const node of copy) {
      node.style.translate = `0 ${String(-out * 120)}px`;
      node.style.opacity = String(1 - out * 1.4);
    }
    scribbles.style.translate = `0 ${String(-out * 260)}px`;
    const grow = clamp(1 - statement.getBoundingClientRect().top / innerHeight);
    statement.style.scale = `${String(0.9 + grow * 0.1)} 1`;
    statement.style.borderRadius = `${String(48 + (1 - grow) * 24)}px`;
  }

  function paint() {
    frame = 0;
    intro();
    if (!enabled) return;
    const rect = tour.getBoundingClientRect();
    const p = clamp(-rect.top / (rect.height - innerHeight));
    const active = Math.min(steps.length - 1, Math.floor(p * steps.length));
    steps.forEach((step, i) => step.classList.toggle('on', i === active));
    links.forEach((link, i) => {
      if (i === active) link.setAttribute('aria-current', 'step');
      else link.removeAttribute('aria-current');
    });
    squiggle.style.strokeDashoffset = String(1 - p);
  }

  const request = () => (frame ||= requestAnimationFrame(paint));

  function layout() {
    enabled = innerWidth >= 900 && innerHeight >= 560;
    tour.classList.toggle('tour-enhanced', enabled);
    tour.style.setProperty('--steps', String(steps.length));
    if (!enabled) for (const step of steps) step.classList.remove('on');
    request();
  }

  function openHash() {
    const index = steps.findIndex((s) => `#${s.id}` === location.hash);
    if (index >= 0 && enabled) go(stepTop(index), { immediate: true, done: paint });
  }

  links.forEach((link, i) => {
    link.addEventListener('click', (event) => {
      if (!enabled) return;
      event.preventDefault();
      history.pushState(null, '', link.hash);
      go(stepTop(i), { done: paint });
    });
  });
  // The statement's bar chart rises once it comes into view.
  const bars = $('.bars');
  new IntersectionObserver(([entry]) => bars.classList.toggle('on', entry.isIntersecting), {
    threshold: 0.3,
  }).observe(bars);
  addEventListener('scroll', request, { passive: true });
  addEventListener('resize', layout);
  addEventListener('hashchange', openHash);
  onPause((paused) => {
    document.body.classList.toggle('motion-paused', paused);
    request();
  });
  layout();
  return openHash;
}
