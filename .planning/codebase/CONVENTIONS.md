# Coding Conventions

**Analysis Date:** 2026-04-23

## Formatting

**Frontend (TypeScript/Vue):**
- Prettier config: `.prettierrc`
  - Semi: true
  - Single quotes: true
  - Trailing commas: all
  - Print width: 100
  - Tab width: 2
  - Arrow parens: always
  - End of line: lf
- ESLint: `.eslintrc.cjs` (root)
  - `no-console: warn` (allow warn/error)
  - `no-debugger: error`
  - Ignores: `node_modules`, `dist`, `.turbo`, `coverage`, `backend`, `*.d.ts`

**Backend (Python):**
- Ruff: `backend/pyproject.toml`
  - Line length: 100
  - Target: Python 3.12
  - Rules: E, F, W, I (isort), B (bugbear), UP (pyupgrade), SIM (simplify), RUF
  - Format: double quotes
- Mypy: strict mode, Python 3.12
- EditorConfig: `.editorconfig`
  - All files: UTF-8, LF, 2-space indent
  - Python/Markdown: 4-space indent
  - Makefile: tab indent

## Naming Conventions

**Files:**
- TypeScript: `kebab-case` (e.g., `chat.ts`, `cubism-core.ts`, `avatar-config.ts`)
- Vue components: `PascalCase` (e.g., `AvatarStage.vue`, `InputBar.vue`, `MessageList.vue`)
- Python: `snake_case` (e.g., `agent_service.py`, `chat_ws.py`, `speaker_repo.py`)

**Directories:**
- TypeScript packages: `kebab-case` (e.g., `live2d-kit`, `sdk-js`)
- Python modules: `snake_case` (e.g., `app/services`, `app/routers`)
- Vue app: `camelCase` for some dirs (e.g., `composables/`), but mostly lowercase

**Functions/Methods:**
- TypeScript: `camelCase` (e.g., `createSession`, `sendUserMessage`, `ensureSession`)
- Python: `snake_case` (e.g., `create_app`, `get_settings`, `register_from_wav`)

**Variables:**
- TypeScript: `camelCase` (e.g., `streamingMessageId`, `reconnectDelay`)
- Python: `snake_case` (e.g., `wav_bytes`, `effective_threshold`)

**Constants:**
- TypeScript: `UPPER_SNAKE_CASE` for module-level constants (e.g., `DEFAULT_AVATAR`, `SYSTEM_PROMPT`)
- Python: `UPPER_SNAKE_CASE` (e.g., `BACKEND_ROOT`, `DEFAULT_PATH`, `SYSTEM_PROMPT`)

**Classes:**
- TypeScript: `PascalCase` (e.g., `ChatSocket`, `HttpClient`, `ChatApi`)
- Python: `PascalCase` (e.g., `AgentService`, `SpeakerService`, `JsonFileSpeakerRepo`)
- Private/internal: prefix with underscore (e.g., `_OpenAIChatAgent`, `_FakeAdapter`, `_ClientBase`)

**Interfaces/Types:**
- TypeScript: `PascalCase` (e.g., `ChatSocketOptions`, `Message`, `SessionSummary`)
- Python: `PascalCase` for Pydantic models (e.g., `ChatRequest`, `ChatResponse`)

**Enums/Unions:**
- TypeScript: Union types preferred over enums (e.g., `type AgentState = 'idle' | 'processing' | 'speaking' | 'listening'`)
- Python: `Literal` types (e.g., `Emotion = Literal["neutral", "joy", ...]`)

## Import Organization

**TypeScript:**
1. External packages (e.g., `import { defineStore } from 'pinia'`)
2. Internal packages with `@webling/` prefix (e.g., `import { AudioQueue } from '@webling/core'`)
3. Relative imports (e.g., `import { chatApi } from '@/lib/webling-clients'`)
4. Type imports use `import type` when possible

**Python:**
1. Standard library (e.g., `import json`, `from pathlib import Path`)
2. Third-party packages (e.g., `from fastapi import APIRouter`)
3. Local imports (e.g., `from app.config import get_settings`)
4. Use `from __future__ import annotations` at top of every file

## TypeScript Conventions

**Strict Mode:**
- `tsconfig.base.json`: `strict: true`
- Additional checks: `noUnusedLocals`, `noUnusedParameters`, `noImplicitOverride`, `noFallthroughCasesInSwitch`

**Interface vs Type:**
- Use `interface` for object shapes (e.g., `interface ChatSocketOptions`, `interface Message`)
- Use `type` for unions, primitives, and utility types (e.g., `type AgentState = 'idle' | 'processing' | 'speaking' | 'listening'`)

**Component Patterns:**
- Vue 3 Composition API with `<script setup lang="ts">`
- Props: `defineProps<{ ... }>()`
- Emits: `defineEmits<{ ... }>()`
- Expose: `defineExpose({ ... })`
- Reactive: `ref()`, `shallowRef()`, `computed()`

**Class Patterns:**
- Use `class` for stateful services (e.g., `ChatSocket`, `HttpClient`, `AgentService`)
- Constructor injection for dependencies (e.g., `constructor(private readonly opts: ChatSocketOptions)`)
- Private members with `private` keyword or `#` prefix
- Properties over getters when simple (e.g., `get isOpen(): boolean`)

## Python Conventions

**Type Hints:**
- All function signatures must have type hints
- Use `from __future__ import annotations` for forward references
- Modern syntax: `str | None` instead of `Optional[str]`
- Use `Literal` for constrained values (e.g., `Emotion = Literal["neutral", "joy", ...]`)

**Docstrings:**
- Every module has a docstring explaining its purpose
- Classes and public methods have docstrings
- Use Chinese comments for domain-specific explanations
- Use triple double quotes (`"""`)

**Import Order:**
- Follow isort rules (enforced by ruff `I` rule)
- Group: stdlib → third-party → local
- Alphabetical within groups

**Singleton Pattern:**
- Module-level `_singleton` variable
- `get_*()` function to access (e.g., `get_agent_service()`, `get_speaker_repo()`)
- `set_*_for_tests()` function for test injection (e.g., `set_speaker_service_for_tests()`)

**Dataclasses:**
- Use `@dataclass(slots=True)` for domain objects (e.g., `Speaker`, `IdentifyOutcome`)
- Use `@dataclass` for simple containers

**Pydantic:**
- Use `BaseModel` for request/response schemas
- Use `BaseSettings` for configuration
- Use `Field()` for validation and defaults
- Use `model_config = {"extra": "forbid"}` for strict schemas

## Git Conventions

**Commit Messages:**
- Not strictly enforced (no conventional commits)
- Chinese or English mixed
- Descriptive of changes

**Branch Naming:**
- `main` and `develop` branches
- Feature branches: descriptive names

**PR Format:**
- No formal template observed

## CSS/Styling

**Tailwind CSS:**
- Utility-first approach
- Inline classes in Vue templates
- No custom CSS modules observed
- Color palette: slate, indigo, amber, pink, sky, rose, violet, emerald, lime

**Class Naming:**
- Tailwind utilities in templates
- Conditional classes with `:class="[...]"` binding
- Emotion-based styling via lookup object (e.g., `EMOTION_CLASSES`)

## Package Structure

**Monorepo:**
- pnpm workspaces: `packages/*`, `apps/*`
- Turborepo for task orchestration
- Scoped packages: `@webling/core`, `@webling/live2d-kit`, `@webling/ui`, `@webling/embed`, `@webling/sdk`

**Package Exports:**
- All packages use `"type": "module"`
- Exports point to source: `"./src/index.ts"`
- Build outputs: `dist/**` (TypeScript compilation)

**Dependencies:**
- Workspace references: `"workspace:*"`
- Peer dependencies for shared packages
- Dev dependencies for build/test tools

---

*Convention analysis: 2026-04-23*
