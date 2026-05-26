<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { journalApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'
import Logo from '../components/Logo.vue'
import BackButton from '../components/BackButton.vue'
import SectBackground from '../components/SectBackground.vue'

const router = useRouter()
const msg = useMessage()
const game = useGameStore()

const entries = ref([])
const loading = ref(true)
const hasMore = ref(true)
const offset = ref(0)
const LIMIT = 20

const EVENT_ICONS = {
  battle_victory: '⚔️',
  battle_defeat: '💀',
  battle_flee: '🏃',
  meditate: '🧘',
  fortune: '🍀',
  craft: '🔥',
  gift: '🎁',
  level_up: '⬆️',
  item_use: '💊',
  daily_claim: '📋',
  drop: '💎',
  default: '📝',
}

const EVENT_COLORS = {
  battle_victory: '#52B788',
  battle_defeat: '#FF6B6B',
  battle_flee: '#FFB454',
  meditate: '#7FC7E8',
  fortune: '#B59CFF',
  craft: '#D4A24C',
  gift: '#FF9B7A',
  level_up: '#FFE0A3',
  daily_claim: '#95D5B2',
  default: '#aaa',
}

onMounted(async () => {
  await loadMore()
})

async function loadMore() {
  loading.value = true
  try {
    const { data } = await journalApi.list(LIMIT, offset.value)
    const items = data.entries || []
    entries.value.push(...items)
    offset.value += items.length
    hasMore.value = items.length === LIMIT
  } catch (e) {
    msg.error(e.message)
  } finally {
    loading.value = false
  }
}

function getIcon(type) {
  return EVENT_ICONS[type] || EVENT_ICONS.default
}

function getColor(type) {
  return EVENT_COLORS[type] || EVENT_COLORS.default
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const diffMs = now - d
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH}小时前`
  const diffD = Math.floor(diffH / 24)
  if (diffD < 7) return `${diffD}天前`
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
</script>

<template>
  <div class="page">
    <SectBackground :sect-id="game.character?.sect || 'canglan'" overlay="normal" :opacity="0.4" />

    <!-- ★ fixed 模式 BackButton 强制显示在左上角(取消 inline,更显眼) -->
    <BackButton to="/home" label="回主城" />
    <div class="brand-bar">
      <Logo :size="32" :text-size="16" />
    </div>

    <header class="header">
      <h1>📜 修行录</h1>
      <p>记载修行路上的点滴际遇</p>
      <div class="header-meta" v-if="entries.length">
        共 {{ entries.length }} 条记录{{ hasMore ? '+' : '' }}
      </div>
    </header>

    <!-- 时间线 -->
    <div v-if="entries.length" class="timeline">
      <div
        v-for="(entry, i) in entries"
        :key="i"
        class="tl-item"
      >
        <div class="tl-line">
          <div class="tl-dot" :style="{ background: getColor(entry.event_type) }"></div>
          <div class="tl-connector" v-if="i < entries.length - 1"></div>
        </div>
        <div class="tl-content">
          <div class="tl-head">
            <span class="tl-icon">{{ getIcon(entry.event_type) }}</span>
            <span class="tl-title" :style="{ color: getColor(entry.event_type) }">
              {{ entry.title || entry.event_type }}
            </span>
            <span class="tl-time">{{ formatTime(entry.created_at) }}</span>
          </div>
          <div class="tl-body" v-if="entry.detail">
            {{ entry.detail }}
          </div>
          <div class="tl-tags" v-if="entry.tags?.length">
            <span v-for="tag in entry.tags" :key="tag" class="tl-tag">{{ tag }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 加载更多 -->
    <div v-if="hasMore && !loading" class="load-more">
      <button class="more-btn" @click="loadMore">翻阅更多...</button>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-hint">
      正在翻阅修行录...
    </div>

    <!-- 空状态 -->
    <div v-if="!loading && entries.length === 0" class="empty">
      <div class="empty-emoji">📜</div>
      <p>修行录空空如也</p>
      <p class="empty-hint">去战斗、打坐、炼丹,修行的点滴都会记录于此</p>
      <div class="empty-actions">
        <button class="back-btn primary" @click="router.push('/explore')">⚔️ 开始修行</button>
        <button class="back-btn ghost" @click="router.push('/home')">↩ 回主城</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 800px; margin: 0 auto;
  padding: 20px 20px 60px;
  min-height: 100vh;
}
.brand-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding-bottom: 18px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  margin-bottom: 22px;
}
.header { margin-bottom: 24px; }
.header h1 { margin: 0; font-size: 24px; color: #D4A24C; letter-spacing: 4px; }
.header p { color: #888; font-size: 13px; margin: 6px 0 0; }
.header-meta { font-size: 11px; color: #666; margin-top: 4px; }

/* 时间线 */
.timeline {
  display: flex; flex-direction: column;
}
.tl-item {
  display: flex; gap: 16px;
  min-height: 60px;
}
.tl-line {
  display: flex; flex-direction: column; align-items: center;
  width: 20px; flex-shrink: 0;
}
.tl-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 6px;
  box-shadow: 0 0 8px currentColor;
}
.tl-connector {
  width: 2px; flex: 1;
  background: rgba(255, 255, 255, 0.08);
  margin: 4px 0;
}

.tl-content {
  flex: 1;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  margin-bottom: 8px;
}
.tl-head {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 4px;
}
.tl-icon { font-size: 16px; }
.tl-title {
  font-size: 13px; font-weight: 500;
  letter-spacing: 1px;
}
.tl-time {
  margin-left: auto;
  font-size: 11px; color: #666;
  white-space: nowrap;
}
.tl-body {
  font-size: 12px; color: #aaa;
  line-height: 1.6;
  padding-left: 24px;
}
.tl-tags {
  display: flex; gap: 4px; flex-wrap: wrap;
  margin-top: 6px;
  padding-left: 24px;
}
.tl-tag {
  font-size: 10px; color: #888;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  padding: 1px 7px; border-radius: 3px;
}

/* 加载更多 */
.load-more { text-align: center; padding: 20px; }
.more-btn {
  background: rgba(212, 162, 76, 0.1);
  border: 1px solid rgba(212, 162, 76, 0.3);
  color: #D4A24C; padding: 8px 24px;
  border-radius: 6px; cursor: pointer;
  font-size: 13px; letter-spacing: 2px;
}
.more-btn:hover {
  background: rgba(212, 162, 76, 0.2);
}

.loading-hint {
  text-align: center; padding: 20px;
  color: #888; font-size: 13px;
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 空状态 */
.empty { text-align: center; padding: 80px 20px; }
.empty-emoji { font-size: 60px; opacity: 0.5; margin-bottom: 12px; }
.empty p { color: #888; font-size: 14px; margin: 4px 0; }
.empty-hint { font-size: 12px; color: #666; }
.empty-actions { display: flex; gap: 10px; justify-content: center; margin-top: 16px; flex-wrap: wrap; }
.back-btn {
  background: linear-gradient(135deg, #D4A24C, #B58A3E);
  border: none; color: #1a1a2e;
  padding: 10px 24px; border-radius: 6px;
  cursor: pointer; letter-spacing: 2px;
  font-family: 'STKaiti', serif;
}
.back-btn.ghost {
  background: transparent;
  color: #D4A24C;
  border: 1px solid rgba(212,162,76,0.5);
}
.back-btn.ghost:hover { background: rgba(212,162,76,0.12); }
</style>
