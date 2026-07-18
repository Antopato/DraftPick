# DraftPick — Herramienta de draft de League of Legends

Monorepo: `backend/` (Python 3.12+ / FastAPI / SQLAlchemy) + `frontend/`
(React + Vite + TypeScript). Fase 1: salas de draft 1v1 en tiempo real.
Fase 2 (futura): análisis automático del draft — por eso los drafts terminados
se persisten íntegros en la BD.

## Invariantes (NO romper)

### Secuencia de draft (torneo estándar, 20 turnos)

```
Bans 1 : B R B R B R            (turnos 0–5)
Picks 1: B1 · R1 R2 · B2 B3 · R3 (turnos 6–11)
Bans 2 : R B R B                 (turnos 12–15)
Picks 2: R4 · B4 B5 · R5         (turnos 16–19)
```

Definida en `backend/app/draft/sequence.py`; verificada literalmente en
`backend/tests/test_engine.py`. No modificar sin actualizar ambos.

### Validación SOLO en servidor

- El estado del draft vive en el servidor (`DraftEngine` en
  `backend/app/draft/engine.py`, puro y sin IO; `RoomManager` orquesta).
- El cliente solo envía intenciones (`ready`, `hover`, `confirm`, `next_game`);
  el servidor valida turno, legalidad del campeón y timer. NUNCA confiar en el
  cliente.
- El rol (azul/rojo/espectador) se deriva SIEMPRE del token de la URL en el
  servidor (`secrets.token_urlsafe`); jamás de un parámetro enviado por el
  cliente. El espectador no puede enviar acciones.
- Timer autoritativo en servidor (tarea asyncio por sala). Al agotarse: se
  confirma el hover; sin hover → pick aleatorio / ban saltado (`champion_id`
  NULL). El timer del cliente es solo visual (usa `deadline` + `server_now`).

### Reglas del draft

- Campeón baneado o elegido en la partida: no reutilizable en esa partida.
- Fearless: los ELEGIDOS (no los baneados) de partidas anteriores de la serie
  quedan bloqueados para ambos equipos (tampoco se pueden banear). Serie
  Bo1/Bo3/Bo5 solo en modo fearless; estándar = 1 partida.
- Timer por turno configurable (5–180 s, por defecto 30).
- El draft empieza con ready check de ambos capitanes.
- El hover es visible en tiempo real para todos (decisión confirmada).

### Sincronización

- WebSockets nativos de FastAPI (`/ws/{token}`). NUNCA polling como mecanismo
  principal; `GET /api/state/{token}` es solo carga inicial/fallback puntual.
- Tras cada evento se difunde el ESTADO COMPLETO (nunca diffs).

### Persistencia

- SQLAlchemy con SQLite en dev; cambiar a Postgres (Neon/Supabase) = cambiar
  solo `DATABASE_URL`. NO acoplar código a SQLite.

### Idioma y hosting

- TODO texto visible al usuario (UI + mensajes de error): **español de España**.
  Código, comentarios y nombres: inglés.
- Objetivo de despliegue GRATUITO: frontend Vercel/Netlify, backend Render free
  (soporta WebSockets pero "duerme": el frontend maneja reconexión con backoff
  y aviso de arranque en frío en `useDraftSocket`).

## Comandos

- Backend: `cd backend && .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000`
- Tests: `cd backend && pytest` (la máquina de estados SIEMPRE con tests)
- Frontend: `cd frontend && npm run dev` (proxy `/api` y `/ws` → :8000)

## Datos de campeones

Riot **Data Dragon** (CDN estático, SIN API key; no usar la Riot API con key):
- Versiones: `https://ddragon.leagueoflegends.com/api/versions.json` (primera = actual)
- Lista es_ES: `/cdn/{v}/data/es_ES/champion.json` · Retratos: `/cdn/{v}/img/champion/{Id}.png`
- El backend valida contra los ids en inglés (`en_US`); el frontend muestra
  nombres es_ES y busca por ambos.
