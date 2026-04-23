#!/bin/bash
# FunASR 部署脚本 — 在 192.168.251.56 上运行
# 用法: bash scripts/deploy-funasr.sh

set -e

echo "=== FunASR 部署 ==="

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "错误: 请先安装 Docker"
    exit 1
fi

# 检查 GPU
if command -v nvidia-smi &> /dev/null; then
    echo "检测到 GPU，使用 GPU 版本"
    GPU_FLAG="--gpus all"
    IMAGE="registry.cn-hangzhou.aliyuncs.com/funasr_repo/funasr:funasr-runtime-sdk-online-cpu-0.1.12"
else
    echo "未检测到 GPU，使用 CPU 版本"
    GPU_FLAG=""
    IMAGE="registry.cn-hangzhou.aliyuncs.com/funasr_repo/funasr:funasr-runtime-sdk-online-cpu-0.1.12"
fi

# 创建数据目录
mkdir -p /app/zert/funasr/models

# 启动 FunASR 服务
echo "启动 FunASR 服务..."
docker run -d \
    --name funasr \
    $GPU_FLAG \
    -p 10095:10095 \
    -p 10096:10096 \
    -v /app/zert/funasr/models:/workspace/models \
    $IMAGE \
    bash -c "cd /workspace && python funasr/bin/model_server.py \
        --model-dir damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch \
        --vad-dir damo/speech_fsmn_vad_zh-cn-16k-common-pytorch \
        --punc-dir damo/punc_ct-transformer_cn-en-common-vocab471067-large \
        --itn-dir thuduj12/itn_zh2ag \
        --hotword /workspace/models/hotwords.txt"

echo ""
echo "=== FunASR 部署完成 ==="
echo "WebSocket 地址: ws://192.168.251.56:10095"
echo "HTTP API 地址: http://192.168.251.56:10096"
echo ""
echo "测试:"
echo "  curl http://192.168.251.56:10096/"
