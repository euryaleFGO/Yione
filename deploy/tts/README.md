# TTS 部署（CosyVoice2）

基于官方 [FunAudioLLM/CosyVoice](https://github.com/FunAudioLLM/CosyVoice) 的 Python 实现，包 Flask HTTP 接口（`service.py`，端口 5001），识别句尾切分流式合成。**需要 NVIDIA GPU**（CPU 实时率差，生产不可用）。

## 目录结构

```
deploy/tts/
├── Dockerfile              # 基于 nvidia/cuda:12.4.1 + py3.10 + pytorch cu121
├── docker-compose.yml      # 挂 models 卷 + GPU reservation
├── .env.example            # TTS_PORT / TTS_MODELS_DIR
├── requirements.txt        # Python 依赖（从 Ling 迁移）
├── src/                    # TTS 源码（service.py / engine / cosyvoice / third_party）
├── ref-audio/              # 参考音频（Ling.wav）
└── models/                 # CosyVoice2-0.5B 模型（gitignore，需自行放置）
```

## 首次部署

### 1. 准备模型

把 CosyVoice2-0.5B 模型放到 `${TTS_MODELS_DIR}/CosyVoice2-0.5B/`，目录结构参照 [iic/CosyVoice2-0.5B](https://modelscope.cn/models/iic/CosyVoice2-0.5B)：

```bash
# 选项 A：从 ModelScope 下
pip install modelscope
python -c "from modelscope import snapshot_download; snapshot_download('iic/CosyVoice2-0.5B', cache_dir='./models')"

# 选项 B：服务器上已有的话直接软链或指向
echo "TTS_MODELS_DIR=/app/zert/models/TTS" > .env
```

模型体积约 5.3GB。

### 2. 构建 + 启动

```bash
cd deploy/tts
cp .env.example .env
docker compose build      # 首次构建 15-30 分钟（下 pytorch + 各种 python 包）
docker compose up -d
docker compose logs -f    # 等到 "[TTS服务] 启动完毕" 或监听端口
```

### 3. 验证

```bash
# 健康检查
curl http://localhost:5001/

# 合成测试
curl -X POST http://localhost:5001/tts -H 'Content-Type: application/json' \
  -d '{"text": "你好，我是玲"}' --output test.wav
```

## 参考音频

`ref-audio/Ling.wav` 是玲这个角色的音色样本，service.py 首次加载时用它做 zero-shot 声音克隆。如要换其他音色，替换这个文件或改 `--ref-audio` 参数。

## 已知限制（迁移遗留）

- `requirements.txt` 来自 Ling 的 Windows 环境，某些包版本在 Linux + py3.10 下可能需要微调
- `pynini==2.1.5` 未装（`ttsfrd` 依赖它），默认走 `wetext` 替代，ITN/TN 能力略弱
- CUDA 12.4 镜像实际用 cu121 的 PyTorch wheel（兼容，不影响）

这些在端到端联调时再调整。

## 停止

```bash
docker compose down
```
