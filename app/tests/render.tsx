import { load } from 'cheerio';
import { renderToStaticMarkup } from 'react-dom/server';
import { StaticRouter } from 'react-router';
import { App } from '../src/app';
import { pages, type Page } from '../src/routes';
import { views } from '../src/views';

export const render = (page: Page) =>
  load(
    renderToStaticMarkup(
      <StaticRouter location={pages[page].path}>
        <App views={views} />
      </StaticRouter>,
    ),
  );
