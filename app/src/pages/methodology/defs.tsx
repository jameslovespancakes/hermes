import { Figures } from './figures';

export function Defs() {
  return (
    <svg className="brand-definitions" width={0} height={0} aria-hidden="true" focusable="false">
      <defs>
        <symbol id="hermes-boots" viewBox="0 0 64 64">
          <path d="M29 25h15v15c0 4 2 6 6 8l7 3c3 1 4 3 4 6v2H24V48l5-5Z" fill="currentColor" />
          <path
            d="M31 36C18 35 9 27 5 13l14 5L12 6l21 12c7 4 8 11 4 16Z"
            fill="var(--cream)"
            stroke="currentColor"
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="m12 20 16 9m-10 1 11 2"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M39 29h4M27 54h31"
            fill="none"
            stroke="var(--cream)"
            strokeWidth={2}
            strokeLinecap="round"
          />
        </symbol>
        <Figures />
      </defs>
    </svg>
  );
}
