// The bar on the map: home, which recorded moment to replay, and the time (it pulses while loading).
import { Calendar } from './calendar';

interface Props {
  date: string;
  time: string;
  loading: boolean;
  onDate: (date: string) => void;
  onTime: (time: string) => void;
}

const FIRST = 7 * 60;
const LAST = 21 * 60;
const STEP = 15;
const minutesOf = (time: string) => Number(time.slice(0, 2)) * 60 + Number(time.slice(3, 5));
const timeOf = (minutes: number) =>
  `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`;

export function TimeControl({ date, time, loading, onDate, onTime }: Props) {
  return (
    <div className="time-control">
      <a className="home" href="/" aria-label="Hermes home">
        <svg viewBox="0 0 64 64" aria-hidden="true">
          <use href="#hermes-boots" />
        </svg>
      </a>
      <Calendar value={date} min="2000-06-01" max="2000-10-31" onChange={onDate} />
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
      <strong className={loading ? 'time loading' : 'time'} aria-busy={loading}>
        {time}
      </strong>
    </div>
  );
}
