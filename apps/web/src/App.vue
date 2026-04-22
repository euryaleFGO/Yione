<script setup lang="ts">
import { RouterView } from 'vue-router';
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <header class="px-4 py-3 border-b border-slate-200 flex items-center gap-3">
      <span class="text-xl font-semibold">玲 · webLing</span>
      <span class="text-xs text-slate-400">v0.0.1 · M0 scaffold</span>
    </header>
    <main class="flex-1">
      <RouterView />
    </main>
  </div>
</template>
