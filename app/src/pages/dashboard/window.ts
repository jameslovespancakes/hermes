// The customer-facing arrival window: the ETA widened to where 80% of parcels really arrived, per city and by how
// far away the estimate is. Set on Sep 1-15 (the tuning window) and checked once on Sep 16-30; see BANDS.
import type { Parcel } from './api';
import BANDS from './windows.json';

const EDGES = [30, 60, 180, 1440];
type Band = { before_min: (number | null)[]; after_min: (number | null)[] };

const shift = (at: string, minutes: number) => {
  const d = new Date(`2000-${at.replace(' ', 'T')}Z`);
  return new Date(d.getTime() + minutes * 60_000);
};
const hhmm = (d: Date) => d.toISOString().slice(11, 16);

/** Earliest and latest likely arrival ('HH:MM'), with the day shown when it is not the ETA's day. */
export function arrivalWindow(parcel: Parcel): { from: string; to: string } {
  const band = (BANDS as Record<string, Band>)[parcel.city];
  const i = EDGES.filter((edge) => parcel.minutes_remaining > edge).length;
  const before = Math.min(0, band.before_min[i] ?? 0);
  const after = Math.max(0, band.after_min[i] ?? 0);
  const from = shift(parcel.eta, before);
  const to = shift(parcel.eta, after);
  const day = (d: Date) => d.toISOString().slice(5, 10);
  const label = (d: Date) =>
    day(d) === parcel.eta.slice(0, 5) ? hhmm(d) : `${hhmm(d)} (${d.toUTCString().slice(5, 11)})`;
  return { from: label(from), to: label(to) };
}
