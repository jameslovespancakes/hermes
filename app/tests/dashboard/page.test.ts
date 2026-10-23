import { expect, test } from 'bun:test';
import { alerts, route, stops } from '../../src/pages/dashboard/alerts';
import { clock, moment, type Overview, type Parcel } from '../../src/pages/dashboard/api';
import { iconSvg } from '../../src/pages/dashboard/icons';
import { PackageIcon } from '@hugeicons/core-free-icons';
import { render } from '../render';

const $ = render('dashboard');

test('moments use the service format', () => {
  expect(moment('2000-09-20', '10:30')).toBe('09-20 10:30:00');
  expect(clock('09-20 10:42:00')).toBe('10:42');
});

test('dashboard shell is the map and one time control', () => {
  expect($('.dash-map')).toHaveLength(1);
  expect($('.calendar-toggle').text()).toBe('Sep 20');
  expect($('.time-control a.home').attr('href')).toBe('/');
  expect($('.navbar')).toHaveLength(0);
  expect($('input[type=range]').attr('value')).toBe(String(10 * 60 + 30));
  expect($('.alert-card')).toHaveLength(0);
});

const parcel = (over: Partial<Parcel>): Parcel => ({
  city: 'yt',
  order_id: 1,
  courier_id: 'a',
  lat: 37.5,
  lng: 121.4,
  position: 1,
  accepted_at: '09-20 08:10:00',
  eta: '09-20 11:00:00',
  minutes_remaining: 30,
  baseline_eta: '09-20 10:55:00',
  slip_min: 5,
  issue: null,
  reasons: [],
  ...over,
});

const overview = (parcels: Parcel[]): Overview => ({
  city: 'yt',
  at: '09-20 10:30:00',
  baseline_at: '09-20 09:30:00',
  couriers: [
    {
      city: 'yt',
      courier_id: 'a',
      lat: 37.5,
      lng: 121.4,
      packages_held: 3,
      feed_age_min: 2,
      model_used: 'standard',
    },
  ],
  parcels,
});

test('one alert per courier: guard flags first, then the biggest slip', () => {
  const view = overview([
    parcel({ order_id: 1, issue: 'late', slip_min: 120, position: 2 }),
    parcel({ order_id: 2, issue: 'silent', slip_min: 10, position: 3 }),
    parcel({ order_id: 3, position: 1 }),
    parcel({ order_id: 4, courier_id: 'b', issue: 'late', slip_min: 95 }),
    parcel({ order_id: 5, courier_id: 'b', issue: 'late', slip_min: 140 }),
  ]);
  const list = alerts(view);
  expect(list.map((a) => a.parcel.order_id)).toEqual([2, 5]);
  expect(list[0]?.route.map((p) => p.order_id)).toEqual([3, 1, 2]);
  expect(list[0]?.courier?.packages_held).toBe(3);
  expect(alerts(view, new Set(['yt:a'])).map((a) => a.parcel.order_id)).toEqual([5]);
  expect(route(view, 'yt:b')).toHaveLength(2);
});

test('stops start at the courier and stop at the flagged parcel', () => {
  const view = overview([
    parcel({ order_id: 1, position: 1 }),
    parcel({ order_id: 2, position: 2, lng: 121.5 }),
  ]);
  const courier = view.couriers[0];
  expect(stops(courier, route(view, 'yt:a'))).toHaveLength(3);
  expect(stops(courier, route(view, 'yt:a'), 1)).toEqual([
    [121.4, 37.5],
    [121.4, 37.5],
  ]);
});

test('icons render as standalone SVG', () => {
  const svg = iconSvg(PackageIcon, { color: '#123456', size: 40, halo: true });
  expect(svg).toStartWith('<svg xmlns="http://www.w3.org/2000/svg"');
  expect(svg).toContain('color="#123456"');
  expect(svg).toContain('stroke-linecap="round"');
  expect(svg).not.toContain('strokeLinecap');
});
