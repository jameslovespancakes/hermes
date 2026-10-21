import { expect, test } from 'bun:test';
import { pages, route } from '../src/routes';
import { render } from './render';

test('routes', () => {
  expect(route('/')).toBe('home');
  expect(route('/benchmarks/')).toBe('benchmarks');
  expect(route('/methodology.html')).toBe('methodology');
});

test('every page renders', () => {
  for (const page of Object.keys(pages) as (keyof typeof pages)[]) {
    const $ = render(page);
    expect($('main#main')).toHaveLength(1);
    expect($('a[aria-label="Hermes home"]')).toHaveLength(1);
  }
});
