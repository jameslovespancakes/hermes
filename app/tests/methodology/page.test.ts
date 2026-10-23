import { expect, test } from 'bun:test';
import { render } from '../render';

const $ = render('methodology');

test('hygiene steps: a number over a faint chart', () => {
  expect($('#data-safeguards .step')).toHaveLength(8);
  expect(
    $('#data-safeguards .step-number')
      .map((_, n) => $(n).text())
      .get(),
  ).toEqual(['175/184', '100%', '0.11', '20 → 2.6', '54.0', '50%', '94/94', '51.0']);
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
  ).toEqual(['51.0', '54.0', '61.1', '61.3', '66.2', '56.5', '64.4']);
});
