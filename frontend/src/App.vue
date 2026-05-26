<script setup>
import { onMounted } from 'vue'
import { darkTheme, NConfigProvider, NMessageProvider, NDialogProvider, zhCN, dateZhCN } from 'naive-ui'
import { ensureItemMap } from './utils/items.js'
import MobileAppShell from './components/MobileAppShell.vue'
import CharacterPreviewModal from './components/CharacterPreviewModal.vue'

// 启动时预拉物品字典(全局复用,显示中文名)
onMounted(() => { ensureItemMap() })

const themeOverrides = {
  common: {
    primaryColor: '#D4A24C',
    primaryColorHover: '#E5B560',
    primaryColorPressed: '#B58A3E',
    primaryColorSuppl: '#D4A24C',
    successColor: '#52B788',
    warningColor: '#FFB454',
    errorColor: '#C03F3F',
    bodyColor: '#0a0a14',
    cardColor: '#16162a',
    modalColor: '#1a1a2e',
    popoverColor: '#1a1a2e',
    fontFamily: '"PingFang SC","Microsoft YaHei","Source Han Sans SC",system-ui,sans-serif',
  },
}
</script>

<template>
  <NConfigProvider :theme="darkTheme" :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <NMessageProvider>
      <NDialogProvider>
        <MobileAppShell />
        <CharacterPreviewModal />
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<style>
:root {
  --app-vh: 100dvh;
  --app-svh: 100svh;
  --visual-vh: 100vh;
  --visual-vw: 100vw;
  --safe-top: env(safe-area-inset-top, 0px);
  --safe-right: env(safe-area-inset-right, 0px);
  --safe-bottom: env(safe-area-inset-bottom, 0px);
  --safe-left: env(safe-area-inset-left, 0px);
  --mobile-bottom-nav-h: 64px;
  --mobile-page-x: 16px;
}

html,
body,
#app {
  min-height: var(--app-svh);
  min-height: 100dvh;
  overscroll-behavior: none;
}

body {
  touch-action: manipulation;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
.fade-in { animation: fadeIn 0.6s ease-out; }

@media (max-width: 768px) {
  .mobile-tab-page {
    padding-bottom: calc(var(--mobile-bottom-nav-h) + var(--safe-bottom));
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
    scroll-behavior: auto !important;
  }
}
</style>
