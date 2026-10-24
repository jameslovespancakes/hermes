// Hero background: sums are handwritten at random spots across the hero. A pen sweep writes each line of
// the working down to the answer, then the ink fades and a new sum appears somewhere else.
import { $ } from './util';

// Each sum is worked line by line; the last line is the answer, correct to the digits shown.
const problems = [
  ['(8.23 + 17.21 + 17.96) ÷ 3', '= 43.40 ÷ 3', '= 14.47 min'],
  ['(61.73 − 46.83) ÷ 61.73', '= 14.90 ÷ 61.73', '= 0.2414'],
  ['d² = (3.2 − 0.8)² + (1.4 + 0.4)²', '= 2.4² + 1.8²', '= 5.76 + 3.24 = 9', 'd = 3 km'],
  ['t = 4.5 km ÷ 18 km/h × 60', '= 0.25 h × 60', '= 15 min'],
  ['MAE = (|12| + |−7| + |3| + |−2|) ÷ 4', '= 24 ÷ 4', '= 6 min'],
  ['w = 0.8 − 0.1 × (−2 × 0.8 × 1.5)', '= 0.8 − 0.1 × (−2.4)', '= 0.8 + 0.24', '= 1.04'],
  ['ETA = 10:20 + 3 × 9.5 + 6', '= 10:20 + 34.5 min', '= 10:54:30'],
  ['y = 2.1 + 0.6 × 4 − 0.3 × 2', '= 2.1 + 2.4 − 0.6', '= 3.9'],
  ['(50.2 + 53.4 + 60.7 + 61.0) ÷ 4', '= 225.3 ÷ 4', '= 56.325'],
  ['e = (22.19 − 12.47) ÷ 12.47', '= 9.72 ÷ 12.47', '= 0.7795'],
  ['P = 41 ÷ 50 × 100', '= 0.82 × 100', '= 82%'],
  ['(155 × 0.05)² ÷ 2', '= 7.75² ÷ 2', '= 60.0625 ÷ 2', '= 30.03125'],
  ['v = 12.6 km ÷ (42 ÷ 60) h', '= 12.6 ÷ 0.7', '= 18 km/h'],
  ['(62.2 − 53.4) ÷ 62.2 × 100', '= 8.8 ÷ 62.2 × 100', '= 14.15%'],
  ['181,388 + 155,296', '= 336,684 checkpoints'],
  ['(81.1 − 61.0) ÷ 81.1', '= 20.1 ÷ 81.1', '= 0.2478'],
  ['RMSE² = (4² + 3² + 0² + 5²) ÷ 4', '= 50 ÷ 4', '= 12.5'],
  ['ETA = 14:05 + 2 × 7.5 + 11', '= 14:05 + 26 min', '= 14:31'],
  ['0.5 × (1 − 0.69) × 3', '= 0.5 × 0.31 × 3', '= 0.465'],
  ['g = −2 × (5 − 4.2) × 0.5', '= −2 × 0.8 × 0.5', '= −0.8'],
  ['(50.4 + 50.2) ÷ 2', '= 100.6 ÷ 2', '= 50.3'],
  ['(71.6 − 60.7) ÷ 71.6', '= 10.9 ÷ 71.6', '= 0.1522'],
  ['3 × 4 × 5 ÷ (3 + 4 + 5)', '= 60 ÷ 12', '= 5'],
  ['x = (−3 + √(9 + 16)) ÷ 2', '= (−3 + 5) ÷ 2', '= 1'],
  ['0.9 × 0.9 × 0.9', '= 0.81 × 0.9', '= 0.729'],
  ['(2 + 3)² − 2 × 3', '= 25 − 6', '= 19'],
  ['800,000 ÷ 125', '= 6,400'],
  ['1.2 ÷ 4.8 × 100', '= 0.25 × 100', '= 25%'],
  ['ŷ = 0.3 × 40 + 0.7 × 52', '= 12 + 36.4', '= 48.4 min'],
  ['|9:40 − 9:52|', '= 12 min'],
];

const wait = (ms: number) => new Promise((done) => setTimeout(done, ms));
const random = (a: number, b: number) => a + Math.random() * (b - a);

export function init() {
  const box = $('.scribbles');
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
      if (!document.hidden) void scribble();
    }
  }

  void loop();
}
