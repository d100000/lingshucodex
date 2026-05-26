<script setup>
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { characterApi } from '../api/client.js'
import { useAuthStore } from '../stores/auth.js'
import { useGameStore } from '../stores/game.js'
import CultivationQueueBar from './CultivationQueueBar.vue'
import MobileTabBar from './MobileTabBar.vue'
import OfflineBoundary from './OfflineBoundary.vue'
import FeedbackEntry from './FeedbackEntry.vue'
import { dispatchResume, installViewportSync, logTelemetry } from '../utils/mobile.js'

const route = useRoute()
const auth = useAuthStore()
const game = useGameStore()

let cleanupViewport = null

const showMobileTab = computed(() => (
  auth.isLoggedIn
  && !!game.character
  && !route.meta.hideMobileTabBar
  && !route.meta.mobileImmersive
))

const showQueue = computed(() => (
  !!game.character
  && route.meta.showQueueBar !== false
  && route.path !== '/home'
))

async function refreshCharacter(reason) {
  if (!auth.isLoggedIn || !game.character) return
  try {
    const { data } = await characterApi.me()
    game.setCharacter(data)
    logTelemetry('resume_refresh_ok', { reason })
  } catch (e) {
    logTelemetry('resume_refresh_failed', { reason, message: e.message })
  }
}

function onVisible() {
  if (document.visibilityState === 'visible') {
    dispatchResume('visibility')
    refreshCharacter('visibility')
  }
}

function onPageShow(event) {
  dispatchResume(event.persisted ? 'pageshow_bfcache' : 'pageshow')
  refreshCharacter('pageshow')
}

function onFocus() {
  dispatchResume('focus')
  refreshCharacter('focus')
}

onMounted(() => {
  cleanupViewport = installViewportSync()
  document.addEventListener('visibilitychange', onVisible)
  window.addEventListener('pageshow', onPageShow)
  window.addEventListener('focus', onFocus)
})

onUnmounted(() => {
  cleanupViewport?.()
  document.removeEventListener('visibilitychange', onVisible)
  window.removeEventListener('pageshow', onPageShow)
  window.removeEventListener('focus', onFocus)
})

watch(() => route.fullPath, (path) => {
  logTelemetry('page_view', { path, title: route.meta.title || '' })
}, { immediate: true })
</script>

<template>
  <div
    class="mobile-app-shell"
    :class="{
      'has-mobile-tab': showMobileTab,
      'mobile-immersive': route.meta.mobileImmersive,
    }"
  >
    <RouterView />
    <CultivationQueueBar v-if="showQueue" />
    <MobileTabBar v-if="showMobileTab" />
    <FeedbackEntry />
    <OfflineBoundary />
  </div>
</template>

<style scoped>
.mobile-app-shell {
  min-height: var(--app-svh);
}

@media (max-width: 768px) {
  .mobile-app-shell.has-mobile-tab {
    padding-bottom: 0;
  }
}
</style>
