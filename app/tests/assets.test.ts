import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { expect, test } from 'bun:test';
import { pages, type Page } from '../src/routes';
import { render } from './render';

test('page assets exist', () => {
  for (const page of Object.keys(pages) as Page[]) {
    const $ = render(page);
    $('[href^="/assets/"], [src^="/assets/"]').each((_, n) => {
      expect(existsSync(`public${String($(n).attr('href') ?? $(n).attr('src'))}`)).toBe(true);
    });
  }
});

test('css assets exist', () => {
  for (const file of readdirSync('src/styles')) {
    for (const [, url] of readFileSync(`src/styles/${file}`, 'utf8').matchAll(/url\('(\/assets\/[^']+)'\)/g))
      expect(existsSync(`public${url}`)).toBe(true);
  }
});

test('downloads match saved evidence', () => {
  expect(readFileSync('public/assets/current-model-metrics.json', 'utf8')).toBe(
    readFileSync('../evidence/model/results/metrics.json', 'utf8'),
  );
  expect(readFileSync('public/assets/current-data-quality.json', 'utf8')).toBe(
    readFileSync('../evidence/baddata/results/results.json', 'utf8'),
  );
});
