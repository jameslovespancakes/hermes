import { expect, test } from 'bun:test';
import { render } from '../render';

const $ = render('benchmarks');
const values = (selector: string) =>
  $(selector)
    .map((_, n) => $(n).attr('data-value'))
    .get();

test('published and matched scores stay separate', () => {
  expect(values('.paper-row')).toEqual(['21.59', '21.25', '20.16', '14.47']);
  expect(values('.matched-observation')).toEqual(['77.11', '58.64']);
  expect($('#comparison-story').text()).not.toContain('58.64');
});

test('rescoring and the closing card', () => {
  expect($('#parcel-scoring').text()).toContain('12.47 to 22.19');
  expect($('.b-voice video').attr('src')).toBe('/assets/video/accuracy.mp4');
  expect($('.scribbles').length).toBe(1);
  expect($('.b-hero .eyebrow').length).toBe(0);
  expect($('.float').length).toBe(0);
});
