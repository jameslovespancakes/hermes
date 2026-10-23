// The card for one courier: every parcel they hold at this moment, in predicted stop order.
import { BikeIcon, Cancel01Icon } from '@hugeicons/core-free-icons';
import { HugeiconsIcon } from '@hugeicons/react';
import { ISSUES } from './alerts';
import { clock, type Courier, type Parcel } from './api';
import { arrivalWindow } from './window';

/** Problems with the courier's feed, the same for every parcel they hold: shown once, under their name. */
const COURIER_ISSUES = new Set(['lagging', 'silent', 'bulk', 'clock']);

const ago = (minutes: number) => {
  const m = Math.round(minutes);
  if (m < 1) return 'just now';
  if (m < 60) return `${String(m)} min ago`;
  if (m < 1440) return `${String(Math.floor(m / 60))} h ${String(m % 60)} min ago`;
  return `${String(Math.floor(m / 1440))} d ${String(Math.floor((m % 1440) / 60))} h ago`;
};

interface Props {
  courier: Courier;
  parcels: Parcel[];
  onClose: () => void;
  onParcel: (parcel: Parcel) => void;
  /** The moment on screen ('MM-DD HH:MM:SS'). */
  now: string;
}

export function CourierCard({ courier, parcels, onClose, onParcel, now }: Props) {
  const feed = parcels.map((p) => p.issue).find((i) => i !== null && COURIER_ISSUES.has(i));
  const feedIssue = feed ? ISSUES[feed] : null;
  const feedReason = parcels.find((p) => p.issue === feed)?.reasons[0];
  return (
    <aside className="courier-card" aria-label={`Courier ${courier.courier_id}`}>
      <header>
        <HugeiconsIcon icon={BikeIcon} size={28} color="#034f46" strokeWidth={1.8} />
        <div>
          <strong>Courier #{courier.courier_id}</strong>
          <span>Last scan: {ago(courier.feed_age_min)}</span>
          {feedIssue && (
            <span className="feed-issue" style={{ color: feedIssue.color }} title={feedReason}>
              <HugeiconsIcon icon={feedIssue.icon} size={14} color={feedIssue.color} strokeWidth={2} />
              {feedIssue.label}
            </span>
          )}
        </div>
        <button type="button" className="alert-close" aria-label="Close" onClick={onClose}>
          <HugeiconsIcon icon={Cancel01Icon} size={18} />
        </button>
      </header>
      <ol>
        {parcels.map((p) => {
          const issue = p.issue && !COURIER_ISSUES.has(p.issue) ? ISSUES[p.issue] : null;
          const { from, to } = arrivalWindow(p, now);
          return (
            <li key={p.order_id}>
              <button
                type="button"
                title={p.reasons.join(' · ') || `Parcel ${String(p.order_id)}`}
                onClick={() => onParcel(p)}
              >
                <span className="stop">{p.position}</span>
                <span className="eta">
                  {from.time}–{to.time}
                </span>
                <span className="taken">taken {clock(p.accepted_at)}</span>
                {issue && <HugeiconsIcon icon={issue.icon} size={16} color={issue.color} strokeWidth={1.9} />}
              </button>
            </li>
          );
        })}
      </ol>
    </aside>
  );
}
