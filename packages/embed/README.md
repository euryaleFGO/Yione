# @webling/embed

嵌入 SDK。UMD + ESM + IIFE 三种产物，详见 `PLAN.md` §7。

## 规划

- `entry.ts` — `window.WebLing.init(...)`
- `web-component.ts` — `<web-ling>` Custom Element（Shadow DOM）
- `widget/` — 悬浮按钮 + 展开面板
- `postmessage.ts` — iframe 模式通信协议
- `embed.html` — iframe 宿主页
