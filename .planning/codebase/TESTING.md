# Testing Patterns

**Analysis Date:** 2026-04-23

## Test Framework

**Frontend (TypeScript):**
- Runner: Vitest (v2.1.8)
- Config: Inline in `package.json` scripts (`vitest run --passWithNoTests`)
- Assertion: Vitest built-in (`expect`)
- Mocking: `vi.fn()`, `vi.mock()`

**Backend (Python):**
- Runner: pytest (v8.3.0)
- Config: `backend/pyproject.toml` `[tool.pytest.ini_options]`
- Assertion: pytest built-in (`assert`)
- Async: pytest-asyncio (auto mode)
- HTTP: FastAPI `TestClient` (httpx-based)
- Mocking: `monkeypatch`, custom fakes

## Test File Organization

**Frontend:**
- Location: `packages/*/tests/`
- Naming: `*.test.ts` (e.g., `ws.test.ts`, `cubism-core.test.ts`)
- Structure: Co-located with source packages

```
packages/
├── core/
│   ├── src/
│   └── tests/
│       └── ws.test.ts
├── live2d-kit/
│   ├── src/
│   └── tests/
│       └── cubism-core.test.ts
├── embed/
│   └── tests/
├── sdk-js/
│   └── tests/
```

**Backend:**
- Location: `backend/tests/`
- Naming: `test_*.py` (e.g., `test_auth.py`, `test_chat_flow.py`)
- Structure: Unit tests in `tests/unit/`, conftest at `tests/conftest.py`

```
backend/
├── app/
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── unit/
        ├── test_auth.py
        ├── test_chat_flow.py
        ├── test_emotion_service.py
        ├── test_health.py
        ├── test_speaker_domain.py
        ├── test_speaker_repo.py
        ├── test_speaker_service.py
        ├── test_speakers_router.py
        └── test_ws_cancel.py
```

## Test Structure

**Frontend (Vitest):**
```typescript
import { describe, expect, it, vi } from 'vitest';

describe('FeatureName', () => {
  it('does something specific', async () => {
    // Arrange
    const mockFn = vi.fn();
    
    // Act
    const result = await someFunction();
    
    // Assert
    expect(result).toBe(expected);
    expect(mockFn).toHaveBeenCalledWith(args);
  });
});
```

**Backend (pytest):**
```python
"""Module docstring explaining test scope."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.services import some_service


def test_specific_behavior() -> None:
    """Test docstring explaining what is tested."""
    # Arrange
    service = some_service.SomeService()
    
    # Act
    result = service.do_something()
    
    # Assert
    assert result == expected


def test_error_case(client: TestClient) -> None:
    """Test error handling."""
    resp = client.post("/api/endpoint", json={})
    assert resp.status_code == 400
```

## Mocking

**Frontend (Vitest):**
```typescript
// Function mocks
const mockFn = vi.fn<(arg: string) => void>();
mockFn.mockReturnValue(value);
mockFn.mockImplementation(() => { /* ... */ });

// Class mocks with injection
const socket = new ChatSocket({
  WebSocketImpl: class extends MockSocket {
    constructor(url: string) {
      super(url);
      instances.push(this);
    }
  } as unknown as typeof WebSocket,
});

// Global mocks
vi.mock('module-name', () => ({
  exportName: vi.fn(),
}));
```

**Backend (pytest):**
```python
# Monkeypatch
def test_with_patch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "attribute", mock_value)
    monkeypatch.setenv("ENV_VAR", "test_value")

# Custom fakes (preferred pattern)
class _FakeAdapter:
    """Minimal fake that implements the interface."""
    available: bool = True
    threshold: float = 0.38
    
    @property
    def is_available(self) -> bool:
        return self.available
    
    def embed(self, audio, sample_rate: int = 16000):
        return [1.0, 0.0, 0.0]

# Test injection via set_*_for_tests()
def test_with_fake_service(client: TestClient) -> None:
    fake = _FakeService(repo)
    set_speaker_service_for_tests(fake)
    # ... test ...
    set_speaker_service_for_tests(None)  # cleanup
```

## Fixtures and Factories

**Backend pytest fixtures:**
```python
# conftest.py
@pytest.fixture(autouse=True)
def _force_echo_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the AgentService singleton to echo mode for tests."""
    svc = agent_service.AgentService()
    svc._agent = None
    monkeypatch.setattr(agent_service, "_singleton", svc)

@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())

# Test-local fixtures
@pytest.fixture
def svc(tmp_path: Path) -> _FakeService:
    repo = JsonFileSpeakerRepo(path=tmp_path / "speakers.json")
    set_speaker_repo_for_tests(repo)
    fake = _FakeService(repo)
    set_speaker_service_for_tests(fake)
    yield fake
    set_speaker_service_for_tests(None)
    set_speaker_repo_for_tests(None)
```

**Test data:**
- Use `tmp_path` fixture for file-based tests
- Inline test data (no external fixture files)
- Realistic but minimal data (e.g., `b"fake-wav-bytes"`, `[1.0, 0.0, 0.0]`)

## Coverage

**Requirements:**
- No explicit coverage targets enforced
- CI runs tests but doesn't fail on coverage thresholds

**View Coverage:**
```bash
# Frontend
pnpm test -- --coverage

# Backend
cd backend && pytest --cov=app --cov-report=term-missing
```

## Test Types

**Unit Tests (Frontend):**
- Scope: Individual functions/classes
- Examples: `ws.test.ts` (ChatSocket), `cubism-core.test.ts` (CubismCore loader)
- Pattern: Mock dependencies, test pure logic

**Unit Tests (Backend):**
- Scope: Services, domain logic, schemas
- Examples: `test_auth.py`, `test_emotion_service.py`, `test_speaker_service.py`
- Pattern: Use fakes, test business logic in isolation

**Integration Tests (Backend):**
- Scope: API endpoints with real FastAPI app
- Examples: `test_chat_flow.py`, `test_speakers_router.py`
- Pattern: Use `TestClient`, test full request/response cycle

**E2E Tests:**
- Not currently implemented
- Playwright listed in context but no config/tests found

## CI Testing

**GitHub Actions (`.github/workflows/ci.yml`):**

**Frontend job:**
```yaml
- Format check: pnpm format:check
- Typecheck: pnpm typecheck
- Test: pnpm test
- Build: pnpm build
```

**Backend job:**
```yaml
- Ruff: ruff check app tests
- Mypy: mypy app
- Pytest: pytest -q
```

**Run Commands:**
```bash
# Frontend - all tests
pnpm test

# Frontend - specific package
pnpm --filter @webling/core test

# Frontend - watch mode
pnpm --filter @webling/core test -- --watch

# Backend - all tests
cd backend && pytest

# Backend - specific test
cd backend && pytest tests/unit/test_auth.py

# Backend - verbose
cd backend && pytest -v
```

## Common Patterns

**Async Testing (Frontend):**
```typescript
it('handles async operations', async () => {
  const socket = new ChatSocket({ /* ... */ });
  await socket.connect();
  await Promise.resolve(); // flush microtasks
  
  socket.sendUserMessage('hi');
  expect(mockFn).toHaveBeenCalled();
  
  socket.close();
});
```

**Error Testing (Frontend):**
```typescript
it('reports errors via callback', async () => {
  const onError = vi.fn<(err: Error) => void>();
  // ... setup with error condition ...
  expect(onError).toHaveBeenCalled();
});
```

**Async Testing (Backend):**
```python
@pytest.mark.asyncio
async def test_async_function() -> None:
    result = await some_async_function()
    assert result == expected
```

**Error Testing (Backend):**
```python
def test_raises_on_invalid_input() -> None:
    with pytest.raises(AuthError):
        auth_service.decode_token("invalid-token")

def test_404_on_missing_resource(client: TestClient) -> None:
    resp = client.get("/api/resource/nonexistent")
    assert resp.status_code == 404
```

**WebSocket Testing (Backend):**
```python
def test_ws_message_flow(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={}).json()["session_id"]
    with client.websocket_connect(f"/ws/chat?session_id={sid}") as ws:
        # Initial state
        first = ws.receive_json()
        assert first == {"type": "state", "value": "idle"}
        
        # Send message
        ws.send_json({"type": "user_message", "text": "ping"})
        
        # Collect responses
        for _ in range(10):
            msg = ws.receive_json()
            if msg["type"] == "subtitle" and msg["is_final"]:
                assert "ping" in msg["text"]
                break
```

**Protocol Conformance Testing:**
```python
def test_adapter_interface_matches_real_adapter() -> None:
    """Ensure fake has same shape as real adapter."""
    real = SVAdapter(threshold=0.38)
    fake = _FakeAdapter()
    for attr in ("is_available", "load_error", "threshold", "embed"):
        assert hasattr(fake, attr)
        assert hasattr(real, attr)
```

## Test Isolation

**Frontend:**
- Each test creates fresh instances
- Mock WebSocket implementation injected
- No shared state between tests

**Backend:**
- `autouse` fixture pins echo agent (no real LLM calls)
- `tmp_path` for file-based tests (isolated filesystem)
- `set_*_for_tests(None)` cleanup in fixtures
- Singletons reset between tests

## Test Data Management

**Frontend:**
- Inline mock data
- Mock classes (e.g., `MockSocket`)
- No external test fixtures

**Backend:**
- Inline test data in test functions
- `tmp_path` for temporary files
- JSON strings for complex data structures
- Chinese text in tests (matches domain)

---

*Testing analysis: 2026-04-23*
