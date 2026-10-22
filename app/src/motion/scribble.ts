// Hero background: sums are handwritten at random spots across the hero. A pen sweep writes each line of
// the working down to the answer, then the ink fades and a new sum appears somewhere else.
import { problems } from '../pages/benchmarks/problems';
import { $, isPaused, onPause } from './util';

const wait = (ms: number) => new Promise((done) => setTimeout(done, ms));
const random = (a: number, b: number) => a + Math.random() * (b - a);

export function init() {
  const box = $('.scribbles');
  let paused = isPaused();
  let next = Math.floor(random(0, problems.length));
  const taken: DOMRect[] = [];

  // A free spot anywhere below the nav. Sums under the headline are written fainter.
  function spot() {
    const { width, height } = box.getBoundingClientRect();
    const size = width < 760 ? [220, 100] : [280, 120];
    for (let tries = 0; tries < 30; tries++) {
      const rect = new DOMRect(random(12, width - size[0]), random(96, height - size[1]), size[0], size[1]);
      if (!taken.some((r) => r.x < rect.right && rect.x < r.right && r.y < rect.bottom && rect.y < r.bottom))
        return rect;
    }
    return undefined;
  }

  const central = (rect: DOMRect) => {
    const { width } = box.getBoundingClientRect();
    return rect.right > width * 0.3 && rect.x < width * 0.7;
  };

  async function write(line: HTMLElement) {
    line.style.animationDuration = `${String(line.textContent.length * 55)}ms`;
    line.classList.add('pen');
    await wait(line.textContent.length * 55 + 300);
  }

  async function scribble() {
    const rect = spot();
    if (!rect) return;
    taken.push(rect);
    const steps = problems[next++ % problems.length];
    const note = document.createElement('div');
    note.className = central(rect) ? 'scribble central' : 'scribble';
    note.style.left = `${String(rect.x)}px`;
    note.style.top = `${String(rect.y)}px`;
    note.style.rotate = `${String(random(-5, 4))}deg`;
    note.style.fontSize = `${String(random(20, 28))}px`;
    const lines = steps.map((text, i) => {
      const line = document.createElement('p');
      line.textContent = text;
      line.classList.toggle('answer', i === steps.length - 1);
      return line;
    });
    note.append(...lines);
    box.append(note);
    for (const line of lines) await write(line);
    await wait(2800);
    note.classList.add('out');
    await wait(900);
    note.remove();
    taken.splice(taken.indexOf(rect), 1);
  }

  async function loop() {
    for (;;) {
      await wait(random(260, 520));
      if (!paused && !document.hidden) void scribble();
    }
  }

  onPause((value) => (paused = value));
  void loop();
}
