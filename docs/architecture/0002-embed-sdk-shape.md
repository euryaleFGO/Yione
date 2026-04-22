# ADR 0002 — 嵌入 SDK 的三种形态

- 状态：Proposed（M8/M9 落地时再 Accept）
- 时间：2026-04-23
- 相关：`PLAN.md` §7

## 背景

接入方有不同的技术栈和隔离需求：
- 偏静态页希望「一段 script」就能接入
- 纯 HTML 或非前端框架希望用 Custom Element 控制
- 安全敏感的场景希望 iframe 完全沙箱

## 决策

提供三种形态，同一份 `@webling/embed` 代码通过 Vite library mode 产出多格式产物：

1. **Script tag / UMD**：`embed.v1.min.js`，读 `<script data-*>` 配置，自动注入悬浮按钮
2. **Custom Element / ESM**：`embed.v1.esm.js`，挂 `<web-ling>`，Shadow DOM 隔离
3. **iframe**：`embed.html` 作为独立页面，父子通过 `postMessage` 通信

三者共享核心：`@webling/core` WS/REST 客户端 + `@webling/ui` 组件 + `@webling/live2d-kit`。

## 限制

- 首屏 JS ≤ 200KB gzip
- Live2D 资源（Hiyori 模型 + Cubism Core）按需加载，不进首屏
- UMD 版本不引入任何全局变量，只在 `window.WebLing` 挂

## 影响

- `packages/embed` 的 Vite 配置有三个 entry，产出不同 format
- 事件/指令 API 稳定前不发布到公网 CDN
