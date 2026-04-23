# 路线图：webLing

**创建日期：** 2026-04-23
**粒度：** 细粒度（每个里程碑 = 一个阶段）

## 概览

| # | 阶段 | 目标 | 需求 | 成功标准数 |
|---|------|------|------|-----------|
| 1 | M3.6 TTS 占位音 | 感知首字延迟减半 | M3.6 | 3 |
| 2 | M7 Character 模块 | 多形象支持 + Mongo 迁移 | M7 | 4 |
| 3 | M8 Embed Script | 第三方可通过 <script> 接入 | M8 | 3 |
| 4 | M9 Embed Web Component | <web-ling> 自定义标签 | M9 | 3 |
| 5 | M10 Embed iframe | iframe 沙箱接入 | M10 | 3 |
| 6 | M11 多 TTS Provider | 切换不同 TTS 引擎 | M11 | 3 |
| 7 | M12 音色管理 UI | 后台管理音色 | M12 | 3 |
| 8 | M13 历史记录 UI | 用户查看对话历史 | M13 | 3 |
| 9 | M14 可观测 | Prometheus metrics | M14 | 3 |
| 10 | M15 麦克风输入 | 语音输入 | M15 | 3 |
| 11 | M17 Speaker UI | 说话人管理界面 | M17 | 3 |
| 12 | M18 流式 ASR | 实时语音识别 | M18 | 3 |
| 13 | M19 打断机制 | VAD + barge-in | M19 | 3 |
| 14 | M20 工具链打通 | Agent 工具调用 | M20 | 3 |
| 15 | M21 Prompt 管理 | Jinja2 模板 + 版本 | M21 | 3 |
| 16 | M22 情感引擎 | EmotionState 模型 | M22 | 3 |
| 17 | M23 人格系统 | persona traits | M23 | 3 |
| 18 | M24 事件总线 | EventBus + 定时 | M24 | 3 |
| 19 | M25 自主循环 | autonomy_service | M25 | 3 |
| 20 | M26 RVC 歌声 | 声线转换 | M26 | 3 |
| 21 | M27 情绪-动作联动 | 情感驱动 Live2D | M27 | 2 |
| 22 | M28 技能插件 | skill-sdk 框架 | M28 | 3 |
| 23 | M29 卡拉OK | LRC + 混音 | M29 | 3 |
| 24 | M30 互动小游戏 | 猜谜 + 问答 | M30 | 3 |
| 25 | M31 知识图谱 UI | 图谱可视化 | M31 | 2 |
| 26 | M32 Prompt 管理后台 | A/B + 指标 | M32 | 3 |
| 27 | M33 生产化 | Grafana + 部署 | M33 | 3 |
| 28 | M34 实时对话循环 | 点击即对话，is_final 自动触发，TTS 可打断 | M34 | 5 |

## 阶段详情

### Phase 1: M3.6 TTS 占位音

**目标：** 感知首字延迟减半

**需求：** M3.6

**成功标准：**
1. 用户发消息后 <500ms 内播放占位音（"嗯..."）
2. 占位音与后续 TTS 音频无缝衔接
3. 占位音不影响正常 TTS 音频队列

**依赖：** M3（已完成）

**计划：** 1 plan
- [ ] 01-01-PLAN.md — 后端协议扩展 + 前端嘴型微动驱动

---

### Phase 2: M7 Character 模块

**目标：** 多形象支持 + Mongo 迁移

**需求：** M7

**成功标准：**
1. sessions/tenants/speakers 数据迁移到 MongoDB
2. 主站可切换不同 Live2D 形象
3. seed 脚本初始化默认角色（玲）
4. Character CRUD API 正常工作

**依赖：** M6（已完成）

**计划：** 3 plans
Plans:
- [ ] 02-01-PLAN.md — MongoDB 连接 + Character 模型 + API
- [ ] 02-02-PLAN.md — Session/Tenant/Speaker 服务迁移到 MongoDB
- [ ] 02-03-PLAN.md — seed 脚本 + 前端角色切换 UI

---

### Phase 3: M8 Embed Script

**目标：** 第三方可通过 <script> 标签接入

**需求：** M8

**成功标准：**
1. `<script src="embed.js">` 自动注入悬浮按钮
2. 点击展开 chat 面板，对话正常
3. data-* 属性配置生效

**依赖：** M6, M7

---

### Phase 4: M9 Embed Web Component

**目标：** <web-ling> 自定义标签

**需求：** M9

**成功标准：**
1. `<web-ling>` 自定义标签正常渲染
2. Shadow DOM 样式隔离生效
3. 属性响应式（改 character 切换形象）

**依赖：** M8

---

### Phase 5: M10 Embed iframe

**目标：** iframe 沙箱接入

**需求：** M10

**成功标准：**
1. iframe 加载 embed.html 正常
2. postMessage 双向通信工作
3. 父页面可控制 open/close/sendMessage

**依赖：** M8

---

### Phase 6: M11 多 TTS Provider

**目标：** 切换不同 TTS 引擎

**需求：** M11

**成功标准：**
1. 支持 CosyVoice + edge-tts 两个 provider
2. 可通过配置切换默认 provider
3. 切换后 TTS 正常工作

**依赖：** M3

---

### Phase 7: M12 音色管理 UI

**目标：** 后台管理音色

**需求：** M12

**成功标准：**
1. 音色列表页面正常显示
2. 可上传/删除音色
3. 音色切换生效

**依赖：** M11

---

### Phase 8: M13 历史记录 UI

**目标：** 用户查看对话历史

**需求：** M13

**成功标准：**
1. 历史记录列表正常加载
2. 点击可查看完整对话
3. 分页/搜索功能正常

**依赖：** M7

---

### Phase 9: M14 可观测

**目标：** Prometheus metrics

**需求：** M14

**成功标准：**
1. /metrics 端点暴露指标
2. 对话延迟、TTS 延迟等核心指标可查
3. Grafana 面板可导入

**依赖：** 无

---

### Phase 10: M15 麦克风输入

**目标：** 语音输入

**需求：** M15

**成功标准：**
1. 浏览器请求麦克风权限
2. 录音 → ASR → 文字 → 对话流程打通
3. 按住说话 / 松开发送

**依赖：** M18

---

### Phase 11: M17 Speaker UI

**目标：** 说话人管理界面

**需求：** M17

**成功标准：**
1. Speaker 列表页面正常显示
2. 可修改 speaker 昵称/备注
3. 可删除 speaker

**依赖：** M16（已完成）

---

### Phase 12: M18 流式 ASR

**目标：** 实时语音识别

**需求：** M18

**成功标准：**
1. 浏览器 MediaRecorder 250ms 分片推后端
2. FunASR streaming 识别，增量 WS 事件
3. 识别结果实时显示

**依赖：** M15

---

### Phase 13: M19 打断机制

**目标：** VAD + barge-in

**需求：** M19

**成功标准：**
1. silero-vad 播放期监听用户说话
2. 检测到说话立即发送 speech_start
3. 后端 cancel 当前生成，上下文续写

**依赖：** M18

---

### Phase 14: M20 工具链打通

**目标：** Agent 工具调用

**需求：** M20

**成功标准：**
1. Web 版 Agent 启用搜索/记忆/提醒/天气工具
2. 工具调用时 WS 推 tool_call 事件
3. 前端 tool_call 气泡正常显示

**依赖：** M16

---

### Phase 15: M21 Prompt 管理

**目标：** Jinja2 模板 + 版本

**需求：** M21

**成功标准：**
1. Prompt 模板化（Jinja2）
2. Mongo 存版本，可回滚
3. 后台改 prompt 立即生效

**依赖：** M7

---

### Phase 16: M22 情感引擎

**目标：** EmotionState 模型

**需求：** M22

**成功标准：**
1. EmotionState 8 维模型正常工作
2. 触发器（对话内容/事件/时间）生效
3. 衰减循环运行正常
4. 情感状态注入 system prompt

**依赖：** M5

---

### Phase 17: M23 人格系统

**目标：** persona traits

**需求：** M23

**成功标准：**
1. persona traits（humor/curiosity/mischief/honesty/formality）可配置
2. 人格影响回复风格
3. 长期记忆维持人格连贯

**依赖：** M22

---

### Phase 18: M24 事件总线

**目标：** EventBus + 定时

**需求：** M24

**成功标准：**
1. EventBus 订阅/发布正常
2. APScheduler 定时事件触发
3. 默认定时事件（早安/晚安）工作

**依赖：** 无

---

### Phase 19: M25 自主循环

**目标：** autonomy_service

**需求：** M25

**成功标准：**
1. autonomy_service.tick() 每 10s 运行
2. 目标管理（goals 集合）正常
3. 主动对话发起工作

**依赖：** M22, M24

---

### Phase 20: M26 RVC 歌声

**目标：** 声线转换

**需求：** M26

**成功标准：**
1. RVC 微服务部署正常
2. /rvc/convert API 工作
3. 前端"唱一首"按钮可触发

**依赖：** M3

---

### Phase 21: M27 情绪-动作联动

**目标：** 情感驱动 Live2D

**需求：** M27

**成功标准：**
1. 情感状态直接驱动 Live2D 动作选择
2. anger → Flick, joy → Tap@Body 等映射生效

**依赖：** M22, M5

---

### Phase 22: M28 技能插件

**目标：** skill-sdk 框架

**需求：** M28

**成功标准：**
1. packages/skill-sdk 接口定义完成
2. 3 个示例技能（天气/日历/笔记）可用
3. 技能注册/调用流程打通

**依赖：** M20

---

### Phase 23: M29 卡拉OK

**目标：** LRC + 混音

**需求：** M29

**成功标准：**
1. LRC 歌词解析 + 滚动高亮
2. 伴奏 + 人声混音正常
3. 卡拉OK 页面可访问

**依赖：** M26

---

### Phase 24: M30 互动小游戏

**目标：** 猜谜 + 问答

**需求：** M30

**成功标准：**
1. 猜谜游戏可玩
2. 问答竞赛可玩
3. 成就系统正常

**依赖：** 无

---

### Phase 25: M31 知识图谱 UI

**目标：** 图谱可视化

**需求：** M31

**成功标准：**
1. /api/knowledge-graph API 正常
2. 前端可视化查看器可访问

**依赖：** 无

---

### Phase 26: M32 Prompt 管理后台

**目标：** A/B + 指标

**需求：** M32

**成功标准：**
1. 模板库可管理
2. A/B 测试功能正常
3. 指标对比面板可访问

**依赖：** M21

---

### Phase 27: M33 生产化

**目标：** Grafana + 部署

**需求：** M33

**成功标准：**
1. Prometheus + Grafana 部署完成
2. 告警规则配置完成
3. 一键部署脚本可用

**依赖：** M14

---

### Phase 28: M34 实时对话循环

**目标：** 从"对讲机式"升级成"实时对谈"——点击"开始对话"后进入 listening 循环，FunASR `is_final` 自动触发 `user_message`，LLM 边流边按句 TTS 播放，用户开口 `speech_start` 立即 cancel 当前 turn 回到 listening。

**需求：** M34

**成功标准：**
1. InputBar 麦克风按钮改造成"开始对话/结束对话"两态切换，点击后进入/退出 listening 循环
2. FunASR `is_final` 到达后前端自动提交 user_message，无需手动确认
3. TTS 播放期麦克风**保持开启**（依赖浏览器 `echoCancellation` 做回声消除，不主动 mute），FunASR 照常监听以便打断
4. 用户在 speaking 状态下开口时触发 `speech_start`（信号源为 FunASR 2pass-online 首个 partial chunk），后端立即 cancel 当前 turn，前端状态切 listening
5. 打断后若没有后续 `is_final` 到达，停在 listening 不自动起新 turn；新 `is_final` 到才开新 turn

**依赖：** M3（按句 TTS pipeline，已完成）、M4（cancel turn 基础设施，已完成）、M18（FunASR 流式 ASR，已完成）

---
*路线图创建：2026-04-23*
*最后更新：2026-04-23，追加 M34*
