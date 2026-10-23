// The card for one alert: what kind, when it should arrive (a window), how far it moved, the route, three actions.
import {
  Call02Icon,
  Cancel01Icon,
  CheckmarkCircle02Icon,
  Notification01Icon,
} from '@hugeicons/core-free-icons';
import { HugeiconsIcon, type IconSvgElement } from '@hugeicons/react';
import { ISSUES, type Alert } from './alerts';
import { clock } from './api';
import { RouteStrip } from './route-strip';
import { arrivalWindow } from './window';

interface Props {
  alert: Alert;
  onClose: () => void;
  onDismiss: () => void;
}

export const signed = (minutes: number) =>
  `${minutes > 0 ? '+' : '−'}${String(Math.round(Math.abs(minutes)))} min`;

function Action({
  icon,
  label,
  primary,
  onClick,
}: {
  icon: IconSvgElement;
  label: string;
  primary?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      className={primary ? 'act primary' : 'act'}
      aria-label={label}
      data-tip={label}
      onClick={onClick}
    >
      <HugeiconsIcon icon={icon} size={22} strokeWidth={1.7} />
    </button>
  );
}

export function AlertCard({ alert, onClose, onDismiss }: Props) {
  const { parcel, route } = alert;
  const issue = ISSUES[parcel.issue];
  const { from, to } = arrivalWindow(parcel);
  const later = (days: number) => (days > 0 ? ` +${String(days)}d` : '');
  const window = `${from.time}${later(from.days)}–${to.time}${later(to.days)}`;
  const before = parcel.baseline_eta
    ? `ETA ${clock(parcel.eta)}, was ${clock(parcel.baseline_eta)}`
    : `ETA ${clock(parcel.eta)}`;
  return (
    <aside className="alert-card" style={{ ['--c' as string]: issue.color }} aria-label={issue.label}>
      <header>
        <span className="alert-kind" title={parcel.reasons.join(', ')}>
          <HugeiconsIcon icon={issue.icon} size={20} color={issue.color} strokeWidth={1.9} />
          {issue.label}
        </span>
        {parcel.slip_min !== null && (
          <span className="alert-slip" title={before}>
            {signed(parcel.slip_min)}
          </span>
        )}
        <button type="button" className="alert-close" aria-label="Close" onClick={onClose}>
          <HugeiconsIcon icon={Cancel01Icon} size={18} />
        </button>
      </header>
      <p className="alert-label">Arrives between</p>
      <strong className="alert-eta" title={before}>
        {from.time}
        {from.days > 0 && <sup>+{from.days}</sup>}
        <span>–</span>
        {to.time}
        {to.days > 0 && <sup>+{to.days}</sup>}
      </strong>
      <p className="alert-why">{parcel.reasons[0]}</p>
      <RouteStrip route={route} parcel={parcel} color={issue.color} />
      <footer>
        <Action icon={Notification01Icon} label={`Notify customer · ${window}`} primary />
        <Action icon={Call02Icon} label={`Call courier #${parcel.courier_id}`} />
        <Action icon={CheckmarkCircle02Icon} label="Dismiss" onClick={onDismiss} />
      </footer>
    </aside>
  );
}
