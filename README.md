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

**约 35 个里程碑已落地**，代码跑通了"文本对话 + Live2D 动起来 + 说话有声音 + 脸有表情 + 嘴型对得上音素 + 能打断 + 声纹识别用户"整条链路。完整规划见 [`PLAN.md`](./PLAN.md)，路线图见 [`ROADMAP.md`](./.planning/ROADMAP.md)。

### 已工作功能

| 能力 | 里程碑 | 说明 |
|---|---|---|
| 文本对话 + WS 流式字幕 | M0-M1 | DeepSeek-V3-Enterprise / MiniMax-M2.5 LLM 可切 |
| Live2D 形象（Hiyori）+ TTS 嘴型 | M2-M3 | CosyVoice2 克隆音色，按句 pipeline |
| 流式打断 | M4 | asyncio.Task + 用户 speech_start 自动 cancel |
| 情绪 → 动作 + 表情 | M5+M36 | LLM 打 [emotion] 标签；9 个 .exp3.json 面部表情；ticker 每帧硬写参数避免 idle motion 擦 |
| JWT + API Key + 多租户 | M6 | embed token 签发 + Origin 白名单 |
| 声纹识别 | M16+M17+M35 | CampPlus 192 维向量；REST 注册/改名/删除/识别；对话中每句自动 identify 贴 speaker 标签 |
| 流式 ASR（FunASR 2pass） | M18 | WebSocket 2pass-online/offline，partial + final 事件 |
| **实时对话循环** | **M34** | 点"开始对话"进入长循环，FunASR is_final 自动提交，speech_start 打断，段间保持 expression |
| **Viseme 嘴型对齐** | **M36** | wav2vec2 CTC forced alignment 产出字符级 timeline，PIXI ticker 驱动 ParamMouthForm |
| 情感 / 人格 / 自主循环 | M22-M25 | 已落代码，后续精修 |
| 工具链 / 技能 / RVC / 卡拉OK / 知识图谱 | M20/M26-M31 | 已落代码，逐个精修 |
| 生产化（Prometheus + Grafana） | M33 | docker-compose 一键 |

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
- **Ling 项目**：`/Users/zert/Work/zert/lkl_code/Ling`（声纹 SVEngine 靠它）
- **GPU 服务器 `192.168.251.56`**（4× RTX A6000）：
  - LLM: `:8080/v1`（llama.cpp、DeepSeek/MiniMax 可切）
  - TTS: `:5001`（CosyVoice2-0.5B，`--load-jit` 开启；内部挂 wav2vec2-xlsr-chinese forced aligner，生成 viseme timeline）
  - FunASR ASR: `:10095`（官方 2pass runtime CPU 版 docker）
  - HF 模型走国内镜像 `HF_ENDPOINT=https://hf-mirror.com`
- **nginx 反代 `172.16.188.253`**：`webling.955id.com:60443` → `172.16.188.37:5173`（开发机 Vite）
- **本地 Mongo**：Docker `liying-mongo`（已跑）
- **Live2D Cubism Core for Web**：手动从 Live2D 官网下载放 `apps/web/public/live2dcubismcore.min.js`

## 开发运行

```bash
# 一键并行启动前后端
./scripts/dev.sh

# 或分开起
./scripts/dev-backend.sh     # uvicorn + --reload @ 8000
pnpm --filter @webling/web exec vite --host 0.0.0.0   # Vite @ 5173

# 反代场景走 webling.955id.com:60443 需要装声纹依赖
cd backend && .venv/bin/pip install -e '.[sv]'

# TTS 服务重启（服务器上）
ssh zert@192.168.251.56
HF_ENDPOINT=https://hf-mirror.com \
  setsid nohup /app/zert/.venv/bin/python src/backend/tts/service.py \
    --model /app/zert/models/TTS/CosyVoice2-0.5B \
    --ref-audio /app/zert/models/Ling.wav \
    --host 0.0.0.0 --port 5001 --load-jit &
```

## 近期关键进展（2026-04-23）

- **M34 实时对话循环**：`InputBar` 改成"开始对话"长循环，FunASR `is_final` 自动提交 user_message，播放期 `speech_start` 打断 turn，浏览器 AEC 消回声
- **表情系统落地（步 1）**：Hiyori 补全 9 个 `.exp3.json`（joy/sadness/anger/affection/crying/surprise/fear/disgust/neutral）
- **表情系统落地（步 2）**：放弃走 fork 的 ExpressionManager，改 PIXI ticker 每帧直接往 `coreModel.setParameterValueById` 写面部参数——idle motion 再怎么 reset 都覆盖不掉
- **声纹识别打通**：`[sv]` 依赖装好（torch/funasr/silero-vad）；CampPlus 模型首次下载 60s，embed RTF 0.017；M17 `/speakers` 页面录音注册；M35 对话里每句 utterance 自动 identify，消息气泡显示 speaker 名
- **M36 Viseme 嘴型对齐**：wav2vec2-xlsr-chinese CTC forced alignment 跑在 GPU 0，每段 wav 生成后产出 `[{char, t_start, t_end, viseme}, ...]`；前端 PIXI ticker 按 `audio.currentTime` 查表驱动 `ParamMouthForm`（A/O/U/I/E 五种嘴形 + rest），情绪 MouthForm 做基准偏置，嘴张合幅度仍交给 fork 的 amplitude lipsync
- **SYSTEM_PROMPT 加人格段**：玲面对用户低落不再一味陪哭，1-2 句共情后主动转向开导；要求每段回复情绪有起伏
- **反代/部署**：修正 nginx `location /` 缺 WS upgrade 导致 Vite HMR 掉线的 bug，加 `map $http_upgrade $connection_upgrade`；`/api` 放宽到 180s 兜住声纹冷启动
- **TTS 提速**：`CosyVoiceRealTimeTTS` 放开硬编码的 `load_jit=False`，A6000 上 flow encoder JIT 提速约 10-20%；TRT / vLLM 是后续优化点
