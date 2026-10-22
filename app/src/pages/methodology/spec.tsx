// A short list of named rules or parts under a step's headline number.
export function Spec({ rows }: { rows: readonly (readonly [string, string])[] }) {
  return (
    <dl className="spec">
      {rows.map(([name, detail]) => (
        <div key={name}>
          <dt>{name}</dt>
          <dd>{detail}</dd>
        </div>
      ))}
    </dl>
  );
}
