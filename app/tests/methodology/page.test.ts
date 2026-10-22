import { expect, test } from 'bun:test';
import { render } from '../render';

const $ = render('methodology');

test('hygiene steps: a number over a faint chart', () => {
  expect($('#data-safeguards .step')).toHaveLength(7);
  expect(
    $('#data-safeguards .step-number')
      .map((_, n) => $(n).text())
      .get(),
  ).toEqual(['4', '3', '88/92', '100%', '7', '60.0', '47/47']);
  expect($('#data-safeguards .step .spec')).toHaveLength(3);
  expect(
    $('#model-stack .step-number')
      .map((_, n) => $(n).text())
      .get(),
  ).toEqual(['3,000', '69.2%', '9', '94']);
  expect($('#hygiene-monitor-art')).toHaveLength(1);
  expect($('#guard-heading').text()).toBe('Cleaninputs.');
});

test('parcel sheets keep their isometric matrix', () => {
  $('.parcel-sheet').each((_, n) => {
    expect($(n).attr('transform')).toStartWith('matrix(.60796 .18475 -.55428 .28165 636.31124 ');
  });
});

test('results compare the bad-data test before and after the controls', () => {
  expect(
    $('#results .step-number')
      .map((_, n) => $(n).text())
      .get(),
  ).toEqual(['58.5', '60.0', '66.7', '66.9']);
});
