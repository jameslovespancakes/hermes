// The whole dashboard canvas: every city's parcels and couriers, and an icon on each alert (all drawn by the map).
// MapLibre needs a browser, so it is imported when the component mounts (pre-rendering skips it).
import type { MapLayerMouseEvent, Map as MapLibre, Popup } from 'maplibre-gl';
import { useEffect, useRef, useState } from 'react';
import type { Alert } from '../alerts';
import { courierKey, parcelKey, type City, type Fleet } from '../api';
import { CHINA, quietBasemap, STYLE_URL } from './basemap';
import { addLayers, drawAlerts, drawOverview } from './layers';

type MapLibreModule = typeof import('maplibre-gl');

const MARGIN = 10; // degrees of map kept around the cities (room to see them all at once)

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

  // Frame every city once they are known, and keep the map within reach of them.
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
      { padding: { top: 140, bottom: 110, left: 80, right: 80 }, duration: 0 },
    );
    map.map.setMaxBounds([
      [west - MARGIN, south - MARGIN],
      [east + MARGIN, north + MARGIN],
    ]);
  }, [map, cities]);

  // Data layers follow the fleet and the selection.
  // Redrawn when the map stops moving, so only what is on screen is drawn.
  const [view, setView] = useState(0);
  useEffect(() => {
    if (!map) return;
    const moved = () => setView((n) => n + 1);
    map.map.on('moveend', moved);
    return () => {
      map.map.off('moveend', moved);
    };
  }, [map]);

  useEffect(() => {
    if (map) drawOverview(map.map, fleet, focus, road);
  }, [map, fleet, focus, road, view]);

  // Alert icons on screen.
  const selectedKey = selected ? parcelKey(selected.parcel) : null;
  useEffect(() => {
    if (map) drawAlerts(map.map, alerts, selectedKey);
  }, [map, alerts, selectedKey, view]);

  // Clicks: a courier opens their card, an alert its card.
  useEffect(() => {
    if (!map) return;
    const property = (event: MapLayerMouseEvent, name: string) => {
      const value: unknown = event.features?.[0]?.properties[name];
      return typeof value === 'string' ? value : null;
    };
    const handlers = {
      couriers: (event: MapLayerMouseEvent) => {
        const key = property(event, 'courier');
        if (key) onCourier(key);
      },
      alerts: (event: MapLayerMouseEvent) => {
        const key = property(event, 'key');
        const alert = alerts.find((a) => parcelKey(a.parcel) === key);
        if (alert) onSelect(alert);
      },
    };
    const pointer = () => (map.map.getCanvas().style.cursor = 'pointer');
    const plain = () => (map.map.getCanvas().style.cursor = '');
    for (const [layer, handler] of Object.entries(handlers)) {
      map.map.on('click', layer, handler);
      map.map.on('mouseenter', layer, pointer);
      map.map.on('mouseleave', layer, plain);
    }
    return () => {
      for (const [layer, handler] of Object.entries(handlers)) {
        map.map.off('click', layer, handler);
        map.map.off('mouseenter', layer, pointer);
        map.map.off('mouseleave', layer, plain);
      }
    };
  }, [map, alerts, onCourier, onSelect]);

  // Hovering an alert shows a small tooltip: how far its estimate moved, or what is wrong.
  useEffect(() => {
    if (!map) return;
    let tip: Popup | null = null;
    const show = (event: MapLayerMouseEvent) => {
      const feature = event.features?.[0];
      const text: unknown = feature?.properties.tip;
      if (!feature || typeof text !== 'string' || feature.geometry.type !== 'Point') return;
      tip?.remove();
      tip = new map.lib.Popup({ closeButton: false, closeOnClick: false, offset: 38, className: 'map-tip' })
        .setLngLat(feature.geometry.coordinates as [number, number])
        .setText(text)
        .addTo(map.map);
    };
    const hide = () => {
      tip?.remove();
      tip = null;
    };
    map.map.on('mouseenter', 'alerts', show);
    map.map.on('mouseleave', 'alerts', hide);
    return () => {
      hide();
      map.map.off('mouseenter', 'alerts', show);
      map.map.off('mouseleave', 'alerts', hide);
    };
  }, [map]);

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
