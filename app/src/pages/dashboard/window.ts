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

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const dayOf = (mmdd: string) => Date.parse(`2000-${mmdd}T00:00Z`);

/** 'MM-DD HH:MM:SS' as 'HH:MM', with its date ('Sep 19') in front when it is not `today` ('MM-DD'). */
export function when(at: string, today: string) {
  const d = new Date(`2000-${at.replace(' ', 'T')}Z`);
  return at.slice(0, 5) === today
    ? hhmm(d)
    : `${MONTHS[d.getUTCMonth()]} ${String(d.getUTCDate())} ${hhmm(d)}`;
}

/** Earliest and latest likely arrival ('HH:MM', never before `now`, 'MM-DD HH:MM:SS'), each with its date ('Sep 22') and days ahead when not today. */
export function arrivalWindow(parcel: Parcel, now: string) {
  const today = now.slice(0, 5);
  const band = (BANDS as Record<string, Band>)[parcel.city];
  const i = EDGES.filter((edge) => parcel.minutes_remaining > edge).length;
  const day = dayOf(today);
  const earliest = new Date(`2000-${now.replace(' ', 'T')}Z`);
  const at = (minutes: number) => {
    const shifted = shift(parcel.eta, minutes);
    const d = shifted < earliest ? earliest : shifted;
    const days = Math.floor((d.getTime() - day) / 86_400_000);
    return {
      time: hhmm(d),
      days,
      date: days !== 0 ? `${MONTHS[d.getUTCMonth()]} ${String(d.getUTCDate())}` : '',
    };
  };
  return { from: at(Math.min(0, band.before_min[i] ?? 0)), to: at(Math.max(0, band.after_min[i] ?? 0)) };
}
