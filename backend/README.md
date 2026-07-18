# DraftPick — Backend (FastAPI)

API REST + WebSockets para el draft en tiempo real. Python 3.12+ (funciona también en 3.13).

## Arrancar en local

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements-dev.txt
copy .env.example .env    # (cp en Linux/macOS) — los valores por defecto valen para dev

uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000/api/health
- Docs interactivas: http://localhost:8000/docs
- Base de datos: SQLite en `backend/draftpick.db` (se crea sola al arrancar).

## Tests

```bash
pytest
```

Los tests cubren la máquina de estados del draft (`app/draft/engine.py`):
secuencia exacta de turnos, acciones ilegales, timeouts y modo Fearless.

## Cambiar a Postgres (Neon/Supabase)

Solo hay que cambiar `DATABASE_URL` en `.env`, p. ej.:

```
DATABASE_URL=postgresql+psycopg2://user:password@host/dbname
```

(instala también `psycopg2-binary`). El código no está acoplado a SQLite.

## Despliegue en Render (free tier)

- **Build command**: `pip install -r requirements.txt`
- **Start command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Variables de entorno: `DATABASE_URL` (Postgres de Neon/Supabase recomendado en
  producción: el disco de Render free es efímero) y `CORS_ORIGINS` con la URL
  del frontend (p. ej. `https://tuapp.vercel.app`).
- El free tier "duerme" tras inactividad: el frontend ya muestra un aviso de
  arranque en frío y reintenta la conexión automáticamente.
