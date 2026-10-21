import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [
    react(),
    {
      // Engines bind to the document once, so source edits reload the page.
      name: 'full-reload',
      handleHotUpdate(context) {
        if (context.file.includes('/src/')) {
          context.server.ws.send({ type: 'full-reload' });
          return [];
        }
      },
    },
    {
      // Preview serves each pre-rendered page, as the API does in production.
      name: 'pages',
      configurePreviewServer(server) {
        server.middlewares.use((request, _response, next) => {
          const page = /^\/(benchmarks|methodology)\/?(\?.*)?$/.exec(request.url ?? '')?.[1];
          if (page) request.url = `/${page}/index.html`;
          next();
        });
      },
    },
  ],
  build: { target: 'es2022', manifest: true },
  server: { port: 5173, strictPort: true },
  preview: { port: 4173, strictPort: true },
});
