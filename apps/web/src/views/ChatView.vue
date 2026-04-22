<script setup lang="ts">
import { onMounted, ref } from 'vue';

const backendOk = ref<boolean | null>(null);
const backendVersion = ref<string>('');

onMounted(async () => {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    backendOk.value = Boolean(data?.ok);
    backendVersion.value = data?.version ?? '';
  } catch {
    backendOk.value = false;
  }
});
</script>

<template>
  <section class="max-w-3xl mx-auto px-6 py-10 space-y-4">
    <h1 class="text-2xl font-bold">你好，玲 👋</h1>
    <p class="text-slate-600">
      M0 骨架：主站 Vue 页面已就位。M1 起会接上
      <code class="bg-slate-100 px-1 rounded">@webling/core</code> 的 chat / ws 客户端。
    </p>

    <div class="rounded-md border border-slate-200 p-4 bg-white">
      <div class="text-sm text-slate-500">后端健康检查</div>
      <div v-if="backendOk === null" class="mt-1 text-slate-400">检查中…</div>
      <div v-else-if="backendOk" class="mt-1 text-emerald-600">
        OK · backend v{{ backendVersion }}
      </div>
      <div v-else class="mt-1 text-rose-600">
        无响应（确认 <code>uvicorn</code> 已在 8000 端口）
      </div>
    </div>
  </section>
</template>
