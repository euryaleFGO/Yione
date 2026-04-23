# Technology Stack

## Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| Vue 3 | ^3.5.32 | UI framework (Composition API) |
| TypeScript | ~5.6.3 | Type-safe JavaScript |
| Vite | ^6.0.5 | Build tool & dev server |
| Pinia | ^2.2.6 | State management |
| Vue Router | ^4.5.0 | Client-side routing |
| Tailwind CSS | ^3.4.17 | Utility-first CSS framework |
| PostCSS | ^8.5.1 | CSS processing |
| Autoprefixer | ^10.4.20 | Vendor prefix automation |
| pixi.js | 7.1.2 | 2D WebGL rendering engine |
| pixi-live2d-display-lipsyncpatch | 0.5.0-ls-8 | Live2D model rendering with lipsync |
| reconnecting-websocket | ^4.4.0 | Auto-reconnecting WebSocket client |

## Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | >=3.12 | Backend language |
| FastAPI | >=0.115.0 | Async web framework |
| Uvicorn | >=0.32.0 | ASGI server |
| Pydantic | >=2.9.0 | Data validation & serialization |
| Pydantic Settings | >=2.6.0 | Environment-based configuration |
| python-dotenv | >=1.0.1 | .env file loading |
| httpx | >=0.28.0 | Async HTTP client |
| structlog | >=24.4.0 | Structured logging |

## Database

| Technology | Version | Purpose |
|------------|---------|---------|
| MongoDB | 7 | Document database |
| pymongo | >=4.10.0 | MongoDB sync driver |
| motor | >=3.6.0 | MongoDB async driver |

## Authentication

| Technology | Version | Purpose |
|------------|---------|---------|
| python-jose | >=3.3.0 | JWT encoding/decoding |
| passlib | >=1.7.4 | Password hashing (bcrypt) |

## Speech Processing (Optional)

| Technology | Version | Purpose |
|------------|---------|---------|
| numpy | >=1.26.0 | Numerical computing |
| soundfile | >=0.12.0 | Audio file I/O |
| funasr | >=1.3.1 | Speech recognition |
| torch | >=2.0.0 | Deep learning framework |
| torchaudio | >=2.0.0 | Audio processing |
| silero-vad | >=6.0.0 | Voice activity detection |

## Development Tools

| Technology | Version | Purpose |
|------------|---------|---------|
| pnpm | 10.30.3 | Node.js package manager |
| Turborepo | ^2.3.3 | Monorepo build orchestration |
| ESLint | - | JavaScript/TypeScript linting |
| Prettier | ^3.3.3 | Code formatting |
| Ruff | >=0.7.0 | Python linting & formatting |
| mypy | >=1.13.0 | Python static type checking |
| Lefthook | - | Git hooks manager |
| EditorConfig | - | Cross-editor consistency |

## Testing

| Technology | Version | Purpose |
|------------|---------|---------|
| Vitest | ^2.1.8 | Frontend unit testing |
| vue-tsc | ^2.2.0 | Vue TypeScript checking |
| pytest | >=8.3.0 | Backend testing framework |
| pytest-asyncio | >=0.24.0 | Async test support |
| pytest-httpx | >=0.33.0 | HTTP client mocking |

## Build & Deploy

| Technology | Purpose |
|------------|---------|
| GitHub Actions | CI/CD pipeline |
| Docker | Containerization (MongoDB service in CI) |
| Vite | Frontend production builds |
| setuptools | Python package building |

## Runtime Requirements

| Requirement | Version |
|-------------|---------|
| Node.js | >=20 |
| Python | >=3.12 |
| MongoDB | 7.x |

---

*Stack analysis: 2026-04-23*
