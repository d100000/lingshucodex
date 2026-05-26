<!--
  Skills.vue — 技能树
  按境界分组,显示 56 招(本派 + 通用 + 已学跨派),可查看 / 升级 / 装备
-->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, useDialog } from 'naive-ui'
import { skillApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'
import Logo from '../components/Logo.vue'
import BackButton from '../components/BackButton.vue'
import SectBackground from '../components/SectBackground.vue'
import ItemIcon from '../components/ItemIcon.vue'

const router = useRouter()
const msg = useMessage()
const dialog = useDialog()
const game = useGameStore()

const skills = ref([])
const dropOverview = ref([])
const sect = ref('canglan')
const equippedCount = ref(0)
const loading = ref(true)
const selected = ref(null)  // 选中查看详情的招式

const REALM_ORDER = ['qi','foundation','golden','yuanying','huashen','hetishi','dacheng','dujie','feisheng']
const REALM_NAMES = {qi:'炼气',foundation:'筑基',golden:'金丹',yuanying:'元婴',huashen:'化神',
                     hetishi:'合体',dacheng:'大乘',dujie:'渡劫',feisheng:'飞升'}
const TYPE_TAG = {attack:'攻',heal:'治',buff:'增益',ult:'必杀',debuff:'削'}
const TYPE_COLOR = {attack:'#FF8888',heal:'#52B788',buff:'#7FC7E8',ult:'#FFD700',debuff:'#B59CFF'}
const TIER_NAME = {basic:'基础',normal:'中阶',special:'高阶',ult:'必杀'}

const filter = ref('all') // all / learned / unlearned / equipped

const filtered = computed(() => {
  let arr = skills.value
  if (filter.value === 'learned')   arr = arr.filter(s => s.learned)
  if (filter.value === 'unlearned') arr = arr.filter(s => !s.learned && s.unlocked)
  if (filter.value === 'equipped')  arr = arr.filter(s => s.equipped)
  return arr
})

// 按境界分组
const byRealm = computed(() => {
  const m = {}
  for (const s of filtered.value) {
    if (!m[s.realm_unlock]) m[s.realm_unlock] = []
    m[s.realm_unlock].push(s)
  }
  return REALM_ORDER.map(r => ({ key: r, name: REALM_NAMES[r], items: m[r] || [] })).filter(x => x.items.length)
})

const counts = computed(() => {
  const a = skills.value
  return {
    all: a.length,
    learned: a.filter(s => s.learned).length,
    unlearned: a.filter(s => !s.learned && s.unlocked).length,
    equipped: a.filter(s => s.equipped).length,
  }
})

const dropGuideItems = computed(() => {
  if (dropOverview.value.length) return dropOverview.value
  const map = new Map()
  for (const s of skills.value) {
    const hint = s.drop_hint
    if (!hint?.sources?.length || map.has(hint.item_id)) continue
    map.set(hint.item_id, hint)
  }
  return Array.from(map.values()).sort((a, b) => (a.item_rarity || 0) - (b.item_rarity || 0))
})

function guideSourceLine(hint, limit = 4) {
  const names = (hint.sources || [])
    .slice(0, limit)
    .map(x => `${x.enemy_name} ${x.rate_label}`)
  const more = hint.more_count ? ` 等 ${hint.more_count + (hint.sources?.length || 0)} 种` : ''
  return `${names.join(' / ')}${more}`
}

async function load() {
  loading.value = true
  try {
    const { data } = await skillApi.listAll()
    skills.value = data.skills
    dropOverview.value = data.drop_overview || []
    sect.value = data.sect
    equippedCount.value = data.equipped_slots_used
  } catch (e) {
    msg.error(e.message)
  } finally {
    loading.value = false
  }
}

async function toggleEquip(s) {
  // 计算当前装备 list
  const cur = skills.value.filter(x => x.equipped).map(x => x.id)
  let next
  if (s.equipped) {
    next = cur.filter(x => x !== s.id)
  } else {
    if (cur.length >= 6) { msg.warning('装备槽已满(最多 6 个)'); return }
    next = [...cur, s.id]
  }
  try {
    const { data } = await skillApi.equip(next)
    if (data.fatigue) {
      game.patchCharacter({ fatigue: data.fatigue.after, max_fatigue: data.fatigue.max })
    }
    await load()
    msg.success(s.equipped ? `已卸下 ${s.name}` : `已装备 ${s.name}`)
  } catch (e) {
    msg.error(e.message)
  }
}

async function upgrade(s) {
  if (!s.next_upgrade) { msg.info('已满级'); return }
  const u = s.next_upgrade
  dialog.warning({
    title: `精进 ${s.name}`,
    content: `Lv ${s.level} → Lv ${u.to_level}, 消耗 ${u.material_count}× 心得`,
    positiveText: '确定精进',
    negativeText: '再想想',
    onPositiveClick: async () => {
      try {
        const { data } = await skillApi.upgrade(s.id)
        if (data.fatigue) {
          game.patchCharacter({ fatigue: data.fatigue.after, max_fatigue: data.fatigue.max })
        }
        await load()
        msg.success(`${s.name} 已晋升至 Lv ${u.to_level}!`)
      } catch (e) {
        msg.error(e.message)
      }
    },
  })
}

onMounted(load)
</script>

<template>
  <div class="page">
    <SectBackground :sect-id="game.character?.sect || 'canglan'" overlay="normal" :opacity="0.4" />
    <BackButton to="/home" label="回主城" />

    <div class="brand-bar">
      <Logo :size="32" :text-size="16" />
    </div>

    <header class="header">
      <h1>📜 修行心法</h1>
      <p>修炼招式、突破境界,精进每一式</p>
      <div class="meta">装备槽 <strong>{{ equippedCount }}</strong>/6</div>
    </header>

    <!-- Filter -->
    <div class="filter-bar">
      <button :class="['fbtn',{active:filter==='all'}]" @click="filter='all'">全部 {{ counts.all }}</button>
      <button :class="['fbtn',{active:filter==='learned'}]" @click="filter='learned'">已学 {{ counts.learned }}</button>
      <button :class="['fbtn',{active:filter==='unlearned'}]" @click="filter='unlearned'">未学 {{ counts.unlearned }}</button>
      <button :class="['fbtn',{active:filter==='equipped'}]" @click="filter='equipped'">已装备 {{ counts.equipped }}</button>
    </div>

    <section class="drop-guide">
      <div>
        <strong>心法掉落提示</strong>
        <span>击败地图妖兽会统一掉落招式心得。怪物等级越高,心得掉率越高;神话妖兽必掉高阶心得。</span>
      </div>
      <button @click="router.push('/explore')">去地图寻怪</button>
      <div v-if="dropGuideItems.length" class="drop-guide-list">
        <div v-for="hint in dropGuideItems" :key="hint.item_id" class="drop-guide-item">
          <strong>
            <ItemIcon
              :icon-url="hint.item_icon_url"
              :emoji="hint.item_icon"
              :name="hint.item_name"
              :size="28"
            />
            {{ hint.item_name }}
          </strong>
          <span>{{ guideSourceLine(hint) }}</span>
        </div>
      </div>
    </section>

    <div v-if="loading" class="empty">⌛ 翻阅心法...</div>

    <!-- 按境界分组列表 -->
    <div v-else v-for="group in byRealm" :key="group.key" class="realm-group">
      <div class="realm-title">
        <span class="rt-name">{{ group.name }}期</span>
        <span class="rt-count">· {{ group.items.length }} 招</span>
      </div>
      <div class="skill-grid">
        <div v-for="s in group.items" :key="s.id"
             class="skill-card"
             :class="{ learned: s.learned, equipped: s.equipped, locked: !s.unlocked && !s.learned }"
             @click="selected = s">
          <div class="sc-head">
            <span class="sc-icon">{{ s.icon }}</span>
            <span class="sc-name">{{ s.name }}</span>
            <span class="sc-lv" v-if="s.learned">Lv {{ s.level }}</span>
          </div>
          <div class="sc-meta">
            <span class="sc-type" :style="{color: TYPE_COLOR[s.type]}">{{ TYPE_TAG[s.type] || s.type }}</span>
            <span class="sc-cost">💧 {{ s.qi_cost }}</span>
            <span class="sc-power" v-if="s.type==='attack' || s.type==='ult'">⚔ {{ s.power.toFixed(1) }}x</span>
          </div>
          <div class="sc-status">
            <span v-if="!s.unlocked && !s.learned" class="locked-tag">🔒 {{ s.realm_unlock_name }}解锁</span>
            <span v-else-if="s.equipped" class="eq-tag">✦ 已装备</span>
            <span v-else-if="s.learned" class="lv-tag">已学</span>
            <span v-else class="ready-tag">可学</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 详情 Modal -->
    <div v-if="selected" class="modal-overlay" @click.self="selected=null">
      <div class="modal-card">
        <button class="close" @click="selected=null">✕</button>
        <div class="m-head">
          <span class="m-icon">{{ selected.icon }}</span>
          <div>
            <div class="m-name">{{ selected.name }}</div>
            <div class="m-tier">{{ TIER_NAME[selected.tier] }} · {{ TYPE_TAG[selected.type] }}招</div>
          </div>
          <div class="m-lv" v-if="selected.learned">Lv {{ selected.level }}/{{ selected.max_level }}</div>
        </div>
        <p class="m-desc">{{ selected.description }}</p>
        <div class="m-stats">
          <div class="stat-row"><span>灵气消耗</span><strong>{{ selected.qi_cost }}</strong></div>
          <div class="stat-row" v-if="selected.power"><span>威力倍率</span><strong>{{ selected.power.toFixed(2) }}x</strong></div>
          <div class="stat-row"><span>命中</span><strong>{{ (selected.hit_rate * 100).toFixed(0) }}%</strong></div>
          <div class="stat-row" v-if="selected.crit_bonus"><span>暴击加成</span><strong>+{{ (selected.crit_bonus * 100).toFixed(0) }}%</strong></div>
        </div>
        <div class="m-actions" v-if="selected.learned">
          <button class="btn" :class="{ active: selected.equipped }" @click="toggleEquip(selected)">
            {{ selected.equipped ? '⊘ 卸下' : '⇲ 装备' }}
          </button>
          <button class="btn primary" v-if="selected.next_upgrade" @click="upgrade(selected)">
            ↑ 精进至 Lv {{ selected.next_upgrade.to_level }}
            <span class="cost-hint">(需 {{ selected.next_upgrade.material_count }} 心得)</span>
          </button>
          <span class="max-hint" v-else>✦ 已达圆满</span>
        </div>
        <div class="m-actions" v-else>
          <span class="locked-modal" v-if="!selected.unlocked">
            🔒 需达到 {{ selected.realm_unlock_name }}期方可习得
          </span>
          <span class="ready-modal" v-else>突破至 {{ selected.realm_unlock_name }}时自动习得</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 1100px; margin: 0 auto; padding: 20px 20px 60px; min-height: 100vh; position: relative; }
.brand-bar { display: flex; justify-content: flex-end; padding-bottom: 18px;
             border-bottom: 1px solid rgba(255,255,255,0.04); margin-bottom: 22px; }
.header { margin-bottom: 18px; }
.header h1 { margin: 0; font-size: 24px; color: #D4A24C; letter-spacing: 4px; }
.header p  { color: #888; font-size: 13px; margin: 6px 0 0; }
.header .meta { color: #FFE0A3; font-size: 11px; margin-top: 4px; }

.filter-bar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; }
.fbtn {
  background: rgba(255,255,255,0.04); color: #999;
  border: 1px solid rgba(212,162,76,0.18); padding: 6px 14px;
  border-radius: 4px; cursor: pointer; font-size: 12px; letter-spacing: 2px;
  font-family: 'STKaiti', serif;
}
.fbtn:hover { border-color: #D4A24C; color: #fff; }
.fbtn.active { background: rgba(212,162,76,0.2); color: #FFE0A3; border-color: #D4A24C; }

.drop-guide {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px;
  margin: 0 0 18px;
  padding: 12px 14px;
  border: 1px solid rgba(127,199,232,0.26);
  border-left: 3px solid #7FC7E8;
  border-radius: 8px;
  background: rgba(127,199,232,0.08);
}
.drop-guide strong {
  display: block;
  color: #B8E4FF;
  margin-bottom: 4px;
  letter-spacing: 2px;
}
.drop-guide span {
  color: #9CA8BB;
  font-size: 12px;
  line-height: 1.6;
}
.drop-guide button {
  min-height: 34px;
  border: 1px solid rgba(127,199,232,0.4);
  background: rgba(127,199,232,0.1);
  color: #B8E4FF;
  border-radius: 6px;
  padding: 0 12px;
  cursor: pointer;
  white-space: nowrap;
}
.drop-guide-list {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 8px;
}
.drop-guide-item {
  padding: 9px 10px;
  border: 1px solid rgba(127,199,232,0.16);
  background: rgba(0,0,0,0.16);
  border-radius: 6px;
}
.drop-guide-item strong {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #FFE0A3;
  letter-spacing: 1px;
}
.drop-guide-item span {
  display: block;
}

.realm-group { margin-bottom: 24px; }
.realm-title { font-size: 14px; letter-spacing: 5px; color: #D4A24C;
               border-bottom: 1px dashed rgba(212,162,76,0.25);
               padding-bottom: 6px; margin-bottom: 10px; font-family: 'STKaiti', serif; }
.rt-count { font-size: 11px; color: #666; margin-left: 6px; letter-spacing: 1px; }

.skill-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px,1fr)); gap: 10px; }
.skill-card {
  padding: 12px; background: rgba(20,30,50,0.55);
  border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;
  cursor: pointer; transition: all 0.18s;
}
.skill-card:hover { border-color: rgba(212,162,76,0.45); transform: translateY(-2px); }
.skill-card.equipped { border-color: rgba(255,200,80,0.65); background: rgba(45,32,16,0.55); }
.skill-card.learned:not(.equipped) { border-color: rgba(127,199,232,0.35); }
.skill-card.locked { opacity: 0.4; cursor: not-allowed; }
.skill-card.locked:hover { transform: none; }

.sc-head { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.sc-icon { font-size: 18px; }
.sc-name { font-size: 14px; color: #FFE0A3; font-family: 'STKaiti', serif; letter-spacing: 1px; flex: 1; }
.sc-lv { font-size: 10px; color: #FFD700; font-family: 'SF Mono', monospace; }
.sc-meta { display: flex; gap: 8px; font-size: 11px; color: #888; margin-bottom: 4px; }
.sc-cost { color: #7FC7E8; }
.sc-power { color: #FF8888; }
.sc-status { font-size: 10px; letter-spacing: 1px; }
.locked-tag { color: #555; }
.eq-tag     { color: #FFD700; }
.lv-tag     { color: #7FC7E8; }
.ready-tag  { color: #95D5B2; }

/* modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.7);
  display: flex; align-items: center; justify-content: center;
  z-index: 200; padding: 20px;
}
.modal-card {
  position: relative;
  width: 100%; max-width: 420px;
  background: linear-gradient(180deg, rgba(15,27,46,0.96), rgba(8,12,24,0.98));
  border: 1px solid rgba(212,162,76,0.45); border-radius: 12px;
  padding: 22px;
}
.close { position: absolute; top: 8px; right: 12px; background: transparent;
         color: #888; border: none; font-size: 20px; cursor: pointer; }
.close:hover { color: #fff; }
.m-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.m-icon { font-size: 32px; }
.m-name { font-size: 20px; color: #FFE0A3; font-family: 'STKaiti', serif; letter-spacing: 2px; }
.m-tier { font-size: 11px; color: #888; letter-spacing: 2px; }
.m-lv   { margin-left: auto; color: #FFD700; font-family: 'SF Mono', monospace; }
.m-desc { color: #aaa; font-size: 13px; line-height: 1.7; font-family: 'STKaiti', serif;
          padding-bottom: 12px; border-bottom: 1px dashed rgba(212,162,76,0.25); }
.m-stats { display: flex; flex-direction: column; gap: 6px; padding: 12px 0; }
.stat-row { display: flex; justify-content: space-between; font-size: 13px; }
.stat-row span { color: #888; }
.stat-row strong { color: #FFE0A3; font-family: 'SF Mono', monospace; }
.m-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
.btn {
  flex: 1; min-width: 120px;
  background: rgba(255,255,255,0.04); color: #FFE0A3;
  border: 1px solid rgba(212,162,76,0.4);
  padding: 9px 12px; border-radius: 6px; cursor: pointer;
  font-family: 'STKaiti', serif; letter-spacing: 2px; font-size: 13px;
}
.btn:hover { background: rgba(212,162,76,0.15); }
.btn.active { background: rgba(255,200,80,0.2); border-color: #FFD700; }
.btn.primary { background: linear-gradient(135deg, #D4A24C, #B58A3E); color: #0F1B2E; border: none; }
.cost-hint { font-size: 10px; opacity: 0.7; margin-left: 4px; }
.max-hint  { color: #FFD700; font-size: 12px; letter-spacing: 2px; }
.locked-modal, .ready-modal { color: #888; font-size: 12px; }

.empty { text-align: center; padding: 60px; color: #888; }

@media (max-width: 560px) {
  .drop-guide {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
