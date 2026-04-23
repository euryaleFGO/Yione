# System Architecture

**Analysis Date:** 2026-04-23

## Pattern Overview

**Overall:** Monorepo with layered packages, event-driven WebSocket streaming, and singleton service pattern

**Key Characteristics:**
- Pure logic packages (`@webling/core`) decoupled from DOM/runtime
- Real-time streaming via WebSocket with cancelable turn-based conversation
- Backend uses singleton services with dependency injection via FastAPI Depends
- Audio pipeline: LLM streaming → sentence segmentation → TTS synthesis → audio queue → Live2D lipsync

## Layers

**Frontend (Vue 3 SPA):**
- Purpose: User interface with chat panel and Live2D avatar
- Location: `apps/web/src/`
- Contains: Vue components, Pinia stores, router, client wrappers
- Depends on: `@webling/core`, `@webling/live2d-kit`
- Used by: End users

**Package Layer (Shared Libraries):**
- Purpose: Reusable logic shared across frontend and future embed scenarios
- Location: `packages/`
- Contains: Pure TS logic, Vue components, Live2D rendering, embed SDK
- Depends on: Nothing (core) → `@webling/core` (live2d-kit, ui, embed)
- Used by: `apps/web`, future embed consumers

**Backend (FastAPI):**
- Purpose: API server, WebSocket handler, LLM/TTS proxy
- Location: `backend/app/`
- Contains: Routers, services, repositories, schemas, domain models
- Depends on: External LLM, CosyVoice TTS, MongoDB
- Used by: Frontend via HTTP/WS

**External Services:**
- Purpose: LLM inference, TTS synthesis, data persistence
- Location: External (configured via env vars)
- Contains: MiniMax LLM, CosyVoice TTS, MongoDB
- Depends on: N/A
- Used by: Backend services

## Data Flow

**Chat Message Flow (WebSocket):**

1. User types message in `InputBar.vue` → calls `chat.submit(text, 'ws')`
2. `chat.ts` store sends via `ChatSocket.sendUserMessage(text)`
3. Backend `chat_ws.py` receives `user_message` event
4. Creates async Task for `_handle_user_message()`:
   - Sends `StateEvent(processing)` to frontend
   - Calls `AgentService.stream_reply()` → LLM streaming
   - For each chunk: strips emotion tags, emits `SubtitleEvent`
   - When sentence complete: queues to TTS worker
5. TTS worker calls `TTSService.synth_stream()`:
   - Enqueues text to CosyVoice
   - Polls for audio segments
   - Saves WAV to `backend/app/static/tts/`
   - Emits `AudioEvent(url, segment_idx, sample_rate)`
6. Frontend receives events:
   - `subtitle` → updates streaming message in chat
   - `audio` → enqueues to `AudioQueue`
   - `motion` → triggers Live2D motion via `AvatarControls.playMotion()`
7. `AudioQueue` dispatches segments to `AvatarStage.speak()`:
   - Uses `pixi-live2d-display-lipsyncpatch` for audio + lipsync
   - Drives `ParamMouthOpenY` automatically

**REST Fallback Flow:**

1. User sends via `ChatApi.send(sessionId, text)`
2. Backend `chat.py` router calls `AgentService.reply_text()`
3. Returns `ChatReply(reply, emotion, motion)`
4. Frontend pushes to messages array

**Session Lifecycle:**

1. Frontend calls `POST /api/sessions` → creates session with greeting
2. Opens WebSocket to `/ws/chat?session_id=...`
3. Session persists in memory until disconnect
4. Future: MongoDB-backed sessions in M7

## Key Abstractions

**WebSocket Protocol (`packages/core/src/types/ws.ts` + `backend/app/schemas/ws.py`):**
- Purpose: Shared type definitions for client↔server events
- Examples: `UserMessageEvent`, `SubtitleEvent`, `AudioEvent`, `MotionEvent`
- Pattern: Discriminated union on `type` field

**AudioQueue (`packages/core/src/audio/queue.ts`):**
- Purpose: FIFO ordering of TTS segments with out-of-order handling
- Examples: Enqueues segments by `segment_idx`, drains in order
- Pattern: Producer-consumer with async drain loop

**AvatarStage (`packages/live2d-kit/src/stage.ts`):**
- Purpose: PIXI Application + Live2D model lifecycle management
- Examples: `mount()`, `speak()`, `playMotion()`, `unmount()`
- Pattern: Stateful wrapper with graceful degradation

**HttpClient (`packages/core/src/api/http.ts`):**
- Purpose: Typed fetch wrapper with auth token injection
- Examples: `get<T>()`, `post<T>()`, automatic Bearer header
- Pattern: Decorator over native fetch

## Entry Points

**Frontend Entry:**
- Location: `apps/web/src/main.ts`
- Triggers: Browser loads SPA
- Responsibilities: Creates Vue app, installs Pinia + router, mounts to DOM

**Backend Entry:**
- Location: `backend/app/main.py`
- Triggers: `uvicorn app.main:app`
- Responsibilities: Creates FastAPI app, configures CORS, mounts routers, initializes services

**WebSocket Endpoint:**
- Location: `backend/app/ws/chat_ws.py`
- Triggers: Client connects to `/ws/chat?session_id=...`
- Responsibilities: Manages turn state, coordinates LLM→TTS pipeline, handles cancel/interrupt

## Error Handling

**Strategy:** Graceful degradation with echo fallbacks

**Patterns:**
- LLM unreachable → `AgentService` returns echo stub message
- TTS failure → emits `ErrorEvent`, continues conversation
- Live2D missing → shows placeholder UI, chat still works
- WebSocket disconnect → cancels active turn, cleans up resources
- Cubism Core missing → `AvatarStage` stays in `cubism_missing` state

## Cross-Cutting Concerns

**Logging:** Python `logging` module, structured with timestamps and context

**Validation:** Pydantic models for all API schemas and WebSocket events

**Authentication:**
- JWT tokens for embed scenarios (`POST /api/embed/token`)
- Dev mode allows anonymous access
- WebSocket auth via query parameter token

**Configuration:** Pydantic Settings with `.env` file support, `WEBLING_` prefix for env vars

## Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Vue 3 SPA)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Pinia       │  │  Components │  │  @webling/*          │ │
│  │  Stores      │  │  (Vue)      │  │  Packages            │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                     │             │
│         └────────────────┼─────────────────────┘             │
│                          │                                   │
│                    ┌─────▼─────┐                             │
│                    │  WebSocket │                             │
│                    │  Client    │                             │
│                    └─────┬─────┘                             │
└──────────────────────────┼───────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │   FastAPI    │
                    │   Backend    │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
   ┌─────▼─────┐    ┌─────▼─────┐    ┌─────▼─────┐
   │    LLM     │    │    TTS    │    │  MongoDB  │
   │  (MiniMax) │    │(CosyVoice)│    │           │
   └───────────┘    └───────────┘    └───────────┘
```

## Dependency Graph (Packages)

```
@webling/core          (no deps - pure logic)
    ↑
@webling/live2d-kit    (depends on core)
    ↑
@webling/ui            (depends on core, live2d-kit)
    ↑
@webling/embed         (depends on core, live2d-kit, ui)

@webling/sdk-js        (no deps - standalone client)

apps/web               (depends on core, live2d-kit, ui)
```

---

*Architecture analysis: 2026-04-23*
