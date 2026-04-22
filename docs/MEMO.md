# 开发备忘

## M0 骨架 ✅（2026-04-23）

- 仓库骨架：pnpm workspaces、Turborepo、TypeScript 基线
- 后端骨架：FastAPI + pydantic-settings + Ling sys.path 注入、`/api/health`
- 前端骨架：Vue 3 + Vite + Tailwind + vue-router + pinia
- 五个 JS 包骨架：`@webling/{core,live2d-kit,ui,embed,sdk}`
- Live2D Hiyori 资源就绪（`apps/web/public/avatars/hiyori/`）
- CI workflow、lefthook、docs 桩

## M1 文本对话 ✅（2026-04-23）

- `packages/core`：HttpClient + ChatApi + ChatSocket（重连、类型分派）
- 后端：`/api/sessions`、`/api/chat`、`/ws/chat`
- `agent_service`：封装 Ling.Agent，Ling 不可用时自动退回 echo stub
- ChatView 能发送消息、WS 流式显示 subtitle、REST 兜底

## M2 Live2D 显示 ✅（2026-04-23）

- `@webling/live2d-kit`：AvatarStage + 动态加载 pixi.js / pixi-live2d-display
- Cubism Core 缺失时优雅降级为 `cubism_missing` 状态，页面展示引导卡片
- 按需加载：主站首屏 38KB gzip，进入 ChatView 时才拉 PIXI / cubism4 chunk
- 用户须手动下载 `live2dcubismcore.min.js` 到 `apps/web/public/` 才能看到玲

## 已知手动步骤

- Cubism Core：`scripts/fetch-cubism-core.sh` 只打印指引（Live2D 协议要求手动下载）
- 首次开发前：根目录跑一次 `pnpm install`；`backend/` 跑一次 `pip install -e '.[dev]'`

## 下一步（M3 TTS + 嘴型）

- 后端 `tts_service.py`：代理 `/api/tts/synth` → CosyVoice；缓存 wav 到
  `backend/app/static/tts/<uuid>.wav`
- 前端 `@webling/core/audio`：AudioContext、分段 FIFO 播放、RMS 提取
- WS 服务端在 subtitle 完成后发 `audio` 事件，前端队列播放并驱动 lipsync
- `@webling/live2d-kit/lipsync.ts`：RMS → `ParamMouthOpenY`
