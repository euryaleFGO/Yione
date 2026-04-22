# @webling/web

主站 Vue 3 + Vite + TypeScript SPA。

## 启动

```bash
pnpm install
pnpm --filter @webling/web dev   # http://localhost:5173
```

## 代理

- `/api` → `VITE_API_BASE` (默认 `http://localhost:8000`)
- `/ws`  → WS proxy
- `/static` → 后端静态资源（TTS wav 等）

## Live2D 资源

- Hiyori 模型：`public/avatars/hiyori/`（由 `scripts/copy-live2d-model.sh` 从 Ling 拷贝）
- Cubism Core：手动从 live2d.com 下载，放 `public/live2dcubismcore.min.js`
  （见 `PLAN.md` §16 第 7 步，已加入 `.gitignore` 不入库）
