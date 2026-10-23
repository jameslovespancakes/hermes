// Map sources and layers: parcels, couriers, alert icons and the selected courier's route, drawn by the map
// itself (no DOM markers), and only those on screen; parcels and couriers only when zoomed in.
import type {
  ExpressionSpecification,
  GeoJSONSource,
  LayerSpecification,
  Map as MapLibre,
} from 'maplibre-gl';
import { ISSUES, type Alert } from '../alerts';
import { signed } from '../alert-card';
import { courierKey, parcelKey, type Fleet } from '../api';
import { iconSvg, MAP_IMAGES } from '../icons';

const empty: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };
/** Below this zoom the map shows one label per city; at and above it, every parcel, courier and alert. */
export const DETAIL_ZOOM = 8;
const zoomed = (...stops: (number | unknown[])[]) =>
  ['interpolate', ['linear'], ['zoom'], ...stops] as ExpressionSpecification;
const dimmed = (normal: number) => ['case', ['get', 'dim'], 0.25, normal];
/** A size that grows by a quarter for the selected alert. */
const picked = (size: number) => ['case', ['get', 'on'], size * 1.25, size];

function image(svg: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  });
}

export async function addLayers(map: MapLibre) {
  const alertImages = Object.entries(ISSUES).map(([name, issue]) => [
    `issue-${name}`,
    iconSvg(issue.icon, { color: issue.color, size: 68, halo: true, fill: `${issue.color}22` }),
  ]);
  for (const [name, svg] of [...Object.entries(MAP_IMAGES), ...alertImages])
    map.addImage(name, await image(svg), { pixelRatio: 2 });
  for (const id of ['parcels', 'stops', 'couriers', 'route', 'alerts'])
    map.addSource(id, { type: 'geojson', data: empty });
  map.addLayer({
    id: 'route',
    type: 'line',
    source: 'route',
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: { 'line-color': '#16201e', 'line-width': zoomed(11, 2, 16, 4), 'line-opacity': 0.7 },
  });
  map.addLayer({
    id: 'parcels',
    type: 'symbol',
    source: 'parcels',
    layout: {
      'icon-image': 'parcel',
      'icon-size': zoomed(8, 0.25, 11, 0.4, 13, 0.55, 15, 0.8, 17, 1.1),
      'icon-allow-overlap': true,
      'icon-ignore-placement': true,
    },
    minzoom: DETAIL_ZOOM,
    paint: { 'icon-opacity': dimmed(1) },
  } as LayerSpecification);
  map.addLayer({
    id: 'couriers',
    type: 'symbol',
    source: 'couriers',
    layout: {
      'icon-image': 'courier',
      'icon-size': zoomed(8, 0.45, 11, 0.7, 14, 0.95, 17, 1.3),
      'icon-allow-overlap': true,
      'icon-ignore-placement': true,
    },
    minzoom: DETAIL_ZOOM,
    paint: { 'icon-opacity': dimmed(1) },
  } as LayerSpecification);
  // The focused courier's stop order, a small number beside each of their parcels.
  map.addLayer({
    id: 'stops',
    type: 'symbol',
    source: 'stops',
    minzoom: DETAIL_ZOOM,
    layout: {
      'text-field': ['to-string', ['get', 'stop']],
      'text-font': ['Noto Sans Bold'],
      'text-size': 11,
      'text-offset': [0.9, -0.9],
      'text-allow-overlap': true,
      'text-ignore-placement': true,
    },
    paint: { 'text-color': '#ffffeb', 'text-halo-color': '#034f46', 'text-halo-width': 3 },
  });
  // Every alert icon at every zoom; the most urgent (lowest rank) is drawn on top.
  map.addLayer({
    id: 'alerts',
    type: 'symbol',
    source: 'alerts',
    layout: {
      'icon-image': ['concat', 'issue-', ['get', 'issue']],
      'icon-allow-overlap': true,
      'icon-ignore-placement': true,
      'icon-anchor': 'bottom',
      'icon-size': zoomed(8, picked(0.55), 12, picked(0.85), 15, picked(1)),
      'symbol-sort-key': ['get', 'rank'],
    },
  });
}

/** Inside the view, with a margin of half a screen so panning does not show gaps before the next redraw. */
function visible(map: MapLibre, { lng, lat }: { lng: number; lat: number }) {
  const b = map.getBounds();
  const dx = (b.getEast() - b.getWest()) / 2;
  const dy = (b.getNorth() - b.getSouth()) / 2;
  return (
    lng > b.getWest() - dx && lng < b.getEast() + dx && lat > b.getSouth() - dy && lat < b.getNorth() + dy
  );
}

/** The hover text: how far the estimate moved, else what is wrong. */
const tip = ({ parcel }: Alert) =>
  parcel.slip_min !== null && Math.abs(parcel.slip_min) >= 1
    ? signed(parcel.slip_min)
    : ISSUES[parcel.issue].label;

/** Alert icons on screen (the selected one larger). */
export function drawAlerts(map: MapLibre, alerts: Alert[], selected: string | null) {
  map.getSource<GeoJSONSource>('alerts')?.setData({
    type: 'FeatureCollection',
    features: alerts
      .filter(({ parcel }) => visible(map, parcel))
      .map((alert, rank) => {
        const key = parcelKey(alert.parcel);
        return {
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [alert.parcel.lng, alert.parcel.lat] },
          properties: {
            key,
            tip: tip(alert),
            issue: alert.parcel.issue,
            on: key === selected,
            rank: key === selected ? -1 : rank,
          },
        };
      }),
  });
}

const points = (
  items: { lat: number; lng: number; dim: boolean; courier: string }[],
): GeoJSON.FeatureCollection => ({
  type: 'FeatureCollection',
  features: items.map(({ lat, lng, dim, courier }) => ({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [lng, lat] },
    properties: { dim, courier },
  })),
});

/** Draws every parcel and courier; with a courier in focus (key 'city:id'), the rest fade and its road route is traced. */
export function drawOverview(
  map: MapLibre,
  fleet: Fleet,
  focus: string | null,
  road: [number, number][] | null,
) {
  const source = (id: string) => map.getSource<GeoJSONSource>(id);
  const at = (items: { city: string; courier_id: string; lat: number; lng: number }[]) =>
    points(
      items.map((i) => {
        const courier = courierKey(i);
        return { lat: i.lat, lng: i.lng, courier, dim: focus !== null && courier !== focus };
      }),
    );
  source('parcels')?.setData(at(fleet.parcels.filter((p) => visible(map, p))));
  source('stops')?.setData({
    type: 'FeatureCollection',
    features: fleet.parcels
      .filter((p) => focus !== null && courierKey(p) === focus)
      .map((p) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [p.lng, p.lat] },
        properties: { stop: p.position },
      })),
  });
  source('couriers')?.setData(at(fleet.couriers.filter((c) => visible(map, c))));
  source('route')?.setData(
    focus && road
      ? { type: 'Feature', geometry: { type: 'LineString', coordinates: road }, properties: {} }
      : empty,
  );
}
