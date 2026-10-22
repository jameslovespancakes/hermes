// Turns the city overview into the few things a dispatcher should look at: one alert per courier at most.
import {
  AlarmClockIcon,
  Copy01Icon,
  HelpCircleIcon,
  Layers01Icon,
  LocationOffline01Icon,
  Upload04Icon,
  WifiDisconnected01Icon,
} from '@hugeicons/core-free-icons';
import type { IconSvgElement } from '@hugeicons/react';
import type { Courier, Issue, Overview, Parcel } from './api';

const DATA = '#e58f0b';

export const ISSUES: Record<Issue, { color: string; label: string; icon: IconSvgElement }> = {
  lagging: { color: DATA, label: 'Uploads lagging', icon: Upload04Icon },
  silent: { color: DATA, label: 'Courier silent', icon: WifiDisconnected01Icon },
  bulk: { color: DATA, label: 'Bulk-synced scans', icon: Layers01Icon },
  moved: { color: DATA, label: 'Address repaired', icon: LocationOffline01Icon },
  resent: { color: DATA, label: 'Duplicate removed', icon: Copy01Icon },
  suspect: { color: '#7c5cff', label: 'May be wrong', icon: HelpCircleIcon },
  late: { color: '#e5484d', label: 'Running late', icon: AlarmClockIcon },
};

// Same order as the server: data problems first, then implausible inputs, then plain slips.
const RANK: Record<Issue, number> = {
  lagging: 0,
  silent: 0,
  bulk: 0,
  moved: 0,
  resent: 0,
  suspect: 1,
  late: 2,
};

export interface Alert {
  parcel: Parcel & { issue: Issue };
  courier: Courier | undefined;
  /** The courier's pending parcels in predicted stop order. */
  route: Parcel[];
}

const flagged = (p: Parcel): p is Parcel & { issue: Issue } => p.issue !== null;

/** The worst flagged parcel of each courier, worst couriers first; dismissed couriers are skipped. */
export function alerts(overview: Overview, dismissed: ReadonlySet<string> = new Set()): Alert[] {
  const worst = new Map<string, Parcel & { issue: Issue }>();
  for (const parcel of overview.parcels.filter(flagged)) {
    if (dismissed.has(parcel.courier_id)) continue;
    const current = worst.get(parcel.courier_id);
    if (!current || severity(parcel) < severity(current)) worst.set(parcel.courier_id, parcel);
  }
  const couriers = new Map(overview.couriers.map((c) => [c.courier_id, c]));
  return [...worst.values()]
    .sort((a, b) => severity(a) - severity(b))
    .map((parcel) => ({
      parcel,
      courier: couriers.get(parcel.courier_id),
      route: route(overview, parcel.courier_id),
    }));
}

/** A courier's position, then each stop in order up to `until`, as (lng, lat). */
export function stops(courier: Courier | undefined, parcels: Parcel[], until = Infinity): [number, number][] {
  const start: [number, number][] = courier ? [[courier.lng, courier.lat]] : [];
  return start.concat(
    parcels.filter((p) => p.position <= until).map((p): [number, number] => [p.lng, p.lat]),
  );
}

/** A courier's pending parcels in predicted stop order. */
export function route(overview: Overview, courierId: string): Parcel[] {
  return overview.parcels.filter((p) => p.courier_id === courierId).sort((a, b) => a.position - b.position);
}

// Lower is worse: issue kind first, then how far the estimate moved.
const severity = (p: Parcel & { issue: Issue }) => RANK[p.issue] * 1e4 - Math.abs(p.slip_min ?? 0);
