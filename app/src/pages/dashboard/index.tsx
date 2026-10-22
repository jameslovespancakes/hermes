// Dispatcher view: the city at a recorded moment, with an icon wherever a delivery needs a person.
// The service replays the Yantai log as it stood at that moment, so nothing shown uses later information.
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Nav } from '../../nav';
import { AlertCard } from './alert-card';
import { alerts as findAlerts, route, stops, type Alert } from './alerts';
import { CourierCard } from './courier-card';
import { api, moment, type DataHealth, type Overview } from './api';
import { Defs } from './defs';
import { CityMap } from './map/city-map';
import { TimeControl } from './time-control';

const SETTLE_MS = 350; // wait for the slider to settle before asking the service

function useMoment(at: string) {
  const [shown, setShown] = useState<{ at: string; overview: Overview } | null>(null);
  const [health, setHealth] = useState<DataHealth | null>(null);
  const [failedAt, setFailedAt] = useState('');

  useEffect(() => {
    let current = true;
    const timer = setTimeout(() => {
      api.overview(at).then(
        (overview) => current && setShown({ at, overview }),
        () => current && setFailedAt(at),
      );
      api.dataHealth(at).then(
        (report) => current && setHealth(report),
        () => current && setHealth(null),
      );
    }, SETTLE_MS);
    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [at]);

  const failed = failedAt === at && shown?.at !== at;
  return {
    overview: shown?.overview ?? null,
    health,
    loading: shown?.at !== at && !failed,
    error: failed
      ? 'The ETA service is not reachable. Start it with: uv run uvicorn server.api.app:create_app --factory'
      : '',
  };
}

// The road path through the given stops, fetched again whenever the stops change.
function useRoad(points: [number, number][] | null) {
  const [road, setRoad] = useState<{ key: string; path: [number, number][] } | null>(null);
  const key = points && points.length > 1 ? points.map((p) => p.join(',')).join(';') : '';
  useEffect(() => {
    if (!points || !key) return;
    let current = true;
    api.route(points).then(
      (route) => current && setRoad({ key, path: route.coordinates }),
      () => current && setRoad(null),
    );
    return () => {
      current = false;
    };
    // `key` captures the stops; `points` is rebuilt every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return road && road.key === key ? road.path : null;
}

export function Dashboard() {
  const [date, setDate] = useState('2000-09-20');
  const [time, setTime] = useState('10:30');
  const { overview, health, error, loading } = useMoment(moment(date, time));
  const [dismissed, setDismissed] = useState<ReadonlySet<string>>(new Set());
  const [selectedOrder, setSelectedOrder] = useState<number | null>(null);
  const [courierId, setCourierId] = useState<string | null>(null);

  const list = useMemo(() => (overview ? findAlerts(overview, dismissed) : []), [overview, dismissed]);
  // Selections follow the parcel or courier across refreshes and disappear with them.
  const selected = list.find((a) => a.parcel.order_id === selectedOrder) ?? null;
  const courier = overview?.couriers.find((c) => c.courier_id === courierId) ?? null;
  const held = useMemo(
    () => (overview && courierId ? route(overview, courierId) : []),
    [overview, courierId],
  );
  const select = useCallback((alert: Alert) => {
    setCourierId(null);
    setSelectedOrder(alert.parcel.order_id);
  }, []);
  const pickCourier = useCallback((id: string) => {
    setSelectedOrder(null);
    setCourierId(id);
  }, []);
  const road = useRoad(
    selected
      ? stops(selected.courier, selected.route, selected.parcel.position)
      : courier
        ? stops(courier, held)
        : null,
  );

  return (
    <>
      <Defs />
      <Nav page="dashboard" />
      <main className="dash">
        <CityMap
          overview={overview}
          alerts={list}
          selected={selected}
          focus={selected?.parcel.courier_id ?? courier?.courier_id ?? null}
          road={road}
          onSelect={select}
          onCourier={pickCourier}
        />
        <TimeControl
          date={date}
          time={time}
          loading={loading}
          health={health}
          onDate={setDate}
          onTime={setTime}
        />
        {error && (
          <p className="dash-error" role="alert">
            {error}
          </p>
        )}
        {selected && (
          <AlertCard
            alert={selected}
            onClose={() => setSelectedOrder(null)}
            onDismiss={() => {
              setDismissed((prev) => new Set(prev).add(selected.parcel.courier_id));
              setSelectedOrder(null);
            }}
          />
        )}
        {courier && <CourierCard courier={courier} parcels={held} onClose={() => setCourierId(null)} />}
      </main>
    </>
  );
}
