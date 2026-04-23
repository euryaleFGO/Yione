# webLing

## 这是什么

webLing 是把桌面版 Ling 玲虚拟助手做成 **Web 应用 + 可嵌入 SDK** 的项目，按 **AI 数字人**方向长期演进。目标产品：
1. 浏览器直接访问的完整 Web 页面（对话 + Live2D 形象 + TTS 播放 + 嘴型同步）
2. 一段 `<script>` 引入到任何第三方站点的嵌入 SDK
3. 多形象（Live2D 模型）+ 多音色（CosyVoice / edge-tts 等）切换
4. 流式双向对话、情感人格、自主行为、唱歌卡拉OK 等 AI 数字人能力

## 核心价值

**让玲在浏览器里活起来**——不只是文字聊天，而是有形象、有声音、有情绪、会主动说话的数字人。如果其他一切失败，"能对话 + 能看 Live2D 形象 + 能听到声音"必须工作。

## 需求

### 已验证

- ✓ M0 monorepo 骨架（pnpm workspaces + Turborepo + FastAPI + Vue 3）— Phase 1
- ✓ M1 文本对话（WS 流式字幕）— Phase 1
- ✓ M2 Live2D 显示（PIXI + Cubism Core 降级）— Phase 1
- ✓ M3 TTS + 嘴型同步（CosyVoice 按句切分 pipeline）— Phase 1
- ✓ M4 流式 WS 打断（asyncio.Task + cancel 协议）— Phase 1
- ✓ M5 情绪 → 动作驱动（emotion_service + motion_map）— Phase 1
- ✓ M6 JWT + API Key 鉴权（embed token + tenant 隔离）— Phase 2
- ✓ M16 声纹识别后端骨架（SVAdapter + SpeakerService）— Phase 4

### 活跃

- [ ] M3.6 快赢：TTS 预录"嗯..."占位音，感知首字延迟减半
- [ ] M7 Character 模块：sessions/tenants/speakers 迁 Mongo + 角色选择 UI
- [ ] M8 Embed SDK Script 形态：<script> 标签 + 悬浮按钮
- [ ] M9 Embed SDK Web Component：<web-ling> 自定义标签
- [ ] M10 Embed SDK iframe 形态：postMessage 通信
- [ ] M11 多 TTS Provider 切换
- [ ] M12 音色管理 UI
- [ ] M13 历史记录 UI
- [ ] M14 可观测（Prometheus metrics）
- [ ] M15 麦克风输入
- [ ] M17 Speaker 管理 UI
- [ ] M18 流式 ASR（浏览器 MediaRecorder → FunASR）
- [ ] M19 打断机制（silero-vad + barge-in）
- [ ] M20 工具链打通（搜索/记忆/提醒/天气）
- [ ] M21 Prompt 最小管理（Jinja2 + Mongo 版本）
- [ ] M22 情感引擎（EmotionState + 触发器 + 衰减）
- [ ] M23 人格系统（persona traits + 一致性记忆）
- [ ] M24 事件总线 + 定时主动（APScheduler）
- [ ] M25 自主循环（autonomy_service + goals）
- [ ] M26 RVC 歌声合成
- [ ] M27 情绪-动作联动
- [ ] M28 技能插件框架
- [ ] M29 卡拉OK（LRC 同步 + 伴奏混音）
- [ ] M30 互动小游戏
- [ ] M31 知识图谱 UI
- [ ] M32 Prompt 管理后台
- [ ] M33 生产化（Grafana + 告警 + 一键部署）

### 范围外

- 桌面原生应用（Java/LWJGL/GLFW）— 淘汰，Web 化
- PyQt6 launcher — 淘汰
- 本地 sounddevice 播放 — 淘汰，改 Web Audio
- 视频通话 — 复杂度高，不在近期范围
- 移动端原生 App — Web 优先

## 上下文

- **技术栈**：pnpm workspaces + Turborepo / Vue 3 + Vite + TypeScript + Pinia + Tailwind / FastAPI + Python 3.12 / MongoDB / CosyVoice TTS / Live2D (pixi-live2d-display + PIXI v7)
- **外部依赖**：Ling 项目（Agent/记忆/RAG 代码）、MiniMax LLM（192.168.251.56:8080）、CosyVoice TTS（:5001）、MongoDB（Docker 本地 27017）
- **已有工作**：M0-M6 + M16 完成，代码库有完整骨架和核心功能
- **关键决策**：WS 协议 schema-first（packages/core/src/types/ws.ts）、TTS 按句切分 pipeline、emotion 边沿触发 motion、dev 环境允许匿名

## 约束

- **技术栈**：前后端同语言（TypeScript/Python），不引入新语言
- **外部服务**：复用 Ling 已部署的 LLM/TTS/MongoDB，不重新部署
- **性能**：首屏 JS <200KB gzip，首次看到形象 <2s（4G 网络）
- **兼容性**：支持主流浏览器（Chrome/Firefox/Safari/Edge）

## 关键决策

| 决策 | 理由 | 结果 |
|------|------|------|
| pnpm workspaces + Turborepo | polyrepo 发布链复杂；Nx 过重 | ✓ 良好 |
| WS 协议 schema-first | 前后端共享类型定义 | — 待验证（CI 一致性检查未做） |
| TTS 按句切分 | 整段丢失流式收益；token 级音质差 | ✓ 良好 |
| emotion 边沿触发 motion | 避免频繁打断动作 | ✓ 良好 |
| dev 允许匿名 | 主站 demo 不登录 | ✓ 良好 |
| tenants 存 sha256(api_key) | 安全性 | ✓ 良好 |
| speakers.json 而非 Mongo | 避免跨里程碑依赖 | — 待迁移到 M7 |

## 演化

这个文档在阶段转换和里程碑边界时更新。

**每个阶段转换后**（通过 `/gsd-transition`）：
1. 需求失效？→ 移到范围外并注明原因
2. 需求验证？→ 移到已验证并注明阶段
3. 新需求出现？→ 加到活跃
4. 需要记录的决策？→ 加到关键决策
5. "这是什么"还准确吗？如果漂移了就更新

**每个里程碑后**（通过 `/gsd-complete-milestone`）：
1. 全面审查所有章节
2. 核心价值检查——还是正确的优先级吗？
3. 审计范围外——原因还有效吗？
4. 用当前状态更新上下文

---
*最后更新：2026-04-23，初始化*
