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
        {/* Local Hugeicons subset. MIT notice is retained in assets/icons.js. */}
        <symbol id="method-package" viewBox="0 0 24 24">
          <g fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22C11.1818 22 10.4002 21.6698 8.83693 21.0095C4.94564 19.3657 3 18.5438 3 17.1613V7M12 22C12.8182 22 13.5998 21.6698 15.1631 21.0095C19.0544 19.3657 21 18.5438 21 17.1613V7M12 22V11.3548" />
            <path d="M8.32592 9.69138L5.40472 8.27785C3.80157 7.5021 3 7.11423 3 6.5C3 5.88577 3.80157 5.4979 5.40472 4.72215L8.32592 3.30862C10.1288 2.43621 11.0303 2 12 2C12.9697 2 13.8712 2.4362 15.6741 3.30862L18.5953 4.72215C20.1984 5.4979 21 5.88577 21 6.5C21 7.11423 20.1984 7.5021 18.5953 8.27785L15.6741 9.69138C13.8712 10.5638 12.9697 11 12 11C11.0303 11 10.1288 10.5638 8.32592 9.69138Z" />
            <path d="M6 12L8 13M17 4L7 9" />
          </g>
        </symbol>
        <symbol id="method-route" viewBox="0 0 24 24">
          <g fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx={18} cy={5} r={3} />
            <circle cx={6} cy={19} r={3} />
            <path d="M12 5H8.5C6.567 5 5 6.567 5 8.5C5 10.433 6.567 12 8.5 12H15.5C17.433 12 19 13.567 19 15.5C19 17.433 17.433 19 15.5 19H12" />
          </g>
        </symbol>
        <symbol id="method-clock" viewBox="0 0 24 24">
          <g fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx={12} cy={12} r={10} />
            <path d="M12 8V12L14 14" />
          </g>
        </symbol>
        <symbol id="method-filter" viewBox="0 0 24 24">
          <g fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 7H6M3 17H9M18 17H21M15 7H21" />
            <rect x={6} y={4} width={6} height={6} rx={2} />
            <rect x={12} y={14} width={6} height={6} rx={2} />
          </g>
        </symbol>
        <symbol id="method-check" viewBox="0 0 24 24">
          <g fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx={12} cy={12} r={10} />
            <path d="M8 12.5 10.5 15 16 9" />
          </g>
        </symbol>
        <symbol id="method-chart" viewBox="0 0 24 24">
          <g fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 21H10C6.70017 21 5.05025 21 4.02513 19.9749C3 18.9497 3 17.2998 3 14V3M13 10V21M18 13V21M8 13V20M21 7.98693C19.16 7.98693 17.1922 8.24252 15.8771 6.49346C14.3798 4.50218 11.6202 4.50218 10.1229 6.49346C8.80782 8.24252 6.84003 7.98693 5 7.98693H3" />
          </g>
        </symbol>
        <Figures />
      </defs>
    </svg>
  );
}
