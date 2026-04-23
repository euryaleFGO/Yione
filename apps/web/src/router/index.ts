import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'chat',
    component: () => import('@/views/ChatView.vue'),
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
  },
  {
    path: '/characters',
    name: 'characters',
    component: () => import('@/views/CharacterPickerView.vue'),
  },
  {
    path: '/voices',
    name: 'voices',
    component: () => import('@/views/VoiceSettingsView.vue'),
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('@/views/HistoryView.vue'),
  },
  {
    path: '/speakers',
    name: 'speakers',
    component: () => import('@/views/SpeakerView.vue'),
  },
  {
    path: '/knowledge',
    name: 'knowledge',
    component: () => import('@/views/KnowledgeGraph.vue'),
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
