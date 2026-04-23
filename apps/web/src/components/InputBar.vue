<script setup lang="ts">
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
// 5 分钟静默自动退出循环
let silenceTimer: ReturnType<typeof setTimeout> | null = null;
const SILENCE_TIMEOUT_MS = 5 * 60 * 1000;
// tab 切后台 30s 自动退出
let hiddenExitTimer: ReturnType<typeof setTimeout> | null = null;
const HIDDEN_EXIT_MS = 30 * 1000;

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

async function startDialog() {
  dialogError.value = null;

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
      if (sentence) {
        text.value = sentence;
        submit();
      }
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
