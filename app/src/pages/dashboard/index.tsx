// Dispatcher view: the city at a recorded moment, with an icon wherever a delivery needs a person.
// The service replays the Yantai log as it stood at that moment, so nothing shown uses later information.
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Nav } from '../../nav';
import { AlertCard } from './alert-card';
import { alerts as findAlerts, type Alert } from './alerts';
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
    error: failed ? 'The ETA service is not reachable. Start it with uvicorn server.api.app:app.' : '',
  };
}

export function Dashboard() {
  const [date, setDate] = useState('2000-09-20');
  const [time, setTime] = useState('10:30');
  const { overview, health, error, loading } = useMoment(moment(date, time));
  const [dismissed, setDismissed] = useState<ReadonlySet<string>>(new Set());
  const [selectedOrder, setSelectedOrder] = useState<number | null>(null);

  const list = useMemo(() => (overview ? findAlerts(overview, dismissed) : []), [overview, dismissed]);
  // The selection follows the parcel across refreshes and disappears with it.
  const selected = list.find((a) => a.parcel.order_id === selectedOrder) ?? null;
  const select = useCallback((alert: Alert) => setSelectedOrder(alert.parcel.order_id), []);

  return (
    <>
      <Defs />
      <Nav page="dashboard" />
      <main className="dash">
        <CityMap overview={overview} alerts={list} selected={selected} onSelect={select} />
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
      </main>
    </>
  );
}
