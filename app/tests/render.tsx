import { load } from 'cheerio';
import { renderToStaticMarkup } from 'react-dom/server';
import { App } from '../src/app';
import type { Page } from '../src/routes';

export const render = (page: Page) => load(renderToStaticMarkup(<App page={page} />));
