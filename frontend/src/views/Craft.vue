<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { recipeApi, inventoryApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'
import Logo from '../components/Logo.vue'
import BackButton from '../components/BackButton.vue'
import SectBackground from '../components/SectBackground.vue'
import ItemIcon from '../components/ItemIcon.vue'
import { itemName } from '../utils/items.js'

const router = useRouter()
const msg = useMessage()
const game = useGameStore()

const recipes = ref([])
const inventory = ref({})   // item_id → count
const crafting = ref(false)
const filter = ref('all')   // all / pill / weapon / material
const loading = ref(true)

const CATEGORY_NAMES = {
  pill: '丹药', weapon: '法宝', material: '材料升级', special: '特殊',
}
const CATEGORY_ICONS = {
  pill: '💊', weapon: '⚔️', material: '🔄', special: '✨',
}

const filtered = computed(() => {
  if (filter.value === 'all') return recipes.value
  return recipes.value.filter(r => r.category === filter.value)
})

const categoryCounts = computed(() => {
  const c = { all: recipes.value.length }
  for (const cat of ['pill', 'weapon', 'material', 'special']) {
    c[cat] = recipes.value.filter(r => r.category === cat).length
  }
  return c
})

onMounted(async () => {
  await loadData()
})

async function loadData() {
  loading.value = true
  try {
    const [recipeResp, invResp] = await Promise.all([
      recipeApi.list(),
      inventoryApi.list(),
    ])
    recipes.value = Array.isArray(recipeResp.data) ? recipeResp.data : (recipeResp.data?.recipes || [])
    // build inventory lookup
    const inv = {}
    for (const item of (invResp.data?.items || [])) {
      inv[item.id] = item.count
    }
    inventory.value = inv
  } catch (e) {
    msg.error(e.message)
  } finally {
    loading.value = false
  }
}

function canCraft(recipe) {
  for (const mat of recipe.materials) {
    if ((inventory.value[mat.item_id] || 0) < mat.count) return false
  }
  return true
}

function matStatus(mat) {
  const have = inventory.value[mat.item_id] || 0
  return { have, need: mat.count, enough: have >= mat.count }
}

async function doCraft(recipe) {
  if (crafting.value || !canCraft(recipe)) return
  crafting.value = true
  try {
    const resp = await recipeApi.craft(recipe.id)
    const result = resp.data || resp
    if (result.fatigue) {
      game.patchCharacter({ fatigue: result.fatigue.after, max_fatigue: result.fatigue.max })
    }
    msg.success(`合成成功!获得 ${result.recipe_name || '物品'} ×${result.result_count || 1}`)
    // reload inventory
    await loadData()
  } catch (e) {
    msg.error(e.message)
  } finally {
    crafting.value = false
  }
}
</script>

<template>
  <div class="page">
    <SectBackground :sect-id="game.character?.sect || 'canglan'" overlay="normal" :opacity="0.4" />

    <div class="brand-bar">
      <BackButton to="/home" label="回主城" inline />
      <Logo :size="32" :text-size="16" />
    </div>

    <header class="header">
      <h1>🔥 炼丹炼器</h1>
      <p>以材料炼制丹药、法宝,提升修行实力</p>
    </header>

    <!-- 筛选 -->
    <div class="filter-bar">
      <button
        v-for="(name, key) in { all: '全部', pill: '💊 丹药', weapon: '⚔️ 法宝', material: '🔄 材料' }"
        :key="key"
        :class="['filter-btn', { active: filter === key }]"
        @click="filter = key"
      >
        {{ name }}
        <span class="count">{{ categoryCounts[key] || 0 }}</span>
      </button>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="empty"><p>正在翻阅配方...</p></div>

    <!-- 配方列表 -->
    <div v-else-if="filtered.length" class="recipe-grid">
      <div
        v-for="recipe in filtered"
        :key="recipe.id"
        class="recipe-card"
        :class="{ craftable: canCraft(recipe), locked: recipe.unlock_level > (game.character?.level || 1) }"
      >
        <div class="rc-head">
          <span class="rc-icon">{{ CATEGORY_ICONS[recipe.category] || '🔮' }}</span>
          <div class="rc-title-area">
            <div class="rc-name">{{ recipe.name }}</div>
            <div class="rc-desc">{{ recipe.desc }}</div>
          </div>
          <span class="rc-cat" :class="recipe.category">{{ CATEGORY_NAMES[recipe.category] }}</span>
        </div>

        <!-- 所需材料 -->
        <div class="rc-materials">
          <div
            v-for="mat in recipe.materials"
            :key="mat.item_id"
            class="mat-chip"
            :class="{ enough: matStatus(mat).enough }"
          >
            <ItemIcon
              class="mc-icon"
              :icon-url="mat.item_icon_url"
              :emoji="mat.item_icon"
              :name="mat.item_name || itemName(mat.item_id)"
              :size="24"
            />
            <span class="mc-name">{{ mat.item_name || itemName(mat.item_id) }}</span>
            <span class="mc-count" :class="{ short: !matStatus(mat).enough }">
              {{ matStatus(mat).have }}/{{ mat.count }}
            </span>
          </div>
        </div>

        <!-- 产出 -->
        <div class="rc-result" :class="`rarity-${recipe.result_rarity || 1}`">
          <span class="rr-arrow">→</span>
          <ItemIcon
            v-if="recipe.result_icon || recipe.result_icon_url"
            class="rr-icon"
            :icon-url="recipe.result_icon_url"
            :emoji="recipe.result_icon"
            :name="recipe.result_name"
            :size="28"
          />
          <span class="rr-name">{{ recipe.result_name || itemName(recipe.result_id) }}</span>
          <span class="rr-count" v-if="recipe.result_count > 1">×{{ recipe.result_count }}</span>
        </div>

        <!-- 操作 -->
        <div class="rc-footer">
          <span class="rc-level" v-if="recipe.unlock_level > 1">
            需 Lv.{{ recipe.unlock_level }}
          </span>
          <button
            class="craft-btn"
            :class="{ ready: canCraft(recipe) }"
            :disabled="!canCraft(recipe) || crafting || recipe.unlock_level > (game.character?.level || 1)"
            @click="doCraft(recipe)"
          >
            {{ recipe.unlock_level > (game.character?.level || 1) ? '🔒 未解锁' : (canCraft(recipe) ? '🔥 合成' : '材料不足') }}
          </button>
        </div>
      </div>
    </div>

    <div v-else class="empty">
      <div class="empty-emoji">🔥</div>
      <p>暂无配方</p>
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
.header { margin-bottom: 20px; }
.header h1 { margin: 0; font-size: 24px; color: #D4A24C; letter-spacing: 4px; }
.header p { color: #888; font-size: 13px; margin: 6px 0 0; }

/* 筛选 */
.filter-bar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; }
.filter-btn {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  color: #aaa; padding: 7px 16px;
  border-radius: 6px; cursor: pointer; font-size: 13px;
  display: flex; gap: 6px; align-items: center;
}
.filter-btn:hover { color: #fff; border-color: #D4A24C; }
.filter-btn.active {
  background: rgba(212,162,76,0.1);
  border-color: #D4A24C; color: #D4A24C;
}
.count {
  background: rgba(0,0,0,0.3); border-radius: 10px;
  padding: 0 7px; font-size: 11px;
}

/* 配方网格 */
.recipe-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
}
.recipe-card {
  background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.2s;
}
.recipe-card.craftable {
  border-color: rgba(82, 183, 136, 0.35);
  background: linear-gradient(180deg, rgba(82,183,136,0.06), rgba(255,255,255,0.01));
}
.recipe-card.locked { opacity: 0.55; }
.recipe-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.3);
}

.rc-head {
  display: flex; align-items: flex-start; gap: 10px;
  margin-bottom: 12px;
}
.rc-icon { font-size: 28px; flex-shrink: 0; }
.rc-title-area { flex: 1; }
.rc-name { font-size: 15px; color: #FFE0A3; letter-spacing: 1px; font-weight: 500; }
.rc-desc { font-size: 11px; color: #888; margin-top: 3px; }
.rc-cat {
  font-size: 10px; color: #aaa;
  padding: 2px 8px; border-radius: 3px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  white-space: nowrap;
}
.rc-cat.pill { color: #95D5B2; border-color: rgba(82,183,136,0.3); }
.rc-cat.weapon { color: #7FC7E8; border-color: rgba(127,199,232,0.3); }
.rc-cat.material { color: #B59CFF; border-color: rgba(181,156,255,0.3); }

/* 材料 */
.rc-materials {
  display: flex; flex-wrap: wrap; gap: 6px;
  margin-bottom: 10px;
}
.mat-chip {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 10px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 5px;
  font-size: 11px;
}
.mat-chip.enough { border-color: rgba(82, 183, 136, 0.3); }
.mc-icon { flex-shrink: 0; }
.mc-name { color: #ccc; }
.mc-count { color: #52B788; font-family: 'SF Mono', monospace; font-weight: 600; }
.mc-count.short { color: #FF6B6B; }

/* 产出 */
.rc-result {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px;
  background: rgba(212, 162, 76, 0.06);
  border: 1px dashed rgba(212, 162, 76, 0.2);
  border-radius: 6px;
  margin-bottom: 12px;
}
.rr-arrow { color: #D4A24C; font-size: 16px; }
.rr-icon { flex-shrink: 0; }
.rr-name { color: #FFE0A3; font-size: 13px; letter-spacing: 1px; font-weight: 500; }
.rr-count { color: #D4A24C; font-size: 12px; font-weight: 600; margin-left: auto; }

/* ★ 产出物按稀有度上色(R1 凡-R6 神) */
.rc-result.rarity-1 .rr-name { color: #C9C9C9; }
.rc-result.rarity-2 .rr-name { color: #95D5B2; }
.rc-result.rarity-3 .rr-name { color: #7FC7E8; }
.rc-result.rarity-4 .rr-name { color: #B59CFF; }
.rc-result.rarity-5 .rr-name { color: #FFB454; }
.rc-result.rarity-6 .rr-name { color: #FF6B6B; text-shadow: 0 0 6px rgba(255,107,107,0.4); }
.rc-result.rarity-4 { border-color: rgba(181, 156, 255, 0.35); background: rgba(181, 156, 255, 0.06); }
.rc-result.rarity-5 { border-color: rgba(255, 180, 84, 0.4); background: rgba(255, 180, 84, 0.08); }
.rc-result.rarity-6 {
  border-color: rgba(255, 107, 107, 0.5);
  background: rgba(255, 107, 107, 0.1);
  box-shadow: 0 0 12px rgba(255, 107, 107, 0.2);
}

/* 底部 */
.rc-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding-top: 10px;
  border-top: 1px solid rgba(255,255,255,0.05);
}
.rc-level { font-size: 11px; color: #888; }
.craft-btn {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.12);
  color: #888; padding: 6px 16px;
  border-radius: 6px; font-size: 12px;
  cursor: not-allowed; letter-spacing: 1px;
}
.craft-btn.ready {
  background: linear-gradient(135deg, rgba(212,162,76,0.2), rgba(212,162,76,0.08));
  border-color: #D4A24C;
  color: #FFE0A3;
  cursor: pointer;
}
.craft-btn.ready:hover {
  background: linear-gradient(135deg, rgba(212,162,76,0.35), rgba(212,162,76,0.15));
  box-shadow: 0 0 12px rgba(212,162,76,0.25);
}
.craft-btn:disabled { opacity: 0.5; }

/* 空状态 */
.empty { text-align: center; padding: 60px 20px; color: #888; }
.empty-emoji { font-size: 60px; opacity: 0.5; margin-bottom: 12px; }
</style>
