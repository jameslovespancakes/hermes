// Every page view, imported up front. Used for pre-rendering and tests; the browser loads pages lazily.
import type { Views } from './app';
import { Page as benchmarks } from './pages/benchmarks';
import { Page as dashboard } from './pages/dashboard';
import { Page as home } from './pages/home';
import { Page as methodology } from './pages/methodology';

export const views: Views = { home, benchmarks, methodology, dashboard };
