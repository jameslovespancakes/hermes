// Home page decorations: city strip and word-by-word heading reveals.
import { $, $$ } from './util';

const curve = 'cubic-bezier(.22,1,.36,1)';

export function init() {
  const body = document.body;
  const running = new Map<Element, Animation>();
  body.classList.add('motion-ready');

  function run(element: Element, keyframes: Keyframe[], options: KeyframeAnimationOptions) {
    if (document.hidden) return;
    running.get(element)?.cancel();
    const animation = element.animate(keyframes, { duration: 700, easing: curve, ...options });
    running.set(element, animation);
    animation.onfinish = animation.oncancel = () => {
      if (running.get(element) === animation) running.delete(element);
    };
    return animation;
  }

  // The city names loop on a seamless strip with one accessible copy.
  const cities = $('.cities');
  const set = document.createElement('div');
  set.className = 'city-set';
  set.append(...cities.childNodes);
  const clone = set.cloneNode(true) as HTMLElement;
  clone.setAttribute('aria-hidden', 'true');
  const track = document.createElement('div');
  track.className = 'city-track';
  track.append(set, clone);
  cities.append(track);

  // One scroll runway for the goal, data, model and perspectives.
  const comparison = $('.time-comparison');
  const runway = document.createElement('div');
  runway.className = 'comparison-scroll';
  comparison.before(runway);
  runway.append(comparison);

  let frame = 0;
  const nav = $('.nav-wrap');
  const paintNav = () => {
    frame = 0;
    nav.classList.toggle('scrolled', scrollY > 65);
  };
  const requestNav = () => (frame ||= requestAnimationFrame(paintNav));
  const layout = () => {
    body.classList.toggle('pin-story', innerWidth >= 960);
    requestNav();
  };
  addEventListener('scroll', requestNav, { passive: true });
  addEventListener('resize', layout);
  layout();

  // Headings arrive word by word.
  const pending = new Set<HTMLElement>();
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const heading = entry.target as HTMLElement;
        observer.unobserve(heading);
        pending.delete(heading);
        heading.style.opacity = '';
        $$('.reveal-word', heading).forEach((word, i) =>
          run(
            word,
            [
              { opacity: 0, transform: 'translateY(28px) rotate(2deg)', filter: 'blur(5px)' },
              { opacity: 1, transform: 'none', filter: 'blur(0px)' },
            ],
            { duration: 850, delay: i * 65, fill: 'backwards' },
          ),
        );
      }
    },
    { threshold: 0.12, rootMargin: '0px 0px -30px 0px' },
  );
  if (!document.hidden) {
    for (const heading of $$('h1, main h2').filter((h) => !h.closest('#data-split, #perspectives'))) {
      splitWords(heading);
      heading.style.opacity = '0';
      pending.add(heading);
      observer.observe(heading);
    }
  }

  function stopAll() {
    for (const animation of running.values()) animation.cancel();
    running.clear();
    for (const heading of pending) {
      heading.style.opacity = '';
      observer.unobserve(heading);
    }
    pending.clear();
  }
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stopAll();
  });
}

function splitWords(heading: HTMLElement) {
  const walker = document.createTreeWalker(heading, NodeFilter.SHOW_TEXT);
  const nodes: Text[] = [];
  while (walker.nextNode()) nodes.push(walker.currentNode as Text);
  for (const node of nodes) {
    const fragment = document.createDocumentFragment();
    for (const part of node.data.split(/(\s+)/)) {
      if (!part) continue;
      if (/^\s+$/.test(part)) {
        fragment.append(part);
        continue;
      }
      const word = document.createElement('span');
      word.className = 'reveal-word';
      word.textContent = part;
      fragment.append(word);
    }
    node.replaceWith(fragment);
  }
}
