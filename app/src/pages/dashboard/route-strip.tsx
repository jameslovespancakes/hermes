// The courier's route as one line: the bike, the stops before this parcel, this parcel, and the stops after it.
// Stops are spaced by predicted time, so long gaps show long legs.
import { BikeIcon } from '@hugeicons/core-free-icons';
import { HugeiconsIcon } from '@hugeicons/react';
import type { Parcel } from './api';

const W = 272; // card content width minus the bike icon
const Y = 14;

export function RouteStrip({ route, parcel, color }: { route: Parcel[]; parcel: Parcel; color: string }) {
  const last = Math.max(1, ...route.map((p) => p.minutes_remaining));
  const x = (p: Parcel) => 6 + (p.minutes_remaining / last) * (W - 12);
  const here = x(parcel);
  const stops = route.length - 1;
  return (
    <div
      className="route-strip"
      title={`${String(parcel.position - 1)} of ${String(stops)} other stops come first`}
    >
      <HugeiconsIcon icon={BikeIcon} size={22} color="#034f46" strokeWidth={1.8} />
      <svg
        width={W}
        height={Y * 2}
        viewBox={`0 0 ${String(W)} ${String(Y * 2)}`}
        role="img"
        aria-label={`Stop ${String(parcel.position)} of ${String(route.length)}`}
      >
        <line x1={6} x2={here} y1={Y} y2={Y} stroke={color} strokeWidth={3} strokeLinecap="round" />
        <line x1={here} x2={W - 6} y1={Y} y2={Y} stroke="#e4e2dc" strokeWidth={3} strokeLinecap="round" />
        {route
          .filter((p) => p.order_id !== parcel.order_id)
          .map((p) => {
            const before = p.position < parcel.position;
            return (
              <circle
                key={p.order_id}
                cx={x(p)}
                cy={Y}
                r={3.2}
                fill={before ? color : '#fff'}
                stroke={before ? '#fff' : '#d6d3cc'}
                strokeWidth={1.5}
              />
            );
          })}
        <circle cx={here} cy={Y} r={7.5} fill="#fff" stroke={color} strokeWidth={3} />
      </svg>
    </div>
  );
}
