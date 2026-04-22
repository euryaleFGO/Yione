# webLing

把 [`Ling`](../Ling) 玲虚拟助手做成 **Web 应用 + 可嵌入 SDK**，并按**AI 数字人**方向长期演进。

## 近期（Phase 1-3）

- 主站：完整的网页对话 + Live2D 形象 + TTS 播放 + 嘴型同步
- 嵌入：一段 `<script>` / `<web-ling>` / `<iframe>`，第三方站点零门槛接入
- 多形象 + 多音色：Character 作为一等数据模型，后台可增删
- Token 认证：短期 JWT + API Key，Tenant/User 两级隔离

## 长期（Phase 4-6，对标 Neuro-sama 等开源项目）

- **流式双向对话**：可打断、低延迟、实时响应
- **多说话人识别**：声纹建档、记得每个用户、个性化回复
- **情感引擎 + 人格系统**：有脾气、有记忆、有一致性
- **自主行为**：定时主动问候、事件触发、自主对话循环
- **工具调用 + 技能插件**：查天气、提醒、搜索、外部 API
- **唱歌 / 卡拉OK**：RVC 声线合成、歌词同步、伴奏混音
- **多模态感知**：视觉工具、知识图谱、场景理解
- **Prompt 管理**：模板热更新、A/B、版本控制

## 当前状态

`v0.0` — **只有规划文档，还没写代码**。完整规划见 [`PLAN.md`](./PLAN.md)。

## 与 `Ling` 的关系

- `Ling` 仓库**不改**，通过 `sys.path` 引入 Agent 代码
- 复用已部署的 LLM (`192.168.251.56:8080`) / CosyVoice TTS (`:5001`) / MongoDB (Docker 本地 27017)
- Hiyori 模型文件从 `Ling/src/frontend/live2d/src/main/resources/res/` 复制

## 技术栈

| 层 | 选择 |
|---|---|
| Monorepo | pnpm workspaces + Turborepo |
| 前端 | Vue 3 + Vite + TypeScript + Pinia + Tailwind |
| Live2D | `pixi-live2d-display` + PIXI v7 + Cubism 4 SDK Web core |
| 后端 | FastAPI + Python 3.12（uvicorn、pydantic-settings、pymongo、httpx） |
| 认证 | JWT (python-jose) + API Key |
| 测试 | Vitest / Playwright / pytest |
| CI | GitHub Actions + lefthook |

## 目录结构（摘要）

```
webLing/
├── packages/
│   ├── core/         纯逻辑（chat / ws / audio / auth / types）
│   ├── live2d-kit/   Live2D 渲染封装
│   ├── ui/           Vue 组件库
│   ├── embed/        嵌入 SDK（Script/WC/iframe，UMD+ESM 打包）
│   └── sdk-js/       裸 JS 客户端（给接入方 Node 用）
├── apps/
│   └── web/          主站 SPA
├── backend/
│   └── app/          FastAPI（routers / ws / services / repositories / schemas / domain）
├── docs/             ADR、接入手册、API 文档
└── scripts/          拷模型、初始化、dev 启动
```

完整结构见 `PLAN.md` 第五节。

## 核心设计原则

1. **模块化到底**：能抽的都抽到 `packages/` 下，`apps/web` 和 `packages/embed` 都只是 `ui` + `core` + `live2d-kit` 的组合
2. **Schema-first**：WS 事件类型在 `packages/core/src/types/ws.ts` 定义一次，前后端共享
3. **配置外置**：URL / token TTL / rate-limit 全走 `.env`
4. **依赖注入**：services 构造函数接 repo/client，便于单测 mock
5. **标准流程**：Conventional Commits + ESLint/ruff + pre-commit + CI lint+test+build

## 迭代路线（摘要）

**MVP / Web 上线**
- **Phase 1（2-3 周）M0-M5**：骨架 → 文本对话 → Live2D → TTS+嘴型 → 流式 → 情绪动作  
- **Phase 2（2 周）M6-M10**：认证 → Character 模块 → Embed SDK（Script/WC/iframe）→ 接入 demo
- **Phase 3（1-2 周）M11-M15**：多 TTS Provider → 音色管理 → 历史 UI → 可观测 → 麦克风

**AI 数字人演进**
- **Phase 4（3-4 周）M16-M21**：声纹识别、流式 ASR、打断、工具调用、Prompt 管理 MVP
- **Phase 5（3-4 周）M22-M27**：情感引擎、人格系统、事件驱动、自主对话、RVC 歌声
- **Phase 6（2-3 周）M28-M33**：技能插件、卡拉OK、小游戏、知识图谱 UI、生产化

## 开发入口

```bash
cd /Users/zert/Work/zert/lkl_code/webLing
# 开新 Claude Code 窗口，让它读 README.md + PLAN.md
# 按 PLAN.md 第十六节 "M0 动手清单" 动手
```

## 外部依赖清单

- **本地**：Node 20+、pnpm 9+、Python 3.12、Docker Desktop
- **Ling 项目**：`/Users/zert/Work/zert/lkl_code/Ling`
- **远程服务**（服务器 `192.168.251.56`）：
  - LLM: `:8080/v1`（MiniMax-M2.5）
  - TTS: `:5001`（CosyVoice2-0.5B）
- **本地 Mongo**：Docker `liying-mongo`（已跑）
- **Live2D Cubism Core for Web**：手动从 Live2D 官网下载放 `apps/web/public/live2dcubismcore.min.js`
