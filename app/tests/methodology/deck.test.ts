import { expect, test } from 'bun:test';
import { headingOpacity, shown, state } from '../../src/motion/deck';

test('each settled step is fully shown alone', () => {
  for (let i = 0; i < 4; i++) {
    const p = (i + 0.25) / 4;
    expect(state(p, 4).active).toBe(i);
    for (let j = 0; j < 4; j++) expect(shown(j, p, 4)).toBe(i === j ? 1 : 0);
  }
});

test('crossfade sums to one', () => {
  const p = 0.84 / 4;
  expect(shown(0, p, 4) + shown(1, p, 4)).toBeCloseTo(1);
});

test('a stepped heading leaves before the next heading arrives', () => {
  for (let i = 0; i <= 100; i++) {
    const t = i / 100;
    if (t >= 0.46) expect(headingOpacity(3, t, 3)).toBe(0);
    if (t <= 0.54) expect(headingOpacity(2, t, 3)).toBe(0);
  }
});
