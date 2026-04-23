# @webling/embed

webLing 的**嵌入 SDK**——让任意第三方网站通过一段 `<script>` 或一个 `<web-ling>` 标签就拥有"会动会说话的 Live2D 玲"。

## 三形态一览

| 形态 | 入口文件 | 体积 | 接入方式 |
|---|---|---|---|
| Script tag | `dist/embed.js` | ~5KB gzip | `<script src data-api-key>` 自动挂浮动按钮 |
| Custom Element | `dist/web-component.js` | ~3KB gzip | `<web-ling api-key>` 声明式 |
| 纯 iframe | `dist/embed.html` | Vue 应用产物 | `<iframe src="...embed.html?api_key=...">` |

三者共用同一个 iframe 运行时（Vue 应用 = `embed.html` + `assets/*`），所以 **Live2D + TTS + 嘴型 + 情绪 + 声纹** 全都拿到，不是简单的文本聊天框。

## 目录结构

```
apps/embed/
├── embed.html              # Vite MPA 入口（Vue 应用挂载点）
├── src/
│   ├── main.ts             # iframe 宿主的 Vue 入口
│   ├── EmbedApp.vue        # 精简聊天外壳（复用 @/components 和 @/stores）
│   ├── style.css           # Tailwind 基础
│   ├── index.ts            # Script tag 打包入口（embed.js）
│   ├── web-component.ts    # Custom Element 打包入口（web-component.js）
│   ├── postmessage.ts      # 父子通信协议 + URL 构造
│   └── shims.d.ts
├── public/
│   └── demo.html           # 演示页（dist/demo.html 可公网访问）
├── scripts/
│   └── copy-web-public.mjs # 构建后从 apps/web/public 拷 avatars / live2dcubismcore
├── vite.app.config.ts      # Vue 应用打包（embed.html + assets）
├── vite.lib.config.ts      # Library 打包（embed.js / web-component.js）
├── tsconfig.{json,app.json,lib.json}
├── tailwind.config.js / postcss.config.js
└── package.json
```

## 构建

```bash
pnpm install
pnpm --filter @webling/embed build
```

产物：`apps/embed/dist/`
- `embed.html` + `assets/*.js` + `assets/*.css`（Vue 运行时）
- `embed.js`（Script tag）
- `web-component.js`（Custom Element）
- `demo.html`（接入演示页）
- `avatars/` + `live2dcubismcore.min.js` + `favicon.svg`（从 apps/web/public 拷贝）

backend `create_app()` 把 `apps/embed/dist/` 挂在 `/embed/`，生产环境直接访问：
- `https://<host>/embed/embed.js`
- `https://<host>/embed/embed.html`
- `https://<host>/embed/demo.html`

## 开发

```bash
# iframe 宿主（需同时开 backend 和 apps/web 才能连 WS/取 avatars）
pnpm --filter @webling/embed dev
# → http://localhost:5174/embed.html?api_key=demo
```

dev 时端口：backend 8000 / web 5173 / embed 5174。Vite proxy 会把 `/api` `/ws` `/static` 转到 8000，`/avatars` `/live2dcubismcore.min.js` 转到 5173。

## 架构决策

### 为什么 iframe 是真运行时，而不是在 Custom Element 里跑 Vue？

1. **样式隔离天然干净**：第三方网站的 Tailwind / Bootstrap / 公司内 CSS reset 都不会污染 webLing UI。Shadow DOM 虽然也能隔离，但 Live2D 用的 WebGL canvas 在 Shadow DOM 里触发事件 / focus / iOS autoplay 有额外坑。
2. **CSP 友好**：嵌入方只需要 `iframe-src https://<webling-host>`，不用 allow inline script / WebGL worker。
3. **升级无缝**：改 iframe 里的 Vue 应用，所有接入方下次打开都拿到新版，不用重新发 CDN `embed.js`。
4. **代码复用最大**：iframe 里的 `EmbedApp.vue` 直接复用 `apps/web/src/components/{AvatarStage,InputBar,MessageList}` 和 `stores/{chat,auth}`，不用抽第二套 UI 组件库。

### 为什么 Script tag 和 Custom Element 不共享一个 Shadow DOM 方案？

Custom Element 的 `embedded` 模式确实用 Shadow DOM 会更干净，但 Live2D + MediaStream（麦克风）在 Shadow DOM 里有渲染 / 事件 bubble 的兼容问题。**统一走 iframe** 省掉一类潜在 bug。

### apiKey 进 URL 安全吗？

embed 场景下 apiKey **本就是半公开**：任何第三方接入页都会在 HTML 源码里放 `data-api-key="..."`，view-source 可得。真正的访问控制在后端的 **Origin 白名单 + daily_quota**（见 `backend/app/services/tenant_service.py::Tenant`）。所以 apiKey 进 URL referer 不比进 HTML 源码更糟。

**短期 JWT 永远不进 URL**——它在 iframe 内部 `auth.fetchEmbedToken` 现换，存 sessionStorage，过期前 30s 自动续签。

### 为什么 dev 模式下可以用 `api_key=demo`？

`TenantService` 没检测到 `tenants.json` 时进 **dev fallback**：任意 api_key 都认成 `demo` tenant，`allowed_origins` 为空视为全通。生产前一定要创建 `backend/app/data/tenants.json` 并正确配置 `allowed_origins` 白名单。

## postMessage 协议

见 `src/postmessage.ts` 的 `ParentToChildMessage` / `ChildToParentMessage` 类型。
接入方使用参考 `docs/embed-integration.md`。
