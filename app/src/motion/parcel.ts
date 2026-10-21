// Folding carton: four hinged flaps open and three sheets rise in an isometric stack.
// The data sheet then unfolds into the dataset figure. Decorative only.
import { $, $$, ease, range } from './util';

type Point = { x: number; y: number };
type Vec = [number, number, number];

const fixed = (values: number[], digits = 5) => values.map((v) => v.toFixed(digits)).join(' ');
const project = ([x, y, z]: Vec): Point => ({
  x: 720 + 127.99158 * x - 98.97857 * z,
  y: 716.28082 + 38.89474 * x - 148.83888 * y + 50.29464 * z,
});
const minus = (a: Point, b: Point): Point => ({ x: a.x - b.x, y: a.y - b.y });

export function create() {
  const assembly = $<SVGGElement>('#parcel-assembly');
  const svg = assembly.ownerSVGElement as SVGSVGElement;
  const guides = $<SVGElement>('#parcel-guides');
  const carton = ['#parcel-ground', '#parcel-back', '#parcel-front', '#parcel-flaps-back', '#parcel-lid'].map(
    (id) => $<SVGElement>(id),
  );

  const layers = (
    [
      ['data', 306.1303, -300],
      ['models', 341.85163, 20],
      ['checks', 377.57296, 340],
    ] as const
  ).map(([name, rest, y]) => ({
    node: $<SVGElement>(`#parcel-sheet-${name}`),
    label: $<SVGElement>(`#parcel-label-${name}`),
    closed: [0.60796, 0.18475, -0.55428, 0.28165, 636.31124, rest],
    open: [0.60796, 0.18475, -0.55428, 0.28165, 636.31124, y],
  }));
  const data = layers[0];
  const ink = [...data.node.children].slice(2) as SVGElement[];

  const flaps = (
    [
      ['left', true, -1, 140],
      ['back', false, -1, 135],
      ['right', true, 1, 140],
      ['front', false, 1, 145],
    ] as const
  ).map(([name, side, sign, degrees]) => {
    const node = $<SVGGElement>(`[data-parcel-flap="${name}"]`);
    const length = side ? 1.12 : 1.32;
    const hinge: [Vec, Vec] = side
      ? [
          [sign * 1.72, 2.04, -1.32],
          [sign * 1.72, 2.04, 1.32],
        ]
      : [
          [-1.72, 2.04, sign * 1.32],
          [1.72, 2.04, sign * 1.32],
        ];
    const free: Vec = [...hinge[0]];
    free[side ? 0 : 2] -= sign * length;
    const source = [...hinge, free].map((p) => project([p[0], 2.15, p[2]]));
    const [a, b, c] = source;
    const points = [a, b, { x: b.x + c.x - a.x, y: b.y + c.y - a.y }, c]
      .map((p) => `${String(p.x)},${String(p.y)}`)
      .join(' ');
    $(`#parcel-clip-${name} polygon`).setAttribute('points', points);
    for (const polygon of $$('polygon', node)) polygon.setAttribute('points', points);
    node.style.visibility = 'visible';
    return {
      node,
      side,
      sign,
      degrees,
      length,
      hinge,
      source,
      outside: $<SVGElement>('.flap-outside', node),
      inside: $<SVGElement>('.flap-inside', node),
    };
  });
  for (const fallback of $$<SVGElement>('.flap-fallback')) fallback.style.display = 'none';

  // Map a flap's flat texture onto its rotated position.
  function fold(flap: (typeof flaps)[number], p: number) {
    const angle =
      ((flap.degrees * Math.PI) / 180) * ease(range(p, flap.side ? 0.1 : 0, flap.side ? 0.62 : 0.48));
    const free: Vec = [...flap.hinge[0]];
    free[1] += flap.length * Math.sin(angle);
    free[flap.side ? 0 : 2] -= flap.sign * flap.length * Math.cos(angle);
    const [a, b, c] = flap.source;
    const [u, v, w] = [...flap.hinge, free].map(project);
    const x = minus(b, a);
    const y = minus(c, a);
    const tx = minus(v, u);
    const ty = minus(w, u);
    const det = x.x * y.y - x.y * y.x;
    const A = (tx.x * y.y - ty.x * x.y) / det;
    const B = (tx.y * y.y - ty.y * x.y) / det;
    const C = (ty.x * x.x - tx.x * y.x) / det;
    const D = (ty.y * x.x - tx.y * y.x) / det;
    flap.node.setAttribute(
      'transform',
      `matrix(${fixed([A, B, C, D, u.x - A * a.x - C * a.y, u.y - B * a.x - D * a.y])})`,
    );
    const outside = Math.cos(angle) * 0.393 + flap.sign * Math.sin(angle) * (flap.side ? 0.562 : 0.727) >= 0;
    flap.outside.style.opacity = outside ? '1' : '0';
    flap.inside.style.opacity = outside ? '0' : '1';
  }

  function draw(p: number) {
    assembly.setAttribute(
      'transform',
      `translate(720 540) scale(${(1.35 - 0.35 * p).toFixed(5)}) translate(-720 -540)`,
    );
    const scale = 1 - 0.32 * p;
    for (const node of carton) {
      node.setAttribute('transform', `matrix(${fixed([scale, 0, 0, scale, 720 * (1 - scale), 436 * p])})`);
      node.style.opacity = '1';
    }
    for (const flap of flaps) fold(flap, p);
    for (const node of ink) node.style.opacity = '1';
    guides.style.opacity = (0.24 * ease(range(p, 0.5, 0.9))).toFixed(5);
    for (const layer of layers) {
      const matrix = layer.closed.map((v, i) => v + (layer.open[i] - v) * p);
      layer.node.setAttribute('transform', `matrix(${fixed(matrix)})`);
      layer.node.style.opacity = ease(range(p, 0.03, 0.22)).toFixed(5);
      layer.label.setAttribute('transform', `translate(1078 ${(matrix[5] + 145).toFixed(3)})`);
      layer.label.style.opacity = ease(range(p, 0.6, 0.9)).toFixed(5);
    }
  }

  // Move the data sheet onto the dataset figure while the carton clears.
  function unfold(t: number, target: Element) {
    const u = ease(t);
    const clear = (1 - ease(range(t, 0, 0.55))).toFixed(5);
    const rect = target.getBoundingClientRect();
    const inverse = (svg.getScreenCTM() as DOMMatrix).inverse();
    const a = new DOMPoint(rect.left, rect.top).matrixTransform(inverse);
    const b = new DOMPoint(rect.right, rect.top).matrixTransform(inverse);
    const c = new DOMPoint(rect.left, rect.bottom).matrixTransform(inverse);
    const to = [(b.x - a.x) / 640, (b.y - a.y) / 640, (c.x - a.x) / 400, (c.y - a.y) / 400, a.x, a.y];
    const matrix = data.open.map((v, i) => v + (to[i] - v) * u);
    matrix[5] -= Math.sin(Math.PI * u) * 80;
    data.node.setAttribute('transform', `matrix(${fixed(matrix)})`);
    data.node.style.opacity = (1 - ease(range(t, 0.72, 1))).toFixed(5);
    for (const node of ink) node.style.opacity = (1 - ease(range(t, 0.3, 0.6))).toFixed(5);
    for (const node of [...carton, layers[1].node, layers[2].node]) node.style.opacity = clear;
    for (const layer of layers) layer.label.style.opacity = (1 - ease(range(t, 0, 0.25))).toFixed(5);
    guides.style.opacity = (0.24 * Number(clear)).toFixed(5);
  }

  return { draw, unfold };
}
