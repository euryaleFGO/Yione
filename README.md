# webLing

把 [`Ling`](../Ling) 玲虚拟助手做成 **Web 应用 + 可嵌入 SDK**，并按 **AI 数字人** 方向长期演进（对标 Neuro-sama）。

## 定位

- **主站**：网页对话 + Live2D 形象 + TTS 播放 + 嘴型/表情同步 + 声纹识别 + 麦克风实时对谈
- **嵌入**：一段 `<script>` / `<web-ling>` / `<iframe>`，第三方站点零门槛接入（Phase 2 目标，未开工）
- **多形象 + 多音色**：Character 作为一等数据模型（Phase 2 目标，未开工）
- **Token 认证**：短期 JWT + API Key，Tenant/User 两级隔离（已落）

## 当前状态（2026-04-23）

**13 个里程碑已落地**：M0-M6（Phase 1 核心）+ M16-M18（声纹 + 流式 ASR）+ M34-M36（实时对话循环 + 对话内识别 + viseme 对齐）。代码跑通了：

> 开始对话 → 麦克风长开 → FunASR 识别 → 声纹识别说话人 → LLM 流式生成 → 按句 TTS → Live2D 情绪表情 + 音素嘴型 → 用户开口自动打断回到 listening

完整规划见 [`PLAN.md`](./PLAN.md)，路线图见 [`.planning/ROADMAP.md`](./.planning/ROADMAP.md)，下一步是 **M3.6 TTS 占位音**（快赢，感知首字延迟减半）。

### 已落地能力

| 能力 | 里程碑 | 要点 |
|---|---|---|
| 文本对话 + WS 流式字幕 | M0-M1 | DeepSeek-V3-Enterprise（SenseNova）非推理模型，首 token <1s |
| Live2D Hiyori + TTS 嘴型 | M2-M3 | pixi-live2d-display-lipsyncpatch fork + Cubism Core 4.x；按句切分 pipeline |
| 流式打断（服务端 cancel） | M4 | `asyncio.Task` + `CancelledError` 级联清理 |
| 情绪 → 动作 + 面部表情 | M5 | LLM 打 `[joy]/[anger]/…` 标签；跨 chunk 拼接；边沿触发 motion |
| 9 张 Hiyori 表情 + 持久化 | - | `.exp3.json` × 9；PIXI ticker 每帧硬写 `setParameterValueById` 绕开 idle motion 擦除 |
| JWT + API Key + Origin 白名单 | M6 | `/api/embed/token` 签发；dev 匿名回退；tenant key 存 sha256 |
| 声纹识别后端 + UI | M16-M17 | Ling `SVEngine` (CampPlus 192 维) fail-close；JSON Repo；REST 5 端点；前端录音注册/识别页 |
| 流式 ASR（FunASR 2pass） | M18 | 官方 runtime docker；`2pass-online` partial + `2pass-offline` committed；后端 yield 结构化 `ASREvent` |
| **实时对话循环** | **M34** | InputBar 状态机（idle/listening/processing/speaking）；FunASR `is_final` 自动提交；播放期保持麦克风靠浏览器 AEC 消回声；`speech_start` 打断 |
| **对话内声纹识别** | **M35** | 每句 utterance PCM → WAV → `/api/speakers/identify` → WS 推 `speaker_detected` → 消息气泡贴 speaker 名 |
| **Viseme 嘴型对齐** | **M36** | wav2vec2-xlsr-chinese CTC forced alignment，每段 wav 产 `[{char, t_start, t_end, viseme}]`；前端 PIXI ticker 按 `audio.currentTime` 驱 `ParamMouthForm`（A/O/U/I/E + rest） |
| 三层独立 docker-compose 部署 | - | `deploy/funasr/` + `deploy/tts/` + 根 compose；`scripts/deploy.sh` 一键 |

### Phase 2+ 尚未开工

Phase 2（Character / Embed SDK / 多 Provider / 可观测）、Phase 4 剩余（M19 silero-vad 客户端 VAD、M20 工具链、M21 Prompt 管理）、Phase 5（情感引擎 / 人格 / 自主循环 / RVC 歌声）、Phase 6（技能 / 卡拉OK / 小游戏 / 知识图谱 / 生产化）——均在 `PLAN.md` / `ROADMAP.md` 里作为未来阶段规划，**代码未落**。

## 与 `Ling` 的关系

- `Ling` 仓库**不改**，通过 `sys.path.insert` 引入 Agent 代码
- 复用已部署的 LLM (`192.168.251.56:8080`) / CosyVoice TTS (`:5001`) / FunASR ASR (`:10095`) / MongoDB (本地 Docker `liying-mongo`)
- Hiyori 模型 + 9 张新表情放 `apps/web/public/avatars/hiyori/`
- 声纹 `SVEngine` 直接 import，`[sv]` optional extra（`pip install -e '.[sv]'`）装 torch/funasr/silero-vad

## 技术栈

| 层 | 选择 |
|---|---|
| Monorepo | pnpm workspaces + Turborepo |
| 前端 | Vue 3 + Vite + TypeScript + Pinia + Tailwind |
| Live2D | `pixi-live2d-display-lipsyncpatch@0.5.0-ls-8` + PIXI v7 + Cubism Core 4.x Web |
| 后端 | FastAPI + Python 3.12（uvicorn、pydantic-settings、pymongo、httpx、websockets） |
| 认证 | JWT (python-jose) + API Key (sha256) |
| ASR | FunASR 官方 2pass runtime (C++ 二进制 in docker) |
| TTS | CosyVoice2-0.5B（零样本），内挂 wav2vec2-xlsr 强对齐 |
| 声纹 | Ling SVEngine (CampPlus ONNX 192 维) |
| 测试 | Vitest / Playwright / pytest（backend 已落 53+ 条） |
| CI | GitHub Actions + lefthook |

## 目录结构

```
webLing/
├── packages/
│   ├── core/         纯逻辑（chat / ws / audio / auth / pcm-wav / types）
│   ├── live2d-kit/   PIXI + Live2D 渲染封装（含 viseme ticker + expression ticker）
│   ├── ui/           Vue 组件库
│   ├── embed/        嵌入 SDK（占位，Phase 2 实装）
│   └── sdk-js/       裸 JS 客户端（占位）
├── apps/
│   └── web/          主站 SPA（InputBar / MessageList / AvatarStage / SpeakerView）
├── backend/
│   └── app/          FastAPI（routers / ws / services / repositories / schemas / domain / integrations）
├── deploy/
│   ├── funasr/       官方 runtime docker + entrypoint
│   ├── tts/          CosyVoice + aligner（src/ + Dockerfile）
│   └── README.md     三层部署指南
├── docs/             ADR、接入手册
├── scripts/          deploy.sh / dev.sh / dev-backend.sh
└── .planning/        GSD 工作区（ROADMAP / STATE / phases/）
```

## 核心设计原则

1. **模块化到底**：能抽的都抽到 `packages/` 下；`apps/web` 和 `packages/embed` 只是 `ui + core + live2d-kit` 的组合
2. **Schema-first**：WS 事件类型在 `packages/core/src/types/ws.ts` 与 `backend/app/schemas/ws.py` 同构（人工同步，CI 校验是待偿技术债）
3. **配置外置**：`.env` 驱动（LLM/TTS/FunASR URL、token TTL、HMR host/port）
4. **Repository 抽象**：`Protocol` 接口 + JsonFile 实现；M7 迁 Mongo 只换 singleton 工厂
5. **可降级的外部依赖**：SVEngine / Ling Agent / CosyVoice 都走 adapter + lazy load + `is_available` 属性，不可用时 fail-close 或 echo 回退
6. **Service testable seam**：把副作用（音频解码、模型调用）和业务（存取/比分）切开，单测走 `*_from_vector`，E2E mock 单例

## 开发运行

### 前置

- Node 20+、pnpm 9+、Python 3.12、Docker Desktop
- **`apps/web/public/live2dcubismcore.min.js`**：Live2D 协议禁止转发，手动从 `https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js` 下载
- 声纹依赖：`cd backend && .venv/bin/pip install -e '.[sv]'`（拉 torch/funasr/silero-vad，约 2GB）
- 首次启动 TTS 会下 wav2vec2-xlsr-chinese 模型（~1.2GB），用 HF 镜像：`export HF_ENDPOINT=https://hf-mirror.com`

### 一键启动

```bash
./scripts/dev.sh
# 或分开：
./scripts/dev-backend.sh                                # uvicorn --reload @ 8000
pnpm --filter @webling/web exec vite --host 0.0.0.0     # Vite @ 5173
```

### 反代场景（webling.955id.com:60443）

nginx `location /` 必须加 WS upgrade header（Vite HMR 走根路径），否则 HMR 永远掉线：

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}
# 并在 location / 里：
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $connection_upgrade;
```

Vite 侧 env 驱动 HMR：`VITE_HMR_HOST=webling.955id.com VITE_HMR_CLIENT_PORT=60443 VITE_HMR_PROTOCOL=wss`。

### 服务器端 TTS 重启

```bash
ssh zert@192.168.251.56
HF_ENDPOINT=https://hf-mirror.com \
  setsid nohup /app/zert/.venv/bin/python src/backend/tts/service.py \
    --model /app/zert/models/TTS/CosyVoice2-0.5B \
    --ref-audio /app/zert/models/Ling.wav \
    --host 0.0.0.0 --port 5001 --load-jit &
```

## 外部依赖清单

- **GPU 服务器 `192.168.251.56`**（4× RTX A6000）：
  - LLM: `:8080/v1`（llama.cpp 兼容，DeepSeek-V3 / MiniMax-M2.5 可切）
  - TTS: `:5001`（CosyVoice2-0.5B `--load-jit`，flow encoder 加速 10-20%；内挂 wav2vec2-xlsr forced aligner，每段 wav 顺带产 viseme timeline）
  - FunASR: `:10095`（官方 `funasr-runtime-sdk-online-cpu-0.1.12` 2pass docker）
  - 模型目录走国内 HF 镜像 `HF_ENDPOINT=https://hf-mirror.com`
- **本地 Mongo**：Docker `liying-mongo`（27017）
- **nginx 反代 `172.16.188.253`**：`webling.955id.com:60443` → `172.16.188.37:5173`

## 近期关键落地（2026-04-23 会话）

- **M34 实时对话循环**：`InputBar` 从 push-to-talk 改成"开始对话/结束对话"两态；ASR WS 长连接，FunASR `is_final` 自动 submit，`asr_partial` 在 speaking 时触发 `speech_start` 打断；5min 静默自动退 + 切后台 30s 退 + 2s 去重窗（FunASR 尾音重发兜底）
- **声纹识别端到端**：装 `[sv]` 依赖；CampPlus embed RTF 0.017；M17 SpeakerView 录音注册；M35 每句 utterance 打包 WAV 自动 identify，消息气泡贴 speaker 名；`/api/speakers` 返裸数组而非 `{speakers:[]}` 的预存 bug 已修
- **Hiyori 9 张表情 + 持久化的三层修法**：(1) `playMotion({resetExpression:false})` → (2) 段间 `model.expression()` 再补一道 → (3) **最终方案**：放弃 fork 的 ExpressionManager，PIXI `app.ticker.add` 每帧直接 `coreModel.setParameterValueById(id, v)` 覆写面部参数，`ParamMouthOpenY` 跳过留给 lipsync
- **M36 viseme 嘴型对齐**：`deploy/tts/src/engine/aligner.py` 跑 wav2vec2 CTC forced alignment；pypinyin 剥声母取 final 映射 A/O/U/I/E + rest；TTS `/dequeue?with_timeline=1` 返 JSON（wav_b64 + timeline）；前端按 `segment_idx` 配对 `audio + timeline`，50ms 超时降级；PIXI ticker 按 `audio.currentTime` 驱 `ParamMouthForm`（叠加 delta），情绪作基准偏置
- **SYSTEM_PROMPT 加人格段**：玲面对用户低落不再一味陪哭，1-2 句共情后主动转向开导；显式要求每段回复情绪有起伏并打标签
- **三层独立 docker-compose 部署收敛**：`deploy/funasr/` 用官方 `funasr-runtime-sdk-online-cpu-0.1.12` + `entrypoint.sh` 直 exec `funasr-wss-server-2pass`（跳过官方脚本 `&` 后台导致容器立退的坑）；`deploy/tts/` 自建 `nvidia/cuda:12.4.1 + py3.10` Dockerfile；`scripts/deploy.sh` 三层一键，支持 `--stop` / 按目标选启
- **nginx/HMR 修**：`location /` 缺 WS upgrade → Vite HMR 永远掉线；`/api/` 加 `proxy_read_timeout 180s` 兜声纹冷启动
- **TTS 提速**：放开硬编码 `load_jit=False`（老 4GB 卡时代遗留），A6000 上 flow encoder JIT 加速 10-20%；`service.py` 加 `--load-jit / --load-trt` 启动参数

## 待偿技术债

- [ ] WS schema 前后端一致性 CI（pydantic ↔ ts d.ts 自动对比，M4 挂账至今）
- [ ] ruff 配置补 `BLE001` select（或继续去掉相关 `# noqa`）
- [ ] `live2dcubismcore.min.js` 手动拷贝 → CDN 分发方案
- [ ] `deploy/tts/` Dockerfile 首次 build 端到端联调（预计踩 `pynini==2.1.5` / `kaldifst` 等 Linux 依赖）
- [ ] 服务器 `funasr-online` 容器切到 `deploy/funasr/entrypoint.sh` 方案（当前还是两步启动）
- [ ] CosyVoice TRT 编译（首次 10-30min，decoder 2-3x）
- [ ] vLLM 加速 `llm.pt` autoregressive（3-5x）
