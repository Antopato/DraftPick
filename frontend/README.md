# DraftPick — Frontend (React + Vite + TypeScript)

## Arrancar en local

```bash
cd frontend
npm install
npm run dev
```

Abre http://localhost:5173. El proxy de Vite redirige `/api` y `/ws` al backend
local (`http://localhost:8000`), así que arranca antes el backend (ver
`backend/README.md`).

## Variables de entorno

- `VITE_API_URL`: URL pública del backend. **Vacía en desarrollo** (se usa el
  proxy). En producción (Vercel/Netlify), ponla a la URL de Render, p. ej.
  `https://draftpick-api.onrender.com`.
- `VITE_PROXY_TARGET`: solo para el proxy de dev (docker-compose la usa para
  apuntar al servicio `backend`).

## Despliegue en Vercel/Netlify

- Directorio raíz: `frontend/` · Build: `npm run build` · Salida: `dist/`.
- Define `VITE_API_URL` con la URL del backend.
- Al ser una SPA con rutas (`/room/:token`), configura el rewrite de todas las
  rutas a `index.html` (en Netlify: `_redirects` con `/* /index.html 200`;
  en Vercel es automático para proyectos Vite).

## Datos de campeones

Se cargan directamente de Riot Data Dragon (CDN estático, sin API key), con
nombres en `es_ES` y caché en `localStorage` (6 h).
