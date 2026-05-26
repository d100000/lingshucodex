<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGameStore } from '../stores/game.js'

const route = useRoute()
const router = useRouter()
const game = useGameStore()

const tabs = [
  { key: 'home', label: '主城', icon: '⌂', to: '/home' },
  { key: 'explore', label: '地图', icon: '⌖', to: '/explore' },
  { key: 'novel', label: '本命书', icon: '▣', to: '/novel' },
  { key: 'inventory', label: '背包', icon: '▤', to: '/inventory' },
  { key: 'more', label: '更多', icon: '☷', to: '/more' },
]

const activeKey = computed(() => route.meta.mobileTab || tabs.find(t => route.path.startsWith(t.to))?.key)
const queueBurning = computed(() => !!game.character?.daily_token_used || !!game.character?.token_total)

function go(tab) {
  if (route.path !== tab.to) router.push(tab.to)
}
</script>

<template>
  <nav class="mobile-tabbar" aria-label="移动端主导航">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      class="mtab"
      :class="{ active: activeKey === tab.key }"
      @click="go(tab)"
    >
      <span class="mtab-icon">{{ tab.icon }}</span>
      <span class="mtab-label">{{ tab.label }}</span>
      <span v-if="tab.key === 'novel' && queueBurning" class="mtab-dot">燃</span>
    </button>
  </nav>
</template>

<style scoped>
.mobile-tabbar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 180;
  display: none;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 2px;
  padding: 7px calc(8px + var(--safe-right)) calc(7px + var(--safe-bottom)) calc(8px + var(--safe-left));
  border-top: 1px solid rgba(212, 162, 76, 0.28);
  background: linear-gradient(180deg, rgba(10, 10, 20, 0.78), rgba(6, 7, 14, 0.96));
  backdrop-filter: blur(12px);
  box-shadow: 0 -10px 26px rgba(0, 0, 0, 0.34);
}

.mtab {
  position: relative;
  min-width: 0;
  min-height: 48px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: #9CA8BB;
  display: grid;
  place-items: center;
  gap: 1px;
  font: inherit;
  cursor: pointer;
}

.mtab.active {
  color: #FFE0A3;
  border-color: rgba(212, 162, 76, 0.28);
  background: rgba(212, 162, 76, 0.1);
}

.mtab-icon {
  font-size: 18px;
  line-height: 1;
}

.mtab-label {
  font-size: 11px;
  letter-spacing: 0;
  white-space: nowrap;
}

.mtab-dot {
  position: absolute;
  top: 4px;
  right: 8px;
  height: 16px;
  min-width: 16px;
  padding: 0 4px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: rgba(212, 162, 76, 0.96);
  color: #1A1208;
  font-size: 9px;
  font-weight: 800;
}

@media (max-width: 768px) {
  .mobile-tabbar { display: grid; }
}

@media (orientation: landscape) and (max-height: 480px) {
  .mobile-tabbar {
    top: 0;
    right: auto;
    width: calc(68px + var(--safe-left));
    grid-template-columns: 1fr;
    grid-auto-rows: minmax(48px, 1fr);
    padding: calc(8px + var(--safe-top)) 6px calc(8px + var(--safe-bottom)) calc(6px + var(--safe-left));
    border-top: 0;
    border-right: 1px solid rgba(212, 162, 76, 0.24);
  }
  .mtab {
    min-height: 44px;
  }
  .mtab-label {
    font-size: 10px;
  }
}
</style>
