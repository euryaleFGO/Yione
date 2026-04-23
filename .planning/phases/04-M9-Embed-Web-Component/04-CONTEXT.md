# Phase 4: M9 Embed Web Component - Context

**收集日期：** 2026-04-23

<decisions>
- D-01: 使用 Custom Elements + Shadow DOM 实现样式隔离
- D-02: 属性响应式：character-id, api-key, position, base-url
- D-03: 复用 M8 的 embed.html 聊天面板逻辑（改为 Shadow DOM 内嵌而非 iframe）
- D-04: 构建为独立 JS 文件（web-component.js），IIFE 格式
- D-05: 不依赖 Vue/React，纯原生 Web Components
</decisions>

*Phase: 4-M9-Embed-Web-Component*
