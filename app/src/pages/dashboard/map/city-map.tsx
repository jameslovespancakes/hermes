// The whole dashboard canvas: a city map with every parcel and courier, and an icon on each alert.
// MapLibre needs a browser, so it is imported when the component mounts (pre-rendering skips it).
import type { Map as MapLibre, Marker } from 'maplibre-gl';
import { useEffect, useRef, useState } from 'react';
import { ISSUES, type Alert } from '../alerts';
import type { Overview } from '../api';
import { iconSvg } from '../icons';
import { BOUNDS, quietBasemap, STYLE_URL, YANTAI } from './basemap';
import { addLayers, drawOverview } from './layers';

type MapLibreModule = typeof import('maplibre-gl');

interface Props {
  overview: Overview | null;
  alerts: Alert[];
  selected: Alert | null;
  /** The selected courier's road path, once loaded. */
  road: [number, number][] | null;
  onSelect: (alert: Alert) => void;
}

// Frame where most parcels are: the 5th-95th percentile box, so a few far-off drops don't zoom the city out.
function core(overview: Overview): [[number, number], [number, number]] {
  const pick = (values: number[], q: number) =>
    values.sort((a, b) => a - b)[Math.floor(q * (values.length - 1))] ?? 0;
  const lng = overview.parcels.map((p) => p.lng);
  const lat = overview.parcels.map((p) => p.lat);
  return [
    [pick(lng, 0.05), pick(lat, 0.05)],
    [pick(lng, 0.95), pick(lat, 0.95)],
  ];
}

// The card sits bottom-right, so a focused alert is framed left of centre.
const FOCUS_OFFSET: [number, number] = [-170, -60];

export function CityMap({ overview, alerts, selected, road, onSelect }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<{ map: MapLibre; lib: MapLibreModule } | null>(null);
  const framed = useRef(false);

  useEffect(() => {
    let instance: MapLibre | undefined;
    let cancelled = false;
    void import('maplibre-gl').then((module) => {
      // The package is UMD; bundlers may expose it as the default export.
      const lib = (module as MapLibreModule & { default?: MapLibreModule }).default ?? module;
      if (cancelled || !container.current) return;
      instance = new lib.Map({
        container: container.current,
        style: STYLE_URL,
        ...YANTAI,
        maxBounds: BOUNDS,
        dragRotate: false,
        pitchWithRotate: false,
      });
      instance.touchZoomRotate.disableRotation();
      const ready = instance;
      ready.on('style.load', () => {
        quietBasemap(ready);
        void addLayers(ready).then(() => {
          if (!cancelled) setMap({ map: ready, lib });
        });
      });
    });
    return () => {
      cancelled = true;
      instance?.remove();
    };
  }, []);

  // Data layers follow the overview and the selection.
  useEffect(() => {
    if (!map || !overview) return;
    drawOverview(map.map, overview, selected, road);
    if (!framed.current && overview.parcels.length) {
      framed.current = true;
      map.map.fitBounds(core(overview), {
        padding: { top: 130, bottom: 90, left: 60, right: 60 },
        duration: 0,
      });
    }
  }, [map, overview, selected, road]);

  // One icon per alert.
  useEffect(() => {
    if (!map) return;
    const markers: Marker[] = alerts.map((alert) => {
      const issue = ISSUES[alert.parcel.issue];
      const element = document.createElement('button');
      element.type = 'button';
      element.className = alert.parcel.order_id === selected?.parcel.order_id ? 'alert-pin on' : 'alert-pin';
      element.title = `${issue.label} · ${alert.parcel.reasons.join(', ')}`;
      element.innerHTML = iconSvg(issue.icon, {
        color: issue.color,
        size: 34,
        halo: true,
        fill: `${issue.color}22`,
      });
      element.addEventListener('click', (event) => {
        event.stopPropagation();
        onSelect(alert);
      });
      const marker = new map.lib.Marker({ element, anchor: 'bottom' })
        .setLngLat([alert.parcel.lng, alert.parcel.lat])
        .addTo(map.map);
      element.setAttribute('aria-label', issue.label); // MapLibre sets a generic label when adding
      return marker;
    });
    return () => {
      for (const marker of markers) marker.remove();
    };
  }, [map, alerts, selected, onSelect]);

  // Fly to a newly selected alert.
  const focus = selected?.parcel.order_id;
  useEffect(() => {
    if (!map || !selected) return;
    map.map.flyTo({
      center: [selected.parcel.lng, selected.parcel.lat],
      zoom: 15.5,
      offset: FOCUS_OFFSET,
      duration: 1200,
    });
    // Only a change of parcel should move the camera, not a refresh of the same alert.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, focus]);

  return <div className="dash-map" ref={container} aria-label="City map" />;
}
