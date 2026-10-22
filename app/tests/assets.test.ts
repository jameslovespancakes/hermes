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
  for (const file of readdirSync('src/styles', { recursive: true }) as string[]) {
    if (!file.endsWith('.css')) continue;
    for (const [, url] of readFileSync(`src/styles/${file}`, 'utf8').matchAll(/url\('(\/assets\/[^']+)'\)/g))
      expect(existsSync(`public${url}`)).toBe(true);
  }
});
