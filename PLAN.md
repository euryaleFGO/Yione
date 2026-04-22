# webLing 规划

> 把桌面版 [`Ling`](../Ling) 玲虚拟助手做成 **Web 应用 + 可嵌入 SDK**，并按**AI 数字人**方向长期演进。
>
> **近期可交付**（Phase 1-3，本文档第十三节）：
> - 浏览器直接访问的完整 Web 页面
> - 一段 `<script>` 引入到任何第三方站点（Token 认证）
> - 多形象（Live2D 模型）+ 多音色（CosyVoice / edge-tts / …）切换
> - 按标准软件工程实践做模块化、组件化、可测试、可 CI
>
> **长期愿景**（Phase 4+，本文档第十九节）：对标 [Neuro-sama](https://neurosama.fandom.com/) 等开源 AI 数字人项目，做到
> - 真正的流式双向对话（可打断、低延迟）
> - 多说话人识别（声纹建档、个性化回复）
> - 情感/人格引擎（有记忆、有脾气、有一致性）
> - 自主决策与主动行为（不只回答，还会主动发起）
> - 唱歌、卡拉 OK、互动小游戏
> - 工具调用与事件驱动（定时提醒、环境感知、外部 API）
> - 视觉/场景理解与多模态输入

## 一、项目定位

- **不改 `Ling` 原项目**：Ling 仓库保持原状，作为 Agent/记忆/RAG 代码的来源
- **多形态交付**：
  1. 主站 `https://webling.example.com` 的完整 Web 应用
  2. 嵌入 SDK：第三方站点一段 `<script>` 就能拥有悬浮版玲
  3. Web Component：`<web-ling>` 自定义标签
  4. npm 包：已有 Vue/React 项目直接 import
- **多形象 / 多音色可扩展**：Character 作为一等数据模型，可后台增删；形象 = { Live2D 模型 + TTS 音色 + 人设提示词 + 欢迎语 + 动作映射 }
- **服务端零改动复用**：LLM、CosyVoice TTS、MongoDB 全部沿用 Ling 的已部署资源

## 二、与原 Ling 项目的关系

### 沿用（Ling 不动）
| 能力 | 方式 |
|---|---|
| `backend.llm.agent.Agent` / `memory/` / `rag/` / `database/` / `tools/` | `sys.path` 引入，**或**打成 `ling-agent` wheel 本地 pip install |
| MongoDB 数据模型（`conversations / long_term_memory / knowledge_base / character_settings / user_profiles / reminders / knowledge_graph`） | 直接复用，新增 `characters`（多形象扩展）、`api_tokens` 两个集合 |
| 远程 CosyVoice TTS 服务 `:5001`（`/tts/enqueue` + `/tts/dequeue`）| 原封不动 |
| 远程 LLM OpenAI 兼容接口 `:8080/v1`（MiniMax-M2.5） | 原封不动 |
| Hiyori `.moc3` 资源 | `scripts/copy-live2d-model.sh` 从 Ling 复制到 `apps/web/public/avatars/hiyori/` |

### 淘汰
- Java/LWJGL/GLFW/Cubism Core Native、PyQt6 launcher、桌面 HTTP 轮询 message_server、sounddevice 本地播放

## 三、技术栈

### 单一事实：`package.json` / `pyproject.toml` 里记录版本；本节只说选择与理由

| 层 | 技术 | 理由 |
|---|---|---|
| Monorepo 管理 | **pnpm workspaces + Turborepo** | 多 package 共享依赖、增量构建、缓存；纯 JS 侧可选 |
| 前端 SPA | **Vue 3 + Vite + TypeScript (strict)** | 轻量、Composition API 组合逻辑、打包快；若后续要 SSR 再加 Nuxt |
| 前端状态 | **Pinia** | Vue 3 官方 store，TS 友好 |
| 前端样式 | **Tailwind CSS + 可选 Headless UI** | 快速迭代，主题化易做 |
| 组件库 | 自研 `@webling/ui` | 形象+聊天是高度定制化，第三方组件库不合适 |
| Live2D 渲染 | **`pixi-live2d-display` + PIXI.js v7 + Cubism 4 SDK Web core** | 支持 `.moc3`，无需 native lib |
| 嵌入 SDK | **Vite library mode + UMD + Custom Elements (lit or native)** | 单文件可 CDN 引；Web Component 封装隔离样式 |
| 后端 | **FastAPI + Uvicorn + Python 3.12** | 原生 WS、自动 OpenAPI、与 Ling 同语言易集成 |
| 后端认证 | **python-jose (JWT) + passlib (hash)** | 无状态 token，嵌入场景友好 |
| 测试 | **Vitest + Playwright (前) / pytest + httpx (后)** | 业界主流 |
| Lint/Format | **ESLint + Prettier + Stylelint (前) / ruff + black + mypy (后)** | 自动化一致风格 |
| Git Hook | **lefthook 或 pre-commit** | 提交前跑 lint+test |
| CI | **GitHub Actions** | 规则简单，免费额度够 |
| 容器 | **Docker + docker-compose** | 本地一键起、线上也能用 |
| 流式 VAD（Phase 4+） | **silero-vad** | 打断检测的事实标准，CPU 即可 |
| 声纹识别（Phase 4+） | **pyannote.audio 3.x** 或 **SpeechBrain ECAPA** | Ling 已有 `SVEngine` 可直接复用，向量存 Chroma |
| 歌声合成（Phase 5+） | **RVC-Project / so-vits-svc** 独立微服务 | 走 HTTP 接入，像 CosyVoice 那样做成第三方服务 |
| 任务调度（Phase 4+） | **APScheduler** + **asyncio.Event** | 定时提醒、主动问候、事件触发 |
| 自主循环（Phase 5+） | **FSM / BDI 简化版**（自研） | Goal/Desire/Intention 列表 + 周期评估；复杂度够用即可 |
| Prompt 管理（Phase 4+） | **Jinja2 + Mongo 存版本** | 模板热更新、A/B、版本回滚 |

## 四、整体架构

```
                                    ┌─ 主站 apps/web (Vue SPA) ─┐
                                    │  完整体验：对话 + Live2D    │
                                    │  + 角色选择 + 历史 + 设置   │
                                    └─────────────┬─────────────┘
                                                  │
┌─ 第三方站点 A ─┐    <script src="embed.js">     │
│  <web-ling     │───┐                            │
│    character=  │   │ token auth (JWT)           │
│    "ling"/>    │   │                            │
└────────────────┘   │                            │
                     ▼                            ▼
┌─ 第三方站点 B (iframe) ─┐     ┌───────── packages/embed UMD ─────────┐
│  <iframe src=           │────>│  运行时：加载 Live2D 形象 + 聊天气泡 │
│  "embed.html?t=…"/>     │     │  依赖 @webling/core、@webling/ui    │
└─────────────────────────┘     └──────────────────┬──────────────────┘
                                                   │  REST + WSS
                                                   ▼
                              ┌────────────── backend (FastAPI) ──────────────┐
                              │  Auth  │  Sessions │  Chat │  WS │  Characters │
                              │  ────────────────────────────────────────── │
                              │  Services: agent (Ling adapter) │ tts │ auth │
                              │            │  characters │  quota/rate-limit │
                              │  ────────────────────────────────────────── │
                              │  Repos: Mongo + ChromaDB (Ling 复用)         │
                              └───┬──────────────┬──────────────┬────────────┘
                                  │              │              │
                           ┌──────┴───┐   ┌──────┴───┐   ┌──────┴────┐
                           │ MiniMax  │   │ CosyVoice│   │ MongoDB   │
                           │ LLM 8080 │   │ TTS 5001 │   │  27017    │
                           └──────────┘   └──────────┘   └───────────┘
```

**关键数据流**：
1. 第三方站点 `embed.js` 自动 attach 到页面
2. 首次交互从后端 `/api/embed/token`（用站点 API Key）换取短期 JWT
3. JWT 建 WSS `/ws/chat?token=…`，发 `user_message`
4. 后端 Agent (Ling) 生成字幕流 → 触发 TTS 拉音频段 → WS 推 `subtitle/audio/motion` 事件
5. 前端 Live2D 引擎嘴型同步 + 聊天气泡同步展示

## 五、Monorepo 目录结构

```
webLing/
├── README.md
├── PLAN.md
├── package.json                    # pnpm workspace root
├── pnpm-workspace.yaml
├── turbo.json                      # Turborepo pipeline
├── .editorconfig
├── .nvmrc
├── .prettierrc
├── .eslintrc.cjs
├── .lefthook.yml
├── .env.example
├── docker-compose.yml
├── .github/
│   └── workflows/
│       ├── ci.yml                  # lint + unit + build
│       └── release.yml             # publish embed package + web deploy
├── docs/
│   ├── architecture/               # ADR：重要决策归档
│   │   ├── 0001-monorepo-vs-polyrepo.md
│   │   ├── 0002-embed-sdk-shape.md
│   │   └── ...
│   ├── api/                        # 从 FastAPI 导出的 OpenAPI + changelog
│   ├── embed-integration.md        # 第三方接入手册
│   └── character-authoring.md      # 如何新建形象
│
├── packages/                       # 可复用 JS 包（pnpm workspace）
│   ├── core/                       # @webling/core：纯逻辑，无 DOM 依赖
│   │   ├── src/
│   │   │   ├── chat/               # 会话模型、消息、状态机
│   │   │   ├── ws/                 # WebSocket client (reconnect, auth)
│   │   │   ├── audio/              # AudioContext, 队列播放, RMS 提取
│   │   │   ├── api/                # REST client（OpenAPI 生成 or 手写）
│   │   │   ├── auth/               # token 管理、刷新
│   │   │   └── types/              # 共享 TS 类型
│   │   └── tests/
│   │
│   ├── live2d-kit/                 # @webling/live2d-kit：Live2D 渲染封装
│   │   ├── src/
│   │   │   ├── stage.ts            # PIXI app + 加载模型
│   │   │   ├── lipsync.ts          # RMS → ParamMouthOpenY
│   │   │   ├── motion.ts           # motion 控制器（情绪→动作）
│   │   │   ├── blink.ts            # 自动眨眼
│   │   │   ├── gaze.ts             # 视线跟随鼠标（可开关）
│   │   │   └── avatar-config.ts    # 形象配置 schema
│   │   └── tests/
│   │
│   ├── ui/                         # @webling/ui：Vue 组件库
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── ChatBubble/
│   │   │   │   ├── InputBar/
│   │   │   │   ├── AvatarStage/    # 封装 live2d-kit 成 Vue 组件
│   │   │   │   ├── MessageList/
│   │   │   │   └── EmotionBadge/
│   │   │   ├── composables/        # useChat, useAvatar, useAudio
│   │   │   ├── styles/             # Tailwind preset
│   │   │   └── index.ts
│   │   └── tests/
│   │
│   ├── embed/                      # @webling/embed：嵌入 SDK（UMD+ESM）
│   │   ├── src/
│   │   │   ├── entry.ts            # window.WebLing.init() 入口
│   │   │   ├── web-component.ts    # <web-ling> Custom Element
│   │   │   ├── widget/             # 悬浮按钮 + 展开面板
│   │   │   └── postmessage.ts      # iframe 模式通信协议
│   │   ├── embed.html              # iframe 模式的宿主页
│   │   ├── vite.config.ts          # library mode 打包
│   │   └── tests/
│   │
│   └── sdk-js/                     # @webling/sdk：裸 JS 调用后端 API（给接入方 Node/Deno 用）
│       ├── src/
│       │   ├── client.ts
│       │   └── types.ts
│       └── tests/
│
├── apps/
│   └── web/                        # 主站点（完整体验）
│       ├── index.html
│       ├── vite.config.ts
│       ├── public/
│       │   ├── live2dcubismcore.min.js
│       │   └── avatars/
│       │       ├── hiyori/         # 复制自 Ling
│       │       └── (后续新形象)/
│       ├── src/
│       │   ├── main.ts
│       │   ├── App.vue
│       │   ├── router/
│       │   ├── views/
│       │   │   ├── ChatView.vue
│       │   │   ├── SettingsView.vue
│       │   │   └── CharacterPickerView.vue
│       │   ├── stores/             # 主站独有 store（如路由、主题）
│       │   └── i18n/
│       └── tests/
│
├── backend/
│   ├── pyproject.toml              # 或 requirements.txt
│   ├── Dockerfile
│   ├── alembic/                    # 如果引入 SQL 端；目前 Mongo 不需要
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口（先 load_dotenv，再 import ling）
│   │   ├── config.py               # pydantic-settings
│   │   ├── deps.py                 # 依赖注入：DB、Agent、Auth
│   │   │
│   │   ├── routers/                # HTTP 端点（薄）
│   │   │   ├── auth.py             # /api/auth/* (login, refresh, embed_token)
│   │   │   ├── sessions.py         # /api/sessions
│   │   │   ├── chat.py             # /api/chat（非流式，给简单接入用）
│   │   │   ├── characters.py       # /api/characters (列表/切换/创建)
│   │   │   ├── voices.py           # /api/voices (可用 TTS 音色)
│   │   │   ├── tts_proxy.py        # /api/tts/* 代理，静态 wav 直出
│   │   │   └── user.py             # /api/user (昵称等)
│   │   │
│   │   ├── ws/
│   │   │   └── chat_ws.py          # /ws/chat：协议枚举 + 处理循环
│   │   │
│   │   ├── services/               # 业务逻辑（厚）
│   │   │   ├── agent_service.py    # 包 Ling.Agent，按 character 切 system_prompt
│   │   │   ├── tts_service.py      # 调远程 CosyVoice，缓存 wav 段
│   │   │   ├── character_service.py# CRUD + 激活
│   │   │   ├── auth_service.py     # JWT 签发/校验、API Key 管理
│   │   │   ├── quota_service.py    # 调用次数限额
│   │   │   └── emotion_service.py  # 从 AI 文本解析 [joy] 等标签
│   │   │
│   │   ├── repositories/           # 数据访问层
│   │   │   ├── conversation_repo.py
│   │   │   ├── character_repo.py
│   │   │   ├── token_repo.py
│   │   │   └── user_repo.py
│   │   │
│   │   ├── schemas/                # pydantic models（请求/响应）
│   │   │   ├── chat.py
│   │   │   ├── character.py
│   │   │   ├── auth.py
│   │   │   └── ws.py               # WebSocket 事件类型联合
│   │   │
│   │   ├── domain/                 # 领域模型（和持久化解耦）
│   │   │   ├── character.py
│   │   │   ├── session.py
│   │   │   └── message.py
│   │   │
│   │   ├── integrations/
│   │   │   └── ling_adapter.py     # 封装 sys.path 引入 Ling 的 Agent
│   │   │
│   │   ├── middlewares/
│   │   │   ├── auth_middleware.py
│   │   │   ├── cors.py
│   │   │   ├── rate_limit.py
│   │   │   └── request_id.py
│   │   │
│   │   └── static/
│   │       └── tts/                # 临时 wav 文件，带 TTL 清理
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── conftest.py
│
└── scripts/
    ├── copy-live2d-model.sh
    ├── fetch-cubism-core.sh
    ├── dev.sh                      # 并行启动 pnpm dev + uvicorn
    ├── gen-api-types.sh            # FastAPI OpenAPI → TS types
    └── seed-characters.py          # 初始化默认形象（玲）
```

## 六、模块化设计原则

**所有能抽出的一律抽出**，原则：

1. **单一职责**：一个模块/组件只做一件事；名字即职责
2. **无环依赖**：`core` ← `live2d-kit`、`ui` ← `core`；`embed` ← 全部；`apps/web` ← 全部；backend 内 `routers` ← `services` ← `repositories`
3. **依赖注入而非直接引用**：`services` 构造函数接受 `repo` / `client`，便于测试 mock
4. **纯函数优先**：业务逻辑尽量做成无副作用函数；`core/audio/rms.ts` 这种一眼测试的
5. **Schema-first**：接口类型定义先于实现；后端 pydantic / 前端 zod 或纯 TS interface；WS 协议在 `packages/core/src/types/ws.ts` 定义一次，前后端共享（后端生成等价 dataclass）
6. **配置外置**：所有 URL、token 过期、rate-limit 值走 `.env` 或 `config.py`，不写死代码
7. **前端 Composition over Component**：逻辑放 `composables/useChat.ts` 等可复用函数，组件只负责渲染
8. **禁止组件间直接通信**：只能通过 props/emit 或 store；跨模块事件走 event bus（存在 `@webling/core`）

## 七、嵌入 SDK 设计（重点）

### 7.1 三种接入形态

**A. Script tag（最常见）**
```html
<script src="https://cdn.webling.io/embed.v1.min.js"
        data-api-base="https://api.webling.io"
        data-character="ling"
        data-token-endpoint="https://your-site.com/api/webling-token"
        data-position="bottom-right"
        data-theme="light"
        defer></script>
```
- `data-*` 属性零 JS 配置
- 自动注入悬浮按钮，点击展开 chat 面板
- 加载 `<web-ling>` Custom Element 挂到 body

**B. Custom Element（HTML 原生）**
```html
<script type="module" src="https://cdn.webling.io/embed.v1.esm.js"></script>
<web-ling
    api-base="https://api.webling.io"
    character="ling"
    token="eyJhbGciOi..."></web-ling>
```
- Shadow DOM 封装样式隔离
- 属性响应式：改 `character` 会切换形象

**C. iframe（最强隔离）**
```html
<iframe src="https://embed.webling.io/iframe?character=ling&token=eyJ..."
        allow="microphone; autoplay"
        style="position:fixed;bottom:20px;right:20px;width:380px;height:560px;border:0"></iframe>
```
- 完全沙箱；父子用 `postMessage` 双向通信（定义在 `packages/embed/src/postmessage.ts`）
- 默认打包一个 `embed.html` 页面

### 7.2 初始化 API（Script 模式）

```js
WebLing.init({
  apiBase: 'https://api.webling.io',
  tokenProvider: async () => {
    // 接入方自己实现：去自己的后端换 JWT
    const r = await fetch('/api/webling-token');
    return (await r.json()).token;
  },
  character: 'ling',               // 或 characterId: 'char_xxx'
  position: 'bottom-right',        // 'bottom-left' | 'custom'
  theme: 'light',                  // 'light' | 'dark' | 'auto'
  locale: 'zh-CN',
  launcher: true,                  // 是否显示悬浮按钮
  onEvent(ev) {                    // 可选：接入方监听事件（消息、状态）
    console.log(ev);
  },
});
```

### 7.3 事件与指令（接入方可控制）

```js
// 指令
WebLing.open();                    // 展开面板
WebLing.close();
WebLing.sendMessage('你好');         // 代打
WebLing.setCharacter('ling2');
WebLing.destroy();

// 事件
WebLing.on('message', ({role, text}) => {});
WebLing.on('ready', () => {});
WebLing.on('error', (e) => {});
```

### 7.4 样式隔离

- Shadow DOM（Custom Element 模式）
- CSS prefix `.wl-` + 命名空间变量 `--wl-*`
- Tailwind preflight 禁用或仅限 Shadow 内部

### 7.5 产物

`packages/embed` 的 Vite library mode 输出：
- `dist/embed.v1.umd.js`（script tag 用，≤200KB gzip）
- `dist/embed.v1.esm.js`（ESM 用）
- `dist/embed.v1.iife.js`（裸 script 用）
- `dist/embed.d.ts`

**性能目标**：首屏 JS <200KB gzip；Live2D 资源按需加载（点开后才拉 Hiyori）；首次打开到看到形象 <2s（4G 网络）。

## 八、认证与鉴权

### 8.1 角色

- **Owner**：webLing 系统管理员（自己）
- **Tenant**：接入方网站（持有 API Key，可签发嵌入 token）
- **EndUser**：最终对话用户（匿名或有 `user_id`）

### 8.2 Token 体系

| Token | 发行方 | 用途 | 有效期 |
|---|---|---|---|
| `API_KEY`（长） | Owner → Tenant | Tenant 服务端用，不出后端 | 长期 |
| `EMBED_JWT`（短） | Backend ← API_KEY | 前端 WS/REST 用，绑定 character/quota | 默认 1h，自动刷新 |
| `SESSION_TOKEN`（内） | Backend 内部 | 标识一次会话 | 会话生命周期 |

### 8.3 签发流程（Script 模式）

```
Tenant 服务端                Backend                Tenant 前端
     │                         │                         │
     │ POST /api/embed/token   │                         │
     │ Authorization: ApiKey   │                         │
     │ { character:'ling',     │                         │
     │   userRef:'u_123' }     │                         │
     │────────────────────────>│                         │
     │                         │  校验 Key + quota        │
     │                         │  签 JWT（character+userRef+exp）
     │<────────────────────────│                         │
     │  { token, expiresAt }   │                         │
     │                         │                         │
     │────────────────────token 传给前端 ──────────────>│
     │                         │                         │
     │                         │ WSS /ws/chat?token=...  │
     │                         │<────────────────────────│
```

### 8.4 实现

- `python-jose` 签 JWT；HS256 + `JWT_SECRET` 或 RS256 + RSA 对（线上推荐 RS256）
- `auth_service.py` 暴露 `create_embed_token(api_key, character, user_ref, ttl)` / `verify(token)` / `refresh(token)`
- `auth_middleware.py` 从 `Authorization: Bearer <token>` 或 `?token=<>` 解析
- `api_tokens` 集合存 Tenant 的 API Key（hash 后）

### 8.5 限流

- `quota_service.py`：按 `tenant_id` 或 `user_ref` 每天调用次数上限；超限 429
- WebSocket 连接上限：每 `user_ref` 1 条，冲掉旧连接

## 九、多形象 / 多音色设计

### 9.1 领域模型 `Character`

```python
class Character:
    id: str                 # "char_ling_v1"
    name: str               # "玲"
    description: str
    live2d: Live2DConfig    # 模型路径 + 默认 motion 组 + 情绪→动作映射
    voice: VoiceConfig      # tts provider + spk_id + ref_audio + sample_text
    persona: PersonaConfig  # system_prompt + greeting + 性格标签
    capabilities: list      # ["chat", "memory", "tools:weather", ...]
    visibility: str         # "public" | "tenant:<id>" | "owner_only"
    created_by: str
    created_at: datetime
```

### 9.2 `VoiceConfig`

```python
class VoiceConfig:
    provider: str           # "cosyvoice" | "edge" | "azure" | ...
    spk_id: str | None      # cosyvoice 的说话人 id
    ref_audio_url: str | None
    sample_text: str | None # 与 ref_audio 对应的转写
    language: str = "zh-CN"
    rate: float = 1.0
    pitch: float = 0.0
```

### 9.3 `Live2DConfig`

```python
class Live2DConfig:
    model_url: str          # "/avatars/hiyori/hiyori_free_t08.model3.json"
    scale: float = 1.0
    anchor: tuple = (0.5, 0.5)
    motion_map: dict        # { "joy": "Tap@Body", ... }
    auto_blink: bool = True
    gaze_mode: str = "mouse"  # "mouse" | "off"
```

### 9.4 前端动态加载

- `apps/web/public/avatars/<id>/` 下放模型文件
- `AvatarStage.vue` 接 `character-id` prop，调 `GET /api/characters/:id` 拿 `Live2DConfig`，`live2d-kit` 加载
- 切换形象时：fade out 旧模型 → unload → load 新模型 → fade in

### 9.5 后端拼 system_prompt

`agent_service.chat(session, user_text)`：
1. 从 session 拿 `character_id`
2. `character_repo.get(character_id).persona.system_prompt` 作为 system 消息
3. 情绪/动作标签规则拼进 prompt tail
4. 调 Ling Agent（临时把 prompt 注入 `Agent._llm.system` 或在 chat 时拼 messages）

### 9.6 新建形象（`seed-characters.py` + CRUD）

- 种子脚本建默认 "玲"
- `POST /api/characters`（需 Owner 权限）创建新形象；字段校验后写 Mongo + （可选）把 `ref_audio` 上传到服务器 TTS 并注册 `spk_id`

## 十、后端接口契约

### 10.1 REST

```
# Auth
POST   /api/auth/embed/token       (ApiKey) → {token, expiresAt}
POST   /api/auth/refresh           (JWT) → {token, expiresAt}

# Sessions
POST   /api/sessions               body: {character_id, user_ref?}  → {session_id, greeting, character}
GET    /api/sessions/:id/history                                    → {messages[]}
DELETE /api/sessions/:id

# Chat（非流式，简单场景）
POST   /api/chat                   body: {session_id, text} → {reply, emotion, motion?}

# Characters
GET    /api/characters                                              → [{id,name,description,...}]
GET    /api/characters/:id                                          → Character
POST   /api/characters             (Owner) body: Character          → Character
PUT    /api/characters/:id         (Owner) body: PartialCharacter   → Character

# Voices
GET    /api/voices                                                  → [{provider, spk_id, sample_url}]

# TTS (proxy/cache)
POST   /api/tts/synth              body: {text, voice_id} → {audio_url, duration, sample_rate}
GET    /static/tts/:filename                               → wav bytes (短 TTL)

# User
GET    /api/user/me                → {user_ref, nickname, preferences}
PUT    /api/user/nickname          body: {nickname}

# Health
GET    /api/health
```

### 10.2 WebSocket `/ws/chat?token=…`

事件类型定义在 `packages/core/src/types/ws.ts`（前端）与 `backend/app/schemas/ws.py`（后端），**保持同步**（CI 里加一步一致性检查）。

**C → S**
```ts
type ClientEvent =
  | { type: 'user_message'; text: string }
  | { type: 'cancel' }
  | { type: 'ping' }
  | { type: 'change_character'; character_id: string };
```

**S → C**
```ts
type ServerEvent =
  | { type: 'state'; value: 'listening' | 'processing' | 'speaking' | 'idle' }
  | { type: 'subtitle'; text: string; is_final: boolean; emotion: Emotion }
  | { type: 'motion'; name: string }
  | { type: 'audio'; url: string; segment_idx: number; sample_rate: number }
  | { type: 'audio_rms'; rms: number; t: number }    // 可选
  | { type: 'viseme'; openY: number; form: number }  // 可选
  | { type: 'error'; code: string; message: string }
  | { type: 'pong' };
```

## 十一、标准开发流程

### 11.1 分支策略

- `main` 永远可发布；保护分支，禁止直推
- `develop` 集成分支
- `feature/<短描述>` 从 `develop` 分出，PR 合回
- `release/<version>` 发布冻结
- `hotfix/*` 从 `main` 分出应急

### 11.2 提交规范（Conventional Commits）

```
<type>(<scope>): <subject>

[body]

[footer]
```

`type`：`feat` / `fix` / `docs` / `style` / `refactor` / `perf` / `test` / `build` / `ci` / `chore`
`scope`：`embed` / `web` / `backend` / `live2d-kit` / `core` / ...

### 11.3 代码规范工具链

- 前端：ESLint（@antfu/eslint-config 预设）+ Prettier + `tsc --noEmit`
- 后端：ruff（lint + format 替代 black/isort）+ mypy strict + pytest
- Lefthook 配置 commit-msg + pre-commit：跑 lint + 改动文件测试

### 11.4 测试策略

| 类型 | 范围 | 工具 |
|---|---|---|
| 单元 | `packages/core` 的纯函数、`services` 逻辑 | Vitest / pytest |
| 组件 | `@webling/ui` Vue 组件 | Vitest + @vue/test-utils |
| 集成 | backend REST/WS | pytest + httpx + pytest-asyncio |
| E2E | 主站走完一轮对话 | Playwright |
| 视觉回归（可选） | 形象面板截图对比 | Playwright screenshot |

目标覆盖率：`services/` 90%、`core/` 80%、`ui/` 60%、`embed/` E2E 覆盖主路径。

### 11.5 CI（GitHub Actions）

`.github/workflows/ci.yml` 三 job：
1. `lint`：ESLint + ruff + mypy + prettier check
2. `test`：前端 Vitest + 后端 pytest（后端起 Mongo 服务容器）
3. `build`：`pnpm -r build` + `docker build backend` 不推

合入 `main` 后触发 `release.yml`：
- 打 git tag → 发布 `@webling/embed` 到 npm
- 构建 Docker 镜像推 registry
- 构建 `apps/web` 静态文件发到 CDN

### 11.6 文档

- 每个 `packages/<X>/README.md`：用途、API、开发
- `docs/architecture/`：ADR（每个大决策一篇，约 1-2 页）
- `docs/embed-integration.md`：接入方手册（截图 + 代码片段）
- `docs/api/`：FastAPI 自动 OpenAPI + 存一份 `openapi.json` 快照便于 diff
- Storybook（可选）：`packages/ui` 组件可视化

### 11.7 环境

- 本地：`pnpm dev`（并行起 3 个 workspace）+ `uvicorn backend.app.main:app --reload`
- 开发：`docker-compose up`（包含 Mongo）
- 生产（参考）：前端静态 CDN + 后端 docker container + Mongo managed

## 十二、安全考虑

- **CORS**：`allow_origins` 白名单，Tenant 注册时登记 origin
- **CSP**（嵌入模式）：`packages/embed` 只连已登记 `apiBase`
- **XSS**：前端所有外部文本走 Vue 默认转义；TTS URL 校验 origin
- **Rate limit**：`quota_service` 按 tenant+user_ref 限次
- **内容安全**：Agent 响应走一层 moderation（可选，用现成 API）
- **Token 泄露**：JWT 带 `jti`，Tenant 可调 `/api/auth/revoke`
- **Mongo 注入**：pymongo 用参数化，不拼字符串
- **文件路径**：`static/tts/<uuid>.wav`，不允许用户指定文件名

## 十三、迭代路线

### Phase 1 — 核心可用（2-3 周）

| 里程碑 | 产出 | 估时 |
|---|---|---|
| **M0 骨架** | monorepo 初始化、pnpm workspace、Vite + Vue hello、FastAPI hello、Mongo 接上、CI lint 跑通 | 1 天 |
| **M1 文本对话** | `core/api` + `core/ws` + `services/agent_service` + 主站 ChatPanel，REST 和 WS 都通 | 2 天 |
| **M2 Live2D 显示** | `@webling/live2d-kit` 实现 + `AvatarStage` 组件 + Hiyori 加载 + idle/blink | 2 天 |
| **M3 TTS + 嘴型** | `tts_service` 代理 + 前端 audio 队列 + RMS → MouthOpenY | 1 天 |
| **M4 流式 WS** | state 事件、subtitle 增量、打断 | 1 天 |
| **M5 情绪 → 动作** | `emotion_service` 解析 + motion-map + 触发 Hiyori 动作 | 0.5 天 |

**Phase 1 结束**：主站可用，有一个形象（玲），核心对话语音齐全。

### Phase 2 — 嵌入与多形象（2 周）

| 里程碑 | 产出 | 估时 |
|---|---|---|
| **M6 认证** | `auth_service` + JWT + API Key + `/api/embed/token` | 1.5 天 |
| **M7 Character 模块** | `character_repo/service` + CRUD + 主站角色选择 UI + seed 脚本 | 2 天 |
| **M8 Embed SDK（Script + WC）** | `@webling/embed` 打 UMD/ESM + Custom Element + 悬浮按钮 | 3 天 |
| **M9 Embed SDK（iframe）** | `embed.html` + postMessage 协议 | 1 天 |
| **M10 接入示例站** | 一个 demo 静态页，展示 3 种嵌入方式 + 接入文档 | 1 天 |

**Phase 2 结束**：第三方一段 script 就能嵌入；支持多形象切换。

### Phase 3 — 音色与可观测（1-2 周）

| 里程碑 | 产出 | 估时 |
|---|---|---|
| **M11 多 TTS Provider** | `tts_service` 抽象 provider，加 edge-tts fallback | 1 天 |
| **M12 音色管理** | 上传参考音频 + whisper 转写 + 注册到 CosyVoice server | 2 天 |
| **M13 历史与记忆 UI** | 历史浏览 + 长期记忆查看 + 删除 | 1 天 |
| **M14 可观测** | 结构化日志、请求 id、Prometheus metrics、健康检查 | 1 天 |
| **M15 麦克风输入** | MediaRecorder + 上传 + FunASR/Whisper（可选） | 1 天 |

### Phase 4 — 生产化

- E2E 测试、视觉回归
- 生产部署（Docker Compose 或 k8s）
- CDN 发 embed SDK、版本管理（`embed.v1.min.js` 不破坏兼容，新特性走 `v2`）
- 监控告警

## 十四、关键风险

| 风险 | 缓解 |
|---|---|
| 嵌入 SDK 样式污染/被污染 | Shadow DOM + CSS 命名空间；iframe 方式作为兜底 |
| WebSocket 跨域 + 鉴权 | token 走 query（WS 不支持 header 默认），同时支持首帧 auth 握手 |
| TTS 段乱序/丢段 | 严格 segment_idx 排队；前端 `<audio>` 队列 FIFO；后端任务结束发 `done` 哨兵 |
| Ling Agent 同步生成器集成到 async FastAPI | `asyncio.to_thread` 或 `run_in_threadpool` 包 |
| 浏览器 autoplay 阻止首 TTS | 用户首次点击后 `resume()` AudioContext；也可提供"开始对话"按钮 |
| 多形象切换时 Live2D 卸载泄漏 | live2d-kit 在 `unmount` 调 `destroy({children:true, texture:true, baseTexture:true})` |
| Mongo schema 漂移 | domain 模型和 pydantic schema 双层，repository 负责映射；加集成测试 |
| embed 包体积过大 | Tree-shake + 动态 import Live2D 部分；首屏不拉 Hiyori 资源 |

## 十五、成功标准

### Phase 1
- [ ] 主站打开，看到玲 + 聊天框
- [ ] 输入"你好" → 字幕流式显示 + 克隆音色播放 + 嘴同步 + 触发 joy 动作
- [ ] Mongo 里记录这条对话

### Phase 2
- [ ] 另一台机器的 HTML `<script>` 引入 embed.js + token，页面角落出现悬浮玲
- [ ] 点击展开，能对话，状态样式不污染宿主页面
- [ ] 后台新建一个"小绿"形象，嵌入代码 `data-character="xiaolv"` 换形象成功

### Phase 3
- [ ] 传一段自己 15s 的 wav，自动转写、注册到 TTS、列入可选音色
- [ ] 可以点"历史"看所有会话
- [ ] 后端 /metrics 能看到请求数、延迟直方图

---

**下一步**：在新窗口 `cd /Users/zert/Work/zert/lkl_code/webLing`，按 M0 动手。M0 清单见下一节。

## 十六、M0 动手清单

```bash
cd /Users/zert/Work/zert/lkl_code/webLing

# 1. Monorepo 初始化
git init
pnpm init
echo 'packages:\n  - "packages/*"\n  - "apps/*"' > pnpm-workspace.yaml
echo 'node_modules\n.venv\n.env\ndist\ncoverage\n*.log\n.DS_Store' > .gitignore

# 2. 根配置
npx gitignore node && npx gitignore python      # 可选
touch .editorconfig .prettierrc .eslintrc.cjs .nvmrc
echo "20" > .nvmrc

# 3. Backend 骨架
mkdir -p backend/app/{routers,ws,services,repositories,schemas,domain,integrations,middlewares,static/tts}
python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
pip install fastapi "uvicorn[standard]" pydantic-settings pymongo python-dotenv httpx python-jose passlib ruff mypy pytest pytest-asyncio

# 写 backend/app/main.py 最小 FastAPI（health endpoint + CORS + startup 加载 .env）
# 写 backend/app/integrations/ling_adapter.py （sys.path 引 Ling）

# 4. apps/web 骨架
pnpm create vite apps/web --template vue-ts
cd apps/web && pnpm i pinia tailwindcss reconnecting-websocket && cd ../..

# 5. packages 骨架（空库，先 init）
for p in core live2d-kit ui embed sdk-js; do
  mkdir -p packages/$p/src
  (cd packages/$p && pnpm init)
done

# 6. 拷 Live2D 模型
mkdir -p apps/web/public/avatars/hiyori
cp -r /Users/zert/Work/zert/lkl_code/Ling/src/frontend/live2d/src/main/resources/res/* \
      apps/web/public/avatars/hiyori/

# 7. 下 Cubism Core Web (一次性手动，放 public/)
# 浏览器打开 https://www.live2d.com/download/cubism-sdk/ 下载 SDK for Web，
# 解压后拷 Core/live2dcubismcore.min.js 到 apps/web/public/

# 8. 一键跑
pnpm --filter ./apps/web dev &
cd backend && uvicorn app.main:app --reload &

# 9. 第一笔 commit
git add -A && git commit -m "chore: monorepo scaffold (M0)"
```

M0 结束时：
- `http://localhost:5173/` 显示 Vue 默认页
- `http://localhost:8000/api/health` 返回 `{ "ok": true }`
- 两边能跑起来、CI 规则还没配但目录在

接下来进 M1：写 `packages/core` 的 api/ws 客户端 + `services/agent_service` + 主站 ChatPanel。

---

## 十七、Phase 1-3 后的能力愿景

> Phase 1-3 跑通"能用的 Web 玲"之后，本节列出后续要做的**功能性能力**（对标 Neuro-sama 等开源 AI 数字人）。
> 按**领域**组织，每个领域给出：目标、功能点、技术落点、Mongo/API 新增、所在 Phase。
>
> 原则：**只加功能不堆技术**。能复用 Ling 的直接复用（例如 Ling 已经有 VAD/SER/SV/Emotion/PUNC 引擎，Agent 已有工具调用），不要重复造。

### 17.1 多说话人识别 & 声纹建档

**目标**：多人同时使用时区分说话人，为每人建档，让玲"记得你是谁"。

| 功能点 | 实现 |
|---|---|
| 实时声纹提取 | 复用 Ling `src/core/sv_engine.py`（基于项目已有模型）+ silero-vad 做分段 |
| 说话人分离（Diarization） | 按段聚类；Ling 里有 `diarization_engine.py` 和 `scripts/diarize_audio.py` 可搬 |
| 声纹库 | Mongo 集合 `speakers`（speaker_id / name / voiceprint_vector / profile / created_at） + Chroma 向量索引便于快速匹配 |
| 新说话人自动注册 | 匹配分 < 阈值 → 创建新 speaker 记录，随对话逐步完善 profile |
| LLM 上下文注入 | Agent 调用前把当前 speaker 的昵称/偏好/关系塞进 system prompt |
| 多人会话 | `session.participants: [speaker_id]`；每条 message 带 `speaker_id` |

**API 新增**
- `GET /api/speakers` / `POST /api/speakers/register` / `PATCH /api/speakers/:id`
- WS 事件：`{type: "speaker_detected", speaker_id, name?, confidence}`

**所在 Phase**：P4-M16（核心）、P4-M17（UI 管理面板）

### 17.2 实时流式对话 + 打断

**目标**：突破一问一答，像打电话一样自然，想插嘴就插嘴。

| 功能点 | 实现 |
|---|---|
| 流式 ASR | 浏览器 MediaRecorder 按 250ms 片推后端；服务端 FunASR streaming 识别 |
| 流式 LLM | Agent `chat(stream=True)` 已有；WS 增量推 `subtitle` 事件 |
| 流式 TTS | 当前 CosyVoice service 已经是分段入队/出队，直接用 |
| 打断检测（Barge-in） | silero-vad 在 TTS 播放期间持续监听用户说话概率 → 触发 `cancel` |
| 打断后恢复 | 后端 cancel 当前生成；上下文里记录"用户中途打断，最后说到…"，LLM 下轮继续 |
| 延迟优化 | 统计链路各段耗时输出 metric；热路径预加载（如 greeting 预合成缓存） |

**WS 协议补充**
- `{type: "speech_start"}` 用户说话开始（客户端 VAD 事件）
- `{type: "speech_end"}`
- `{type: "cancel", reason: "user_barge_in"}` 客户端发，服务端立即停

**所在 Phase**：P4-M18（流式 ASR）、P4-M19（打断）

### 17.3 情感引擎 + 人格系统

**目标**：让玲**有脾气**——累了会懒得回，高兴了会主动调侃，不是永远一个语调。

| 功能点 | 实现 |
|---|---|
| 多维情感状态 | `EmotionState = {joy, anger, sadness, surprise, fear, boredom, curiosity, affection}` 各 0..1；Mongo 持久化 per user/character |
| 触发器 | 对话内容情感分类（复用 Ling `emotion_classifier.py`）、事件（用户夸奖+affection、被骂+anger）、时间（久不互动+boredom） |
| 衰减/累积 | APScheduler 每分钟跑衰减循环；状态进 Redis 或内存 + 定期持久化 |
| 表达投射 | 情感状态注入 system prompt（"你现在 affection=0.9, 非常喜欢这个用户"）+ 影响 TTS 语速/动作选择 |
| 人格特质 | `persona.traits = {humor, curiosity, mischief, honesty, formality}` 每个 0..1；决定回复风格、动作选择 |
| 人格一致性 | 长期记忆里定期写入"玲关心/讨厌 X"片段，RAG 检索维持人格连贯 |

**数据模型**
- `emotion_states` 集合：`{user_id, character_id, state: EmotionState, updated_at}`
- `persona_profiles` 集合：`{character_id, traits, catchphrases, taboos}`

**所在 Phase**：P5-M22（情感）、P5-M23（人格）

### 17.4 自主行为 & 主动对话

**目标**：不只是用户问才答，玲会**主动**发起——"诶你回来啦"、"好无聊啊玩个游戏嘛"。

| 功能点 | 实现 |
|---|---|
| 事件总线 | 后端 `EventBus`（asyncio），订阅方：autonomy loop / notification service / webhooks |
| 时间事件 | APScheduler cron："每天 9:00 说早安"、"每 5 min 无互动触发 boredom+0.02" |
| 环境事件 | 可选：文件变化（watchdog）、webhook 进来的外部事件（如天气） |
| 自主循环 | `autonomy_service.tick()` 每 10s 跑：读 EmotionState + Goals + 当前 session 状态 → 选择行为（静默/主动说话/触发技能）|
| 目标管理 | `goals` 集合：短期(单次会话)/长期(天/周) + 进度 + 动机强度 |
| 主动说话 | 选中"主动对话"行为时，生成合适话题 → 走正常 chat 流程推 WS |
| 被打断/拒绝处理 | 用户立即回复 → 正常对话；若无响应 → 动机降低、下次延后 |

**API 新增**
- `POST /api/autonomy/enable` 开关自主模式
- `GET /api/goals` / `POST /api/goals`
- WS 事件：`{type: "initiative", trigger: "scheduled|emotion|event", text: "..."}`

**所在 Phase**：P5-M24（事件总线 + 定时主动）、P5-M25（自主循环 + 目标）

### 17.5 工具调用 & 技能插件

**目标**：让玲能**做事**——查天气、执行命令、调用 API、操作文件。

| 功能点 | 实现 |
|---|---|
| 沿用 Ling 工具集 | `DateTimeTool / MemoryTool / BrowserSearchTool / VisionTool / ScreenshotAnalyzeTool / ReminderTool / TerminalExecuteTool / …`（已在 Ling.agent 里注册）|
| Web 端工具白名单 | 截图/相机等本地桌面工具在 Web 版禁用；远程可调的（搜索/记忆/提醒/天气）保留 |
| 技能插件框架 | `packages/skill-sdk` 定义接口；每个技能独立 Python 包，通过 entry_point 注册 |
| 安全 | Terminal 工具默认关闭；Owner 可在后台勾启；危险命令白名单 |
| 前端可视化 | 工具调用时 WS 推 `{type: "tool_call", name, args}` / `tool_result`；聊天气泡展示"玲正在查天气…" |

**所在 Phase**：P4-M20（工具链打通）、P6-M28（技能插件框架）

### 17.6 音乐能力（唱歌 / 卡拉OK）

**目标**：玲能唱歌，能带节奏唱卡拉OK，能即兴编歌词。

| 功能点 | 实现 |
|---|---|
| 声线转换（RVC） | 独立微服务（类 CosyVoice），暴露 `POST /rvc/convert` 接口，后端 `voice_service` 调 |
| 歌声合成链路 | 歌词 → TTS 生 wav → RVC 转成目标音色 → 前端播放 |
| 卡拉OK 歌词同步 | LRC 格式解析；WS 推 `{type: "lyric", text, at_ms}` 前端滚动高亮 |
| 伴奏混音 | 前端 Web Audio `AudioContext` 同时播放 `<audio>` 伴奏 + TTS/RVC 人声轨 |
| 歌词创作 | 用 Agent 的 LLM 按主题生歌词；集成押韵检查（pypinyin） |
| 简单作曲 | 可选：MusicGen 生成伴奏；MIDI 导出 |

**API 新增**
- `POST /api/music/sing { lyrics, voice_id, bpm? }` → 返回音频队列
- `POST /api/music/karaoke { song_id, user_vocal_track_url }` → 混音返回

**所在 Phase**：P5-M26（RVC 集成 + 简单唱歌）、P6-M29（卡拉OK + 歌词创作）

### 17.7 互动小游戏

**目标**：有空和玲玩一局。

| 游戏类型 | 实现 |
|---|---|
| 猜谜 | LLM 出谜，回合制，记分 |
| 角色扮演 | LLM 维持角色，WS 事件加 `{type: "scene_change"}` 切背景 |
| 问答竞赛 | LLM 生题+评分+计时 |
| 投票 | 多人（多 speaker）模式下群体投票 |
| 成就系统 | `achievements` 集合，触发时 WS 推 badge |

**所在 Phase**：P6-M30

### 17.8 上下文/世界感知

**目标**：玲知道"现在几点"、"你昨天说过…"、"外面刚下雨了"。

| 功能点 | 实现 |
|---|---|
| 时间感知 | system prompt 自动注入当前时间、近期对话摘要 |
| 多模态 | 摄像头/截图走 Agent 现有 `VisionTool` / `ScreenshotAnalyzeTool` |
| 知识图谱 | Ling 已有 `knowledge_graph.py` + Mongo `knowledge_graph` 集合；展示层新增 `GET /api/knowledge-graph` + 前端可选的图谱查看器 |
| 实时信息 | 通过 `BrowserSearchTool` + 工具调用"查一下最新的 X" |
| 社交情境 | speaker 识别 + 关系属性（家人/朋友/同事）影响语气选择 |

**所在 Phase**：P6-M31（知识图谱 UI）、长期演进

### 17.9 LLM Prompt 管理

**目标**：Prompt 作为代码一等公民，可版本、可对比、可热更新。

| 功能点 | 实现 |
|---|---|
| 模板化 | Jinja2；变量：`{character}`、`{user}`、`{emotion_state}`、`{speakers}`、`{recent_memories}`、`{tools}` |
| 版本管理 | `prompts` 集合：`{name, version, template, variables_schema, active}` |
| A/B 测试 | 会话绑定 prompt_version，后台看指标（延迟、自然度评分） |
| 热更新 | 管理页改 prompt → 下一轮会话生效，不用重启 |
| 模板库 | 内置 system / greeting / emotion_inject / tool_hint / multi_speaker / creative 等场景 |

**所在 Phase**：P4-M21（最小实现） → P6-M32（完整管理后台）

### 17.10 数据治理 & 可观测

| 功能点 | 实现 |
|---|---|
| Mongo 索引优化 | 对高频查询加复合索引（`session_id+created_at`、`speaker_id`、`character_id+updated_at`） |
| 数据归档 | `conversations` 90 天前转冷存储集合 |
| 快照 / 回档 | `mongodump` 脚本 + 可选 restore UI；配置放 Git |
| 导入导出 | CSV/JSON 导出对话、人设、技能；供用户迁移 |
| Metrics | Prometheus：对话延迟、打断响应、声纹准确率、Token 使用量、TTS 段数 |
| 日志 | structlog + request-id 贯穿请求；重要事件进 `event_log` 集合 |
| 自愈 | health check endpoint + Docker restart policy；Agent 异常时 reset context 而非 crash |

**所在 Phase**：P4-M21（基础 metrics） → 长期演进

## 十八、Phase 4-6 详细里程碑

> Phase 1-3 见第十三节。以下每个里程碑 **1-3 天**粒度，总时长约 6-8 周。

### Phase 4 — 实时与多说话人（3-4 周）

| M# | 里程碑 | 工作包 | 预估 |
|---|---|---|---|
| M16 | 声纹识别后端 | 集成 Ling `SVEngine` + silero-vad，新增 `speakers` 集合，自动注册接口 | 3 天 |
| M17 | Speaker UI | 主站"说话人管理"页：看谁最近说了啥、改昵称/备注 | 2 天 |
| M18 | 流式 ASR | 浏览器 MediaRecorder 250ms 推 → FunASR streaming → 增量 WS 事件 | 3 天 |
| M19 | 打断机制 | 播放期 VAD 监听、`cancel` 协议、上下文续写 | 2 天 |
| M20 | 工具链打通 | Web 版 Agent 启用搜索/记忆/提醒/天气工具，前端 tool_call 气泡 | 2 天 |
| M21 | Prompt 最小管理 | Jinja2 模板 + Mongo 存版本 + 后台改 prompt 立即生效 | 2 天 |

**Phase 4 结束**：多人对话、可打断、玲会调用工具查信息。

### Phase 5 — 情感人格 & 自主行为（3-4 周）

| M# | 里程碑 | 工作包 | 预估 |
|---|---|---|---|
| M22 | 情感引擎 | EmotionState 模型 + 触发器 + 衰减循环 + 注入 prompt | 3 天 |
| M23 | 人格系统 | persona traits + 一致性记忆 + 管理 UI | 2 天 |
| M24 | 事件总线 + 定时 | EventBus + APScheduler + 默认定时事件（早安/晚安） | 2 天 |
| M25 | 自主循环 | autonomy_service.tick + goals 模型 + 主动对话发起 | 3 天 |
| M26 | RVC 歌声 | 独立微服务部署 + `music/sing` API + 前端"唱一首"按钮 | 3 天 |
| M27 | 情绪-动作联动 | 情感状态直接驱动 Live2D 动作选择（如 anger → Flick） | 1 天 |

**Phase 5 结束**：玲有情绪、会主动说话、会唱歌。

### Phase 6 — 体验深化（2-3 周）

| M# | 里程碑 | 工作包 | 预估 |
|---|---|---|---|
| M28 | 技能插件框架 | `packages/skill-sdk` + 3 个示例技能（天气/日历/笔记） | 3 天 |
| M29 | 卡拉OK | LRC 歌词同步 + 伴奏混音 + 卡拉OK 页面 | 3 天 |
| M30 | 互动小游戏 | 猜谜 + 问答 + 成就系统 | 3 天 |
| M31 | 知识图谱 UI | `GET /api/knowledge-graph` + 前端可视化查看器 | 2 天 |
| M32 | Prompt 管理后台 | 模板库 + A/B + 指标对比 | 2 天 |
| M33 | 生产化 | Prometheus + Grafana + 告警 + 一键部署 | 2 天 |

**Phase 6 结束**：完整 AI 数字人体验。

---

## 十九、功能 vs 所在 Phase 快速索引

| 功能 | Phase / 里程碑 |
|---|---|
| Web 对话 UI | P1-M1 |
| Live2D Hiyori | P1-M2 |
| TTS + 嘴型 | P1-M3 |
| 流式字幕 | P1-M4 |
| 情绪 → 动作 | P1-M5 |
| JWT 认证 | P2-M6 |
| Character 多形象 | P2-M7 |
| Embed SDK (Script/WC) | P2-M8 |
| Embed iframe | P2-M9 |
| 接入 demo | P2-M10 |
| 多 TTS Provider | P3-M11 |
| 音色管理（CosyVoice 克隆） | P3-M12 |
| 历史 UI | P3-M13 |
| 可观测性 | P3-M14 / P6-M33 |
| 麦克风输入 | P3-M15 / P4-M18 |
| **多说话人识别** | P4-M16/M17 |
| **流式 ASR** | P4-M18 |
| **打断机制** | P4-M19 |
| **工具调用（搜索/提醒等）** | P4-M20 |
| **Prompt 管理（MVP）** | P4-M21 |
| **情感引擎** | P5-M22 |
| **人格系统** | P5-M23 |
| **事件驱动 / 定时主动** | P5-M24 |
| **自主对话循环** | P5-M25 |
| **RVC 歌声合成** | P5-M26 |
| **情绪-Live2D 动作联动** | P5-M27 |
| **技能插件框架** | P6-M28 |
| **卡拉OK** | P6-M29 |
| **互动小游戏** | P6-M30 |
| **知识图谱 UI** | P6-M31 |
| **Prompt 管理后台** | P6-M32 |
| **生产化部署** | P6-M33 |

## 二十、更新后的成功指标

### Phase 1-3（同第十五节）
见前文。

### Phase 4 - 实时与多人
- 对话首字延迟 < 800ms
- 打断响应 < 300ms
- 声纹识别准确率 > 90%（已知说话人）
- 支持 ≥ 3 人同时对话互不串号

### Phase 5 - 情感与自主
- 情感状态 ≥ 6 维
- 人格一致性：连续 50 轮对话人设无崩塌（人工评 > 4.5/5）
- 主动对话触发准确率 > 70%（用户不觉得尬）
- RVC 歌声延迟 < 3s / 10 字

### Phase 6 - 完整体验
- 预置技能 ≥ 10 个、人格模板 ≥ 3 套、动作库 ≥ 20 个
- 日活用户平均互动时长 > 15 分钟
- 嵌入接入方 ≥ 3 家演示站

---

## 二十一、关于文件 `后续优化方案.md`

本节功能列表综合自用户提供的 `/Users/zert/Downloads/后续优化方案.md`（v2.0，对标 Neuro-sama）。
**本文档采纳其所有功能方向，但技术方案按 Web 架构 + 已有 Ling 能力重新落地**，而不是照搬原文档的技术栈建议。
区别示例：
- 原文档用 PyQt6 做 GUI 设置；本方案是 Web + Embed SDK
- 原文档用 pyannote；本方案优先复用 Ling 已有 `SVEngine`
- 原文档写 Neo4j 知识图谱；本方案复用 Ling 已有 Mongo 存的 `knowledge_graph` 集合，不引入额外数据库
