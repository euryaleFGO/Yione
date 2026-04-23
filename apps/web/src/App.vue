<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router';
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <header class="px-4 py-3 border-b border-slate-200 flex items-center gap-4">
      <RouterLink to="/" class="text-xl font-semibold hover:text-indigo-600">玲 · webLing</RouterLink>
      <nav class="flex items-center gap-1 text-sm">
        <RouterLink to="/" class="px-3 py-1.5 rounded hover:bg-slate-100" active-class="bg-indigo-50 text-indigo-600">聊天</RouterLink>
        <RouterLink to="/characters" class="px-3 py-1.5 rounded hover:bg-slate-100" active-class="bg-indigo-50 text-indigo-600">形象</RouterLink>
        <RouterLink to="/voices" class="px-3 py-1.5 rounded hover:bg-slate-100" active-class="bg-indigo-50 text-indigo-600">音色</RouterLink>
        <RouterLink to="/speakers" class="px-3 py-1.5 rounded hover:bg-slate-100" active-class="bg-indigo-50 text-indigo-600">说话人</RouterLink>
        <RouterLink to="/history" class="px-3 py-1.5 rounded hover:bg-slate-100" active-class="bg-indigo-50 text-indigo-600">历史</RouterLink>
        <RouterLink to="/knowledge" class="px-3 py-1.5 rounded hover:bg-slate-100" active-class="bg-indigo-50 text-indigo-600">图谱</RouterLink>
        <RouterLink to="/prompts" class="px-3 py-1.5 rounded hover:bg-slate-100" active-class="bg-indigo-50 text-indigo-600">Prompt</RouterLink>
        <a href="/docs" target="_blank" class="px-3 py-1.5 rounded hover:bg-slate-100">API</a>
      </nav>
    </header>
    <main class="flex-1">
      <RouterView />
    </main>
  </div>
</template>
