import { expect, test } from 'bun:test';
import { render } from '../render';

const $ = render('home');

test('content', () => {
  expect($('h1').text()).toBe('Predict the route.Update the ETA.');
  expect(
    $('.split-group')
      .map((_, n) => $(n).attr('data-count'))
      .get(),
  ).toEqual(['800000', '181388', '155296']);
  expect($('.quality-card')).toHaveLength(6);
  expect($('.wall-card')).toHaveLength(6);
});

test('navigation', () => {
  expect($('input[value=deliver]').is('[checked]')).toBe(true);
  expect($('a[aria-current=page]').attr('href')).toBe('/');
});

test('svg references resolve', () => {
  $('use[href^="#"]').each((_, n) => {
    expect($(String($(n).attr('href')))).toHaveLength(1);
  });
});
