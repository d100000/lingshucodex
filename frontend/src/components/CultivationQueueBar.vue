<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { cultivationApi, characterApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'

const props = defineProps({
  embedded: { type: Boolean, default: false },
})

const router = useRouter()
const route = useRoute()
const game = useGameStore()
const queue = ref({ tasks: [], running: null, queued_count: 0, active_count: 0 })
const expanded = ref(false)
let timer = null

const running = computed(() => queue.value.running)
const visible = computed(() => !!game.character && (props.embedded || route.path !== '/home'))
const title = computed(() => running.value?.title || (queue.value.tasks?.[0]?.title || '墨炉待燃'))
const stateLabel = computed(() => {
  if (running.value) return '燃灵中'
  if (queue.value.queued_count) return '待燃'
  return '空闲'
})
const tokenLabel = computed(() => {
  if (running.value) return `${running.value.estimated_tokens} token`
  if (queue.value.queued_count) return `${queue.value.queued_count} 个等待`
  return '无排队'
})

async function refresh() {
  if (!visible.value) return
  try {
    const { data } = await cultivationApi.queue()
    queue.value = data
    if (data.running) {
      const me = await characterApi.me()
      game.setCharacter(me.data)
    }
  } catch (_) {}
}

async function resume(task) {
  await cultivationApi.resume(task.id)
  refresh()
}

async function cancel(task) {
  await cultivationApi.cancel(task.id)
  refresh()
}

function openBook() {
  expanded.value = false
  router.push('/novel')
}

onMounted(() => {
  refresh()
  timer = setInterval(refresh, 1800)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div v-if="visible" class="queue-shell" :class="{ expanded, embedded: props.embedded, floating: !props.embedded }">
    <div class="queue-actions">
      <button class="queue-main" @click="expanded = !expanded">
        <span class="furnace-mark" :class="{ active: running }">
          <img src="/images/ui/moluo-icon.png" alt="" />
        </span>
        <span class="queue-copy">
          <span class="queue-topline">
            <span class="label">墨炉</span>
            <span class="state-pill" :class="{ active: running, waiting: queue.queued_count && !running }">
              {{ stateLabel }}
            </span>
          </span>
          <span class="title">{{ title }}</span>
          <span class="tokens">{{ tokenLabel }}</span>
        </span>
        <span class="chevron" :class="{ open: expanded }">⌄</span>
      </button>
      <button class="book-btn" @click="openBook">本命书</button>
    </div>

    <div v-if="expanded" class="queue-drawer">
      <div class="drawer-head">
        <div>
          <span>燃灵队列</span>
          <small>{{ queue.active_count || 0 }} 个处理中</small>
        </div>
        <button class="drawer-close" @click="expanded = false">收起</button>
      </div>
      <div v-if="!queue.tasks?.length" class="empty-row">
        墨炉空闲，等待新的章节入炉。
      </div>
      <div v-for="task in queue.tasks" :key="task.id" class="task-row">
        <div>
          <div class="task-title">{{ task.title }}</div>
          <div class="task-meta">{{ task.status }} · {{ task.estimated_tokens }} token · 修为 +{{ task.cultivation_gained }}</div>
          <div v-if="task.error" class="task-error">{{ task.error }}</div>
        </div>
        <div class="task-actions">
          <button v-if="task.status === 'budget_blocked' || task.status === 'paused'" @click="resume(task)">继续</button>
          <button v-if="task.status !== 'running'" @click="cancel(task)">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.queue-shell {
  pointer-events: none;
  font-family: 'STKaiti', 'KaiTi', serif;
}

.queue-shell.floating {
  position: fixed;
  right: 18px;
  top: calc(92px + var(--safe-top));
  z-index: 90;
  max-width: calc(100vw - 24px);
}

.queue-shell.embedded {
  position: relative;
  z-index: 70;
  pointer-events: auto;
}

.queue-actions {
  display: flex;
  align-items: stretch;
  justify-content: flex-end;
  gap: 8px;
  pointer-events: auto;
}

.queue-main,
.book-btn {
  border: 1px solid rgba(212,162,76,0.34);
  background:
    linear-gradient(180deg, rgba(28,20,10,0.92), rgba(8,8,18,0.94));
  color: #F3E4C3;
  box-shadow: 0 10px 28px rgba(0,0,0,0.32);
  height: 52px;
  cursor: pointer;
  transition: border-color 0.18s, box-shadow 0.18s, transform 0.18s, background 0.18s;
}

.queue-main:hover,
.book-btn:hover {
  border-color: rgba(255,224,163,0.72);
  box-shadow: 0 12px 30px rgba(0,0,0,0.36), 0 0 18px rgba(212,162,76,0.16);
}

.queue-main {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 260px;
  padding: 7px 10px;
  border-radius: 8px;
  text-align: left;
}

.book-btn {
  width: 78px;
  border-radius: 8px;
  font-weight: 700;
  letter-spacing: 2px;
  font-size: 13px;
}

.furnace-mark {
  flex: 0 0 34px;
  width: 34px;
  height: 34px;
  border-radius: 7px;
  display: grid;
  place-items: center;
  overflow: hidden;
  background: rgba(8,8,18,0.82);
  border: 1px solid rgba(212,162,76,0.32);
  box-shadow: inset 0 0 14px rgba(212,162,76,0.08), 0 0 10px rgba(0,0,0,0.32);
}

.furnace-mark img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transform: scale(1.12);
}

.furnace-mark.active {
  background: rgba(212,162,76,0.18);
  border-color: rgba(255,224,163,0.72);
  box-shadow: 0 0 14px rgba(212,162,76,0.42), inset 0 0 16px rgba(212,162,76,0.1);
}

.queue-copy {
  min-width: 0;
  flex: 1;
  display: grid;
  gap: 2px;
}

.queue-topline {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.label {
  color: #D4A24C;
  font-weight: 800;
  letter-spacing: 2px;
}

.state-pill {
  height: 18px;
  padding: 0 7px;
  border-radius: 9px;
  display: inline-flex;
  align-items: center;
  color: #8E98AA;
  background: rgba(255,255,255,0.05);
  font-size: 11px;
  letter-spacing: 1px;
  white-space: nowrap;
}

.state-pill.active {
  color: #FFE0A3;
  background: rgba(212,162,76,0.18);
}

.state-pill.waiting {
  color: #7FC7E8;
  background: rgba(127,199,232,0.12);
}

.title {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  color: #F3E4C3;
  font-size: 13px;
  letter-spacing: 1px;
}

.tokens {
  color: #B8C7E0;
  font-size: 11px;
  letter-spacing: 1px;
}

.chevron {
  color: #8E98AA;
  transform: translateY(-1px);
  transition: transform 0.18s, color 0.18s;
  font-size: 16px;
}

.chevron.open {
  color: #D4A24C;
  transform: rotate(180deg) translateY(1px);
}

.queue-drawer {
  position: absolute;
  right: 0;
  top: calc(100% + 10px);
  width: min(360px, calc(100vw - 28px));
  border: 1px solid rgba(212,162,76,0.35);
  background:
    linear-gradient(180deg, rgba(18,14,26,0.98), rgba(8,8,18,0.98));
  box-shadow: 0 12px 36px rgba(0,0,0,0.46);
  max-height: min(460px, 72vh);
  overflow: auto;
  pointer-events: auto;
  border-radius: 8px;
  animation: drawer-in 0.16s ease-out;
}

@keyframes drawer-in {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}

.drawer-head,
.empty-row,
.task-row {
  padding: 10px 12px;
}

.drawer-head {
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  background: rgba(14,12,22,0.98);
  border-bottom: 1px solid rgba(212,162,76,0.2);
  color: #D4A24C;
  font-weight: 800;
}

.drawer-head small {
  display: block;
  margin-top: 2px;
  color: #8E98AA;
  font-size: 12px;
  font-weight: 400;
}

.drawer-close {
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(255,255,255,0.04);
  color: #B8C7E0;
  height: 28px;
  padding: 0 10px;
  border-radius: 6px;
  cursor: pointer;
}

.drawer-close:hover {
  color: #FFE0A3;
  border-color: rgba(212,162,76,0.42);
}

.empty-row {
  color: #8E98AA;
  font-size: 13px;
}

.task-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

.task-title {
  color: #F3E4C3;
  font-weight: 700;
}

.task-meta,
.task-error {
  margin-top: 4px;
  color: #9CA8BB;
  font-size: 12px;
}

.task-error {
  color: #FFB454;
}

.task-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

.task-actions button {
  border: 1px solid rgba(255,255,255,0.16);
  background: rgba(255,255,255,0.06);
  color: #E8D6B0;
  height: 28px;
  padding: 0 10px;
  cursor: pointer;
}

@media (max-width: 640px) {
  .queue-shell.floating {
    top: calc(74px + var(--safe-top));
    right: calc(10px + var(--safe-right));
  }
  .queue-main {
    width: min(250px, calc(100vw - 20px));
  }
  .queue-drawer {
    right: 0;
  }
  .tokens {
    display: none;
  }
  .queue-shell.embedded {
    width: 100%;
  }
  .queue-shell.embedded .queue-actions {
    justify-content: stretch;
  }
  .queue-shell.embedded .queue-main {
    flex: 1;
    width: auto;
  }
}
</style>
