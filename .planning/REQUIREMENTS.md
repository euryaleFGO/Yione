# 需求：webLing

**定义日期：** 2026-04-23
**核心价值：** 让玲在浏览器里活起来——有形象、有声音、有情绪、会主动说话的数字人

## v1 需求（Phase 1-3）

### Phase 1 — MVP / 文本→语音→Live2D

- [x] **M0**: monorepo 骨架搭建（pnpm workspaces + Turborepo + FastAPI + Vue 3）
- [x] **M1**: 文本对话端到端（WS 流式字幕）
- [x] **M2**: Live2D 形象显示（PIXI + Cubism Core 降级）
- [x] **M3**: TTS + 嘴型同步（CosyVoice 按句切分 pipeline）
- [x] **M4**: 流式 WS 打断（asyncio.Task + cancel 协议）
- [x] **M5**: 情绪 → 动作驱动（emotion_service + motion_map）
- [ ] **M3.6**: 快赢：TTS 预录占位音，感知首字延迟减半

### Phase 2 — 认证 + Character + Embed SDK

- [x] **M6**: JWT + API Key 鉴权（embed token + tenant 隔离）
- [ ] **M7**: Character 模块（sessions/tenants/speakers 迁 Mongo + 角色选择 UI）
- [ ] **M8**: Embed SDK Script 形态（<script> 标签 + 悬浮按钮）
- [ ] **M9**: Embed SDK Web Component（<web-ling> 自定义标签）
- [ ] **M10**: Embed SDK iframe 形态（postMessage 通信）

### Phase 3 — 体验打磨

- [ ] **M11**: 多 TTS Provider 切换
- [ ] **M12**: 音色管理 UI
- [ ] **M13**: 历史记录 UI
- [ ] **M14**: 可观测（Prometheus metrics）
- [ ] **M15**: 麦克风输入

## v2 需求（Phase 4-6）

### Phase 4 — 实时与多说话人

- [x] **M16**: 声纹识别后端骨架
- [ ] **M17**: Speaker 管理 UI
- [ ] **M18**: 流式 ASR（浏览器 MediaRecorder → FunASR）
- [ ] **M19**: 打断机制（silero-vad + barge-in）
- [ ] **M20**: 工具链打通（搜索/记忆/提醒/天气）
- [ ] **M21**: Prompt 最小管理（Jinja2 + Mongo 版本）

### Phase 5 — 情感人格 & 自主行为

- [ ] **M22**: 情感引擎（EmotionState + 触发器 + 衰减）
- [ ] **M23**: 人格系统（persona traits + 一致性记忆）
- [ ] **M24**: 事件总线 + 定时主动（APScheduler）
- [ ] **M25**: 自主循环（autonomy_service + goals）
- [ ] **M26**: RVC 歌声合成
- [ ] **M27**: 情绪-动作联动

### Phase 6 — 体验深化

- [ ] **M28**: 技能插件框架
- [ ] **M29**: 卡拉OK（LRC 同步 + 伴奏混音）
- [ ] **M30**: 互动小游戏
- [ ] **M31**: 知识图谱 UI
- [ ] **M32**: Prompt 管理后台
- [ ] **M33**: 生产化（Grafana + 告警 + 一键部署）

## 范围外

| 功能 | 原因 |
|------|------|
| 桌面原生应用（Java/LWJGL/GLFW） | 淘汰，Web 化 |
| PyQt6 launcher | 淘汰 |
| 本地 sounddevice 播放 | 淘汰，改 Web Audio |
| 视频通话 | 复杂度高，不在近期范围 |
| 移动端原生 App | Web 优先 |

## 追踪性

| 需求 | 阶段 | 状态 |
|------|------|------|
| M0 | Phase 1 | 完成 |
| M1 | Phase 1 | 完成 |
| M2 | Phase 1 | 完成 |
| M3 | Phase 1 | 完成 |
| M4 | Phase 1 | 完成 |
| M5 | Phase 1 | 完成 |
| M3.6 | Phase 1 | 待开始 |
| M6 | Phase 2 | 完成 |
| M7 | Phase 2 | 待开始 |
| M8 | Phase 2 | 待开始 |
| M9 | Phase 2 | 待开始 |
| M10 | Phase 2 | 待开始 |
| M11 | Phase 3 | 待开始 |
| M12 | Phase 3 | 待开始 |
| M13 | Phase 3 | 待开始 |
| M14 | Phase 3 | 待开始 |
| M15 | Phase 3 | 待开始 |
| M16 | Phase 4 | 完成 |
| M17 | Phase 4 | 待开始 |
| M18 | Phase 4 | 待开始 |
| M19 | Phase 4 | 待开始 |
| M20 | Phase 4 | 待开始 |
| M21 | Phase 4 | 待开始 |
| M22 | Phase 5 | 待开始 |
| M23 | Phase 5 | 待开始 |
| M24 | Phase 5 | 待开始 |
| M25 | Phase 5 | 待开始 |
| M26 | Phase 5 | 待开始 |
| M27 | Phase 5 | 待开始 |
| M28 | Phase 6 | 待开始 |
| M29 | Phase 6 | 待开始 |
| M30 | Phase 6 | 待开始 |
| M31 | Phase 6 | 待开始 |
| M32 | Phase 6 | 待开始 |
| M33 | Phase 6 | 待开始 |

**覆盖率：**
- v1 需求：18 个（Phase 1-3）
- 已映射到阶段：18
- 未映射：0 ✓

---
*需求定义：2026-04-23*
*最后更新：2026-04-23，初始化*
