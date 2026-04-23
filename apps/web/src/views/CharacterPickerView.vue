<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';

import { useChatStore } from '@/stores/chat';

const chat = useChatStore();
const router = useRouter();

onMounted(async () => {
  await chat.fetchCharacters();
});

async function selectCharacter(id: string) {
  await chat.changeCharacter(id);
  router.push('/');
}
</script>

<template>
  <section class="max-w-3xl mx-auto px-6 py-10">
    <h1 class="text-2xl font-bold mb-6">选择形象</h1>

    <div v-if="chat.characters.length === 0" class="text-slate-500">
      暂无可用形象
    </div>

    <div v-else class="grid grid-cols-2 md:grid-cols-3 gap-4">
      <button
        v-for="char in chat.characters"
        :key="char.id"
        type="button"
        class="p-4 border rounded-lg hover:border-indigo-500 transition-colors text-left"
        :class="{
          'border-indigo-500 bg-indigo-50': chat.currentCharacter?.id === char.id,
          'border-slate-200': chat.currentCharacter?.id !== char.id,
        }"
        @click="selectCharacter(char.id)"
      >
        <div class="font-medium text-lg">{{ char.name }}</div>
        <div class="text-sm text-slate-500 mt-1">ID: {{ char.id }}</div>
        <div v-if="char.greeting" class="text-xs text-slate-400 mt-2 line-clamp-2">
          {{ char.greeting }}
        </div>
      </button>
    </div>
  </section>
</template>
