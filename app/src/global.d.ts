export {};

declare global {
  interface WindowEventMap {
    'arrival:motion': CustomEvent<{ paused: boolean }>;
  }
}
