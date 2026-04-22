# 形象（Character）创作指南（草稿）

> 占位文档。完整内容随 M7 落地。

一个 Character 由四部分组成（详见 `PLAN.md` §9）：

1. **Live2D 配置**：`.moc3` 模型、motion 映射、眨眼/视线选项
2. **语音配置**：TTS provider（CosyVoice / edge-tts / ...）、spk_id 或 ref_audio
3. **人设**：system prompt、问候语、性格标签
4. **能力**：可用工具 / RAG / 长期记忆开关

## 新建流程（草案）

1. `scripts/seed-characters.py` 或管理后台创建 Character 记录
2. 把 `.moc3` / 贴图放到 `apps/web/public/avatars/<id>/`
3. 如需克隆音色，上传 15s 参考音频到 CosyVoice，将 `spk_id` 填回 Character
