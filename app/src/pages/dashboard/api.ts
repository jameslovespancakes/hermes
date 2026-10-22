// Typed client for the ETA API (server/api/app.py, under /api). Times use the source format 'MM-DD HH:MM:SS'.

/** Data problems the safeguards caught (most urgent first). */
export type DataIssue = 'lagging' | 'silent' | 'bulk' | 'moved' | 'resent';
/** Why a parcel needs a person: a data problem, inputs that look wrong, or an ETA that slipped. */
export type Issue = DataIssue | 'suspect' | 'late';

export interface Parcel {
  city: string;
  order_id: number;
  courier_id: string;
  lat: number;
  lng: number;
  /** Predicted stop number on the courier's route (1 = next). */
  position: number;
  accepted_at: string;
  eta: string;
  minutes_remaining: number;
  /** The ETA the model gave an hour earlier, if the courier held the parcel then. */
  baseline_eta: string | null;
  /** Minutes the ETA moved since then (positive = later). */
  slip_min: number | null;
  issue: Issue | null;
  reasons: string[];
}

export interface Courier {
  city: string;
  courier_id: string;
  lat: number;
  lng: number;
  packages_held: number;
  feed_age_min: number;
  model_used: string;
}

export interface Overview {
  city: string;
  at: string;
  baseline_at: string;
  couriers: Courier[];
  parcels: Parcel[];
}

/** Every city's couriers and parcels together. */
export type Fleet = Pick<Overview, 'couriers' | 'parcels'>;

/** Ids repeat between cities, so couriers and parcels are keyed by city too. */
export const courierKey = (x: { city: string; courier_id: string }) => `${x.city}:${x.courier_id}`;
export const parcelKey = (p: { city: string; order_id: number }) => `${p.city}:${String(p.order_id)}`;

/** City-wide input check: 'watch' or 'act' means today's data passed the contract but looks unlike training. */
export interface DataHealth {
  at: string;
  status: 'ok' | 'watch' | 'act';
}

/** A city with a trained model; bounds are the south-west and north-east (lng, lat) corners. */
export interface City {
  id: string;
  name: string;
  bounds: [[number, number], [number, number]];
}

/** A road path through stops, as (lng, lat) pairs. */
export interface Route {
  coordinates: [number, number][];
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) throw new Error(`${path}: ${String(response.status)}`);
  return (await response.json()) as T;
}

const query = (city: string, at: string) => `?city=${city}&at=${encodeURIComponent(at)}`;

export const api = {
  cities: () => json<City[]>('/api/cities'),
  overview: (city: string, at: string) => json<Overview>(`/api/overview${query(city, at)}`),
  dataHealth: (city: string, at: string) => json<DataHealth>(`/api/data-health${query(city, at)}`),
  route: (city: string, points: [number, number][]) =>
    json<Route>('/api/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ city, points }),
    }),
};

// Inputs give '2000-09-20' and '10:30'; the API wants '09-20 10:30:00'.
export const moment = (date: string, time: string) => `${date.slice(5)} ${time}:00`;

// '09-20 10:42:00' -> '10:42'
export const clock = (at: string) => at.slice(6, 11);
