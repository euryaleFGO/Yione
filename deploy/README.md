# webLing 部署

webLing 整体由三层服务组成，推荐分三个独立 `docker-compose` 拉起：

| 层 | 位置 | 资源 | 说明 |
|---|---|---|---|
| FunASR（流式 ASR）| `deploy/funasr/` | CPU，~1.7GB 模型 | 官方镜像 + entrypoint.sh 一步启动 |
| CosyVoice（TTS）| `deploy/tts/` | **GPU**，~5.3GB 模型 | 自建镜像（基于 nvidia/cuda 12.4 + py3.10） |
| webLing 核心（backend + web + mongo + 监控）| 根 `docker-compose.yml` | 通用 | 通过环境变量连接上面两层 |

## 部署顺序

```bash
# 1. 启 FunASR（不依赖其他服务）
cd deploy/funasr
cp .env.example .env    # 按需改 FUNASR_PORT / FUNASR_MODELS_DIR
docker compose up -d
docker compose logs -f  # 等首次下载 ~1.7GB 模型 + "asr model init finished"

# 2. 启 TTS（需 GPU）
cd ../tts
cp .env.example .env    # 按需改 TTS_PORT / TTS_MODELS_DIR
# 把 CosyVoice2-0.5B 模型放到 ${TTS_MODELS_DIR}/CosyVoice2-0.5B/
docker compose build    # 首次 15-30 分钟
docker compose up -d

# 3. 启 webLing 核心
cd ../..
cp .env.example .env    # 确认 FUNASR_WS_URL / TTS_BASE_URL 指向上面两个服务
docker compose up -d
```

或一键（已写成 `scripts/deploy.sh`）：

```bash
./scripts/deploy.sh
```

## 开发模式

本地开发不需要把全套都跑在 docker 里：

- FunASR / CosyVoice 跑在服务器（或本机 docker-compose up -d 独立启）
- 前后端通过 `scripts/dev.sh` 裸跑（`pnpm dev` + `uvicorn --reload`）
- `.env` 里 `FUNASR_WS_URL` / `TTS_BASE_URL` 指向服务器 IP 即可

## 跨机器部署

三层可以在不同机器上。backend 通过环境变量连接，例如：

```bash
# backend 机器的 .env
FUNASR_WS_URL=ws://192.168.251.56:10095
TTS_BASE_URL=http://192.168.251.56:5001
LLM_BASE_URL=http://192.168.251.56:8080/v1
```

## 模型路径约定

默认每层的模型存在自己的 `./models/` 下（compose 挂卷，git 忽略）。如果你的服务器上已有统一的模型目录，可以在各层 `.env` 里指向绝对路径：

```bash
# deploy/funasr/.env
FUNASR_MODELS_DIR=/app/zert/funasr-online/models

# deploy/tts/.env
TTS_MODELS_DIR=/app/zert/models/TTS
```

## 已知限制

- TTS 镜像首次构建时会下载 PyTorch cu121 wheel + 若干 audio 包，国内 15-30 分钟
- `pynini==2.1.5` 因只能通过 conda 装，当前 Dockerfile 未装；ITN/TN 走 `wetext` 替代
- FunASR 只有 CPU 版本镜像（官方 GPU 镜像走同一仓库不同 tag，必要时改 `deploy/funasr/docker-compose.yml` 的 `image:`）

端到端联调发现的坑写回各自 README 的"已知限制"段。
