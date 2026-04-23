#!/bin/bash
# FunASR 2pass server 启动脚本
# 官方镜像默认 CMD 是 /bin/bash，不自启服务。本脚本直接 exec 二进制作为容器主进程，
# 避开官方 run_server_2pass.sh 用 & 后台启动导致容器立即退出的问题。
set -e

exec /workspace/FunASR/runtime/websocket/build/bin/funasr-wss-server-2pass \
  --download-model-dir "${FUNASR_MODEL_DIR:-/workspace/models}" \
  --model-dir "${FUNASR_MODEL:-damo/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-onnx}" \
  --online-model-dir "${FUNASR_ONLINE_MODEL:-damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online-onnx}" \
  --vad-dir "${FUNASR_VAD:-damo/speech_fsmn_vad_zh-cn-16k-common-onnx}" \
  --punc-dir "${FUNASR_PUNC:-damo/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727-onnx}" \
  --itn-dir "${FUNASR_ITN:-thuduj12/fst_itn_zh}" \
  --lm-dir "${FUNASR_LM:-damo/speech_ngram_lm_zh-cn-ai-wesp-fst}" \
  --decoder-thread-num "${FUNASR_DECODER_THREADS:-32}" \
  --model-thread-num "${FUNASR_MODEL_THREADS:-1}" \
  --io-thread-num "${FUNASR_IO_THREADS:-2}" \
  --port "${FUNASR_PORT:-10095}" \
  --certfile "" \
  --keyfile "" \
  --hotword "${FUNASR_HOTWORD:-/workspace/FunASR/runtime/websocket/hotwords.txt}"
