import { Suspense, useEffect, type ComponentType } from 'react';
import { Route, Routes } from 'react-router';
import { start } from './motion/start';
import { pages, type Page } from './routes';

export type Views = Record<Page, ComponentType>;

// Story pages own document-wide scroll engines, so each one starts its motion once.
function Story({ page, View }: { page: Exclude<Page, 'dashboard'>; View: ComponentType }) {
  useEffect(() => {
    void start(page);
  }, [page]);
  return <View />;
}

// Views are passed in so the browser can load only the current page's code.
export function App({ views }: { views: Views }) {
  return (
    <Suspense>
      <Routes>
        <Route path={pages.home.path} element={<Story page="home" View={views.home} />} />
        <Route path={pages.benchmarks.path} element={<Story page="benchmarks" View={views.benchmarks} />} />
        <Route
          path={pages.methodology.path}
          element={<Story page="methodology" View={views.methodology} />}
        />
        <Route path={pages.dashboard.path} element={<views.dashboard />} />
        <Route path="*" element={<Story page="home" View={views.home} />} />
      </Routes>
    </Suspense>
  );
}
