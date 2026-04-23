# Phase 3: M8 Embed Script - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning
**Source:** User provided context

<domain>
## Phase Boundary

第三方可通过 `<script>` 标签接入 webLing 聊天功能。提供一个独立的 embed.js 文件，第三方网站通过 `<script src="...">` 引入后，自动在页面注入悬浮按钮，点击后打开聊天面板（iframe 隔离），连接到 webLing 后端进行对话。

</domain>

<decisions>
## Implementation Decisions

### Script 配置方式
- **D-01**: 使用 `data-*` 属性进行配置：`data-api-key`, `data-character-id`, `data-position`, `data-base-url`
- **D-02**: 默认位置为右下角，可通过 `data-position` 配置（支持 bottom-right, bottom-left, top-right, top-left）

### 面板隔离
- **D-03**: 使用 iframe 实现聊天面板，确保样式隔离
- **D-04**: iframe 加载独立的 embed.html 页面，通过 postMessage 与父页面通信

### 构建方式
- **D-05**: embed.js 作为独立的 Vite 库构建（library mode）
- **D-06**: 输出格式为 IIFE，支持直接 `<script>` 引入

### 后端集成
- **D-07**: 使用 M6 已有的 POST /api/embed/token 端点获取 JWT token
- **D-08**: 使用 M7 已有的 Character API 获取角色信息
- **D-09**: 使用现有的 WebSocket 聊天端点进行实时对话

### Claude's Discretion
- 悬浮按钮的具体样式和动画效果
- iframe 通信协议的具体消息格式
- 错误处理和加载状态的 UI 表现
- 移动端适配策略

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 现有代码
- `apps/web/src/stores/auth.ts` — Auth store，包含 embed token 支持
- `apps/api/src/routes/embed.ts` — POST /api/embed/token 端点（M6 已实现）
- `apps/api/src/routes/character.ts` — Character API（M7 待实现）
- `apps/api/src/routes/chat.ts` — 聊天 WebSocket 端点

### 项目结构
- `apps/web/vite.config.ts` — 现有 Vite 配置
- `packages/` — monorepo 包结构

</canonical_refs>

<specifics>
## Specific Ideas

- embed.js 应该是零依赖的，不引入额外的框架
- 配置应该通过 script 标签的 data-* 属性，而不是全局变量
- 面板打开/关闭应该有平滑的过渡动画
- 应该支持多个 embed 实例在同一页面（虽然不太常见）
- 需要处理 API key 无效或网络错误的情况

</specifics>

<deferred>
## Deferred Ideas

- M9: Web Component 形态 (`<web-ling>` 自定义标签)
- M10: 纯 iframe 形态（无 script 注入）
- 高级配置（主题定制、自定义按钮样式等）

</deferred>

---

*Phase: 03-M8-Embed-Script*
*Context gathered: 2026-04-23*
