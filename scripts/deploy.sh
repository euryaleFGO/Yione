#!/usr/bin/env bash
# webLing 一键部署：串联 FunASR → TTS → 核心服务
#
# 需要提前就位：
#   1. docker + docker compose v2（>= 20.10）
#   2. TTS 容器需要 GPU：nvidia-container-toolkit
#   3. 把 CosyVoice2-0.5B 模型放到 deploy/tts/models/CosyVoice2-0.5B/
#      或在 deploy/tts/.env 里 TTS_MODELS_DIR 指向已有模型目录
#
# 用法：
#   ./scripts/deploy.sh                 # 全部（三层）
#   ./scripts/deploy.sh core            # 只起核心（不起 FunASR/TTS）
#   ./scripts/deploy.sh funasr tts      # 只起依赖
#   ./scripts/deploy.sh --stop          # 全部停止

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

log() { printf '\033[36m[deploy] %s\033[0m\n' "$*"; }

require_docker() {
  command -v docker >/dev/null 2>&1 || { echo "需要先安装 docker"; exit 1; }
  docker compose version >/dev/null 2>&1 || { echo "需要 docker compose v2（>= 20.10）"; exit 1; }
}

ensure_env() {
  local dir=$1
  if [[ ! -f "$dir/.env" ]] && [[ -f "$dir/.env.example" ]]; then
    cp "$dir/.env.example" "$dir/.env"
    log "已根据 .env.example 生成 $dir/.env"
  fi
}

up_funasr() {
  log "↑ FunASR (deploy/funasr)"
  ensure_env "$ROOT/deploy/funasr"
  (cd "$ROOT/deploy/funasr" && docker compose up -d)
  log "FunASR 容器已启动。首次请 docker compose logs -f 看 ~1.7GB 模型下载进度，等 'asr model init finished'。"
}

up_tts() {
  log "↑ TTS (deploy/tts)"
  ensure_env "$ROOT/deploy/tts"
  if [[ ! -d "$ROOT/deploy/tts/models/CosyVoice2-0.5B" ]] \
     && ! grep -q '^TTS_MODELS_DIR=' "$ROOT/deploy/tts/.env" 2>/dev/null; then
    echo "警告：deploy/tts/models/CosyVoice2-0.5B/ 不存在，且 .env 未设 TTS_MODELS_DIR。"
    echo "     TTS 容器启动后会无法加载模型。参考 deploy/tts/README.md 下模型。"
  fi
  (cd "$ROOT/deploy/tts" && docker compose up -d --build)
}

up_core() {
  log "↑ webLing 核心 (backend + frontend + mongo + 监控)"
  ensure_env "$ROOT"
  (cd "$ROOT" && docker compose up -d --build)
}

down_all() {
  log "停止全部服务"
  (cd "$ROOT" && docker compose down || true)
  (cd "$ROOT/deploy/tts" && docker compose down || true)
  (cd "$ROOT/deploy/funasr" && docker compose down || true)
}

require_docker

if [[ "${1:-}" == "--stop" ]]; then
  down_all
  exit 0
fi

targets=("$@")
if [[ ${#targets[@]} -eq 0 ]]; then
  targets=(funasr tts core)
fi

for t in "${targets[@]}"; do
  case "$t" in
    funasr) up_funasr ;;
    tts)    up_tts ;;
    core)   up_core ;;
    *) echo "未知目标：$t（可用：funasr tts core）"; exit 1 ;;
  esac
done

log "完成。"
log "- 前端：http://localhost"
log "- 后端 API：http://localhost:8000"
log "- API 文档：http://localhost:8000/docs"
log "- Grafana：http://localhost:3000 (admin/admin)"
log "- Prometheus：http://localhost:9090"
