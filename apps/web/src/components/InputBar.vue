<script setup lang="ts">
import { encodePcmInt16ToWav } from '@webling/core';
import { computed, onBeforeUnmount, ref, watch } from 'vue';

type AgentState = 'idle' | 'processing' | 'speaking' | 'listening';

const props = withDefaults(
  defineProps<{
    disabled?: boolean;
    agentState?: AgentState;
  }>(),
  { agentState: 'idle' },
);

const emit = defineEmits<{
  send: [text: string];
  'speech-start': [];
  /** M35：每句 utterance 的 16k mono WAV，供上层丢给 /api/speakers/identify 做声纹识别 */
  'identify-audio': [wav: Blob];
}>();

const text = ref('');
const composing = ref(false);

// M34 实时对话循环：用户点"开始对话"后进入循环，ASR WS 长连接，is_final 自动 submit，
// agentState 为 speaking 时检测到 ASR partial 视作打断
const dialogMode = ref(false);
const dialogError = ref<string | null>(null);

let audioContext: AudioContext | null = null;
let mediaStream: MediaStream | null = null;
let workletNode: ScriptProcessorNode | null = null;
let asrWs: WebSocket | null = null;

// M34 循环内用于判重：每句 utterance 只发一次 speech_start
let bargedInThisUtterance = false;
// FunASR 偶尔对同一 utterance 重复发 2pass-offline（尾音余振再次触发 VAD），
// 导致同一句提交两次。用"文本 + 时间窗"去重；窗口取 2s，足够覆盖重复且不会
// 误判快速连续两句"嗯嗯"。
let lastSubmittedSentence: { text: string; at: number } | null = null;
const DEDUP_WINDOW_MS = 2000;
// 5 分钟静默自动退出循环
let silenceTimer: ReturnType<typeof setTimeout> | null = null;
const SILENCE_TIMEOUT_MS = 5 * 60 * 1000;
// tab 切后台 30s 自动退出
let hiddenExitTimer: ReturnType<typeof setTimeout> | null = null;
const HIDDEN_EXIT_MS = 30 * 1000;

// M35 声纹识别：每轮 utterance 累积 PCM，到 asr_final 时打包 WAV 发给上层
// 上限 30s 防止有人讲太长撑爆内存（16k*2B*30s = 960KB）
let utterancePcm: Int16Array[] = [];
let utteranceSamples = 0;
const UTTERANCE_MAX_SAMPLES = 16000 * 30;
// 识别也需要足够长的片段；太短（<1s）直接不发
const UTTERANCE_MIN_SAMPLES = 16000;

// 对话态展示：dialogMode=false → 'off'；否则按 agentState 分档
const dialogPhase = computed<'off' | 'listening' | 'processing' | 'speaking'>(() => {
  if (!dialogMode.value) return 'off';
  if (props.agentState === 'processing') return 'processing';
  if (props.agentState === 'speaking') return 'speaking';
  // idle 或 listening 都视为在听
  return 'listening';
});

const dialogLabel = computed(() => {
  switch (dialogPhase.value) {
    case 'off':
      return '开始对话';
    case 'listening':
      return '正在听…';
    case 'processing':
      return '思考中…';
    case 'speaking':
      return '说话中…';
  }
  return '';
});

function submit() {
  const trimmed = text.value.trim();
  if (!trimmed || props.disabled) return;
  emit('send', trimmed);
  text.value = '';
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !composing.value) {
    e.preventDefault();
    submit();
  }
}

// ---------- M34 实时对话循环 ----------

function resetSilenceTimer() {
  if (silenceTimer) clearTimeout(silenceTimer);
  silenceTimer = setTimeout(() => {
    dialogError.value = '静默超过 5 分钟，已退出对话循环';
    stopDialog();
  }, SILENCE_TIMEOUT_MS);
}

async function toggleDialog() {
  if (dialogMode.value) {
    stopDialog();
  } else {
    await startDialog();
  }
}

// 一个 46 字节的静音 wav，用于 iOS Safari autoplay unlock——在用户 gesture
// 里 play() 一次，之后 Live2D fork new Audio(ttsUrl) 才能正常出声
const SILENT_WAV_DATAURL =
  'data:audio/wav;base64,UklGRjIAAABXQVZFZm10IBIAAAABAAEAQB8AAEAfAAABAAgAAABmYWN0BAAAAAAAAABkYXRhAAAAAA==';

async function startDialog() {
  dialogError.value = null;

  // iOS/移动端 autoplay unlock：在用户点"开始对话"的 gesture 上下文里
  // 播一条静音，把整页的 Audio 子系统标记为 unlocked，后续 Live2D fork 创建
  // 新 HTMLAudioElement 播 TTS 才不会被 Safari 的自动播放策略静默屏蔽。
  // 注意：不能 await —— iOS Safari 某些版本返回的 play() Promise 永不 settle，
  // 会把整个 startDialog 卡死。fire-and-forget 即可，unlock 是同步副作用。
  try {
    const warmup = new Audio(SILENT_WAV_DATAURL);
    warmup.muted = true;
    const p = warmup.play();
    if (p && typeof p.catch === 'function') p.catch(() => { /* ignore */ });
  } catch { /* ignore */ }
  // 顺便尝试 resume AudioContext（Chrome/Firefox 走这条更标准）
  try {
    const Ctx = (window as any).AudioContext || (window as any).webkitAudioContext;
    if (Ctx) {
      const probeCtx = new Ctx();
      if (probeCtx.state === 'suspended') void probeCtx.resume().catch(() => {});
      // 保留 ctx 引用在闭包里；让浏览器自己 GC，不显式 close 避免短时间内再次挂起
    }
  } catch { /* ignore */ }

  let stream: MediaStream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        // 依赖浏览器内置 AEC/NS/AGC 解决 TTS 回拾问题
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
  } catch (err) {
    dialogError.value = '麦克风权限被拒绝，实时对话需要授权';
    return;
  }

  // 开 ASR WS 长会话
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/ws/asr`);
  asrWs = ws;
  mediaStream = stream;

  ws.onopen = () => {
    if (ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ sample_rate: 16000 }));

    audioContext = new AudioContext({ sampleRate: 16000 });
    const source = audioContext.createMediaStreamSource(stream);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);
    processor.onaudioprocess = (e) => {
      if (ws.readyState !== WebSocket.OPEN) return;
      const data = e.inputBuffer.getChannelData(0);
      const pcm = new Int16Array(data.length);
      for (let i = 0; i < data.length; i++) {
        const s = Math.max(-1, Math.min(1, data[i]));
        pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      ws.send(pcm.buffer);
      // M35：攒当前 utterance 的 PCM，asr_final 到达时打包为 WAV 做声纹识别
      if (utteranceSamples < UTTERANCE_MAX_SAMPLES) {
        utterancePcm.push(pcm);
        utteranceSamples += pcm.length;
      }
    };
    source.connect(processor);
    processor.connect(audioContext.destination);
    workletNode = processor;

    dialogMode.value = true;
    resetSilenceTimer();
  };

  ws.onmessage = (ev) => {
    let data: any;
    try {
      data = JSON.parse(ev.data);
    } catch {
      return;
    }

    if (data.type === 'asr_partial') {
      // 活动计时器重置
      resetSilenceTimer();
      // 服务端在"说话中"时收到 partial → 本次 utterance 需打断 TTS
      if (props.agentState === 'speaking' && !bargedInThisUtterance) {
        bargedInThisUtterance = true;
        emit('speech-start');
      }
      // 把 ASR 中间稿显示到输入框作为反馈
      if (typeof data.text === 'string') text.value = data.text;
    } else if (data.type === 'asr_final') {
      resetSilenceTimer();
      // 一句完成 → 提交并重置打断标记；同时清空 text 供下一句
      const sentence = (data.text as string | undefined)?.trim() ?? '';
      let submitted = false;
      if (sentence) {
        const now = Date.now();
        const last = lastSubmittedSentence;
        if (last && last.text === sentence && now - last.at < DEDUP_WINDOW_MS) {
          // FunASR 重复发了同一句 offline；忽略第二份
        } else {
          lastSubmittedSentence = { text: sentence, at: now };
          text.value = sentence;
          submit();
          submitted = true;
        }
      }
      // M35：取这段 utterance 的 PCM 做声纹识别；重复提交的去重份也不发识别
      if (submitted && utteranceSamples >= UTTERANCE_MIN_SAMPLES) {
        const merged = new Int16Array(utteranceSamples);
        let offset = 0;
        for (const chunk of utterancePcm) {
          merged.set(chunk, offset);
          offset += chunk.length;
        }
        try {
          const wav = encodePcmInt16ToWav(merged, 16000);
          emit('identify-audio', wav);
        } catch { /* ignore */ }
      }
      utterancePcm = [];
      utteranceSamples = 0;
      bargedInThisUtterance = false;
    } else if (data.type === 'asr_result') {
      // 旧 M18 兼容消息；M34 循环里忽略（已通过 asr_final 处理）
    } else if (data.type === 'asr_error') {
      dialogError.value = `识别出错：${data.message}`;
      stopDialog();
    }
  };

  ws.onerror = () => {
    dialogError.value = 'ASR 连接出错';
    stopDialog();
  };
  ws.onclose = () => {
    if (dialogMode.value) {
      // 非主动关：清理一下状态，保留错误提示
      dialogError.value = dialogError.value ?? 'ASR 连接已关闭';
      stopDialog();
    }
  };
}

function stopDialog() {
  dialogMode.value = false;
  bargedInThisUtterance = false;
  utterancePcm = [];
  utteranceSamples = 0;

  if (silenceTimer) {
    clearTimeout(silenceTimer);
    silenceTimer = null;
  }

  if (workletNode) {
    try { workletNode.disconnect(); } catch { /* ignore */ }
    workletNode = null;
  }
  if (audioContext) {
    audioContext.close().catch(() => { /* ignore */ });
    audioContext = null;
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }
  if (asrWs) {
    const ws = asrWs;
    asrWs = null;
    if (ws.readyState === WebSocket.OPEN) {
      try { ws.send(JSON.stringify({ eof: true })); } catch { /* ignore */ }
      try { ws.close(); } catch { /* ignore */ }
    }
  }

  text.value = '';
}

// ---------- 页面生命周期 ----------

function onVisibilityChange() {
  if (!dialogMode.value) return;
  if (document.hidden) {
    hiddenExitTimer = setTimeout(() => {
      dialogError.value = '页面长时间在后台，已退出对话循环';
      stopDialog();
    }, HIDDEN_EXIT_MS);
  } else if (hiddenExitTimer) {
    clearTimeout(hiddenExitTimer);
    hiddenExitTimer = null;
  }
}
document.addEventListener('visibilitychange', onVisibilityChange);

// agentState 变 speaking 时，准备好下一次 partial 触发的打断（重置标记）
watch(
  () => props.agentState,
  (next, prev) => {
    if (prev === 'speaking' && next !== 'speaking') {
      // 说完话或被打断后 → 下一句 utterance 重新允许 speech_start
      bargedInThisUtterance = false;
    }
  },
);

onBeforeUnmount(() => {
  stopDialog();
  if (hiddenExitTimer) clearTimeout(hiddenExitTimer);
  document.removeEventListener('visibilitychange', onVisibilityChange);
});
</script>

<template>
  <form
    class="border-t border-slate-200 bg-white px-3 py-2 flex gap-2 items-end"
    @submit.prevent="submit"
  >
    <textarea
      v-model="text"
      :disabled="disabled || dialogMode"
      rows="2"
      class="flex-1 resize-none border border-slate-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring focus:ring-indigo-200 disabled:bg-slate-50 disabled:text-slate-400"
      :placeholder="dialogMode ? dialogLabel : '说点什么…（Enter 发送，Shift+Enter 换行）'"
      @keydown="onKeydown"
      @compositionstart="composing = true"
      @compositionend="composing = false"
    />

    <!-- 实时对话循环按钮（M34）：替代了原 M18 的 push-to-talk 麦克风 -->
    <button
      type="button"
      class="shrink-0 rounded-md px-3 py-2 text-sm border transition-colors"
      :class="[
        dialogMode
          ? 'bg-rose-500 text-white border-rose-500 hover:bg-rose-600 animate-pulse'
          : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50',
      ]"
      :disabled="disabled"
      :title="dialogMode ? '结束对话' : '开始对话（麦克风实时监听）'"
      @click="toggleDialog"
    >
      <span v-if="!dialogMode">🎙 开始对话</span>
      <span v-else>■ {{ dialogLabel }}</span>
    </button>

    <!-- 文本发送按钮（保留文字输入路径） -->
    <button
      type="submit"
      class="shrink-0 rounded-md px-3 py-2 text-sm bg-indigo-500 text-white hover:bg-indigo-600 disabled:bg-slate-300 disabled:text-slate-400"
      :disabled="disabled || dialogMode || !text.trim()"
    >
      发送
    </button>
  </form>

  <div
    v-if="dialogError"
    class="border-t border-rose-100 bg-rose-50 text-rose-700 text-xs px-3 py-1.5"
  >
    {{ dialogError }}
  </div>
</template>
