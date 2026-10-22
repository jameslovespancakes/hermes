// The whole dashboard canvas: a city map with every parcel and courier, and an icon on each alert.
// MapLibre needs a browser, so it is imported when the component mounts (pre-rendering skips it).
import type { MapLayerMouseEvent, Map as MapLibre, Marker } from 'maplibre-gl';
import { useEffect, useRef, useState } from 'react';
import { ISSUES, type Alert } from '../alerts';
import { courierKey, type City, type Fleet } from '../api';
import { iconSvg } from '../icons';
import { CHINA, quietBasemap, STYLE_URL } from './basemap';
import { addLayers, drawOverview } from './layers';

type MapLibreModule = typeof import('maplibre-gl');

interface Props {
  /** Every city on the map; the first view frames them all. */
  cities: City[];
  fleet: Fleet;
  alerts: Alert[];
  selected: Alert | null;
  /** The courier in focus (selected alert's or clicked courier); others fade. */
  focus: string | null;
  /** The focused courier's road path, once loaded. */
  road: [number, number][] | null;
  onSelect: (alert: Alert) => void;
  onCourier: (courierId: string) => void;
}

// The card sits bottom-right, so a focused alert is framed left of centre.
const FOCUS_OFFSET: [number, number] = [-170, -60];

export function CityMap({ cities, fleet, alerts, selected, focus, road, onSelect, onCourier }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<{ map: MapLibre; lib: MapLibreModule } | null>(null);

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
        ...CHINA,
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

  // Frame every city once they are known.
  useEffect(() => {
    if (!map || !cities.length) return;
    const west = Math.min(...cities.map((c) => c.bounds[0][0]));
    const south = Math.min(...cities.map((c) => c.bounds[0][1]));
    const east = Math.max(...cities.map((c) => c.bounds[1][0]));
    const north = Math.max(...cities.map((c) => c.bounds[1][1]));
    map.map.fitBounds(
      [
        [west, south],
        [east, north],
      ],
      { padding: 80, duration: 0 },
    );
  }, [map, cities]);

  // Data layers follow the fleet and the selection.
  useEffect(() => {
    if (map) drawOverview(map.map, fleet, focus, road);
  }, [map, fleet, focus, road]);

  // Clicking a courier opens their card.
  useEffect(() => {
    if (!map) return;
    const click = (event: MapLayerMouseEvent) => {
      const key: unknown = event.features?.[0]?.properties.courier;
      if (typeof key === 'string') onCourier(key);
    };
    const pointer = () => (map.map.getCanvas().style.cursor = 'pointer');
    const plain = () => (map.map.getCanvas().style.cursor = '');
    map.map.on('click', 'couriers', click);
    map.map.on('mouseenter', 'couriers', pointer);
    map.map.on('mouseleave', 'couriers', plain);
    return () => {
      map.map.off('click', 'couriers', click);
      map.map.off('mouseenter', 'couriers', pointer);
      map.map.off('mouseleave', 'couriers', plain);
    };
  }, [map, onCourier]);

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

  // Fly to a newly selected alert or courier.
  const parcelId = selected?.parcel.order_id;
  useEffect(() => {
    if (!map) return;
    const courier = fleet.couriers.find((c) => courierKey(c) === focus);
    const target = selected ? selected.parcel : courier;
    if (!target) return;
    map.map.flyTo({ center: [target.lng, target.lat], zoom: 15.5, offset: FOCUS_OFFSET, duration: 1200 });
    // Only a change of parcel or courier should move the camera, not a refresh of the same one.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, parcelId, focus]);

  return <div className="dash-map" ref={container} aria-label="City map" />;
}
