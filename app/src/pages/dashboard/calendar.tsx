// The date picker on the time bar: a small month grid in the site's style (the browser's own picker cannot be styled).
import { ArrowLeft01Icon, ArrowRight01Icon } from '@hugeicons/core-free-icons';
import { HugeiconsIcon } from '@hugeicons/react';
import { useEffect, useRef, useState } from 'react';

export const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const WEEK = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
const pad = (n: number) => String(n).padStart(2, '0');
const iso = (year: number, month: number, day: number) => `${String(year)}-${pad(month + 1)}-${pad(day)}`;

interface Props {
  value: string;
  min: string;
  max: string;
  onChange: (date: string) => void;
}

export function Calendar({ value, min, max, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const [year, month] = [Number(value.slice(0, 4)), Number(value.slice(5, 7)) - 1];
  const [shown, setShown] = useState({ year, month });
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const away = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', away);
    document.addEventListener('keydown', escape);
    return () => {
      document.removeEventListener('mousedown', away);
      document.removeEventListener('keydown', escape);
    };
  }, [open]);

  const first = new Date(Date.UTC(shown.year, shown.month, 1));
  const days = new Date(Date.UTC(shown.year, shown.month + 1, 0)).getUTCDate();
  const blanks = (first.getUTCDay() + 6) % 7;
  const step = (by: number) => {
    const m = shown.month + by;
    setShown({ year: shown.year + Math.floor(m / 12), month: ((m % 12) + 12) % 12 });
  };
  const monthStart = iso(shown.year, shown.month, 1);
  const monthEnd = iso(shown.year, shown.month, days);

  return (
    <div className="calendar" ref={root}>
      <button
        type="button"
        className="calendar-toggle"
        aria-label="Date"
        aria-expanded={open}
        onClick={() => {
          setShown({ year, month });
          setOpen(!open);
        }}
      >
        {MONTHS[month]} {Number(value.slice(8, 10))}
      </button>
      {open && (
        <div className="calendar-pop" role="dialog" aria-label="Choose a date">
          <header>
            <button
              type="button"
              aria-label="Previous month"
              disabled={monthStart <= min}
              onClick={() => step(-1)}
            >
              <HugeiconsIcon icon={ArrowLeft01Icon} size={16} />
            </button>
            <strong>
              {MONTHS[shown.month]} {shown.year}
            </strong>
            <button type="button" aria-label="Next month" disabled={monthEnd >= max} onClick={() => step(1)}>
              <HugeiconsIcon icon={ArrowRight01Icon} size={16} />
            </button>
          </header>
          <div className="calendar-grid">
            {WEEK.map((d, i) => (
              <span key={`w${String(i)}`} className="weekday">
                {d}
              </span>
            ))}
            {Array.from({ length: blanks }, (_, i) => (
              <span key={`b${String(i)}`} />
            ))}
            {Array.from({ length: days }, (_, i) => {
              const date = iso(shown.year, shown.month, i + 1);
              return (
                <button
                  key={date}
                  type="button"
                  className={date === value ? 'day on' : 'day'}
                  disabled={date < min || date > max}
                  onClick={() => {
                    onChange(date);
                    setOpen(false);
                  }}
                >
                  {i + 1}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
