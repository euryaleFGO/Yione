# @webling/live2d-kit

Live2D 渲染封装。构筑于 `pixi-live2d-display` + PIXI v7 + Cubism 4 Web core。

## 模块（M2 起实现）

- `stage.ts` — PIXI 应用创建、模型加载、resize
- `lipsync.ts` — 基于 RMS → `ParamMouthOpenY`
- `motion.ts` — motion 控制器；情绪 → 动作映射
- `blink.ts` — 自动眨眼
- `gaze.ts` — 视线跟随鼠标（可开关）
- `avatar-config.ts` — 形象配置 schema
