// Illustrative LightGBM training figure: one isometric board and a seven-node tree.
// The notation explains the method; nothing here is a fitted value.
import { $, $$, clamp, ease, range } from './util';

export interface Box {
  left: number;
  top: number;
  width: number;
  height: number;
  radius: number;
}

interface View {
  width: number;
  height: number;
  mobile: boolean;
  handoff: { source: Box | undefined; progress: number; content: number };
}

const stages = [
  {
    title: 'Start with past deliveries.',
    copy: 'Past checkpoints pair delivery signals with time left to deliver.',
    equation: '(<var>x</var><sub>i</sub>, <var>y</var><sub>i</sub>)',
    note: 'Signals x, observed minutes remaining y.',
    graphic:
      'Illustrative checkpoint pairs: input signals x and recorded minutes remaining y. The amber column is the target. Matrix dimensions are schematic.',
  },
  {
    title: 'Describe the work ahead.',
    copy: 'Distance, workload and recent pace become model inputs.',
    equation: '<var>x</var> = [distance, workload, pace, …]',
    note: 'Inputs available at the checkpoint.',
    graphic:
      'A feature vector includes distance, workload and recent pace, using information available at the checkpoint. Bar lengths are illustrative, not measured values or importance.',
  },
  {
    title: 'Learn which splits help.',
    copy: 'LightGBM learns splits that reduce ETA training error.',
    equation: '<var>x</var><sub>j</sub> ≤ <var>τ</var>',
    note: 'A feature and a learned threshold define a split.',
    graphic:
      'A seven-node decision tree on one slim isometric surface. One root, two intermediate nodes and four leaves. The notation compares a feature with a learned threshold; no actual fitted threshold is shown.',
  },
  {
    title: 'Combine small corrections.',
    copy: 'Each tree adds a correction. Together, they refine the ETA.',
    equation:
      '<var>ŷ</var>(<var>x</var>) = <var>b</var> + <var>η</var> ∑<sub>m</sub> <var>T</var><sub>m</sub>(<var>x</var>)',
    note: 'Baseline + learning rate × tree corrections.',
    graphic:
      'One path is highlighted through the illustrative tree. The equation adds learning-rate-weighted tree corrections to a baseline. LightGBM combines many trees, not only the one shown.',
  },
] as const;

const fitted = [0.94, 0.22, -0.55, 0.62, 350, 228];
const projection = `matrix(${fitted.join(' ')})`;
const board = '<rect x="-235" y="-140" width="470" height="280" rx="10"/>';
const n = String;

const columns = ['x₁', 'x₂', 'x₃', '⋯', 'xₖ', 'y']
  .map(
    (label, c) =>
      `<text class="ml-table-label" x="${n(-158 + c * 62)}" y="-108" text-anchor="middle">${label}</text>`,
  )
  .join('');

const records = [0, 1, 2, 3]
  .map((r) => {
    const cells = [0, 1, 2, 3, 4, 5]
      .map((c) => {
        const target = c === 5;
        const opacity = target ? 1 : 0.4 + ((r + c) % 3) * 0.22;
        return `<rect class="${target ? 'ml-target' : ''}" x="${n(-174 + c * 62)}" y="${n(-88 + r * 52)}" width="32" height="9" rx="4.5" opacity="${n(opacity)}"/>`;
      })
      .join('');
    return `<path class="ml-record-rule" d="M-188 ${n(-66 + r * 52)}H188"/>${cells}`;
  })
  .join('');

const signals = [242, 164, 209]
  .map((w, i) => {
    const y = n(-72 + i * 65);
    return `<g class="ml-signal-row"><circle cx="-172" cy="${n(-65 + i * 65)}" r="7"/><rect class="ml-signal-track" x="-135" y="${y}" width="290" height="14" rx="7"/><rect x="-135" y="${y}" width="${n(w)}" height="14" rx="7"/></g>`;
  })
  .join('');

const branches = [
  'M0-88V-55',
  'M0-55C0-28-110-30-110 0M0-55C0-28 110-30 110 0',
  'M-110 0C-110 48-176 44-176 96M-110 0C-110 48-64 44-64 96',
  'M110 0C110 48 64 44 64 96M110 0C110 48 176 44 176 96',
]
  .map((d) => `<path class="ml-branch" pathLength="1" d="${d}"/>`)
  .join('');

const nodes = (
  [
    [0, -88, 0, 11],
    [-110, 0, 1, 8],
    [110, 0, 1, 8],
    [-176, 96, 2, 6],
    [-64, 96, 2, 6],
    [64, 96, 3, 6],
    [176, 96, 3, 6],
  ] as const
)
  .map(
    ([x, y, level, r]) =>
      `<g class="ml-node" data-level="${n(level)}"><circle class="ml-node-depth" cx="${n(x)}" cy="${n(y + 3)}" r="${n(r)}"/><circle class="ml-node-face" cx="${n(x)}" cy="${n(y)}" r="${n(r)}"/></g>`,
  )
  .join('');

const markup = `<div class="training-visual" role="img" aria-label="Illustrative LightGBM training"><div class="training-figure-label" aria-hidden="true">Illustrative schematic</div><div class="training-drawing"><svg class="training-sheet" viewBox="0 35 700 390" fill="none" aria-hidden="true" focusable="false"><defs><linearGradient id="hermes-model-surface" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#f0f2e8"/><stop offset="1" stop-color="#dce4d5"/></linearGradient></defs><ellipse class="ml-board-shadow" cx="350" cy="373" rx="240" ry="14"/><g transform="translate(0 5)"><g class="ml-board-edge" transform="${projection}">${board}</g></g><g class="ml-board" transform="${projection}"><g class="ml-board-face">${board}</g><g class="ml-records">${columns}${records}</g><g class="ml-signals">${signals}</g><g class="ml-tree">${branches}<path class="ml-trace" pathLength="1" d="M0-88V-55C0-28-110-30-110 0C-110 48-64 44-64 96"/>${nodes}<circle class="ml-selected" cx="-64" cy="96" r="15"/></g></g></svg></div><div class="training-notation" aria-hidden="true"><div class="training-equation"></div><div class="training-equation-note"></div></div></div><div class="training-caption"><div class="training-method">LightGBM / Offline training</div><h3></h3><p></p><div class="training-progress" aria-hidden="true"><i></i><i></i><i></i><i></i></div></div>`;

const branchTimes = [
  [0.41, 0.5],
  [0.48, 0.62],
  [0.6, 0.73],
  [0.68, 0.81],
] as const;
const nodeTimes = [
  [0.39, 0.47],
  [0.53, 0.64],
  [0.65, 0.76],
  [0.73, 0.84],
] as const;

function trace(path: SVGElement, p: number) {
  path.style.strokeDasharray = p === 1 ? 'none' : '1';
  path.style.strokeDashoffset = String(1 - p);
}

export function create(parent: HTMLElement) {
  const root = document.createElement('div');
  root.className = 'training-stage';
  root.setAttribute('aria-hidden', 'true');
  root.innerHTML = markup;
  parent.append(root);

  const visual = $('.training-visual', root);
  const caption = $('.training-caption', root);
  const label = $('.training-figure-label', root);
  const notation = $('.training-notation', root);
  const equation = $('.training-equation', root);
  const equationNote = $('.training-equation-note', root);
  const title = $('h3', caption);
  const copy = $('p', caption);
  const markers = $$('.training-progress i', caption);
  const history = $<SVGElement>('.ml-records', root);
  const features = $<SVGElement>('.ml-signals', root);
  const tree = $<SVGElement>('.ml-tree', root);
  const rows = $$<SVGElement>('.ml-signal-row', root);
  const paths = $$<SVGElement>('.ml-branch', root);
  const dots = $$<SVGElement>('.ml-node', root);
  const highlight = $<SVGElement>('.ml-trace', root);
  const selected = $<SVGElement>('.ml-selected', root);
  const sheet = $<SVGSVGElement>('.training-sheet', root);
  const surface = $<SVGElement>('.ml-board', root);
  const edge = $<SVGElement>('.ml-board-edge', root);
  const depth = edge.parentElement as unknown as SVGElement;
  const shadow = $<SVGElement>('.ml-board-shadow', root);
  const rects = [$<SVGElement>('.ml-board-face rect', root), $<SVGElement>('rect', edge)];

  let stage = -1;
  let layoutKey = '';
  let handoffKey = '';
  let source = fitted;
  let radii = [10, 10];

  function layout(width: number, height: number, mobile: boolean) {
    const key = `${n(width)}:${n(height)}:${n(mobile)}:${n(stage)}`;
    if (key === layoutKey) return;
    layoutKey = key;
    const chrome = (w: number) => {
      visual.style.width = `${n(w)}px`;
      return label.offsetHeight + notation.offsetHeight + 28;
    };
    let w, h, left, top;
    if (mobile) {
      caption.style.width = `${n(Math.min(width - 12, 540))}px`;
      caption.style.left = `${n(width / 2)}px`;
      const text = caption.offsetHeight;
      w = Math.min(width * 0.98, 760);
      const extra = chrome(w);
      h = Math.max(extra + 72, Math.min(w * 0.59 + extra, height - text - 46));
      const start = Math.max(12, (height - text - 18 - h) / 2);
      caption.style.top = `${n(start)}px`;
      left = (width - w) / 2;
      top = start + text + 18;
    } else {
      const text = Math.min(320, Math.max(244, width * 0.28));
      w = Math.min(760, width - text - 36);
      const extra = chrome(w);
      h = Math.min(Math.max(extra + 80, height - 48), w * 0.59 + extra);
      const start = (width - text - 36 - w) / 2;
      caption.style.width = `${n(text)}px`;
      caption.style.left = `${n(start)}px`;
      caption.style.top = `${n(Math.max(18, (height - caption.offsetHeight) / 2))}px`;
      left = start + text + 36;
      top = (height - h) / 2;
    }
    visual.style.height = `${n(h)}px`;
    visual.style.left = `${n(left)}px`;
    visual.style.top = `${n(top)}px`;
  }

  // Morph the board from the training strip of the data figure.
  function morph({ source: box, progress: amount }: View['handoff']) {
    let matrix = fitted;
    let rx = 10;
    let ry = 10;
    if (box && amount < 1) {
      const key = `${layoutKey}:${n(box.left)}:${n(box.top)}:${n(box.width)}:${n(box.height)}`;
      const screen = sheet.getScreenCTM();
      if (!screen) return;
      if (key !== handoffKey) {
        const inverse = screen.inverse();
        const bounds = parent.getBoundingClientRect();
        const point = (x: number, y: number) =>
          new DOMPoint(bounds.left + x, bounds.top + y).matrixTransform(inverse);
        const tl = point(box.left, box.top);
        const tr = point(box.left + box.width, box.top);
        const bl = point(box.left, box.top + box.height);
        const center = point(box.left + box.width / 2, box.top + box.height / 2);
        source = [
          (tr.x - tl.x) / 470,
          (tr.y - tl.y) / 470,
          (bl.x - tl.x) / 280,
          (bl.y - tl.y) / 280,
          center.x,
          center.y,
        ];
        radii = [box.radius / Math.abs(screen.a * source[0]), box.radius / Math.abs(screen.d * source[3])];
        handoffKey = key;
      }
      matrix = source.map((v, i) => v + (fitted[i] - v) * amount);
      rx = radii[0] + (10 - radii[0]) * amount;
      ry = radii[1] + (10 - radii[1]) * amount;
    }
    const transform = `matrix(${matrix.map((v) => v.toFixed(6)).join(' ')})`;
    surface.setAttribute('transform', transform);
    edge.setAttribute('transform', transform);
    depth.setAttribute('transform', `translate(0 ${n(5 * amount)})`);
    for (const rect of rects) {
      rect.setAttribute('rx', n(rx));
      rect.setAttribute('ry', n(ry));
    }
    shadow.style.opacity = n(0.055 * ease(range(amount, 0.65, 1)));
  }

  function paint(progress: number, visibility: number, view: View) {
    root.style.opacity = n(visibility);
    root.style.visibility = visibility > 0 ? 'visible' : 'hidden';
    root.setAttribute('aria-hidden', n(visibility < 0.5));
    if (visibility <= 0) return;
    const t = clamp(progress);
    const next = t < 0.22 ? 0 : t < 0.4 ? 1 : t < 0.82 ? 2 : 3;
    if (next !== stage) {
      stage = next;
      const s = stages[next];
      title.textContent = s.title;
      copy.textContent = s.copy;
      equation.innerHTML = s.equation;
      equationNote.textContent = s.note;
      visual.setAttribute('aria-label', s.graphic);
      markers.forEach((marker, i) => {
        marker.classList.toggle('complete', i < next);
        marker.classList.toggle('current', i === next);
      });
    }
    layout(view.width, view.height, view.mobile);
    morph(view.handoff);
    const content = view.handoff.content;
    root.style.setProperty('--figure-detail-opacity', n(content));
    caption.style.opacity = n(content);
    history.style.opacity = n((1 - range(t, 0.18, 0.29)) * content);
    features.style.opacity = n(range(t, 0.18, 0.29) * (1 - range(t, 0.36, 0.44)) * content);
    rows.forEach((row, i) => {
      const reveal = ease(range(t, 0.18 + i * 0.025, 0.28 + i * 0.025));
      row.style.transform = `translateX(${n((1 - reveal) * 16)}px)`;
      row.style.opacity = n(reveal);
    });
    tree.style.opacity = n(range(t, 0.36, 0.44) * content);
    paths.forEach((path, i) => {
      const [a, b] = branchTimes[i];
      trace(path, ease(range(t, a, b)));
    });
    for (const dot of dots) {
      const [a, b] = nodeTimes[Number(dot.dataset.level)];
      dot.style.opacity = n(ease(range(t, a, b)));
    }
    highlight.style.opacity = n(range(t, 0.82, 0.85));
    trace(highlight, ease(range(t, 0.82, 0.97)));
    selected.style.opacity = n(range(t, 0.95, 1));
  }

  return {
    paint,
    invalidate() {
      layoutKey = handoffKey = '';
    },
  };
}
