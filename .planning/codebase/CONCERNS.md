# Codebase Concerns

**Analysis Date:** 2026-04-23

## Tech Debt

### Hardcoded Default Secrets and Credentials

- **Issue**: JWT secret and LLM API key have insecure default values that could accidentally be used in production
- **Files**: `backend/app/config.py:40`, `backend/app/config.py:54`
- **Impact**: If environment variables aren't set, the app runs with `jwt_secret="change-me-in-prod"` and `llm_api_key="dummy"`, creating severe security vulnerabilities
- **Fix approach**: Remove default values for sensitive fields; fail fast if not configured, or use conditional defaults based on `env`

### Hardcoded Local Paths

- **Issue**: Default `ling_repo_path` is a hardcoded absolute path to a specific developer's machine
- **Files**: `backend/app/config.py:33-36`
- **Impact**: Will fail silently or confusingly on any other machine; makes onboarding harder
- **Fix approach**: Default to empty string or auto-detect based on environment; add validation in lifespan

### In-Memory Session Storage (No Persistence)

- **Issue**: Sessions are stored in a plain Python dict — lost on restart, no multi-worker support
- **Files**: `backend/app/services/session_service.py:1-43`
- **Impact**: All sessions vanish on server restart; cannot scale horizontally; no conversation history persistence
- **Fix approach**: Migrate to MongoDB (planned for M7)

### No Conversation History Passed to LLM

- **Issue**: Each LLM call only sends the current user message, not conversation history
- **Files**: `backend/app/services/agent_service.py:57-66`
- **Impact**: LLM has no memory of prior turns in the conversation — responses are stateless
- **Fix approach**: Pass recent message history in `messages` array; M4+ plans Agent with memory/RAG

### Duplicate Type Definitions (TS ↔ Python)

- **Issue**: WebSocket event types are defined independently in TypeScript and Python with no automated consistency check
- **Files**: `packages/core/src/types/ws.ts` vs `backend/app/schemas/ws.py`
- **Impact**: Types can drift silently; breaking changes may not be caught until runtime
- **Fix approach**: Add CI check (planned for M4); or generate one from the other using a shared schema

### Stub Packages with No Implementation

- **Issue**: `embed`, `sdk-js`, and `ui` packages are empty stubs
- **Files**: `packages/embed/src/index.ts`, `packages/sdk-js/src/index.ts`, `packages/ui/src/index.ts`
- **Impact**: Dead code in repo; workspace dependencies reference them but they export nothing useful
- **Fix approach**: Implement in M8/M9 or remove from workspace until ready

### Dead Dependency: `reconnecting-websocket`

- **Issue**: Listed in `apps/web/package.json` but never imported — the project reimplements its own `ChatSocket` with reconnect logic
- **Files**: `apps/web/package.json:18`, `packages/core/src/ws/client.ts`
- **Impact**: Adds unnecessary install weight; confusing for developers
- **Fix approach**: Remove from dependencies

### No TTS Audio Cache Cleanup

- **Issue**: TTS wav files are written to disk but never cleaned up
- **Files**: `backend/app/services/tts_service.py:183-189`
- **Impact**: Disk usage grows unbounded; `static/tts/` directory will accumulate files indefinitely
- **Fix approach**: M11 plans a TTL sweeper; interim: add a simple scheduled cleanup or size cap

### Dev Mode Auth Bypass is Too Permissive

- **Issue**: In development/test mode, `require_user` returns a hardcoded anonymous token with `exp=2^31-1` (year 2038), bypassing all auth
- **Files**: `backend/app/middlewares/auth.py:53-62`, `backend/app/middlewares/auth.py:28-30`
- **Impact**: Easy to accidentally deploy with `WEBLING_ENV=development` and have zero auth
- **Fix approach**: Add startup warning; consider a separate `DEV_AUTH_BYPASS` flag that must be explicitly enabled

### No Input Validation on WebSocket Messages

- **Issue**: WebSocket message parsing uses pydantic but the error handling just sends an error event and continues — no rate limiting or abuse protection
- **Files**: `backend/app/ws/chat_ws.py:346-349`
- **Impact**: Malicious client could flood the server with invalid messages or rapid-fire user messages
- **Fix approach**: Add per-connection rate limiting; add message size limits; consider disconnecting after N consecutive errors

### `isServerEvent` Type Guard is Weak

- **Issue**: The TypeScript type guard only checks `typeof value === 'object' && 'type' in value` — doesn't validate the actual event structure
- **Files**: `packages/core/src/types/ws.ts:48-54`
- **Impact**: Malformed server events pass the guard and could cause runtime errors in event handlers
- **Fix approach**: Add discriminant validation per event type, or use a runtime schema validator (zod)

### Ling Adapter Uses `sys.path` Injection

- **Issue**: Imports from the Ling repo are done by prepending its path to `sys.path` at runtime, with a `type: ignore` on the import
- **Files**: `backend/app/integrations/ling_adapter.py:33-34`, `backend/app/integrations/ling_sv_adapter.py:73`
- **Impact**: Fragile — no type checking, no version pinning, path resolution depends on filesystem layout
- **Fix approach**: Package Ling as a proper Python dependency, or use a plugin interface with protocol classes

### Singleton Services with Mutable Global State

- **Issue**: Most backend services use a module-level `_singleton` pattern with `global` keyword — not thread-safe, hard to test without monkey-patching
- **Files**: `backend/app/services/agent_service.py:141-148`, `backend/app/services/tts_service.py:196-203`, `backend/app/services/session_service.py:36-43`, `backend/app/services/tenant_service.py:129-136`, `backend/app/services/speaker_service.py:222-229`, `backend/app/ws/connections.py:56-63`
- **Impact**: Testing requires explicit `set_*_for_tests()` calls; potential race conditions under async; state leaks between test cases
- **Fix approach**: Use FastAPI dependency injection properly; or at least use an async-safe initialization pattern

## Known Bugs

### httpx Clients Never Closed

- **Symptoms**: Resource leak warnings; potential connection pool exhaustion under load
- **Files**: `backend/app/services/agent_service.py:50-55`, `backend/app/services/tts_service.py:66`
- **Trigger**: Long-running server process with many LLM/TTS calls
- **Workaround**: Restart the server periodically

### `audio_rms` and `viseme` Events Defined But Never Emitted

- **Symptoms**: Frontend receives these event types but has no handlers; events silently dropped
- **Files**: `backend/app/schemas/ws.py:105-115`, `packages/core/src/types/ws.ts:36-37`
- **Trigger**: Should never trigger since server never sends them, but they clutter the protocol
- **Workaround**: None needed yet; clean up when implementing or remove

### `_OPENAI_CHAT_AGENT._client` Never Cleaned Up

- **Symptoms**: If `AgentService` is replaced (e.g., in tests), the old httpx client leaks
- **Files**: `backend/app/services/agent_service.py:50-55`
- **Trigger**: Test teardown, or hot-swapping agent config
- **Workaround**: Restart process

## Security Considerations

### JWT Secret Default is Insecure

- **Risk**: `jwt_secret` defaults to `"change-me-in-prod"` — if `.env` is missing, tokens are signed with a known secret
- **Files**: `backend/app/config.py:54`
- **Current mitigation**: Relies on developers setting the env var
- **Recommendations**: Fail startup if `JWT_SECRET` is the default value and `WEBLING_ENV != "development"`

### Tenant Dev Fallback Accepts Any Key

- **Risk**: When `tenants.json` doesn't exist, any API key is accepted and returns a demo tenant
- **Files**: `backend/app/services/tenant_service.py:74-81`, `backend/app/services/tenant_service.py:106-126`
- **Current mitigation**: Warning log message; only activates when file is missing
- **Recommendations**: Make this opt-in via a `DEV_ACCEPT_ANY_KEY` flag; fail closed in production

### No Rate Limiting on Embed Token Endpoint

- **Risk**: `POST /api/embed/token` has no rate limiting — an attacker could brute-force API keys
- **Files**: `backend/app/routers/embed.py:34-66`
- **Current mitigation**: API key is hashed (SHA-256), so brute-forcing is slow but not impossible
- **Recommendations**: Add rate limiting per IP; add account lockout after N failures

### WebSocket Auth Bypass in Dev Mode

- **Risk**: `decode_ws_token` returns `None` (no auth) when token is missing and `env` is development
- **Files**: `backend/app/middlewares/auth.py:94-105`
- **Current mitigation**: Only active in dev/test mode
- **Recommendations**: Same as above — ensure production uses `WEBLING_ENV=production`

### Static TTS Files World-Readable

- **Risk**: TTS audio files are served from `/static/tts/` with no auth; anyone with the URL can access them
- **Files**: `backend/app/main.py:47-49`, `backend/app/services/tts_service.py:183-189`
- **Current mitigation**: URLs contain UUIDs (hard to guess); no sensitive data in audio (currently)
- **Recommendations**: If TTS content becomes sensitive, add auth to static file serving or use signed URLs

## Performance Bottlenecks

### TTS Polling Loop is Synchronous-Blocking

- **Problem**: `synth_stream` polls `GET /tts/dequeue` in a loop with 10s timeout per poll
- **Files**: `backend/app/services/tts_service.py:130-193`
- **Cause**: The CosyVoice protocol is poll-based; no WebSocket or SSE alternative
- **Improvement path**: Add a circuit breaker; reduce poll timeout; consider a separate async worker per TTS job

### No Connection Pooling for TTS/LLM Clients

- **Problem**: Each `TTSService` and `_OpenAIChatAgent` creates a single httpx client; no pool size tuning
- **Files**: `backend/app/services/tts_service.py:66`, `backend/app/services/agent_service.py:54`
- **Cause**: httpx defaults are used
- **Improvement path**: Configure pool limits based on expected concurrency; add health checks

### Session Service is In-Memory Only

- **Problem**: All session data is lost on restart; no horizontal scaling possible
- **Files**: `backend/app/services/session_service.py`
- **Cause**: M1 placeholder; Mongo migration planned for M7
- **Improvement path**: Migrate to MongoDB repository pattern (follow `speaker_repo.py` pattern)

## Fragile Areas

### Emotion Detection (Keyword-Based)

- **Files**: `backend/app/services/emotion_service.py:31-54`
- **Why fragile**: Keyword matching is brittle — misses synonyms, sarcasm, context-dependent emotions; keyword list is hardcoded and Chinese-focused
- **Safe modification**: Add keywords to `_KEYWORDS` dict; don't change `detect()` logic until classifier is ready
- **Test coverage**: No tests found for `emotion_service.py`

### Sentence Splitting in WebSocket Handler

- **Files**: `backend/app/ws/chat_ws.py:70-98`
- **Why fragile**: Regex-based sentence splitting (`_SENTENCE_END`, `_SOFT_BREAK`) with magic number thresholds; edge cases with mixed punctuation or emoji could cause incorrect splits
- **Safe modification**: Tune `_SOFT_BREAK_AFTER` and `_MIN_SENTENCE_CHARS` carefully; test with diverse LLM outputs
- **Test coverage**: `backend/tests/unit/test_chat_flow.py` exists but may not cover edge cases

### Live2D Stage Initialization

- **Files**: `packages/live2d-kit/src/stage.ts:111-200`
- **Why fragile**: Complex initialization chain: Cubism Core check → dynamic PIXI import → model load → resize observer; any step failing silently degrades the experience
- **Safe modification**: Always test the `cubism_missing` and `error` paths; don't remove fallback states
- **Test coverage**: `packages/live2d-kit/tests/cubism-core.test.ts` exists but stage tests are missing

### Voiceprint Vector Merging

- **Files**: `backend/app/domain/speaker.py:42-57`
- **Why fragile**: Weighted average merge assumes vectors are L2-normalized; dimension mismatch raises ValueError but doesn't prevent data corruption if caught incorrectly
- **Safe modification**: Always validate dimensions before merge; ensure callers handle ValueError
- **Test coverage**: `backend/tests/unit/test_speaker_domain.py` exists

## Scaling Limits

### In-Memory State (Sessions + WS Connections)

- **Current capacity**: Single process, ~thousands of concurrent sessions
- **Limit**: Cannot horizontally scale; all state lost on restart
- **Scaling path**: MongoDB for sessions; Redis pub/sub for WS broadcasts (planned M14)

### JSON File Storage (Tenants + Speakers)

- **Current capacity**: Fine for <100 records
- **Limit**: File locking contention under concurrent writes; full rewrite on every save
- **Scaling path**: MongoDB repositories (planned M7)

### TTS File Storage on Local Disk

- **Current capacity**: Limited by disk space; no cleanup
- **Limit**: Disk fills up over time
- **Scaling path**: Object storage (S3/MinIO) + CDN; TTL sweeper (M11)

## Dependencies at Risk

### `pixi-live2d-display-lipsyncpatch` (Fork)

- **Risk**: Community fork (`0.5.0-ls-8`) of `pixi-live2d-display`; may not receive upstream updates
- **Impact**: If the fork is abandoned, lipsync support may break with new PIXI/Live2D versions
- **Migration plan**: Monitor upstream `pixi-live2d-display` for native lipsync support; or maintain the fork

### `pixi.js` 7.1.2 (Pinned Older Version)

- **Risk**: Pinned to 7.1.2 while current is 7.4.2; may miss security patches
- **Impact**: Potential vulnerabilities; compatibility issues with newer browser APIs
- **Migration plan**: Test upgrade to 7.4.2; check `pixi-live2d-display-lipsyncpatch` compatibility

### Cubism Core (Manual Install Required)

- **Risk**: `live2dcubismcore.min.js` must be manually downloaded (license prohibits npm distribution)
- **Impact**: Onboarding friction; version drift if developers use different SDK versions
- **Migration plan**: Document exact SDK version in `scripts/fetch-cubism-core.sh`; consider CI artifact

## Missing Critical Features

### Conversation Memory

- **Problem**: LLM has no context of previous messages in the session
- **Blocks**: Natural multi-turn conversation; user experience is degraded

### Proper Error Boundaries

- **Problem**: Frontend has no global error handler; errors are shown as raw text in the status bar
- **Blocks**: User-friendly error recovery; graceful degradation

### Multi-Character Support

- **Problem**: Only Hiyori is supported; character picker, motion maps, and avatar configs are single-character
- **Blocks**: M7 goals; extensibility

## Test Coverage Gaps

### No Backend Integration Tests

- **What's not tested**: End-to-end flow: REST API → service → LLM → TTS → WS events
- **Files**: `backend/tests/unit/` contains only unit tests
- **Risk**: Integration issues between services go undetected
- **Priority**: High

### No Frontend Tests at All

- **What's not tested**: Vue components, Pinia stores, WebSocket client behavior
- **Files**: `apps/web/` has `vitest` configured but no test files found
- **Risk**: UI regressions undetected; store logic bugs
- **Priority**: High

### No Live2D Stage Tests

- **What's not tested**: `packages/live2d-kit/src/stage.ts` — the 302-line core rendering class
- **Files**: Only `cubism-core.test.ts` exists
- **Risk**: Rendering regressions; resize/scale bugs; memory leaks on unmount
- **Priority**: Medium

### Emotion Service Untested

- **What's not tested**: Keyword matching, tag stripping, edge cases
- **Files**: `backend/app/services/emotion_service.py`
- **Risk**: Emotion detection bugs silently degrade UX
- **Priority**: Medium

### TTS Service Untested

- **What's not tested**: Polling loop, error handling, segment parsing
- **Files**: `backend/app/services/tts_service.py`
- **Risk**: TTS failures may not surface correctly to the frontend
- **Priority**: Medium

---

*Concerns audit: 2026-04-23*
