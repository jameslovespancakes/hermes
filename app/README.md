# Hermes frontend

React + TypeScript, built with Vite and Bun 1.4.2. Pages: `/`, `/benchmarks`, `/methodology`.

```sh
bun install --frozen-lockfile
bun run dev          # http://localhost:5173
bun run lint         # strict type-aware ESLint
bun run typecheck
bun test tests
bun run build        # dist/, with every page pre-rendered
```

## Layout

- `src/pages/<page>/` – one component per section; `index.tsx` assembles the page.
- `src/motion/` – scroll animation, one module per scene. `start.ts` runs them once per page.
- `src/styles/` – `home.css`, `benchmarks.css` and `methodology.css` import their parts.
- `public/` – fonts, images, saved result downloads and licences.
- `tests/<page>/` – Bun tests on the rendered markup and animation maths.

Research pages stay hidden until their first scroll pose is drawn, so a reload never flashes the finished animation.

## Docker

The root `Dockerfile` builds this app and serves it from the API container on port 8000.
