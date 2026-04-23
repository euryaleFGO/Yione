# webLing 嵌入集成手册

把 "会动会说话的 Live2D 玲" 嵌入你的网站，三种方式任选其一。

> **TL;DR**：最简单的方式是一段 `<script>` 标签（2 分钟接入），页面右下角就会出现紫色按钮，点击展开聊天面板。

- [1. 准备工作](#1-准备工作)
- [2. 方式 A — Script tag（推荐）](#2-方式-a--script-tag推荐)
- [3. 方式 B — `<web-ling>` 自定义元素](#3-方式-b--web-ling-自定义元素)
- [4. 方式 C — iframe 直连](#4-方式-c--iframe-直连)
- [5. 父子通信（postMessage）](#5-父子通信postmessage)
- [6. 手动程序化 API](#6-手动程序化-api)
- [7. 后端 tenant 配置](#7-后端-tenant-配置)
- [8. CSP / 反代 / HTTPS](#8-csp--反代--https)
- [9. 排错](#9-排错)

---

## 1. 准备工作

1. **找 webLing 管理员要一个 API Key**，并告知你的网站域名（Origin，如 `https://example.com`）。管理员会在后端 `tenants.json` 里登记：
   ```json
   {
     "id": "example",
     "api_key_hash": "<sha256(your-api-key)>",
     "allowed_origins": ["https://example.com", "https://www.example.com"],
     "character_whitelist": ["ling"],
     "daily_quota": 2000,
     "scope": ["chat", "embed"]
   }
   ```
   每天的对话配额、允许使用的角色都在这里控制。
2. **确认 webLing 宿主域名**（下文记作 `<webling-host>`，如 `https://webling.example.com`）。三种接入方式都会从这个域名加载资源和建立 WebSocket。
3. **浏览器要求**：麦克风（语音输入 M18）需要 HTTPS 或 `localhost`；iOS Safari 首次使用需要用户手动点击按钮才能解锁音频自动播放——这部分 webLing 内部已处理。

---

## 2. 方式 A — Script tag（推荐）

在任意 HTML 页面里加一行：

```html
<script
  src="https://<webling-host>/embed/embed.js"
  data-api-key="pk_your_key"
  data-character-id="ling"
  data-position="bottom-right"
  async defer
></script>
```

页面加载后会在**右下角**挂一个紫色圆形按钮，点击展开 380×620 聊天面板（移动端自动全屏）。面板里是完整的 webLing 体验：Live2D 玲 + 流式对话 + TTS 语音 + 嘴型同步 + 情绪动作 + 声纹识别。

### 可用的 `data-*` 属性

| 属性 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `data-api-key` | ✅ | – | 后端签发的 API Key |
| `data-character-id` | | `ling` | 角色 ID，需在 tenant `character_whitelist` 内 |
| `data-position` | | `bottom-right` | 浮动按钮位置：`bottom-right` / `bottom-left` / `top-right` / `top-left` |
| `data-base-url` | | script 所在域 | webLing 宿主域，默认从 script src 推断 |
| `data-api-base` | | = `baseUrl` | 后端 API 域（若与前端分域部署） |
| `data-open-by-default` | | `false` | 设为 `"true"` 时加载就展开，不显示按钮 |

---

## 3. 方式 B — `<web-ling>` 自定义元素

声明式写法，适合 CMS / 可视化编辑器。

```html
<script src="https://<webling-host>/embed/web-component.js" defer></script>

<!-- 浮动模式（默认，行为等同 Script tag） -->
<web-ling
  api-key="pk_your_key"
  character-id="ling"
  position="bottom-right"
></web-ling>

<!-- 内联模式：iframe 直接贴在 <web-ling> 自身里，由宿主决定尺寸 -->
<web-ling
  api-key="pk_your_key"
  character-id="ling"
  embedded
  style="display:block; width:400px; height:600px;"
></web-ling>
```

### 属性对照

| 属性 | 对应 Script tag |
|---|---|
| `api-key` | `data-api-key` |
| `character-id` | `data-character-id` |
| `position` | `data-position` |
| `base-url` | `data-base-url` |
| `api-base` | `data-api-base` |
| `embedded` | — （内联模式独有）|

属性修改后元素会自动重新挂载。

---

## 4. 方式 C — iframe 直连

不想加载任何 JS、只想要最大隔离性：

```html
<iframe
  src="https://<webling-host>/embed/embed.html?api_key=pk_your_key&character_id=ling"
  allow="microphone; autoplay; clipboard-write"
  style="width: 380px; height: 620px; border: 0; border-radius: 12px;"
  title="webLing"
></iframe>
```

URL 支持的 query 参数：

| 参数 | 必填 | 说明 |
|---|---|---|
| `api_key` | ✅ | 后端签发的 API Key |
| `character_id` | | 角色 ID，默认 `ling` |
| `api_base` | | 后端 API 域，默认与当前 iframe 同域 |

**注意**：`allow` 属性里的 `microphone` 是 M18 语音输入所必需，`autoplay` 是 TTS 播放所必需，缺一会导致功能降级。

---

## 5. 父子通信（postMessage）

三种方式下 iframe（子）和你的页面（父）可以用 postMessage 双向通信。

### 5.1 子 → 父（带 `source: 'webling'`）

```ts
window.addEventListener('message', (e) => {
  if (e.data?.source !== 'webling') return;

  switch (e.data.type) {
    case 'webling:ready':         // iframe 加载完，等待初始化
      break;
    case 'webling:session':       // 会话建立成功，带 character_id
      console.log('会话已开 character=', e.data.character_id);
      break;
    case 'webling:state':         // agent 状态：idle | processing | speaking | listening
      updateBadge(e.data.value);
      break;
    case 'webling:message':       // 新消息：role + text + id
      logMessage(e.data);
      break;
    case 'webling:error':         // 启动 / 鉴权 / 会话失败
      alert(`webLing 错误（${e.data.code}）：${e.data.message}`);
      break;
    case 'webling:request_close': // 用户点了 iframe 内的 × 关闭
      hideIframe();
      break;
  }
});
```

### 5.2 父 → 子（带 `target: 'webling'`）

```ts
const iframe = document.querySelector('iframe');

// 程序化发一条用户消息（跟用户在 InputBar 里输入等效）
iframe.contentWindow.postMessage(
  { target: 'webling', type: 'send', text: '你好玲' },
  '*',
);

// 打断当前 turn（相当于用户点击红色"停止"按钮）
iframe.contentWindow.postMessage({ target: 'webling', type: 'interrupt' }, '*');

// 断开连接并通知 iframe 自毁（释放 WS / AudioContext）
iframe.contentWindow.postMessage({ target: 'webling', type: 'close' }, '*');
```

> 所有消息都带 `target: 'webling'` / `source: 'webling'` 标识，避免浏览器扩展或其他 iframe 的噪声被误识别为指令。

---

## 6. 手动程序化 API

Script tag 被加载后会在 `window.WeblingEmbed` 上暴露 `mount()`，适合动态创建 / 多实例场景：

```html
<script src="https://<webling-host>/embed/embed.js"></script>
<!-- 注意：没有 data-api-key，不会自动挂 -->
<script>
  const handle = window.WeblingEmbed.mount({
    apiKey: 'pk_your_key',
    characterId: 'ling',
    position: 'bottom-left',
    openByDefault: true,
    width: 420,
    height: 680,
  });

  // handle.open() / handle.close() / handle.toggle()
  // handle.send('你好')         // 程序化说话
  // handle.interrupt()          // 打断
  // handle.unmount()            // 销毁并移除 DOM
  // handle.iframe               // 直接拿到 iframe 元素，可加样式
</script>
```

---

## 7. 后端 tenant 配置

管理员编辑 `backend/app/data/tenants.json`（或 Mongo `tenants` 集合，M7 以后）：

```json
{
  "tenants": [
    {
      "id": "example",
      "api_key_hash": "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
      "allowed_origins": ["https://example.com", "https://www.example.com"],
      "character_whitelist": ["ling"],
      "daily_quota": 2000,
      "scope": ["chat", "embed"]
    }
  ]
}
```

- `api_key_hash` 是**明文 API Key 的 sha256**。明文只在创建时发给接入方，一次性；不入盘。
- `allowed_origins` 为空数组或 `["*"]` 视为全通（仅开发阶段用）。生产环境务必填具体域名。
- `character_whitelist` 控制这个 tenant 能用的角色。空列表表示全部角色都允许。
- `daily_quota` 超出会在后续里程碑限流。

生成 API Key 的推荐方法：

```bash
# 生成 32 字节随机 key
key=$(openssl rand -hex 32)
echo "给接入方：$key"
# 存哈希到 tenants.json
echo -n "$key" | shasum -a 256 | awk '{print $1}'
```

### dev 模式回退

没检测到 `tenants.json` 时，后端进 dev 模式：任何 API Key 都认成 `demo` tenant，`allowed_origins` 全通。本地联调方便，生产部署前务必创建 `tenants.json`。

---

## 8. CSP / 反代 / HTTPS

### CSP（Content Security Policy）

在接入方网站的 CSP 里需要放行：

```
frame-src https://<webling-host>;
connect-src https://<webling-host> wss://<webling-host>;
script-src https://<webling-host>;  # Script tag / Custom Element 场景
```

WebSocket 必须允许 `wss://`（语音输入 `/ws/asr` 和主对话 `/ws/chat` 都要）。

### HTTPS

生产必须 HTTPS。浏览器 `getUserMedia`（麦克风）在非 HTTPS 下除 `localhost` 外都会拒绝。

### 反代（nginx）

典型配置：

```nginx
location /embed/ {
    # 静态产物（embed.js / web-component.js / embed.html / avatars）
    root /var/www/webling/apps/embed/dist;
    try_files $uri $uri/ =404;
    add_header Cache-Control "public, max-age=31536000, immutable";
}

location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 180s;   # 声纹冷启动 / TTS 长句容忍
}

# WebSocket upgrade
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
location /ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header Host $host;
    proxy_read_timeout 7200s;  # 长连接保活
}
```

---

## 9. 排错

| 现象 | 可能原因 | 处理 |
|---|---|---|
| iframe 空白 + 控制台 `403 origin not allowed` | tenant 的 `allowed_origins` 没登记接入方域名 | 联系管理员补白名单 |
| iframe 显示"鉴权失败" | API Key 写错或被回收 | 检查 `data-api-key` / 请求管理员换发 |
| 玲不出现 / WebGL 报错 | `live2dcubismcore.min.js` 加载失败 | 确认 `<webling-host>/embed/live2dcubismcore.min.js` 200，CSP 放行 |
| TTS 有文字无声音 | 浏览器 autoplay 被拦 | 用户首次必须有交互动作才解锁（点按钮即可）；iOS Safari 尤其严格 |
| 语音输入按钮灰色 | iframe `allow` 少 `microphone` | 加上 `allow="microphone; autoplay; clipboard-write"` |
| 断连 / WS 握手失败 | 反代缺 `Upgrade` header | 按上方 nginx 配置加 `map $http_upgrade $connection_upgrade` + `proxy_set_header Upgrade` |
| WS 4401 close | embed JWT 失效且 apiKey 丢失 | 页面刷新；如果频繁，检查客户端时钟是否严重偏差 |
| 展开面板遮挡网站内容 | z-index 或 position 冲突 | `data-position` 改到空闲角；或加自定义 CSS 压盖 button（z-index 默认 2147483647 最大了，别更高） |
| 同一页想挂多个实例 | Script tag 只认最后一个 `data-api-key` | 用 `window.WeblingEmbed.mount(opts)` 程序化挂多份 |

### 调试模式

iframe 内部就是 `apps/web` 的 Vue 应用，浏览器打开 `https://<webling-host>/embed/embed.html?api_key=...` 直接看到全部控制台输出。`window.__webling` 暴露了 live2d 调试 probe（见 `packages/live2d-kit/src/stage.ts`）。

### 反馈 / 报 bug

代码仓库：`github.com/<org>/webLing`，embed 相关逻辑在 `apps/embed/`。
