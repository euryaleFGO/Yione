# ADR 0001 — Monorepo 采用 pnpm workspaces + Turborepo

- 状态：Accepted
- 时间：2026-04-23
- 相关：`PLAN.md` §3 §5

## 背景

webLing 需要同时交付：主站 SPA（`apps/web`）、嵌入 SDK（`packages/embed`）、裸 JS SDK（`packages/sdk-js`），以及一层 FastAPI 后端（`backend/`）。前端多个产物需要共享 `core/ui/live2d-kit`。

## 决策

采用 **pnpm workspaces + Turborepo** 单仓多包结构：

- `packages/*` 为可发布 / workspace-linked 的库
- `apps/*` 为最终产物（目前只有 `web`）
- `backend/` 独立 Python 包，不加入 pnpm 工作区
- 构建通过 Turborepo 的 task graph，lint/typecheck/test/build 可并行、带缓存

## 替代方案

- **polyrepo**：发布链路复杂、类型版本漂移风险高、本地开发需要 `npm link`，不选。
- **Nx**：功能齐全但复杂，Turborepo 对我们的规模够用。

## 影响

- 根 `package.json` 聚合 lint/typecheck/test 入口
- 跨包依赖用 `workspace:*` 语义，避免循环需要架构上保证
- CI 一个 job 跑前端、一个 job 跑后端
