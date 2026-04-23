# Codebase Structure

**Analysis Date:** 2026-04-23

## Directory Layout

```
webLing/
├── apps/
│   └── web/                    # Main Vue 3 SPA
├── packages/
│   ├── core/                   # Pure logic (chat/ws/audio/auth/types)
│   ├── live2d-kit/             # Live2D rendering wrapper
│   ├── ui/                     # Vue component library
│   ├── embed/                  # Embed SDK (Script/WC/iframe)
│   └── sdk-js/                 # Bare JS client for Node.js
├── backend/
│   └── app/                    # FastAPI backend
├── docs/                       # ADR, integration guides, API docs
├── scripts/                    # Model copying, initialization, dev startup
├── .planning/                  # Project planning and documentation
│   └── codebase/               # Architecture and structure docs
├── package.json                # Root workspace config
├── pnpm-workspace.yaml         # Workspace definition
└── turbo.json                  # Turborepo task config
```

## Directory Purposes

**apps/web:**
- Purpose: Main SPA application
- Contains: Vue components, stores, router, views, assets
- Key files: `src/main.ts`, `src/App.vue`, `src/stores/chat.ts`

**packages/core:**
- Purpose: Pure TypeScript logic, no DOM dependencies
- Contains: HTTP client, WebSocket client, audio queue, type definitions
- Key files: `src/api/http.ts`, `src/ws/client.ts`, `src/audio/queue.ts`

**packages/live2d-kit:**
- Purpose: Live2D rendering with PIXI.js
- Contains: AvatarStage, lipsync driver, motion controller, Cubism Core loader
- Key files: `src/stage.ts`, `src/lipsync.ts`, `src/cubism-core.ts`

**packages/ui:**
- Purpose: Reusable Vue components (currently empty, M1+ will populate)
- Contains: Components, composables, styles
- Key files: `src/index.ts` (placeholder)

**packages/embed:**
- Purpose: Embed SDK for third-party integration
- Contains: Script tag, Custom Element, iframe implementations
- Key files: `src/index.ts` (placeholder for M8/M9)

**packages/sdk-js:**
- Purpose: Bare JS client for Node.js/Deno consumers
- Contains: API client for backend REST endpoints
- Key files: `src/index.ts` (minimal stub)

**backend/app:**
- Purpose: FastAPI API server
- Contains: Routers, services, repositories, schemas, WebSocket handlers
- Key files: `main.py`, `config.py`, `ws/chat_ws.py`

**backend/app/routers:**
- Purpose: HTTP endpoint definitions
- Contains: `chat.py`, `sessions.py`, `tts.py`, `embed.py`, `speakers.py`, `health.py`
- Key files: Each router file defines API routes

**backend/app/services:**
- Purpose: Business logic layer
- Contains: `agent_service.py`, `tts_service.py`, `session_service.py`, `auth_service.py`, `emotion_service.py`, `motion_map.py`, `speaker_service.py`
- Key files: Each service is a singleton with `get_*_service()` factory

**backend/app/ws:**
- Purpose: WebSocket handling
- Contains: `chat_ws.py` (main WS endpoint), `connections.py` (connection registry)
- Key files: `chat_ws.py` implements the full LLM→TTS streaming pipeline

**backend/app/schemas:**
- Purpose: Pydantic models for validation
- Contains: `chat.py`, `ws.py`, `speaker.py`
- Key files: `ws.py` mirrors `packages/core/src/types/ws.ts`

**backend/app/domain:**
- Purpose: Domain models
- Contains: `speaker.py` (Speaker entity with voiceprint)
- Key files: `speaker.py` defines core business entities

**backend/app/repositories:**
- Purpose: Data persistence layer
- Contains: `speaker_repo.py` (JSON file-based storage)
- Key files: `speaker_repo.py` implements CRUD operations

**backend/app/integrations:**
- Purpose: External service adapters
- Contains: `ling_adapter.py` (Ling repo injection), `ling_sv_adapter.py` (speaker verification), `audio_io.py` (WAV decoding)
- Key files: Each adapter handles one external dependency

**backend/app/middlewares:**
- Purpose: FastAPI middleware and dependencies
- Contains: `auth.py` (JWT validation, optional/required auth)
- Key files: `auth.py` provides `require_user`, `optional_user`, `require_scope`

**backend/app/static:**
- Purpose: Static file serving
- Contains: `tts/` directory for cached WAV files
- Key files: Generated at runtime by TTS service

## Key File Locations

**Entry Points:**
- `apps/web/src/main.ts`: Vue app bootstrap
- `backend/app/main.py`: FastAPI app creation and router mounting

**Configuration:**
- `package.json`: Root workspace scripts and dependencies
- `pnpm-workspace.yaml`: Workspace package locations
- `turbo.json`: Turborepo task pipeline
- `backend/app/config.py`: Backend settings (Pydantic Settings)
- `.env`: Environment variables (gitignored)
- `.env.example`: Environment variable template

**Core Logic:**
- `packages/core/src/api/http.ts`: HTTP client with auth
- `packages/core/src/ws/client.ts`: WebSocket client with reconnect
- `packages/core/src/audio/queue.ts`: Audio segment queue
- `packages/core/src/types/ws.ts`: WebSocket protocol types
- `packages/live2d-kit/src/stage.ts`: Live2D avatar stage
- `backend/app/ws/chat_ws.py`: WebSocket chat handler
- `backend/app/services/agent_service.py`: LLM integration
- `backend/app/services/tts_service.py`: TTS proxy

**Testing:**
- `packages/core/tests/`: Core package tests
- `packages/live2d-kit/tests/`: Live2D kit tests
- `packages/ui/tests/`: UI component tests
- `packages/embed/tests/`: Embed SDK tests
- `packages/sdk-js/tests/`: SDK client tests
- `backend/tests/`: Backend tests (unit + integration)

## Naming Conventions

**Files:**
- TypeScript: camelCase (`chatApi.ts`, `audioQueue.ts`)
- Vue: PascalCase (`ChatView.vue`, `AvatarStage.vue`)
- Python: snake_case (`chat_ws.py`, `agent_service.ts`)

**Directories:**
- Packages: kebab-case (`live2d-kit`, `sdk-js`)
- Backend modules: snake_case (`routers/`, `services/`)
- Frontend modules: camelCase (`stores/`, `composables/`)

**Exports:**
- Packages: Use barrel files (`index.ts`) for public API
- Backend services: Singleton pattern with `get_*_service()` factory
- Vue components: Default export with `<script setup>`

## Where to Add New Code

**New Feature (Frontend):**
- Primary code: `apps/web/src/views/` or `apps/web/src/components/`
- Store: `apps/web/src/stores/`
- Composable: `apps/web/src/composables/`
- Tests: Co-located or in package `tests/`

**New Feature (Backend):**
- Router: `backend/app/routers/`
- Service: `backend/app/services/`
- Schema: `backend/app/schemas/`
- Repository: `backend/app/repositories/`
- Tests: `backend/tests/`

**New Package:**
- Implementation: `packages/<name>/src/`
- Package config: `packages/<name>/package.json`
- Tests: `packages/<name>/tests/`
- Update: `pnpm-workspace.yaml` (auto-included via `packages/*`)

**New Shared Logic:**
- Pure logic (no DOM): `packages/core/src/`
- Vue components: `packages/ui/src/components/`
- Vue composables: `packages/ui/src/composables/`

**Utilities:**
- Shared helpers: `packages/core/src/` (if pure logic)
- Backend utils: `backend/app/services/` or new `backend/app/utils/`

## Special Directories

**backend/app/static/tts:**
- Purpose: Cached TTS audio files
- Generated: Yes (at runtime by TTSService)
- Committed: No (gitignored)

**.planning:**
- Purpose: Project planning, roadmaps, codebase docs
- Generated: Partially (codebase docs are generated)
- Committed: Yes

**node_modules:**
- Purpose: Installed dependencies
- Generated: Yes (by pnpm install)
- Committed: No (gitignored)

**.venv:**
- Purpose: Python virtual environment
- Generated: Yes (by python -m venv)
- Committed: No (gitignored)

## Package Dependencies

```
@webling/core
├── No runtime dependencies
├── Dev: typescript, vitest
└── Exports: HttpClient, ChatApi, ChatSocket, AudioQueue, types

@webling/live2d-kit
├── Runtime: pixi.js 7.1.2, pixi-live2d-display-lipsyncpatch 0.5.0-ls-8
├── Peer: @webling/core
├── Dev: typescript, vitest
└── Exports: AvatarStage, AvatarConfig, AvatarControls, cubism-core, lipsync, motion

@webling/ui
├── Peer: @webling/core, @webling/live2d-kit, vue ^3.5.0
├── Dev: typescript, vitest, vue, vue-tsc
└── Exports: Components, composables (M1+ will populate)

@webling/embed
├── Peer: @webling/core, @webling/live2d-kit, @webling/ui
├── Dev: typescript, vitest
└── Exports: EMBED_VERSION (placeholder)

@webling/sdk
├── No runtime dependencies
├── Dev: typescript, vitest
└── Exports: WebLingClient (stub)
```

## Backend Module Structure

```
backend/app/
├── __init__.py
├── main.py                 # FastAPI app factory
├── config.py               # Pydantic Settings
├── routers/
│   ├── __init__.py
│   ├── chat.py             # POST /api/chat
│   ├── sessions.py         # POST/GET /api/sessions
│   ├── tts.py              # TTS endpoints
│   ├── embed.py            # Embed token endpoints
│   ├── speakers.py         # Speaker management
│   └── health.py           # GET /api/health
├── services/
│   ├── __init__.py
│   ├── agent_service.py    # LLM integration (OpenAI-compatible)
│   ├── tts_service.py      # CosyVoice TTS proxy
│   ├── session_service.py  # In-memory session store
│   ├── auth_service.py     # JWT issuance/validation
│   ├── emotion_service.py  # Emotion detection (tags + keywords)
│   ├── motion_map.py       # Emotion → Live2D motion mapping
│   ├── speaker_service.py  # Speaker registration/identification
│   └── tenant_service.py   # Multi-tenant support (M6)
├── schemas/
│   ├── __init__.py
│   ├── chat.py             # Chat request/response models
│   ├── ws.py               # WebSocket event schemas
│   └── speaker.py          # Speaker schemas
├── domain/
│   ├── __init__.py
│   └── speaker.py          # Speaker entity with voiceprint
├── repositories/
│   ├── __init__.py
│   └── speaker_repo.py     # JSON file-based speaker storage
├── integrations/
│   ├── __init__.py
│   ├── ling_adapter.py     # Ling repo sys.path injection
│   ├── ling_sv_adapter.py  # Speaker verification adapter
│   └── audio_io.py         # WAV decoding utilities
├── middlewares/
│   ├── __init__.py
│   └── auth.py             # Auth dependencies (optional/require/scope)
├── ws/
│   ├── __init__.py
│   ├── chat_ws.py          # WebSocket chat endpoint
│   └── connections.py      # WS connection registry
├── data/
│   └── tenants.example.json
└── static/
    └── tts/                # Cached TTS audio files
```

## Configuration Files

**Root Level:**
- `package.json`: Workspace scripts (`dev`, `build`, `lint`, `test`)
- `pnpm-workspace.yaml`: Defines `packages/*` and `apps/*` as workspaces
- `turbo.json`: Task pipeline with dependency ordering
- `tsconfig.base.json`: Shared TypeScript config
- `.prettierrc`: Prettier formatting rules
- `.eslintrc.cjs`: ESLint configuration
- `.editorconfig`: Editor settings
- `.lefthook.yml`: Git hooks (pre-commit, pre-push)
- `.nvmrc`: Node.js version (currently v20)
- `.env.example`: Environment variable template

**Backend:**
- `backend/pyproject.toml`: Python project config (implied by setup)
- `backend/requirements.txt` or `pyproject.toml`: Python dependencies
- `backend/.env`: Backend-specific env vars (gitignored)

**Packages:**
- Each package has its own `package.json` and `tsconfig.json`
- Build configs: `tsconfig.build.json` in each package

---

*Structure analysis: 2026-04-23*
