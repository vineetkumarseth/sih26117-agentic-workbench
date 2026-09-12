# Frontend — Sovereign Workbench dashboard

React + Vite + Tailwind. Talks to the backend over `VITE_API_BASE_URL`
(default `http://localhost:8000`).

## Development

```bash
npm install
npm run dev        # http://localhost:5173, hot reload
```

Copy `.env.example` to `.env` first if your backend isn't on the default
port/host.

## Production build

```bash
npm run build       # outputs static files to dist/
npm run preview      # serve the production build locally to sanity-check it
```

`dist/` is a set of static files — serve them with any static host
(nginx, Caddy, a CDN, or the plant's internal web server). There's no
Node server to run in production; Vite/React only need Node at build
time.

If you containerize this later, a minimal approach is a two-stage
Dockerfile: `node:20-slim` to run `npm run build`, then copy `dist/` into
an `nginx:alpine` image. Not included here on purpose — see the root
`docker-compose.yml` comment for why `npm run dev` is the faster path for
a hackathon demo.

## Structure

```
src/
  api/           axios client + JWT auth context (token kept in memory only)
  components/    Login, Sidebar, ChatWindow, MessageBubble, AgentTracePanel,
                 DocumentUpload, GuardrailAlert
  pages/         Dashboard.jsx — composes the above
```

Design tokens (colors, fonts, animation) live in `tailwind.config.js` and
`src/index.css`. Fonts (Space Grotesk, IBM Plex Mono) are self-hosted via
`@fontsource` — no external font CDN, consistent with the backend's
"nothing calls outside this network" design.
