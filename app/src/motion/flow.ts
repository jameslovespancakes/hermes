// Research pages: chapters share one sticky figure on the native scroll position.
// Figures stay in their own sections; nothing is cloned.
import * as deck from './deck';
import * as parcel from './parcel';
import { go } from './scroll';
import { $, $$, clamp, ease, frames, isPaused, onPause, range } from './util';

interface Scene {
  node: HTMLElement;
  index: number;
  kind: string;
  header: HTMLElement;
  figure: HTMLElement;
  surface: HTMLElement;
  span: number;
  stop: number;
  steps?: ReturnType<typeof deck.create>;
}

// Each chapter sets its colour (data-tone) and background photo strength (data-photo).
const tones: Record<string, string> = { cream: '#ffffeb', peach: '#ffe1b5', green: '#034f46' };

const rgb = (hex: string) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
const luminance = (c: number[]) =>
  c
    .map((v) => v / 255)
    .map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4))
    .reduce((sum, v, i) => sum + v * [0.2126, 0.7152, 0.0722][i], 0);
const contrast = (hex: string, l: number) => {
  const a = luminance(rgb(hex));
  return (Math.max(a, l) + 0.05) / (Math.min(a, l) + 0.05);
};

export function init() {
  const journey = $('#method-journey');
  const opening = journey.querySelector<HTMLElement>('.method-opening');
  const nodes = [...(opening ? [opening] : []), ...$$('[data-method-section]', journey)];
  const overview = $('.method-figure', nodes[0]);
  let stop = 0;
  const scenes: Scene[] = nodes.map((node, index) => {
    const figure = node.querySelector<HTMLElement>('.method-figure') ?? overview;
    const kind = node.dataset.methodSection ?? 'parcel';
    const steps = node.querySelector('.steps') ? deck.create(node) : undefined;
    const span = steps?.count ?? 1;
    const scene = {
      node,
      index,
      kind,
      header: $('.method-heading,.opening-copy', node),
      figure,
      surface: $('.visual-surface', figure),
      span,
      stop,
      steps,
    };
    stop += span;
    return scene;
  });
  const last = scenes.length - 1;
  // The last chapter may have several steps; scrolling ends on its final one.
  const end = scenes[last].stop + scenes[last].span - 1;
  const stepped = scenes.filter((s) => s.steps);
  const aliases: Record<string, number> = Object.fromEntries(scenes.map((s) => [s.node.id, s.index]));
  const lines = $$<SVGPathElement>('[data-model-line]', journey);
  const colors = scenes.map((s) => tones[s.node.dataset.tone ?? 'cream']);
  const photos = scenes.map((s) => Number(s.node.dataset.photo ?? 0));
  // The folding parcel only exists on Methodology; its unpack chapter hands off to the next.
  const box = opening ? parcel.create() : undefined;
  const unpack = scenes.findIndex((s) => s.kind === 'unpack');
  let enabled = false;
  let visible = true;
  let paused = isPaused();
  let frame = 0;
  let start = 0;
  let distance = 900;

  // Background and text colours follow the chapter, keeping readable contrast.
  function color(index: number, t: number) {
    const a = rgb(colors[index]);
    const b = rgb(colors[Math.min(last, index + 1)]);
    const f = ease(range(t, 0.12, 0.88));
    const background = a.map((v, i) => Math.round(v + (b[i] - v) * f));
    const l = luminance(background);
    let ink = contrast('#ffffeb', l) > contrast('#1a1a1a', l) ? '#ffffeb' : '#1a1a1a';
    if (contrast(ink, l) < 4.5) ink = l > 0.179 ? '#000000' : '#ffffff';
    let accent = l < 0.18 ? '#ffe1b5' : '#034f46';
    if (contrast(accent, l) < 3.5) accent = ink;
    const style = document.body.style;
    style.setProperty('--journey-background', `rgb(${background.join(',')})`);
    style.setProperty('--journey-ink', ink);
    style.setProperty('--journey-accent', accent);
    style.setProperty('--journey-muted', ink);
    style.setProperty(
      '--chapter-image-opacity',
      (photos[index] + (photos[Math.min(last, index + 1)] - photos[index]) * f).toFixed(4),
    );
  }

  function pose(scene: Scene, opacity: number, rise = 0, pitch = 0, yaw = 0, scale = 1) {
    scene.figure.style.opacity = opacity.toFixed(5);
    const style = scene.surface.style;
    style.setProperty('--surface-rise', `${rise.toFixed(3)}px`);
    style.setProperty('--surface-pitch', `${pitch.toFixed(3)}deg`);
    style.setProperty('--surface-yaw', `${yaw.toFixed(3)}deg`);
    style.setProperty('--surface-scale', scale.toFixed(5));
  }

  function detail(scene: Scene, p: number) {
    if (scene.kind === 'stack')
      for (const line of lines) {
        line.style.strokeDasharray = '1';
        line.style.strokeDashoffset = (1 - ease(range(p * scene.span, 0.02, 0.3))).toFixed(5);
      }
    scene.steps?.render(p, enabled, paused);
  }

  // Stepped sections keep a sticky heading through their steps.
  function headings(index: number, t: number) {
    for (const s of stepped) {
      const opacity = deck.headingOpacity(index, t, s.index, paused);
      s.header.style.opacity = String(opacity);
      s.header.style.visibility = opacity > 0.001 ? 'visible' : 'hidden';
      s.header.inert = opacity <= 0.001;
    }
  }

  function paint() {
    cancelAnimationFrame(frame);
    frame = 0;
    if (document.hidden) return;
    if (!enabled) {
      color(0, 0);
      box?.draw(1);
      for (const scene of scenes) {
        pose(scene, 1);
        scene.header.style.opacity = '1';
        scene.header.style.visibility = '';
        scene.header.inert = false;
        detail(scene, 1);
      }
      return;
    }
    const travel = clamp((scrollY - start) / distance, 0, end + 0.45);
    let index = 0;
    while (index < last && travel >= scenes[index + 1].stop) index++;
    const scene = scenes[index];
    const local = (travel - scene.stop) / scene.span;
    const q = index + local;
    // Unpack and stepped chapters hand off late; others cross-fade mid-scroll.
    const [a, b] = index === unpack ? [0.55, 0.92] : scene.steps ? [0.88, 1] : [0.35, 0.78];
    const t = index < last ? range(local, a, b) : 0;
    const progress = (s: Scene) => clamp((travel - s.stop) / s.span);
    color(index, t);
    for (const s of scenes) {
      pose(s, 0);
      s.header.style.opacity = String(0.45 + 0.55 * (1 - clamp(Math.abs(q - s.index) * 0.8)));
    }
    headings(index, t);

    if (paused) {
      // Paused: show the nearest complete chapter.
      const current = Math.min(last, index + (t >= 0.5 ? 1 : 0));
      color(current, 0);
      box?.draw(current === 0 ? 0 : 1);
      pose(scenes[current], 1);
      for (const s of scenes) detail(s, s.steps ? progress(s) : 1);
      return;
    }

    box?.draw(ease(range(q, 0.12, 1)));
    if (index === 0 && box) pose(scenes[0], 1);
    else if (t === 0 || t === 1) pose(scenes[index + t], 1);
    else if (box && index === unpack) {
      // The data sheet unfolds into the dataset figure.
      pose(scene, 1);
      pose(scenes[index + 1], ease(range(t, 0.65, 1)));
      box.unfold(t, scenes[index + 1].surface);
    } else {
      const next = scenes[index + 1];
      const leave = ease(range(t, 0, 0.46));
      const arrive = ease(range(t, 0.54, 1));
      pose(scene, 1 - leave, 12 * leave);
      // Results arrive flat; measured charts never tilt or scale.
      if (next.kind === 'results') pose(next, arrive);
      else pose(next, arrive, 22 * (1 - arrive), 8 * (1 - arrive), -4 * (1 - arrive), 0.975 + 0.025 * arrive);
    }
    for (const s of scenes) {
      if (s.steps) detail(s, progress(s));
      else if (Math.abs(q - s.index) < 1.1) detail(s, clamp((q - s.index + 0.22) / 0.74));
      else detail(s, 1);
    }
  }

  const request = () => {
    if (!frame && !document.hidden && visible) frame = requestAnimationFrame(paint);
  };

  function layout() {
    const top = parseFloat(getComputedStyle(document.body).getPropertyValue('--method-top')) || 104;
    const height = innerHeight - top;
    enabled = innerWidth >= 960 && height >= 600;
    distance = Math.max(720, innerHeight * 0.9);
    journey.style.setProperty('--chapter-distance', `${distance}px`);
    journey.style.setProperty('--stage-height', `${height}px`);
    document.body.classList.toggle('method-sticky', enabled);
    journey.style.gridTemplateRows = enabled
      ? [...scenes.map((s) => `${s.span * distance}px`), `${distance * 0.45}px`].join(' ')
      : '';
    for (const s of scenes) {
      s.header.style.gridRow = enabled ? String(s.index + 1) : '';
      // Focus the heading when sticky, the section otherwise.
      if (enabled) {
        s.node.removeAttribute('tabindex');
        s.header.tabIndex = 0;
      } else {
        s.header.removeAttribute('tabindex');
        s.node.tabIndex = 0;
      }
    }
    for (const s of stepped)
      s.node.style.setProperty('--heading-height', `${s.header.getBoundingClientRect().height}px`);
    const first = scenes[0].header.getBoundingClientRect();
    start = scrollY + first.top + first.height / 2 - (top + height / 2);
    paint();
  }

  function seek(index: number, smooth = false, done?: () => void) {
    if (!enabled && index === unpack) index = 0;
    const scene = scenes[index];
    const padding = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0;
    const y = enabled
      ? start + (scene.stop + (index ? 0.28 : 0)) * distance
      : scrollY + scene.node.getBoundingClientRect().top - padding - 12;
    go(y, {
      immediate: !smooth || paused,
      done: () => {
        paint();
        done?.();
      },
    });
  }

  // Keyboard: arrows visit adjacent chapters, Home and End the first and last.
  const help = document.createElement('span');
  help.id = 'method-key-help';
  help.className = 'sr-only';
  help.textContent =
    'Scroll through the chapters. With a chapter heading focused, arrow keys visit adjacent chapters; Home and End visit the first and last.';
  const announcement = document.createElement('span');
  announcement.className = 'sr-only';
  announcement.setAttribute('aria-live', 'polite');
  document.body.append(help, announcement);

  function visit(index: number) {
    const scene = scenes[!enabled && index === unpack ? 0 : index];
    seek(scene.index, true, () => {
      (enabled ? scene.header : scene.node).focus({ preventScroll: true });
      announcement.textContent = scene.header.innerText.replace(/\s+/g, ' ');
    });
  }

  for (const scene of scenes) {
    scene.node.setAttribute('aria-describedby', 'method-key-help');
    scene.header.setAttribute('aria-describedby', 'method-key-help');
    scene.node.addEventListener('keydown', (event) => {
      if (event.target !== scene.node && event.target !== scene.header) return;
      if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      const available = enabled ? scenes : scenes.filter((s) => s.kind !== 'unpack');
      const i = available.indexOf(scene);
      const ahead = available[Math.min(available.length - 1, i + 1)].index;
      const behind = available[Math.max(0, i - 1)].index;
      const keys: Record<string, number> = {
        ArrowRight: ahead,
        ArrowDown: ahead,
        ArrowLeft: behind,
        ArrowUp: behind,
        Home: 0,
        End: last,
      };
      if (!(event.key in keys)) return;
      event.preventDefault();
      visit(keys[event.key]);
    });
  }

  document.addEventListener('click', (event) => {
    const link = (event.target as Element | null)?.closest('a[href^="#"]');
    if (!link || event.defaultPrevented || event.button !== 0 || link.hasAttribute('download')) return;
    if (event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return;
    const hash = link.getAttribute('href') ?? '';
    const id = hash.slice(1);
    if (!(id in aliases)) return;
    event.preventDefault();
    if (location.hash !== hash) history.pushState(null, '', hash);
    visit(aliases[id]);
  });

  function openHash() {
    const id = location.hash.slice(1);
    if (id in aliases) seek(aliases[id]);
  }

  new IntersectionObserver(
    ([entry]) => {
      visible = entry.isIntersecting;
      if (visible) request();
    },
    { rootMargin: '200px 0px' },
  ).observe(journey);
  addEventListener('scroll', request, { passive: true });
  addEventListener('resize', layout);
  addEventListener('pageshow', layout);
  addEventListener('hashchange', () => void frames().then(openHash));
  onPause((value) => {
    paused = value;
    document.body.classList.toggle('motion-paused', paused);
    paint();
  });
  document.addEventListener('visibilitychange', request);
  layout();
  return openHash;
}
