// Typed client for the ETA API (server/api/app.py, under /api). Times use the source format 'MM-DD HH:MM:SS'.

/** Why a parcel needs a person: guards flagged its data, it passed them but looks wrong, or its ETA slipped. */
export type Issue = 'data' | 'suspect' | 'late';

export interface Parcel {
  order_id: number;
  courier_id: string;
  lat: number;
  lng: number;
  /** Predicted stop number on the courier's route (1 = next). */
  position: number;
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

/** City-wide input check: 'watch' or 'act' means today's data passed the contract but looks unlike training. */
export interface DataHealth {
  at: string;
  status: 'ok' | 'watch' | 'act';
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

const query = (at: string) => `?at=${encodeURIComponent(at)}`;

export const api = {
  overview: (at: string) => json<Overview>(`/api/overview${query(at)}`),
  dataHealth: (at: string) => json<DataHealth>(`/api/data-health${query(at)}`),
  route: (points: [number, number][]) =>
    json<Route>('/api/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ points }),
    }),
};

// Inputs give '2000-09-20' and '10:30'; the API wants '09-20 10:30:00'.
export const moment = (date: string, time: string) => `${date.slice(5)} ${time}:00`;

// '09-20 10:42:00' -> '10:42'
export const clock = (at: string) => at.slice(6, 11);
