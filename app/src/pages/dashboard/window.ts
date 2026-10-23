// The customer-facing arrival window: the ETA widened to where 80% of parcels really arrived, per city and by how
// far away the estimate is. Set on Sep 1-15 (the tuning window) and checked once on Sep 16-30 (windows.json).
import type { Parcel } from './api';
import BANDS from './windows.json';

const EDGES = [30, 60, 180, 1440];
type Band = { before_min: (number | null)[]; after_min: (number | null)[] };

const shift = (at: string, minutes: number) => {
  const d = new Date(`2000-${at.replace(' ', 'T')}Z`);
  return new Date(d.getTime() + minutes * 60_000);
};
const hhmm = (d: Date) => d.toISOString().slice(11, 16);

/** Earliest and latest likely arrival ('HH:MM') and how many days after the ETA's day each falls. */
export function arrivalWindow(parcel: Parcel) {
  const band = (BANDS as Record<string, Band>)[parcel.city];
  const i = EDGES.filter((edge) => parcel.minutes_remaining > edge).length;
  const day = Date.parse(`2000-${parcel.eta.slice(0, 5)}T00:00Z`);
  const at = (minutes: number) => {
    const d = shift(parcel.eta, minutes);
    return { time: hhmm(d), days: Math.floor((d.getTime() - day) / 86_400_000) };
  };
  return { from: at(Math.min(0, band.before_min[i] ?? 0)), to: at(Math.max(0, band.after_min[i] ?? 0)) };
}
