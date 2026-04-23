<script setup lang="ts">
import type { AvatarControls } from '@webling/live2d-kit';
import { storeToRefs } from 'pinia';
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import AvatarStage from '@/components/AvatarStage.vue';
import InputBar from '@/components/InputBar.vue';
import MessageList from '@/components/MessageList.vue';
import { useChatStore } from '@/stores/chat';

const chat = useChatStore();
const router = useRouter();
const { messages, agentState, connection, lastError, session, currentCharacter } = storeToRefs(chat);
const backendOk = ref<boolean | null>(null);
const backendVersion = ref('');

// agent 在忙（processing 或 speaking）时暴露"停止"按钮
const canInterrupt = computed(
  () => agentState.value === 'processing' || agentState.value === 'speaking',
);

onMounted(async () => {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    backendOk.value = Boolean(data?.ok);
    backendVersion.value = data?.version ?? '';
  } catch {
    backendOk.value = false;
    return;
  }
  try {
    await chat.connectSocket();
  } catch {
    /* errors surfaced via lastError */
  }
});

onBeforeUnmount(() => {
  void chat.disconnect();
});

function onAvatarReady(controls: AvatarControls) {
  chat.setAvatarControls(controls);
}

async function onSend(text: string) {
  await chat.submit(text, connection.value === 'open' ? 'ws' : 'rest');
}

function onInterrupt() {
  chat.interrupt();
}

// M34：对话循环中前端检测到用户开口，通知服务端打断
function onSpeechStart() {
  chat.sendSpeechStart();
}

// M35：每句 utterance 的 WAV → POST 给 /api/speakers/identify 做声纹识别
function onIdentifyAudio(wav: Blob) {
  void chat.identifySpeakerFromWav(wav);
}
</script>

<template>
  <section class="h-[calc(100vh-60px)] flex flex-col lg:flex-row">
    <!-- Avatar panel -->
    <div class="flex-1 min-w-0 min-h-0 relative overflow-hidden border-b lg:border-b-0 lg:border-r border-slate-200">
      <AvatarStage @ready="onAvatarReady" />
      <div
        class="absolute top-2 left-2 z-10 text-xs bg-white/80 backdrop-blur rounded px-2 py-1 flex gap-2"
      >
        <span>
          后端：
          <span v-if="backendOk === null">…</span>
          <span v-else-if="backendOk" class="text-emerald-600">v{{ backendVersion }}</span>
          <span v-else class="text-rose-600">未就绪</span>
        </span>
        <span>·</span>
        <span>{{ connection }}</span>
        <span>·</span>
        <span>{{ agentState }}</span>
      </div>

      <!-- 打断/停止按钮：只在玲正在思考或说话时出现 -->
      <button
        v-if="canInterrupt"
        type="button"
        class="absolute top-2 right-2 z-10 text-xs px-3 py-1.5 rounded-full bg-rose-500/90 hover:bg-rose-500 text-white shadow-sm backdrop-blur"
        @click="onInterrupt"
      >
        停止
      </button>
    </div>

    <!-- Chat panel -->
    <div
      class="shrink-0 flex flex-col bg-white w-full lg:w-[380px] h-[55vh] lg:h-auto"
    >
      <div class="px-4 py-2 text-xs text-slate-500 border-b border-slate-100 flex gap-2 items-center">
        <span>会话：{{ session?.id ?? '未建立' }}</span>
        <span v-if="currentCharacter" class="cursor-pointer hover:text-indigo-600" @click="router.push('/characters')">
          · {{ currentCharacter.name }}
        </span>
        <span v-if="lastError" class="text-rose-600 truncate">· {{ lastError }}</span>
      </div>
      <MessageList :messages="messages" class="flex-1 min-h-0" />
      <InputBar
        :disabled="connection === 'error'"
        :agent-state="agentState"
        @send="onSend"
        @speech-start="onSpeechStart"
        @identify-audio="onIdentifyAudio"
      />
    </div>
  </section>
</template>
