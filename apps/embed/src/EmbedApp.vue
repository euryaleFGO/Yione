<script setup lang="ts">
import type { AvatarControls } from '@webling/live2d-kit';
import { storeToRefs } from 'pinia';
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

// 复用 web 的组件和 store —— alias '@' → apps/web/src
import AvatarStage from '@/components/AvatarStage.vue';
import InputBar from '@/components/InputBar.vue';
import MessageList from '@/components/MessageList.vue';
import { useAuthStore } from '@/stores/auth';
import { useChatStore } from '@/stores/chat';

const auth = useAuthStore();
const chat = useChatStore();
const { messages, agentState, connection, lastError, currentCharacter } = storeToRefs(chat);

const initError = ref<string | null>(null);
const canInterrupt = computed(
  () => agentState.value === 'processing' || agentState.value === 'speaking',
);

// postMessage 桥：向父页面报告状态变化，父页面可据此隐藏按钮、显示红点等
function postToParent(payload: Record<string, unknown>): void {
  try {
    window.parent.postMessage({ source: 'webling', ...payload }, '*');
  } catch {
    // 跨源拒绝时静默
  }
}

// 监听父页面发过来的控制消息（sendMessage / close / setCharacter）
function onParentMessage(ev: MessageEvent): void {
  const data = ev.data;
  if (!data || typeof data !== 'object') return;
  // 只认明确带 webling 标识的，避免把浏览器扩展等噪声当作指令
  if (data.target !== 'webling') return;
  switch (data.type) {
    case 'send':
      if (typeof data.text === 'string' && data.text.trim()) {
        void chat.submit(data.text, 'ws');
      }
      break;
    case 'interrupt':
      chat.interrupt();
      break;
    case 'close':
      void chat.disconnect();
      postToParent({ type: 'webling:closed' });
      break;
  }
}

onMounted(async () => {
  window.addEventListener('message', onParentMessage);

  const params = new URLSearchParams(location.search);
  // 兼容旧版裸 HTML 的 apiKey / characterId 驼峰
  const apiKey = params.get('api_key') || params.get('apiKey');
  const characterId = params.get('character_id') || params.get('characterId') || 'ling';
  const apiBase =
    params.get('api_base') || params.get('apiBase') || location.origin.replace(/\/$/, '');

  // 后端 health 探针：embed 场景后端挂了要明确告诉接入方
  try {
    const res = await fetch(`${apiBase}/api/health`);
    if (!res.ok) throw new Error(`health ${res.status}`);
  } catch (err) {
    initError.value = `后端不可达：${(err as Error).message}`;
    postToParent({ type: 'webling:error', code: 'backend_down', message: initError.value });
    return;
  }

  // 换 embed JWT（允许无 api_key：dev 模式下后端放行，便于本地调试）
  if (apiKey) {
    try {
      await auth.fetchEmbedToken(apiKey, apiBase);
    } catch (err) {
      initError.value = `鉴权失败：${(err as Error).message}`;
      postToParent({ type: 'webling:error', code: 'auth_failed', message: initError.value });
      return;
    }
  }

  // 连 chat（内部会 ensureSession(characterId)、拿 greeting、开 WS）
  try {
    await chat.changeCharacter(characterId);
    await chat.connectSocket();
    postToParent({ type: 'webling:session', character_id: characterId });
  } catch (err) {
    initError.value = `会话建立失败：${(err as Error).message}`;
    postToParent({ type: 'webling:error', code: 'session_failed', message: initError.value });
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('message', onParentMessage);
  void chat.disconnect();
});

// 把 chat store 的状态变化镜像给父页面
watch(agentState, (state) => postToParent({ type: 'webling:state', value: state }));
watch(
  () => messages.value[messages.value.length - 1],
  (msg) => {
    if (!msg) return;
    postToParent({
      type: 'webling:message',
      role: msg.role,
      text: msg.text,
      id: msg.id,
    });
  },
);

function onAvatarReady(controls: AvatarControls): void {
  chat.setAvatarControls(controls);
}

async function onSend(text: string): Promise<void> {
  await chat.submit(text, connection.value === 'open' ? 'ws' : 'rest');
}

function onInterrupt(): void {
  chat.interrupt();
}

function onSpeechStart(): void {
  chat.sendSpeechStart();
}

function onIdentifyAudio(wav: Blob): void {
  void chat.identifySpeakerFromWav(wav);
}

function onClose(): void {
  postToParent({ type: 'webling:request_close' });
}
</script>

<template>
  <div class="h-full flex flex-col bg-white text-slate-900 overflow-hidden">
    <!-- mini header -->
    <header
      class="flex-none flex items-center gap-2 px-3 py-2 border-b border-slate-200 bg-white"
    >
      <div class="w-2 h-2 rounded-full" :class="{
        'bg-emerald-500': connection === 'open',
        'bg-amber-500': connection === 'connecting',
        'bg-rose-500': connection === 'error' || connection === 'closed',
        'bg-slate-300': connection === 'idle',
      }" />
      <div class="text-sm font-semibold truncate">
        {{ currentCharacter?.name || '玲' }}
      </div>
      <div class="flex-1" />
      <button
        v-if="canInterrupt"
        class="text-xs px-2 py-1 rounded bg-rose-50 text-rose-600 hover:bg-rose-100"
        @click="onInterrupt"
      >
        停止
      </button>
      <button
        class="text-lg leading-none px-1 text-slate-400 hover:text-slate-700"
        aria-label="关闭"
        @click="onClose"
      >
        ×
      </button>
    </header>

    <!-- error banner -->
    <div
      v-if="initError || lastError"
      class="flex-none text-xs px-3 py-2 bg-rose-50 text-rose-700 border-b border-rose-100"
    >
      {{ initError || lastError }}
    </div>

    <!-- avatar (flex-1 上半) -->
    <div class="flex-1 min-h-0 relative bg-gradient-to-b from-indigo-50 via-white to-white">
      <AvatarStage @ready="onAvatarReady" />
    </div>

    <!-- messages (固定高度或 flex-1 分配) -->
    <div class="flex-none h-[180px] border-t border-slate-100 overflow-hidden wl-scroll">
      <MessageList :messages="messages" />
    </div>

    <!-- input -->
    <div class="flex-none border-t border-slate-200 bg-white">
      <InputBar
        :disabled="connection !== 'open'"
        @send="onSend"
        @speech-start="onSpeechStart"
        @identify-audio="onIdentifyAudio"
      />
    </div>
  </div>
</template>
