#!/usr/bin/env bash
# 本地并行启动：前端 (vite) + 后端 (uvicorn)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

trap 'kill 0' INT TERM EXIT

(
  cd "$ROOT"
  pnpm --filter @webling/web dev
) &

(
  cd "$ROOT/backend"
  # 优先使用 venv 里的 uvicorn
  if [[ -x .venv/bin/uvicorn ]]; then
    UV=".venv/bin/uvicorn"
  else
    UV="uvicorn"
  fi
  "$UV" app.main:app --reload --host 0.0.0.0 --port 8000
) &

wait
