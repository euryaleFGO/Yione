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
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
