export type Page = 'home' | 'benchmarks' | 'methodology' | 'dashboard';

export const pages: Record<Page, { path: string; title: string; body: string; description: string }> = {
  home: {
    path: '/',
    title: 'Hermes',
    body: '',
    description: 'Route-aware delivery estimates, informed by recorded delivery history.',
  },
  benchmarks: {
    path: '/benchmarks',
    title: 'Benchmarks | Hermes',
    body: 'research-page benchmark-page',
    description: 'Published results, input audits and matched model comparisons.',
  },
  methodology: {
    path: '/methodology',
    title: 'Methodology | Hermes',
    body: 'research-page methodology-page journey-page',
    description: 'Delivery data, prediction models, data hygiene and saved research results.',
  },
  dashboard: {
    path: '/dashboard',
    title: 'Overview | Hermes',
    body: 'app-page',
    description: 'Live courier workloads and model ETAs for dispatchers.',
  },
};

// '/benchmarks', '/benchmarks/' and '/benchmarks.html' all match; anything else is home.
export function route(path: string): Page {
  const name = path
    .replace(/\/$/, '')
    .replace(/\.html$/, '')
    .slice(1);
  return name in pages && name !== 'home' ? (name as Page) : 'home';
}
