# 开发备忘

## M0 完成情况（2026-04-23）

- ✅ 仓库骨架：pnpm workspaces、Turborepo、TypeScript 基线
- ✅ 后端骨架：FastAPI + pydantic-settings + Ling sys.path 注入、`/api/health`
- ✅ 前端骨架：Vue 3 + Vite + Tailwind + vue-router + pinia，ChatView 自检 backend
- ✅ 五个 JS 包骨架：`@webling/{core,live2d-kit,ui,embed,sdk}`
- ✅ Live2D Hiyori 资源就绪（`apps/web/public/avatars/hiyori/`）
- ✅ CI workflow、lefthook、docs 桩
- ⚠️ **手动步骤**：`live2dcubismcore.min.js` 需从 live2d.com 下载（见
  `scripts/fetch-cubism-core.sh`）
- ⚠️ 依赖安装：根 `pnpm install` 需要首次跑一遍（下一次开发 M1 时执行）

## 下一步（M1）

- `packages/core/src/ws/client.ts` 实现重连 WS 客户端
- `packages/core/src/api/http.ts` 简单 REST 封装
- `backend/app/routers/chat.py` + `backend/app/ws/chat_ws.py` 最小实现
- `backend/app/services/agent_service.py` 对接 `Ling.Agent`（`asyncio.to_thread`）
- 前端 ChatView 接入 `useChat()`，能来回一条消息
