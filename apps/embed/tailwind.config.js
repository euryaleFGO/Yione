/** @type {import('tailwindcss').Config} */
export default {
  // 复用 apps/web 的组件，要把路径加进来不然 tailwind 扫不到 class
  content: [
    './embed.html',
    './src/**/*.{vue,ts,js}',
    '../web/src/components/**/*.{vue,ts}',
    '../web/src/views/**/*.{vue,ts}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
