// Map sources and layers for parcels, couriers and the selected courier's route.
import type { GeoJSONSource, LayerSpecification, Map as MapLibre } from 'maplibre-gl';
import type { Alert } from '../alerts';
import type { Overview } from '../api';
import { MAP_IMAGES } from '../icons';

type Point = [number, number];
const empty: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };
const zoomed = (...stops: number[]) => ['interpolate', ['linear'], ['zoom'], ...stops];
const dimmed = (normal: number) => ['case', ['get', 'dim'], 0.25, normal];

function image(svg: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  });
}

export async function addLayers(map: MapLibre) {
  for (const [name, svg] of Object.entries(MAP_IMAGES))
    map.addImage(name, await image(svg), { pixelRatio: 2 });
  for (const id of ['parcels', 'couriers', 'route']) map.addSource(id, { type: 'geojson', data: empty });
  map.addLayer({
    id: 'route',
    type: 'line',
    source: 'route',
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: { 'line-color': '#16201e', 'line-width': 2, 'line-dasharray': [1, 2], 'line-opacity': 0.55 },
  });
  map.addLayer({
    id: 'parcels',
    type: 'symbol',
    source: 'parcels',
    layout: {
      'icon-image': 'parcel',
      'icon-size': zoomed(11, 0.4, 13, 0.55, 15, 0.8, 17, 1.1),
      'icon-allow-overlap': true,
    },
    paint: { 'icon-opacity': dimmed(1) },
  } as LayerSpecification);
  map.addLayer({
    id: 'couriers',
    type: 'symbol',
    source: 'couriers',
    layout: {
      'icon-image': 'courier',
      'icon-size': zoomed(11, 0.7, 14, 0.95, 17, 1.3),
      'icon-allow-overlap': true,
    },
    paint: { 'icon-opacity': dimmed(1) },
  } as LayerSpecification);
}

const points = (items: { lat: number; lng: number; dim: boolean }[]): GeoJSON.FeatureCollection => ({
  type: 'FeatureCollection',
  features: items.map(({ lat, lng, dim }) => ({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [lng, lat] },
    properties: { dim },
  })),
});

/** Draws every parcel and courier; with an alert selected, the rest fade and its route is traced. */
export function drawOverview(map: MapLibre, overview: Overview, selected: Alert | null) {
  const focus = selected?.parcel.courier_id;
  const dim = (courierId: string) => focus !== undefined && courierId !== focus;
  const source = (id: string) => map.getSource<GeoJSONSource>(id);
  source('parcels')?.setData(
    points(overview.parcels.map((p) => ({ lat: p.lat, lng: p.lng, dim: dim(p.courier_id) }))),
  );
  source('couriers')?.setData(
    points(overview.couriers.map((c) => ({ lat: c.lat, lng: c.lng, dim: dim(c.courier_id) }))),
  );
  const path: Point[] = [];
  if (selected) {
    if (selected.courier) path.push([selected.courier.lng, selected.courier.lat]);
    for (const stop of selected.route.filter((p) => p.position <= selected.parcel.position))
      path.push([stop.lng, stop.lat]);
  }
  source('route')?.setData(
    path.length > 1
      ? { type: 'Feature', geometry: { type: 'LineString', coordinates: path }, properties: {} }
      : empty,
  );
}
