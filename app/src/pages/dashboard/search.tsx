// Top-right search: a courier or parcel id, across every city; picking a match opens it on the map.
import { Search01Icon } from '@hugeicons/core-free-icons';
import { HugeiconsIcon } from '@hugeicons/react';
import { useMemo, useState } from 'react';
import { courierKey, parcelKey, type City, type Fleet, type Parcel } from './api';

const LIMIT = 8;
const courier = (key: string): Found => ({ kind: 'courier', key });
const parcel = (p: Parcel): Found => ({ kind: 'parcel', parcel: p });

export type Found = { kind: 'courier'; key: string } | { kind: 'parcel'; parcel: Parcel };

interface Props {
  fleet: Fleet;
  cities: City[];
  onPick: (found: Found) => void;
}

export function Search({ fleet, cities, onPick }: Props) {
  const [text, setText] = useState('');
  const name = (id: string) => cities.find((c) => c.id === id)?.name ?? id;
  const matches = useMemo(() => {
    const q = text.trim().replace(/^#/, '');
    if (!q) return [];
    const couriers = fleet.couriers
      .filter((c) => c.courier_id.startsWith(q))
      .map((c) => ({
        id: `c${courierKey(c)}`,
        label: `Courier #${c.courier_id}`,
        city: name(c.city),
        found: courier(courierKey(c)),
      }));
    const parcels = fleet.parcels
      .filter((p) => String(p.order_id).startsWith(q))
      .map((p) => ({
        id: `p${parcelKey(p)}`,
        label: `Parcel ${String(p.order_id)}`,
        city: name(p.city),
        found: parcel(p),
      }));
    return [...couriers, ...parcels].slice(0, LIMIT);
    // `name` reads `cities`, which is a dependency.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, fleet, cities]);

  const pick = (found: Found) => {
    setText('');
    onPick(found);
  };

  return (
    <div className="search">
      <label>
        <HugeiconsIcon icon={Search01Icon} size={17} strokeWidth={1.8} />
        <input
          type="search"
          placeholder="Courier or parcel"
          aria-label="Find a courier or parcel"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && matches[0]) pick(matches[0].found);
            if (e.key === 'Escape') setText('');
          }}
        />
      </label>
      {text.trim() && (
        <ul role="listbox">
          {matches.length ? (
            matches.map((m) => (
              <li key={m.id}>
                <button type="button" onClick={() => pick(m.found)}>
                  <strong>{m.label}</strong>
                  <span>{m.city}</span>
                </button>
              </li>
            ))
          ) : (
            <li className="none">Nothing held at this moment</li>
          )}
        </ul>
      )}
    </div>
  );
}
