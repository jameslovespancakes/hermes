// Pre-render each page into dist so content shows before (and without) JavaScript.
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { renderToString } from 'react-dom/server';
import { App } from '../src/app';
import { pages, type Page } from '../src/routes';

const template = await readFile('dist/index.html', 'utf8');
const manifest = JSON.parse(await readFile('dist/.vite/manifest.json', 'utf8')) as Record<
  string,
  { file: string }
>;

for (const page of Object.keys(pages) as Page[]) {
  const { title, body, description } = pages[page];
  const css = manifest[`src/styles/${page}.css`].file;
  const html = template
    .replace(
      '<title>Hermes</title>',
      `<title>${title}</title><meta name="description" content="${description}" /><link rel="stylesheet" href="/${css}" />`,
    )
    .replace('<body>', `<body class="${body}">`)
    .replace('<div id="root"></div>', `<div id="root">${renderToString(<App page={page} />)}</div>`);
  const folder = page === 'home' ? 'dist' : `dist/${page}`;
  await mkdir(folder, { recursive: true });
  await writeFile(`${folder}/index.html`, html);
}
