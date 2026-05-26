<script setup>
import { ref, onMounted, computed } from 'vue'
import { useMessage } from 'naive-ui'
import { dailyApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'

const msg = useMessage()
const game = useGameStore()

const daily = ref(null)
const claiming = ref(false)
const showReward = ref(false)

const completedCount = computed(() => {
  if (!daily.value) return 0
  return daily.value.tasks.filter(t => t.completed).length
})

const canClaim = computed(() => {
  if (!daily.value) return false
  return completedCount.value >= daily.value.required && !daily.value.claimed
})

const progressPct = computed(() => {
  if (!daily.value) return 0
  return Math.min(100, (completedCount.value / daily.value.required) * 100)
})

onMounted(async () => {
  try {
    const { data } = await dailyApi.get()
    daily.value = data
  } catch (e) {
    // silently fail — daily is optional
  }
})

async function claim() {
  if (claiming.value || !canClaim.value) return
  claiming.value = true
  try {
    const { data } = await dailyApi.claim()
    if (data.fatigue) {
      game.patchCharacter({ fatigue: data.fatigue.after, max_fatigue: data.fatigue.max })
    }
    msg.success('修行令已完成!获得灵气尘 ×3 与宗门贡献')
    daily.value.claimed = true
    showReward.value = true
    setTimeout(() => { showReward.value = false }, 3000)
  } catch (e) {
    msg.error(e.message)
  } finally {
    claiming.value = false
  }
}
</script>

<template>
  <div v-if="daily" class="daily-card">
    <div class="dc-header">
      <div class="dc-title">
        <span class="dc-icon">📋</span>
        <span>今日修行令</span>
      </div>
      <div class="dc-progress">
        <span class="dc-count" :class="{ done: canClaim }">
          {{ completedCount }}/{{ daily.required }}
        </span>
        <div class="dc-bar">
          <div class="dc-bar-fill" :style="{ width: progressPct + '%' }"></div>
        </div>
      </div>
    </div>

    <div class="dc-tasks">
      <div
        v-for="task in daily.tasks"
        :key="task.id"
        class="dc-task"
        :class="{ completed: task.completed }"
      >
        <span class="dt-icon">{{ task.icon }}</span>
        <div class="dt-info">
          <span class="dt-name">{{ task.name }}</span>
          <span class="dt-desc">{{ task.desc }}</span>
        </div>
        <span class="dt-check">{{ task.completed ? '✅' : '⬜' }}</span>
      </div>
    </div>

    <div class="dc-footer">
      <div class="dc-reward-preview">
        🎁 完成奖励: 灵气尘×3 · 宗门贡献+10
      </div>
      <button
        v-if="!daily.claimed"
        class="dc-claim-btn"
        :class="{ ready: canClaim }"
        :disabled="!canClaim || claiming"
        @click="claim"
      >
        {{ canClaim ? '✨ 领取奖励' : `还差 ${daily.required - completedCount} 项` }}
      </button>
      <div v-else class="dc-claimed">
        ✅ 今日修行令已完成
      </div>
    </div>

    <!-- 领取动画 -->
    <Transition name="reward-pop">
      <div v-if="showReward" class="reward-popup">
        🎊 灵气尘 ×3 · 贡献 +10
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.daily-card {
  background: linear-gradient(180deg, rgba(20, 15, 8, 0.8), rgba(8, 5, 2, 0.95));
  border: 1px solid rgba(212, 162, 76, 0.25);
  border-radius: 12px;
  padding: 16px 18px;
  margin-bottom: 20px;
  position: relative;
  overflow: hidden;
}
.daily-card::before {
  content: '';
  position: absolute;
  top: 0; left: 10%; right: 10%; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(212, 162, 76, 0.6), transparent);
}

.dc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.dc-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  color: #D4A24C;
  letter-spacing: 3px;
  font-family: 'STKaiti', 'KaiTi', serif;
}
.dc-icon { font-size: 20px; }
.dc-progress {
  display: flex;
  align-items: center;
  gap: 10px;
}
.dc-count {
  font-size: 13px;
  color: #aaa;
  font-weight: 600;
  font-family: 'SF Mono', monospace;
}
.dc-count.done { color: #52B788; }
.dc-bar {
  width: 80px;
  height: 6px;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 3px;
  overflow: hidden;
}
.dc-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #D4A24C, #FFE0A3);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.dc-tasks {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
  margin-bottom: 14px;
}
.dc-task {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  transition: all 0.2s;
}
.dc-task.completed {
  background: rgba(82, 183, 136, 0.08);
  border-color: rgba(82, 183, 136, 0.25);
}
.dt-icon { font-size: 18px; flex-shrink: 0; }
.dt-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.dt-name {
  font-size: 12px;
  color: #ddd;
  letter-spacing: 1px;
}
.dc-task.completed .dt-name { color: #95D5B2; }
.dt-desc {
  font-size: 10px;
  color: #777;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dt-check { font-size: 14px; flex-shrink: 0; }

.dc-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}
.dc-reward-preview {
  font-size: 11px;
  color: #888;
  letter-spacing: 1px;
}
.dc-claim-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #888;
  padding: 7px 18px;
  border-radius: 6px;
  font-size: 12px;
  cursor: not-allowed;
  letter-spacing: 1px;
}
.dc-claim-btn.ready {
  background: linear-gradient(135deg, rgba(212, 162, 76, 0.2), rgba(212, 162, 76, 0.08));
  border-color: #D4A24C;
  color: #FFE0A3;
  cursor: pointer;
  animation: claim-pulse 1.5s ease-in-out infinite;
}
.dc-claim-btn.ready:hover {
  background: linear-gradient(135deg, rgba(212, 162, 76, 0.35), rgba(212, 162, 76, 0.15));
  transform: scale(1.02);
}
.dc-claim-btn:disabled { opacity: 0.6; }
.dc-claimed {
  color: #52B788;
  font-size: 12px;
  letter-spacing: 2px;
}

@keyframes claim-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(212, 162, 76, 0.4); }
  50% { box-shadow: 0 0 0 6px rgba(212, 162, 76, 0); }
}

.reward-popup {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(20, 15, 8, 0.95);
  border: 2px solid #D4A24C;
  border-radius: 10px;
  padding: 14px 24px;
  color: #FFE0A3;
  font-size: 14px;
  letter-spacing: 2px;
  box-shadow: 0 0 40px rgba(212, 162, 76, 0.4);
  z-index: 10;
}
.reward-pop-enter-active { transition: all 0.3s ease-out; }
.reward-pop-leave-active { transition: all 0.5s ease-in; }
.reward-pop-enter-from { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
.reward-pop-leave-to { opacity: 0; transform: translate(-50%, -40%) scale(1.05); }
</style>
