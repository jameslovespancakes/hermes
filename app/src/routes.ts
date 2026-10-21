export type Page = 'home' | 'benchmarks' | 'methodology';

export const pages: Record<Page, { title: string; body: string; description: string }> = {
  home: {
    title: 'Hermes',
    body: '',
    description: 'Route-aware delivery estimates, informed by recorded delivery history.',
  },
  benchmarks: {
    title: 'Benchmarks | Hermes',
    body: 'research-page benchmark-page',
    description: 'Published results, input audits and matched model comparisons.',
  },
  methodology: {
    title: 'Methodology | Hermes',
    body: 'research-page methodology-page journey-page',
    description: 'Delivery data, prediction models, data hygiene and saved research results.',
  },
};

// '/benchmarks', '/benchmarks/' and '/benchmarks.html' all match; anything else is home.
export function route(path: string): Page {
  const name = path
    .replace(/\/$/, '')
    .replace(/\.html$/, '')
    .slice(1);
  return name === 'benchmarks' || name === 'methodology' ? name : 'home';
}
