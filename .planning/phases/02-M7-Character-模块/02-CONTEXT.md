# Phase 2: M7 Character 模块 - Context

**收集日期：** 2026-04-23
**状态：** 准备规划

<domain>
## 阶段边界

把 sessions/tenants/speakers 从内存/JSON 迁移到 MongoDB，并实现 Character CRUD API + 前端角色切换。

**改变：** SessionService、TenantService、SpeakerService 的存储后端；新增 Character 模型和 API
**不改变：** WS 协议、对话流程、TTS pipeline、Live2D 渲染逻辑

</domain>

<decisions>
## 实现决策

### Character 数据模型
- **D-01:** Character 作为独立全局集合，不归 tenant 所有（多租户共享角色库）
- **D-02:** 字段：id, name, avatar_config(modelUrl/scale/anchor/motionMap), greeting, system_prompt, voice_id, enabled
- **D-03:** Tenant 通过 character_whitelist 控制可用角色，无白名单 = 全部可用

### MongoDB 接入
- **D-04:** 使用 motor（异步原生驱动），不用 ODM（beanie/motorantic）
- **D-05:** 连接配置走 MONGO_URL 环境变量，app.state.db 挂在 FastAPI 上
- **D-06:** 现有 3 个 Service 都迁到 Mongo：sessions、tenants、speakers 集合

### 数据迁移
- **D-07:** 写 scripts/seed.py 初始化默认 Character（ling）+ demo Tenant
- **D-08:** 保留 JSON fallback：dev 环境没 Mongo 时自动降级到内存/JSON

### 前端角色切换
- **D-09:** ChatView 加角色选择器（dropdown 或卡片）
- **D-10:** 切换时发 change_character WS 事件 → 后端更新 session → 前端重新 mount AvatarStage
- **D-11:** 不断 WS 连接，只切换模型

### 多租户隔离
- **D-12:** Character 全局共享，Tenant 白名单控制权限
- **D-13:** 现有 character_whitelist 机制不变，M7 只需确保存在对应的 Character 文档

</decisions>

<canonical_refs>
## 规范引用

### 核心实现文件
- `backend/app/services/session_service.py` — 现有内存 session，需迁到 Mongo
- `backend/app/services/tenant_service.py` — 现有 JSON tenant，需迁到 Mongo
- `backend/app/services/speaker_service.py` — 现有 JSON speaker，需迁到 Mongo
- `backend/app/schemas/chat.py` — SessionCreate/SessionInfo，需扩展
- `packages/live2d-kit/src/avatar-config.ts` — AvatarConfig，Character 的 avatar_config 来源

### 参考文档
- `backend/app/data/tenants.example.json` — 现有 tenant 结构
- `backend/app/domain/speaker.py` — Speaker domain 模型参考

</canonical_refs>

<code_context>
## 现有代码洞察

### 可复用资产
- `TenantService` 的 dev fallback 模式 — 可复用到 Session/Speaker
- `SessionInfo` schema — 已有 session_id/character_id/greeting 字段
- `AvatarConfig` interface — 直接作为 Character 的 avatar_config 类型
- `change_character` WS 事件 — 已定义，M7 只需真正落地处理

### 已建立模式
- JSON 文件 fallback → 无 Mongo 时降级
- Singleton service pattern（get_xxx_service()）
- Pydantic schema 验证

### 集成点
- `chat_ws.py:_Session.character_id` — 切换 character 时更新
- `chat_ws.py:chat_ws` endpoint — session 创建时关联 character
- 前端 `AvatarStage.vue` — 需支持动态切换 config
- 前端 `chat.ts` store — 需管理 character 列表和当前选中

</code_context>

<specifics>
## 具体想法

- MongoDB 用 Docker 本地 27017（已部署）
- seed 脚本至少初始化 1 个默认角色（ling）
- Character API：GET /api/characters, GET /api/characters/:id
- 前端角色切换需要实时预览（缩略图或 Live2D 预览）

</specifics>

<deferred>
## 延迟想法

- Character CRUD 后台管理 UI（M12 音色管理 UI 时一起考虑）
- Character 归属 tenant（多租户自定义角色）
- Character 热更新（不重启服务）

</deferred>

---

*Phase: 2-M7-Character-模块*
*Context 收集日期: 2026-04-23*
