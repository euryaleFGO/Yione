# FunASR 部署（2pass 流式）

基于官方镜像 `registry.cn-hangzhou.aliyuncs.com/funasr_repo/funasr:funasr-runtime-sdk-online-cpu-0.1.12`，通过 `entrypoint.sh` 把 `funasr-wss-server-2pass` 作为容器主进程一步启动（替代官方 `run_server_2pass.sh` 用 `&` 后台启动导致容器立即退出的问题）。

## 启动

```bash
cd deploy/funasr
cp .env.example .env    # 按需编辑端口/模型目录
docker compose up -d
docker compose logs -f  # 首次需下载 ~1.7GB ONNX 模型，等到 "asr model init finished. listen on port:10095" 表示就绪
```

## 端口

- `10095`：WebSocket 端口（非 TLS，客户端连 `ws://host:10095`）

## 模型

首次启动会从 ModelScope 下载以下 ONNX 模型到 `${FUNASR_MODELS_DIR}`（默认 `./models`）：

- `damo/speech_fsmn_vad_zh-cn-16k-common-onnx` - VAD
- `damo/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-onnx` - 离线 ASR
- `damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online-onnx` - 流式 ASR
- `damo/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727-onnx` - 标点
- `damo/speech_ngram_lm_zh-cn-ai-wesp-fst` - 语言模型
- `thuduj12/fst_itn_zh` - 逆文本归一化

共约 1.7GB。国内走 ModelScope 一般 5-10 分钟。

## 验证

```bash
# 容器内看加载进度
docker compose exec funasr tail -f /tmp/*.log 2>/dev/null || docker compose logs -f

# 外部可达性
nc -zv localhost 10095
```

## 停止

```bash
docker compose down
```

模型缓存保留在 `${FUNASR_MODELS_DIR}`，下次启动秒起。
