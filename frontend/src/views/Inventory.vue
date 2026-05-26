<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { inventoryApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'
import Logo from '../components/Logo.vue'
import BackButton from '../components/BackButton.vue'
import SectBackground from '../components/SectBackground.vue'
import ItemIcon from '../components/ItemIcon.vue'

const router = useRouter()
const msg = useMessage()
const game = useGameStore()
const inv = ref(null)
const filter = ref('all')   // all / material / consumable / equipment / skill_book / treasure
const using = ref(false)

const RARITY_COLOR = {
  1: '#B0B0B0', 2: '#2EBB6B', 3: '#4A90E2',
  4: '#8B5CF6', 5: '#F59E0B', 6: '#EF4444',
}

const TYPE_NAMES = {
  material: '材料', consumable: '丹药',
  equipment: '法宝', skill_book: '心法', treasure: '灵宝',
}

const filtered = computed(() => {
  if (!inv.value) return []
  if (filter.value === 'all') return inv.value.items
  return inv.value.items.filter(i => i.type === filter.value)
})

onMounted(async () => {
  await load()
})

async function load() {
  try {
    const { data } = await inventoryApi.list()
    inv.value = data
  } catch (e) {
    msg.error(e.message)
    if (e.code === 'NOT_FOUND') router.replace('/onboarding')
  }
}

async function useItem(item) {
  if (using.value) return
  using.value = true
  try {
    const { data } = await inventoryApi.use(item.id)
    if (data.fatigue) {
      game.patchCharacter({ fatigue: data.fatigue.after, max_fatigue: data.fatigue.max })
    }
    msg.success(`已使用 ${item.name} — ${data.effect_summary}`)
    await load()
  } catch (e) {
    msg.error(e.message)
  } finally {
    using.value = false
  }
}

function counts() {
  if (!inv.value) return {}
  const c = { all: inv.value.total_kinds }
  for (const t of ['material', 'consumable', 'equipment', 'skill_book', 'treasure']) {
    c[t] = inv.value.items.filter(i => i.type === t).length
  }
  return c
}
</script>

<template>
  <div class="page">
    <!-- ★ 门派背景图 -->
    <SectBackground :sect-id="game.character?.sect || 'canglan'" overlay="normal" :opacity="0.45" />

    <div class="brand-bar">
      <BackButton to="/home" label="回主城" inline />
      <Logo :size="32" :text-size="16" />
    </div>

    <header class="header">
      <h1>🎒 我的背包</h1>
      <p v-if="inv">共 {{ inv.total_kinds }} 种物品 / {{ inv.total_count }} 件</p>
    </header>

    <div v-if="inv" class="filter-bar">
      <button
        v-for="(name, key) in {all:'全部', material:'材料', consumable:'丹药', equipment:'法宝', skill_book:'心法', treasure:'灵宝'}"
        :key="key"
        :class="['filter-btn', { active: filter === key }]"
        @click="filter = key"
      >
        {{ name }} <span class="count">{{ counts()[key] || 0 }}</span>
      </button>
    </div>

    <div v-if="filtered.length === 0" class="empty">
      <div class="empty-emoji">📭</div>
      <p>这里空空如也</p>
      <p class="empty-hint">去 修行 击败怪物获取战利品</p>
      <button class="back-btn" @click="router.push('/explore')">⚔️ 立即修行</button>
    </div>

    <div v-else class="grid">
      <div
        v-for="item in filtered"
        :key="item.id"
        class="item-card"
        :style="{ '--rcolor': RARITY_COLOR[item.rarity] }"
      >
        <div class="card-head">
          <ItemIcon class="card-icon" :item="item" :size="52" />
          <div class="card-count" v-if="item.count > 1">×{{ item.count }}</div>
        </div>
        <div class="card-body">
          <div class="card-name" :style="{ color: RARITY_COLOR[item.rarity] }">
            {{ item.name }}
          </div>
          <div class="card-meta">
            <span class="rar" :style="{ background: RARITY_COLOR[item.rarity] + '22', color: RARITY_COLOR[item.rarity] }">
              {{ item.rarity_name }}
            </span>
            <span class="type">{{ TYPE_NAMES[item.type] || item.type }}</span>
          </div>
          <p class="card-desc">{{ item.description }}</p>
          <p class="card-lore">「 {{ item.lore }} 」</p>

          <div v-if="item.type === 'consumable'" class="card-actions">
            <button class="use-btn" :disabled="using" @click="useItem(item)">使用</button>
            <span class="value">价值 {{ item.value_qi }} 灵气</span>
          </div>
          <div v-else class="card-meta-bar">
            <span class="value">价值 {{ item.value_qi }} 灵气</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 1100px; margin: 0 auto;
  padding: 20px 20px 60px;
  min-height: 100vh;
}
.brand-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding-bottom: 18px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  margin-bottom: 22px;
}
.text-btn {
  background: none; border: 1px solid rgba(255,255,255,0.15);
  color: #aaa; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px;
}
.text-btn:hover { color: #fff; border-color: #D4A24C; }

.header { margin-bottom: 24px; }
.header h1 { margin: 0; font-size: 24px; color: #D4A24C; letter-spacing: 4px; }
.header p { color: #888; font-size: 13px; margin: 6px 0 0; }

.filter-bar {
  display: flex; gap: 8px; flex-wrap: wrap;
  margin-bottom: 20px;
}
.filter-btn {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  color: #aaa; padding: 8px 16px;
  border-radius: 6px; cursor: pointer;
  font-size: 13px;
  display: flex; gap: 8px; align-items: center;
}
.filter-btn:hover { color: #fff; border-color: #D4A24C; }
.filter-btn.active {
  background: rgba(212,162,76,0.1);
  border-color: #D4A24C; color: #D4A24C;
}
.count {
  background: rgba(0,0,0,0.3); border-radius: 10px;
  padding: 0 8px; font-size: 11px;
}

.empty {
  text-align: center; padding: 80px 20px;
}
.empty-emoji { font-size: 80px; opacity: 0.5; margin-bottom: 16px; }
.empty p { color: #888; font-size: 14px; margin: 4px 0; }
.empty-hint { font-size: 12px; }
.back-btn {
  margin-top: 16px;
  background: linear-gradient(135deg, #D4A24C, #B58A3E);
  border: none; color: #1a1a2e;
  padding: 10px 24px; border-radius: 6px;
  cursor: pointer; letter-spacing: 2px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
}
.item-card {
  background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
  border: 1px solid var(--rcolor, rgba(255,255,255,0.1));
  border-radius: 10px;
  padding: 16px;
  position: relative;
  transition: all 0.2s;
}
.item-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.4);
}
.card-head {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 8px;
}
.card-icon { flex-shrink: 0; }
.card-count {
  background: rgba(0,0,0,0.5); color: #FFE0A3;
  padding: 2px 8px; border-radius: 3px;
  font-size: 13px; font-weight: 600;
}
.card-name { font-size: 16px; font-weight: 500; letter-spacing: 1px; }
.card-meta {
  display: flex; gap: 6px;
  margin: 6px 0 8px;
  font-size: 11px;
}
.rar { padding: 1px 8px; border-radius: 3px; }
.type {
  background: rgba(255,255,255,0.05);
  color: #aaa; padding: 1px 8px; border-radius: 3px;
}
.card-desc {
  color: #ccc; font-size: 12px; line-height: 1.6;
  margin: 0 0 6px;
}
.card-lore {
  color: #888; font-size: 11px; font-style: italic;
  line-height: 1.6; margin: 0 0 8px;
  border-left: 2px solid rgba(255,255,255,0.08);
  padding-left: 8px;
}
.card-actions {
  display: flex; justify-content: space-between; align-items: center;
  border-top: 1px solid rgba(255,255,255,0.05);
  padding-top: 8px;
}
.use-btn {
  background: linear-gradient(135deg, #D4A24C, #B58A3E);
  border: none; color: #1a1a2e;
  padding: 5px 14px; border-radius: 4px;
  cursor: pointer; font-size: 12px;
  letter-spacing: 1px;
}
.use-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.value, .card-meta-bar {
  font-size: 11px; color: #7FC7E8;
  border-top: 1px solid rgba(255,255,255,0.05);
  padding-top: 8px;
}
.card-meta-bar { text-align: right; }
</style>
