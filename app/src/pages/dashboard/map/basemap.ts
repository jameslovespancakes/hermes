// A quiet, warm basemap: OpenFreeMap's Positron vector style (no API key), recoloured so the data stands out.
import type { Map as MapLibre } from 'maplibre-gl';

export const STYLE_URL = 'https://tiles.openfreemap.org/styles/positron';
export const YANTAI = { center: [121.38, 37.505] as [number, number], zoom: 12 };
export const BOUNDS: [[number, number], [number, number]] = [
  [120.6, 37.0],
  [122.0, 37.8],
];

const paint = (map: MapLibre, id: string, property: string, value: unknown) => {
  try {
    map.setPaintProperty(id, property, value);
  } catch {
    // the property does not apply to this layer type
  }
};

export function quietBasemap(map: MapLibre) {
  for (const layer of map.getStyle().layers) {
    const source = 'source-layer' in layer ? layer['source-layer'] : undefined;
    const { id, type } = layer;
    if (type === 'background') paint(map, id, 'background-color', '#f2f0ea');
    else if (source === 'water') paint(map, id, type === 'fill' ? 'fill-color' : 'line-color', '#d3e3e6');
    else if (source === 'waterway') paint(map, id, 'line-color', '#d3e3e6');
    else if (id === 'park' || id === 'landcover_wood') paint(map, id, 'fill-color', '#e2eadb');
    else if (id === 'landuse_residential') paint(map, id, 'fill-color', '#eeece5');
    else if (source === 'building') paint(map, id, 'fill-color', '#e9e6df');
    else if (source === 'boundary') map.setLayoutProperty(id, 'visibility', 'none');
    else if (type === 'symbol') {
      paint(map, id, 'text-color', '#9a9f9c');
      paint(map, id, 'text-halo-color', '#f2f0ea');
    }
  }
}
