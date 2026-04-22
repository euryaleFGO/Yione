#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

if [[ -x .venv/bin/uvicorn ]]; then
  exec .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
else
  exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
fi
