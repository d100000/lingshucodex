<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { itemApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'
import Logo from '../components/Logo.vue'
import BackButton from '../components/BackButton.vue'
import SectBackground from '../components/SectBackground.vue'
import ItemIcon from '../components/ItemIcon.vue'

const router = useRouter()
const msg = useMessage()
const game = useGameStore()
const items = ref([])
const filter = ref('all')
const search = ref('')

const RARITY_COLOR = {
  1: '#B0B0B0', 2: '#2EBB6B', 3: '#4A90E2',
  4: '#8B5CF6', 5: '#F59E0B', 6: '#EF4444',
}
const TYPE_NAMES = {
  material: '材料', consumable: '丹药',
  equipment: '法宝', skill_book: '心法', treasure: '灵宝',
}

// ★ 把后端原始字段名翻成中文,展示更友好
const STAT_LABELS = {
  atk: '攻击', def: '防御', def_: '防御',
  hp: '生命', max_hp: '生命上限',
  qi: '灵气', max_qi: '灵气上限', qi_max: '灵气上限',
  spd: '速度',
  crit_rate: '暴击率', crit_dmg: '暴击伤害', evasion: '闪避',
  hp_percent: '生命恢复', breakthrough_bonus: '突破成功率',
  unlock_card: '解锁招式',
  atk_per_round: '每回合攻击递增', atk_speed: '攻速',
  clone_enemy: '克隆敌人', enemy_evasion: '敌人闪避',
  inspect: '识破之能', counter_heal: '反击回血',
  cross_sect_cards: '跨派招式槽', qi_regen: '灵气回复',
}
// 这些字段值是 0~1 的小数,需要 *100 显示成百分比
const PCT_DECIMAL = new Set([
  'crit_rate','crit_dmg','evasion','breakthrough_bonus',
  'atk_per_round','atk_speed','enemy_evasion','counter_heal','qi_regen',
])
// 这些字段值是整数百分比(如 hp_percent: 30 = 30%)
const PCT_INT = new Set(['hp_percent'])
// 这些字段是计数 / 槽位类
const COUNT_FIELDS = new Set(['clone_enemy','inspect','cross_sect_cards'])

function formatStat(key, v) {
  const label = STAT_LABELS[key] || key
  if (typeof v === 'string') return `${label}:${v}`
  if (PCT_DECIMAL.has(key)) {
    const sign = v >= 0 ? '+' : ''
    return `${label} ${sign}${Math.round(v * 100)}%`
  }
  if (PCT_INT.has(key)) {
    const sign = v >= 0 ? '+' : ''
    return `${label} ${sign}${v}%`
  }
  if (COUNT_FIELDS.has(key)) return `${label} ×${v}`
  const sign = v >= 0 ? '+' : ''
  return `${label} ${sign}${v}`
}

const filtered = computed(() => {
  let list = items.value
  if (filter.value !== 'all') list = list.filter(i => i.type === filter.value)
  if (search.value.trim()) {
    const k = search.value.toLowerCase()
    list = list.filter(i =>
      i.name.toLowerCase().includes(k) ||
      i.description.toLowerCase().includes(k) ||
      i.lore.toLowerCase().includes(k)
    )
  }
  return list.sort((a, b) => b.rarity - a.rarity)
})

onMounted(async () => {
  try {
    const { data } = await itemApi.list()
    items.value = data
  } catch (e) { msg.error(e.message) }
})
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
      <h1>💊 修行物品全集</h1>
      <p>共 {{ items.length }} 种物品 · 包含丹药/法宝/心法/灵宝/材料</p>
    </header>

    <div class="control-bar">
      <input class="search" v-model="search" placeholder="搜索物品名/描述/故事..." />
      <div class="filter-bar">
        <button
          v-for="(name, key) in {all:'全部', material:'材料', consumable:'丹药', equipment:'法宝', skill_book:'心法', treasure:'灵宝'}"
          :key="key"
          :class="['filter-btn', { active: filter === key }]"
          @click="filter = key"
        >{{ name }}</button>
      </div>
    </div>

    <div class="grid">
      <div
        v-for="item in filtered"
        :key="item.id"
        class="item-card"
        :style="{ '--rcolor': RARITY_COLOR[item.rarity] }"
      >
        <div class="card-head">
          <ItemIcon class="card-icon" :item="item" :size="48" />
          <span class="rar" :style="{ background: RARITY_COLOR[item.rarity] + '22', color: RARITY_COLOR[item.rarity] }">
            {{ item.rarity_name }}
          </span>
        </div>
        <div class="card-name" :style="{ color: RARITY_COLOR[item.rarity] }">
          {{ item.name }}
        </div>
        <div class="type-bar">{{ TYPE_NAMES[item.type] }}</div>
        <p class="card-desc">{{ item.description }}</p>
        <p class="card-lore">「 {{ item.lore }} 」</p>
        <div v-if="item.use_effect" class="effect">
          <strong>使用效果:</strong>
          <span v-for="(v, k) in item.use_effect" :key="k" class="stat-chip">{{ formatStat(k, v) }}</span>
        </div>
        <div v-if="item.equip_stats" class="effect">
          <strong>装备属性:</strong>
          <span v-for="(v, k) in item.equip_stats" :key="k" class="stat-chip">{{ formatStat(k, v) }}</span>
        </div>
        <div class="value">价值 {{ item.value_qi }} 灵气</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 1200px; margin: 0 auto; padding: 20px 20px 60px; min-height: 100vh; }
.brand-bar { display: flex; justify-content: space-between; align-items: center; padding-bottom: 18px; border-bottom: 1px solid rgba(255,255,255,0.04); margin-bottom: 22px; }
.text-btn { background: none; border: 1px solid rgba(255,255,255,0.15); color: #aaa; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.text-btn:hover { color: #fff; border-color: #D4A24C; }
.header h1 { margin: 0; font-size: 24px; color: #D4A24C; letter-spacing: 4px; }
.header p { color: #888; font-size: 13px; margin: 6px 0 0; }

.control-bar { display: flex; gap: 12px; margin: 20px 0; align-items: center; flex-wrap: wrap; }
.search {
  flex: 1; min-width: 200px;
  background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1);
  color: #fff; padding: 10px 14px; border-radius: 6px; font-size: 13px; outline: none;
}
.search:focus { border-color: #D4A24C; }
.filter-bar { display: flex; gap: 6px; flex-wrap: wrap; }
.filter-btn {
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  color: #aaa; padding: 6px 12px; border-radius: 5px; cursor: pointer; font-size: 12px;
}
.filter-btn.active { background: rgba(212,162,76,0.1); border-color: #D4A24C; color: #D4A24C; }

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}
.item-card {
  background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
  border: 1px solid var(--rcolor, rgba(255,255,255,0.1));
  border-radius: 10px; padding: 16px;
}
.card-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.card-icon { flex-shrink: 0; }
.rar { padding: 2px 8px; border-radius: 3px; font-size: 11px; }
.card-name { font-size: 15px; font-weight: 500; letter-spacing: 1px; margin-bottom: 4px; }
.type-bar { font-size: 11px; color: #888; margin-bottom: 8px; }
.card-desc { color: #ccc; font-size: 12px; line-height: 1.6; margin: 0 0 6px; }
.card-lore { color: #888; font-size: 11px; font-style: italic; line-height: 1.6; margin: 0 0 8px; border-left: 2px solid rgba(255,255,255,0.08); padding-left: 8px; }
.effect { font-size: 11px; color: #7FC7E8; margin: 4px 0; display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
.effect strong { color: #FFE0A3; margin-right: 4px; flex-shrink: 0; }
.stat-chip {
  background: rgba(127,199,232,0.08);
  border: 1px solid rgba(127,199,232,0.18);
  padding: 1px 7px; border-radius: 10px;
  font-size: 11px; color: #7FC7E8;
  white-space: nowrap;
}
.value { font-size: 11px; color: #FFB454; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px; margin-top: 8px; }
</style>
