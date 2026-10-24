// Dispatcher view: every city at a recorded moment, with an icon wherever a delivery needs a person.
// The service replays each city's log as it stood at that moment, so nothing shown uses later information.
import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertCard } from './alert-card';
import { alerts as findAlerts, routes, stops, type Alert } from './alerts';
import { CourierCard } from './courier-card';
import { api, courierKey, moment, parcelKey, type City, type Fleet, type Overview, type Parcel } from './api';
import { Defs } from './defs';
import { CityMap } from './map/city-map';
import { Search, type Found } from './search';
import { TimeControl } from './time-control';

const SETTLE_MS = 350; // wait for the slider to settle before asking the service

function useCities() {
  const [cities, setCities] = useState<City[]>([]);
  useEffect(() => {
    void api.cities().then(setCities);
  }, []);
  return cities;
}

// Every city's overview at `at`; each city shows its latest view until the new one arrives.
function useMoment(cities: City[], at: string) {
  const [views, setViews] = useState<Partial<Record<string, Overview>>>({});
  const [failed, setFailed] = useState<Partial<Record<string, string>>>({});

  useEffect(() => {
    let current = true;
    const timer = setTimeout(() => {
      for (const city of cities) {
        api.overview(city.id, at).then(
          (overview) => current && setViews((prev) => ({ ...prev, [city.id]: overview })),
          () => current && setFailed((prev) => ({ ...prev, [city.id]: at })),
        );
      }
    }, SETTLE_MS);
    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [cities, at]);

  const shown = Object.values(views).filter((v): v is Overview => v !== undefined);
  const fleet = useMemo<Fleet>(
    () => ({ couriers: shown.flatMap((v) => v.couriers), parcels: shown.flatMap((v) => v.parcels) }),
    // `views` changes whenever a city's view does.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [views],
  );
  const down = cities.filter((c) => failed[c.id] === at && views[c.id]?.at !== at);
  return {
    fleet,
    loading: cities.some((c) => views[c.id]?.at !== at && failed[c.id] !== at),
    error: down.length
      ? `No data for ${down.map((c) => c.name).join(', ')}. Is the API running? uv run uvicorn server.api.app:create_app --factory`
      : '',
  };
}

// The road path through the given stops, fetched again whenever the stops change.
function useRoad(city: string | null, points: [number, number][] | null) {
  const [road, setRoad] = useState<{ key: string; path: [number, number][] } | null>(null);
  const key =
    city && points && points.length > 1 ? `${city}|${points.map((p) => p.join(',')).join(';')}` : '';
  useEffect(() => {
    if (!city || !points || !key) return;
    let current = true;
    api.route(city, points).then(
      (result) => current && setRoad({ key, path: result.coordinates }),
      () => current && setRoad(null),
    );
    return () => {
      current = false;
    };
    // `key` captures the city and stops; `points` is rebuilt every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return road && road.key === key ? road.path : null;
}

export function Page() {
  const cities = useCities();
  const [date, setDate] = useState('2000-09-20');
  const [time, setTime] = useState('10:30');
  const now = moment(date, time);
  const { fleet, loading, error } = useMoment(cities, now);
  const [dismissed, setDismissed] = useState<ReadonlySet<string>>(new Set());
  const [selectedParcel, setSelectedParcel] = useState<string | null>(null);
  const [selectedCourier, setSelectedCourier] = useState<string | null>(null);
  const [spot, setSpot] = useState<Parcel | null>(null);

  const list = useMemo(() => findAlerts(fleet, dismissed), [fleet, dismissed]);
  // Selections follow the parcel or courier across refreshes and disappear with them.
  const selected = list.find((a) => parcelKey(a.parcel) === selectedParcel) ?? null;
  const courier = fleet.couriers.find((c) => courierKey(c) === selectedCourier) ?? null;
  const byKey = useMemo(() => routes(fleet.parcels), [fleet.parcels]);
  const held = (selectedCourier ? byKey.get(selectedCourier) : undefined) ?? [];
  const select = useCallback((alert: Alert) => {
    setSelectedCourier(null);
    setSelectedParcel(parcelKey(alert.parcel));
  }, []);
  const pickCourier = useCallback((key: string) => {
    setSelectedParcel(null);
    setSpot(null);
    setSelectedCourier(key);
  }, []);
  // A search result: a courier opens their card; a parcel opens its alert, or its courier's card with it marked.
  const find = (found: Found) => {
    if (found.kind === 'courier') {
      pickCourier(found.key);
      return;
    }
    const alert = list.find((a) => parcelKey(a.parcel) === parcelKey(found.parcel));
    if (alert) {
      select(alert);
      return;
    }
    pickCourier(courierKey(found.parcel));
    setSpot(found.parcel);
  };
  const road = useRoad(
    selected?.parcel.city ?? courier?.city ?? null,
    selected
      ? stops(selected.courier, selected.route, selected.parcel.position)
      : courier
        ? stops(courier, held)
        : null,
  );

  return (
    <>
      <Defs />
      <main className="dash">
        <CityMap
          cities={cities}
          fleet={fleet}
          alerts={list}
          selected={selected}
          focus={selected ? courierKey(selected.parcel) : selectedCourier}
          road={road}
          onSelect={select}
          onCourier={pickCourier}
          spot={spot}
        />
        <Search fleet={fleet} cities={cities} onPick={find} />
        <TimeControl date={date} time={time} loading={loading} onDate={setDate} onTime={setTime} />
        {error && (
          <p className="dash-error" role="alert">
            {error}
          </p>
        )}
        {selected && (
          <AlertCard
            now={now}
            alert={selected}
            onClose={() => setSelectedParcel(null)}
            onDismiss={() => {
              setDismissed((prev) => new Set(prev).add(parcelKey(selected.parcel)));
              setSelectedParcel(null);
            }}
          />
        )}
        {courier && (
          <CourierCard
            now={now}
            courier={courier}
            parcels={held}
            onClose={() => {
              setSelectedCourier(null);
              setSpot(null);
            }}
            onParcel={setSpot}
          />
        )}
      </main>
    </>
  );
}
