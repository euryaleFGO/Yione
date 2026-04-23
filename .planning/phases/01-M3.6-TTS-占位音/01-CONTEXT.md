# Phase 1: M3.6 TTS 占位音 - Context

**收集日期：** 2026-04-23
**状态：** 准备规划

<domain>
## 阶段边界

减少用户等待 TTS 首个音频的感知延迟。当前流程中，用户发消息后需要等待 LLM 首 token + TTS 合成才能听到声音，期间完全静默。本阶段通过在等待期间显示 Live2D 嘴型微动来暗示"在听"，将感知首字延迟减半。

**不改变：** TTS 合成流程、AudioQueue 逻辑、LLM 流式输出方式
**只增加：** 用户发消息后立即触发的嘴型占位效果

</domain>

<decisions>
## 实现决策

### 占位音内容
- **D-01:** 使用静音 + Live2D 嘴型微动，不播放实际音频
- **D-02:** 嘴型微动幅度适中（不是大幅张合），暗示"在听"而非"在说话"

### 触发时机
- **D-03:** 用户发消息后立即触发占位效果（在 `user_message` 事件处理中）
- **D-04:** 不等待 LLM 首 token，最大化感知响应速度

### 衔接方式
- **D-05:** 直接衔接 — 当 TTS 首段音频开始播放时，停止占位嘴型
- **D-06:** 占位嘴型停止与 TTS 播放之间无间隙（TTS 播放会自动接管嘴型）

### 打断处理
- **D-07:** 用户打断时立即停止占位嘴型
- **D-08:** 打断后进入 listening 状态（与现有 M4 行为一致）

### Claude's Discretion
- 嘴型微动的具体参数（频率、幅度）由实现决定
- 前端如何检测 TTS 首段播放并停止占位由实现决定

</decisions>

<canonical_refs>
## 规范引用

**下游代理在规划和实现前必须阅读这些文件。**

### 核心实现文件
- `backend/app/ws/chat_ws.py` — TTS worker 和 turn 处理逻辑，占位效果需在此集成
- `packages/live2d-kit/src/stage.ts` — Live2D 播放控制，AvatarControls.speak/stopSpeaking
- `packages/core/src/audio/queue.ts` — 前端音频队列，需要感知占位状态

### 协议定义
- `packages/core/src/types/ws.ts` — WS 事件类型，可能需要新增占位状态事件
- `backend/app/schemas/ws.py` — 后端 WS schema，与前端同步

### 参考文档
- `PLAN.md` §十三 — Phase 1 详细里程碑描述（M3.6 快赢）

</canonical_refs>

<code_context>
## 现有代码洞察

### 可复用资产
- `AvatarControls.speak()` — Live2DModel.speak 已处理嘴型同步
- `AvatarControls.stopSpeaking()` — 停止当前 speak + 嘴型
- `AudioQueue.clear()` — M4 打断时清空队列
- `_Session.cancel_current()` — 取消当前 turn

### 已建立模式
- WS 事件驱动：后端发事件 → 前端响应
- StateEvent 状态机：idle → processing → speaking → idle
- asyncio.Task 可取消 turn

### 集成点
- `chat_ws.py:_handle_user_message` — 在 LLM 流式开始前触发占位
- `chat_ws.py:_tts_worker` — TTS 首段到达时停止占位
- 前端 ChatView / AvatarStage 组件 — 接收并响应占位状态

</code_context>

<specifics>
## 具体想法

无特定要求 — 采用标准实现方式

</specifics>

<deferred>
## 延迟想法

无 — 讨论保持在阶段范围内

</deferred>

---

*Phase: 1-M3.6-TTS-占位音*
*Context 收集日期: 2026-04-23*
