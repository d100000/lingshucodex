<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { dispatchResume } from '../utils/mobile.js'

const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine)
const showBack = ref(false)
let backTimer = null

function onOnline() {
  online.value = true
  showBack.value = true
  if (backTimer) clearTimeout(backTimer)
  backTimer = setTimeout(() => { showBack.value = false }, 3500)
  dispatchResume('online')
}

function onOffline() {
  online.value = false
}

onMounted(() => {
  window.addEventListener('online', onOnline)
  window.addEventListener('offline', onOffline)
})

onUnmounted(() => {
  window.removeEventListener('online', onOnline)
  window.removeEventListener('offline', onOffline)
  if (backTimer) clearTimeout(backTimer)
})
</script>

<template>
  <Transition name="netbar">
    <div v-if="!online" class="offline-bar">
      <strong>网络暂离</strong>
      <span>已保留当前进度,恢复后会重新同步墨炉与角色状态。</span>
    </div>
    <div v-else-if="showBack" class="offline-bar back">
      <strong>灵脉重连</strong>
      <span>正在校准修行状态。</span>
    </div>
  </Transition>
</template>

<style scoped>
.offline-bar {
  position: fixed;
  left: calc(12px + var(--safe-left));
  right: calc(12px + var(--safe-right));
  top: calc(10px + var(--safe-top));
  z-index: 520;
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 40px;
  padding: 8px 12px;
  border: 1px solid rgba(255, 180, 84, 0.42);
  border-radius: 8px;
  background: rgba(28, 18, 8, 0.96);
  color: #FFE0A3;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.36);
  font-size: 13px;
}

.offline-bar.back {
  border-color: rgba(82, 183, 136, 0.42);
  background: rgba(8, 28, 20, 0.94);
  color: #B6F0CE;
}

.offline-bar span {
  color: #C8BFAE;
}

.netbar-enter-active,
.netbar-leave-active {
  transition: opacity 0.18s, transform 0.18s;
}
.netbar-enter-from,
.netbar-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
