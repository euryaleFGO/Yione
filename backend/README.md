# webLing backend

FastAPI + Python 3.12. Sibling Ling repo is imported via `sys.path` injection
(see `app/integrations/ling_adapter.py`), not packaged.

## Quickstart

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp ../.env.example ../.env   # adjust LING_REPO_PATH / MONGO_URI / LLM_* if needed

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Smoke test: `curl http://localhost:8000/api/health` → `{"ok": true, ...}`

## Layout

```
app/
  main.py              FastAPI entry (lifespan, CORS, static mount)
  config.py            pydantic-settings
  routers/             HTTP endpoints (thin)
  ws/                  WebSocket handlers
  services/            business logic
  repositories/        Mongo data access
  schemas/             pydantic request/response
  domain/              internal domain models
  integrations/        external adapters (Ling, TTS, LLM)
  middlewares/         auth, CORS, rate limit, request-id
  static/tts/          cached TTS wav files
```

## Dev loop

```bash
ruff check app tests && ruff format app tests
mypy app
pytest
```
