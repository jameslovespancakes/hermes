import { useEffect } from 'react';
import { start } from './motion/start';
import { Page as Benchmarks } from './pages/benchmarks';
import { Page as Home } from './pages/home';
import { Page as Methodology } from './pages/methodology';
import type { Page } from './routes';

const views = { home: Home, benchmarks: Benchmarks, methodology: Methodology };

export function App({ page }: { page: Page }) {
  useEffect(() => {
    void start(page);
  }, [page]);
  const View = views[page];
  return <View />;
}
