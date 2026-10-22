// Map sources and layers for parcels, couriers and the selected courier's route.
import type {
  ExpressionSpecification,
  GeoJSONSource,
  LayerSpecification,
  Map as MapLibre,
} from 'maplibre-gl';
import { courierKey, type Fleet } from '../api';
import { MAP_IMAGES } from '../icons';

const empty: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };
const zoomed = (...stops: number[]) =>
  ['interpolate', ['linear'], ['zoom'], ...stops] as ExpressionSpecification;
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
    paint: { 'line-color': '#16201e', 'line-width': zoomed(11, 2, 16, 4), 'line-opacity': 0.7 },
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
  source('parcels')?.setData(at(fleet.parcels));
  source('couriers')?.setData(at(fleet.couriers));
  source('route')?.setData(
    focus && road
      ? { type: 'Feature', geometry: { type: 'LineString', coordinates: road }, properties: {} }
      : empty,
  );
}
