<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue';

const props = defineProps<{
  disabled?: boolean;
}>();

const emit = defineEmits<{ send: [text: string] }>();

const text = ref('');
const composing = ref(false);
const recording = ref(false);
const asrText = ref('');

let mediaRecorder: MediaRecorder | null = null;
let asrWs: WebSocket | null = null;

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

async function toggleVoice() {
  if (recording.value) {
    stopVoice();
  } else {
    await startVoice();
  }
}

async function startVoice() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    // 连接 ASR WebSocket
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    asrWs = new WebSocket(`${proto}://${location.host}/ws/asr`);

    asrWs.onopen = () => {
      // 发送配置
      asrWs!.send(JSON.stringify({ sample_rate: 16000 }));

      // 开始录音
      mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0 && asrWs?.readyState === WebSocket.OPEN) {
          e.data.arrayBuffer().then((buf) => {
            asrWs!.send(buf);
          });
        }
      };

      mediaRecorder.start(250); // 每 250ms 发送一次
      recording.value = true;
      asrText.value = '';
    };

    asrWs.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      if (data.type === 'asr_result') {
        if (data.text) {
          asrText.value = data.text;
          text.value = data.text;
        }
        if (data.is_final) {
          stopVoice();
          // 自动发送
          if (text.value.trim()) {
            submit();
          }
        }
      } else if (data.type === 'asr_error') {
        console.error('ASR error:', data.message);
        stopVoice();
      }
    };

    asrWs.onerror = () => {
      stopVoice();
    };

    asrWs.onclose = () => {
      if (recording.value) stopVoice();
    };
  } catch (err) {
    console.error('Microphone access denied:', err);
    alert('无法访问麦克风，请检查浏览器权限');
  }
}

function stopVoice() {
  recording.value = false;

  if (mediaRecorder?.state === 'recording') {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach((t) => t.stop());
  }
  mediaRecorder = null;

  if (asrWs?.readyState === WebSocket.OPEN) {
    asrWs.close();
  }
  asrWs = null;
}

onBeforeUnmount(() => {
  stopVoice();
});
</script>

<template>
  <form
    class="border-t border-slate-200 bg-white px-3 py-2 flex gap-2 items-end"
    @submit.prevent="submit"
  >
    <textarea
      v-model="text"
      :disabled="disabled"
      rows="2"
      class="flex-1 resize-none rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:bg-slate-100"
      placeholder="和玲说点什么，Enter 发送，Shift+Enter 换行"
      @keydown="onKeydown"
      @compositionstart="composing = true"
      @compositionend="composing = false"
    />
    <button
      type="button"
      :class="[
        'px-3 py-2 rounded-md text-sm transition-colors',
        recording
          ? 'bg-red-500 text-white animate-pulse'
          : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
      ]"
      :title="recording ? '停止录音' : '语音输入'"
      @click="toggleVoice"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
        <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
      </svg>
    </button>
    <button
      type="submit"
      :disabled="disabled || !text.trim()"
      class="px-4 py-2 rounded-md bg-indigo-500 text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
    >
      发送
    </button>
  </form>
</template>
