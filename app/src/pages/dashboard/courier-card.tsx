// The card for one courier: every parcel they hold at this moment, in predicted stop order.
import { BikeIcon, Cancel01Icon } from '@hugeicons/core-free-icons';
import { HugeiconsIcon } from '@hugeicons/react';
import { ISSUES } from './alerts';
import { clock, type Courier, type Parcel } from './api';

interface Props {
  courier: Courier;
  parcels: Parcel[];
  onClose: () => void;
}

export function CourierCard({ courier, parcels, onClose }: Props) {
  return (
    <aside className="courier-card" aria-label={`Courier ${courier.courier_id}`}>
      <header>
        <HugeiconsIcon icon={BikeIcon} size={28} color="#2f6fed" strokeWidth={1.8} />
        <div>
          <strong>Courier #{courier.courier_id}</strong>
          <span>
            {parcels.length} parcels · last scan {Math.round(courier.feed_age_min)} min ago
          </span>
        </div>
        <button type="button" className="alert-close" aria-label="Close" onClick={onClose}>
          <HugeiconsIcon icon={Cancel01Icon} size={18} />
        </button>
      </header>
      <ol>
        {parcels.map((p) => {
          const issue = p.issue ? ISSUES[p.issue] : null;
          return (
            <li key={p.order_id} title={p.reasons.join(' · ')}>
              <span className="stop">{p.position}</span>
              <span className="eta">{clock(p.eta)}</span>
              <span className="taken">taken {clock(p.accepted_at)}</span>
              {issue && <HugeiconsIcon icon={issue.icon} size={16} color={issue.color} strokeWidth={1.9} />}
            </li>
          );
        })}
      </ol>
    </aside>
  );
}
