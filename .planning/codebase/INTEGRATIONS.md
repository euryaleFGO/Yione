# External Integrations

## Services

| Service | Purpose | Connection | Config |
|---------|---------|------------|--------|
| LLM API | AI chat responses (OpenAI-compatible) | HTTP SSE streaming | `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` |
| CosyVoice TTS | Text-to-speech synthesis | HTTP (enqueue/dequeue) | `TTS_BASE_URL`, `TTS_DEFAULT_SPK_ID` |
| MongoDB | Data persistence (sessions, speakers, tenants) | TCP connection | `MONGO_URI`, `MONGO_DB` |
| Ling SVEngine | Speaker voiceprint embedding | Python import (optional) | `LING_REPO_PATH` |

## APIs

### LLM API (OpenAI-compatible)
- **Endpoint**: `{LLM_BASE_URL}/v1/chat/completions`
- **Protocol**: HTTP POST with SSE streaming
- **Authentication**: Bearer token (`LLM_API_KEY`)
- **Default Model**: MiniMax-M2.5
- **Implementation**: `backend/app/services/agent_service.py`
- **Fallback**: Echo stub when unavailable

### CosyVoice TTS API
- **Enqueue Endpoint**: `POST {TTS_BASE_URL}/tts/enqueue`
  - Request: `{text, use_clone, spk_id, client_id}`
  - Response: `{status, job_id}`
- **Dequeue Endpoint**: `GET {TTS_BASE_URL}/tts/dequeue?job_id=...&timeout=N`
  - Response: WAV audio segments (200) or status codes (204/409/404)
- **Protocol**: Job queue with polling
- **Implementation**: `backend/app/services/tts_service.py`
- **Cache**: Local filesystem (`TTS_CACHE_DIR`)

### Ling SVEngine API
- **Import Path**: `src.core.sv_engine.SVEngine` (from Ling repo)
- **Methods**: `embed(audio, sample_rate)` → L2-normalized vector
- **Threshold**: 0.38 (cosine similarity)
- **Implementation**: `backend/app/integrations/ling_sv_adapter.py`
- **Degradation**: Returns `engine_available=False` when dependencies missing

## SDKs

### @webling/sdk (JavaScript)
- **Purpose**: Bare JS client for Node.js/Deno consumers
- **Location**: `packages/sdk-js/`
- **Output**: ESM module

### @webling/embed (Embeddable Widget)
- **Purpose**: Script tag / Custom Element / iframe embedding
- **Location**: `packages/embed/`
- **Output**: UMD + ESM bundles (planned M8)

## Authentication & Authorization

### JWT Authentication
- **Library**: python-jose (HS256)
- **Secret**: `JWT_SECRET` environment variable
- **Token Types**:
  - `embed`: Short-lived tokens for third-party embeds (1 hour default)
  - `access`: User access tokens (1 hour default)
  - `refresh`: Refresh tokens (24 hours default)
- **Implementation**: `backend/app/services/auth_service.py`
- **Middleware**: `backend/app/middlewares/auth.py`

### API Key Authentication
- **Header**: `X-API-Key`
- **Purpose**: Embed token issuance
- **Validation**: Against tenants.json (planned)

## WebSocket Connections

### Chat WebSocket
- **Endpoint**: `ws://{host}/ws/chat`
- **Protocol**: JSON messages
- **Features**:
  - Streaming LLM responses
  - TTS audio segments
  - Emotion tags
  - Lipsync data
- **Implementation**: `backend/app/ws/chat_ws.py`
- **Client**: `packages/core/src/ws/client.ts`

## Data Storage

### MongoDB Collections
- **Database**: `MONGO_DB` (default: `webling`)
- **Collections**:
  - `sessions`: Chat session data
  - `speakers`: Voiceprint embeddings
  - `tenants`: Multi-tenant configuration (planned)
- **Drivers**: pymongo (sync), motor (async)
- **Connection**: `MONGO_URI` environment variable

### File Storage
- **TTS Cache**: `backend/app/static/tts/` (WAV files)
- **Static Files**: Served at `/static/` endpoint
- **TTL**: Configurable via `TTS_CACHE_TTL_SECONDS`

## Environment Configuration

### Backend Variables
```bash
# Runtime
WEBLING_ENV=development          # Environment mode
WEBLING_HOST=0.0.0.0            # Server host
WEBLING_PORT=8000               # Server port
WEBLING_CORS_ORIGINS=http://localhost:5173

# Ling Integration
LING_REPO_PATH=/path/to/Ling   # Ling repository path

# LLM
LLM_BASE_URL=http://...        # OpenAI-compatible endpoint
LLM_API_KEY=...                # API key
LLM_MODEL=MiniMax-M2.5         # Model name

# TTS
TTS_BASE_URL=http://...        # CosyVoice endpoint
TTS_DEFAULT_SPK_ID=            # Default speaker ID
TTS_CACHE_DIR=backend/app/static/tts
TTS_CACHE_TTL_SECONDS=3600

# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB=webling

# Auth
JWT_SECRET=change-me-in-prod
JWT_ALGORITHM=HS256
JWT_EMBED_TTL_SECONDS=3600
JWT_REFRESH_TTL_SECONDS=86400

# Rate Limiting
RATE_LIMIT_PER_MIN=60
QUOTA_PER_DAY=2000
```

### Frontend Variables
```bash
VITE_API_BASE=http://localhost:8000   # Backend API URL
VITE_WS_BASE=ws://localhost:8000      # WebSocket URL
```

## CI/CD Pipeline

### GitHub Actions (`ci.yml`)
- **Triggers**: Push/PR to `main` and `develop`
- **Frontend Job**:
  - pnpm install
  - Format check (Prettier)
  - Typecheck (vue-tsc)
  - Test (Vitest)
  - Build (Vite)
- **Backend Job**:
  - Python 3.12 setup
  - Install with dev dependencies
  - Lint (Ruff)
  - Type check (mypy)
  - Test (pytest with MongoDB service)

## External Dependencies at Risk

| Dependency | Risk | Mitigation |
|------------|------|------------|
| Ling Repository | Not packaged, injected via sys.path | Graceful degradation when unavailable |
| CosyVoice TTS | External HTTP service | Echo fallback on failure |
| LLM API | External HTTP service | Echo stub when unreachable |
| SVEngine (torch/funasr) | Heavy optional dependencies | Lazy loading, `engine_available=False` fallback |

---

*Integration audit: 2026-04-23*
