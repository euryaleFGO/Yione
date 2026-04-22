#!/usr/bin/env bash
# Cubism Core Web SDK 不能从 live2d 官网自动下载（需登录并接受协议）。
# 本脚本只是提示——请手动下载后放到 apps/web/public/live2dcubismcore.min.js。
set -e

DEST="$(cd "$(dirname "$0")/.." && pwd)/apps/web/public/live2dcubismcore.min.js"
if [[ -f "$DEST" ]]; then
  echo "Cubism Core 已就位：$DEST"
  exit 0
fi

cat <<EOF
[!] Cubism Core 未安装。

请按以下步骤手动获取：
  1. 浏览器打开 https://www.live2d.com/download/cubism-sdk/
  2. 下载 "Cubism SDK for Web"
  3. 解压后把 Core/live2dcubismcore.min.js 放到：
     $DEST

（该文件受 Live2D 协议约束，不纳入版本控制。）
EOF
exit 1
