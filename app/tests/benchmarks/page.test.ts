import { expect, test } from 'bun:test';
import { render } from '../render';

const $ = render('benchmarks');
const values = (selector: string) =>
  $(selector)
    .map((_, n) => $(n).attr('data-value'))
    .get();

test('published and matched scores stay separate', () => {
  expect(values('.paper-row')).toEqual(['23.32', '22.41', '21.36', '17.21']);
  expect(values('.matched-observation')).toEqual(['77.11', '58.64']);
  expect($('#comparison-story').text()).not.toContain('58.64');
});

test('rescores', () => {
  const rows = $('.notes-table tbody tr')
    .map((_, row) => $(row).find('td').text())
    .get();
  expect(rows).toEqual(['12.4722.19', '12.0923.27']);
  expect($('#study-notes').text()).toContain('149,263 matched');
});
