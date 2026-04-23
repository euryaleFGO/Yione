# webLing CosyVoice2 TTS 服务
#
# 参照 FunAudioLLM/CosyVoice 官方 docker/Dockerfile，基于 nvidia cuda 12.4 + python 3.10。
# 镜像本身不含模型权重（CosyVoice2-0.5B ~5.3GB），通过 volume 挂载。
#
# 构建：docker compose build
# 启动：docker compose up -d

FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 系统依赖（ffmpeg/sox 音频处理；libsndfile 给 soundfile；build-essential 给 C 扩展）
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3.10 python3.10-dev python3.10-venv python3-pip \
      git curl ca-certificates \
      ffmpeg sox libsox-dev libsndfile1 \
      build-essential pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.10 /usr/local/bin/python && \
    ln -sf /usr/bin/python3.10 /usr/local/bin/python3

WORKDIR /workspace

# 先装 PyTorch（cu121 wheel 兼容 cu124 运行时，避免重复下载）
RUN python -m pip install --upgrade pip && \
    python -m pip install \
      torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 \
      --index-url https://download.pytorch.org/whl/cu121

# 其余 Python 依赖（requirements.txt 由 Ling 迁移而来）
COPY requirements.txt /workspace/requirements.txt
RUN python -m pip install -r /workspace/requirements.txt

# TTS 源码（service.py + engine/ + cosyvoice/ + third_party/Matcha-TTS + tools/）
COPY src/ /workspace/src/

# 参考音频（Ling.wav 等）
COPY ref-audio/ /workspace/ref-audio/

# PYTHONPATH 让 service.py 能 import engine/cosyvoice/third_party 等
ENV PYTHONPATH=/workspace/src:/workspace/src/third_party/Matcha-TTS \
    MODELSCOPE_CACHE=/workspace/models/.modelscope \
    HF_HOME=/workspace/models/.huggingface

EXPOSE 5001

# 默认命令；可被 docker-compose.yml command 覆盖
CMD ["python", "-u", "/workspace/src/service.py", \
     "--model", "/workspace/models/CosyVoice2-0.5B", \
     "--ref-audio", "/workspace/ref-audio/Ling.wav", \
     "--host", "0.0.0.0", "--port", "5001"]
