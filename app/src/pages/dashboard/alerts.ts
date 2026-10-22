// Turns the city overview into the few things a dispatcher should look at: one alert per courier at most.
import { AlarmClockIcon, Alert02Icon, HelpCircleIcon } from '@hugeicons/core-free-icons';
import type { IconSvgElement } from '@hugeicons/react';
import type { Courier, Issue, Overview, Parcel } from './api';

export const ISSUES: Record<Issue, { color: string; label: string; icon: IconSvgElement }> = {
  data: { color: '#e58f0b', label: 'Data issue', icon: Alert02Icon },
  suspect: { color: '#7c5cff', label: 'May be wrong', icon: HelpCircleIcon },
  late: { color: '#e5484d', label: 'Running late', icon: AlarmClockIcon },
};

// Same order as the server: guard flags first, then implausible data, then plain slips.
const RANK: Record<Issue, number> = { data: 0, suspect: 1, late: 2 };

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

export function route(overview: Overview, courierId: string): Parcel[] {
  return overview.parcels.filter((p) => p.courier_id === courierId).sort((a, b) => a.position - b.position);
}

// Lower is worse: issue kind first, then how far the estimate moved.
const severity = (p: Parcel & { issue: Issue }) => RANK[p.issue] * 1e4 - Math.abs(p.slip_min ?? 0);
