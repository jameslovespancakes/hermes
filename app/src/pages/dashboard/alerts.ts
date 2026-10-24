// Turns the city overview into what a dispatcher should look at: every flagged parcel, worst first. Couriers carry
// their own feed problems (see api.ts), so the map and the courier card show the same icons.
import {
  AlarmClockIcon,
  Clock04Icon,
  Copy01Icon,
  HelpCircleIcon,
  Layers01Icon,
  LocationOffline01Icon,
  PackageSearchIcon,
  Upload04Icon,
  WifiDisconnected01Icon,
} from '@hugeicons/core-free-icons';
import type { IconSvgElement } from '@hugeicons/react';
import {
  courierKey,
  parcelKey,
  type Courier,
  type Fleet,
  type Issue,
  type ParcelIssue,
  type Parcel,
} from './api';

const DATA = '#e58f0b';

export const ISSUES: Record<Issue, { color: string; label: string; icon: IconSvgElement }> = {
  lagging: { color: DATA, label: 'Uploads lagging', icon: Upload04Icon },
  silent: { color: DATA, label: 'Courier silent', icon: WifiDisconnected01Icon },
  bulk: { color: DATA, label: 'Bulk-synced scans', icon: Layers01Icon },
  clock: { color: DATA, label: 'Device clock fast', icon: Clock04Icon },
  moved: { color: DATA, label: 'Address repaired', icon: LocationOffline01Icon },
  resent: { color: DATA, label: 'Duplicate removed', icon: Copy01Icon },
  missed: { color: DATA, label: 'Scan may be missing', icon: PackageSearchIcon },
  suspect: { color: '#7c5cff', label: 'May be wrong', icon: HelpCircleIcon },
  late: { color: '#e5484d', label: 'Running late', icon: AlarmClockIcon },
};

// Same order as the server: data problems first, then implausible inputs, then plain slips.
const RANK: Record<ParcelIssue, number> = { moved: 0, resent: 0, missed: 0, suspect: 1, late: 2 };

export interface Alert {
  parcel: Parcel & { issue: ParcelIssue };
  courier: Courier | undefined;
  /** The courier's pending parcels in predicted stop order. */
  route: Parcel[];
}

const flagged = (p: Parcel): p is Parcel & { issue: ParcelIssue } => p.issue !== null;

/** Every flagged parcel, worst first; dismissed parcels (by key 'city:order') are skipped. */
export function alerts(fleet: Fleet, dismissed: ReadonlySet<string> = new Set()): Alert[] {
  const couriers = new Map(fleet.couriers.map((c) => [courierKey(c), c]));
  const byKey = routes(fleet.parcels);
  return fleet.parcels
    .filter(flagged)
    .filter((p) => !dismissed.has(parcelKey(p)))
    .sort((a, b) => severity(a) - severity(b))
    .map((parcel) => ({
      parcel,
      courier: couriers.get(courierKey(parcel)),
      route: byKey.get(courierKey(parcel)) ?? [],
    }));
}

/** Parcels grouped by courier key, each in predicted stop order. */
export function routes(parcels: Parcel[]): Map<string, Parcel[]> {
  const groups = new Map<string, Parcel[]>();
  for (const parcel of parcels) {
    const group = groups.get(courierKey(parcel));
    if (group) group.push(parcel);
    else groups.set(courierKey(parcel), [parcel]);
  }
  for (const group of groups.values()) group.sort((a, b) => a.position - b.position);
  return groups;
}

/** A courier's position, then each stop in order up to `until`, as (lng, lat). */
export function stops(courier: Courier | undefined, parcels: Parcel[], until = Infinity): [number, number][] {
  const start: [number, number][] = courier ? [[courier.lng, courier.lat]] : [];
  return start.concat(
    parcels.filter((p) => p.position <= until).map((p): [number, number] => [p.lng, p.lat]),
  );
}

// Lower is worse: issue kind first, then how far the estimate moved.
const severity = (p: Parcel & { issue: ParcelIssue }) => RANK[p.issue] * 1e4 - Math.abs(p.slip_min ?? 0);
