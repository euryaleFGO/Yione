#!/usr/bin/env bash
# 从 Ling 仓库拷贝 Hiyori Live2D 资源到 apps/web/public/avatars/hiyori/
# 可重入：覆盖同名文件。
set -euo pipefail

LING_SRC="${LING_SRC:-/Users/zert/Work/zert/lkl_code/Ling/src/frontend/live2d/src/main/resources/res}"
DEST="${DEST:-$(cd "$(dirname "$0")/.." && pwd)/apps/web/public/avatars/hiyori}"

if [[ ! -d "$LING_SRC" ]]; then
  echo "Ling 资源目录不存在：$LING_SRC" >&2
  exit 1
fi

mkdir -p "$DEST"
cp -R "$LING_SRC"/. "$DEST"/
echo "Hiyori 资源已同步 → $DEST"
ls -1 "$DEST"
