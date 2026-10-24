// The customer-facing arrival window: the ETA widened to where 80% of parcels really arrived, per city and by how
// far away the estimate is. Set on Sep 1-15 (the tuning window) and checked once on Sep 16-30 (windows.json).
import type { Parcel } from './api';
import { MONTHS } from './calendar';
import BANDS from './windows.json';

const EDGES = [30, 60, 180, 1440];
type Band = { before_min: (number | null)[]; after_min: (number | null)[] };

const parse = (at: string) => new Date(`2000-${at.replace(' ', 'T')}Z`);
const hhmm = (d: Date) => d.toISOString().slice(11, 16);

/** Earliest and latest likely arrival ('HH:MM', never before `now`, 'MM-DD HH:MM:SS'), each with its date ('Sep 22') and days ahead when not today. */
export function arrivalWindow(parcel: Parcel, now: string) {
  const band = (BANDS as Record<string, Band>)[parcel.city];
  const i = EDGES.filter((edge) => parcel.minutes_remaining > edge).length;
  const day = parse(`${now.slice(0, 5)} 00:00:00`).getTime();
  const earliest = parse(now);
  const eta = parse(parcel.eta).getTime();
  const at = (minutes: number) => {
    const shifted = new Date(eta + minutes * 60_000);
    const d = shifted < earliest ? earliest : shifted;
    const days = Math.floor((d.getTime() - day) / 86_400_000);
    return {
      time: hhmm(d),
      days,
      date: days > 0 ? `${MONTHS[d.getUTCMonth()]} ${String(d.getUTCDate())}` : '',
    };
  };
  return { from: at(Math.min(0, band.before_min[i] ?? 0)), to: at(Math.max(0, band.after_min[i] ?? 0)) };
}
