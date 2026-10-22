// The one control on the map: which recorded moment to replay. Also shows loading and city-wide input health.
import type { DataHealth } from './api';

interface Props {
  date: string;
  time: string;
  loading: boolean;
  health: DataHealth | null;
  onDate: (date: string) => void;
  onTime: (time: string) => void;
}

const FIRST = 7 * 60;
const LAST = 21 * 60;
const STEP = 15;
const minutesOf = (time: string) => Number(time.slice(0, 2)) * 60 + Number(time.slice(3, 5));
const timeOf = (minutes: number) =>
  `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`;

export function TimeControl({ date, time, loading, health, onDate, onTime }: Props) {
  const unusual = health && health.status !== 'ok';
  return (
    <div className="time-control">
      <input
        type="date"
        value={date}
        min="2000-06-01"
        max="2000-10-31"
        aria-label="Date"
        onChange={(e) => {
          if (e.target.value) onDate(e.target.value);
        }}
      />
      <input
        type="range"
        min={FIRST}
        max={LAST}
        step={STEP}
        value={minutesOf(time)}
        aria-label="Time"
        onChange={(e) => {
          onTime(timeOf(Number(e.target.value)));
        }}
      />
      <strong className="time">{time}</strong>
      <span
        className={loading ? 'status loading' : unusual ? 'status unusual' : 'status'}
        title={
          loading
            ? 'Updating'
            : unusual
              ? "Today's data passed every check but looks unlike the training data; estimates may be less certain"
              : 'Inputs look normal'
        }
      />
    </div>
  );
}
