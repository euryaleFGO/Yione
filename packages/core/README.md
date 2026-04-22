# @webling/core

纯逻辑包，供 `@webling/ui` / `@webling/embed` / `apps/web` 复用。

## 模块（M1 起逐步实现）

- `chat/` — 会话模型、消息状态机
- `ws/` — WebSocket client（重连、鉴权、事件分发）
- `audio/` — AudioContext、队列播放、RMS 提取
- `api/` — REST client
- `auth/` — token 管理、刷新
- `types/` — 共享 TS 类型（**ws 协议事实来源**）
