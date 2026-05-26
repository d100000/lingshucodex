<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { bossApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'
import Logo from '../components/Logo.vue'
import BackButton from '../components/BackButton.vue'
import SectBackground from '../components/SectBackground.vue'
import RoundPortrait from '../components/RoundPortrait.vue'
import { bossPreview } from '../utils/characterPreview.js'

const router = useRouter()
const msg = useMessage()
const game = useGameStore()
const bosses = ref([])
const sects = ref([])
const stories = ref({})
const activeStory = ref('A')
const activeBoss = ref(null)

onMounted(async () => {
  try {
    const [b, s, l] = await Promise.all([
      bossApi.list(), bossApi.listSects(), bossApi.storylines(),
    ])
    bosses.value = b.data
    sects.value = s.data
    stories.value = l.data
  } catch (e) { msg.error(e.message) }
})

const sectMap = computed(() => {
  const m = {}; sects.value.forEach(s => m[s.id] = s); return m
})
const bossMap = computed(() => {
  const m = {}; bosses.value.forEach(b => m[b.id] = b); return m
})

const currentStory = computed(() => stories.value[activeStory.value])
const storyBosses = computed(() => {
  if (!currentStory.value) return []
  const ids = [...(currentStory.value.key_bosses || []), ...(currentStory.value.side_bosses || [])]
  return ids.map(id => bossMap.value[id]).filter(Boolean)
})

async function writeBossChapter() {
  if (!activeBoss.value) return
  try {
    const { data } = await bossApi.chapter(activeBoss.value.id)
    if (data.fatigue) {
      game.patchCharacter({ fatigue: data.fatigue.after, max_fatigue: data.fatigue.max })
    }
    msg.success('道君外传已入墨炉')
  } catch (e) {
    msg.error(e.message)
  }
}

// 故事线进度摘要(当前全部为 0,后续接入后端时替换)
const storylines = computed(() => {
  return Object.entries(stories.value).map(([key, s]) => {
    const total = (s.key_bosses?.length || 0) + (s.side_bosses?.length || 0)
    return { id: key, name: s.name, total, completed: 0 }
  })
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
      <h1>👑 修真名录 · 故事卷宗</h1>
      <p>共 {{ bosses.length }} 位 Boss · {{ sects.length }} 大宗派 · 4 条故事线交织</p>
    </header>

    <!-- 故事进度概览 -->
    <div v-if="storylines.length" class="progress-overview">
      <h3 class="po-title">📚 故事进度</h3>
      <div class="po-grid">
        <div v-for="sl in storylines" :key="sl.id" class="po-card">
          <div class="po-name">{{ sl.name }}</div>
          <div class="po-bar">
            <div class="po-fill" :style="{ width: sl.total ? (sl.completed / sl.total * 100) + '%' : '0%' }"></div>
          </div>
          <div class="po-label">🔒 尚未开启</div>
        </div>
      </div>
    </div>

    <!-- 故事线切换 -->
    <div class="story-tabs">
      <button
        v-for="(s, key) in stories"
        :key="key"
        :class="['tab', { active: activeStory === key }]"
        @click="activeStory = key; activeBoss = null"
      >
        <span class="tab-key">{{ key }}</span>
        {{ s.name }}
      </button>
    </div>

    <!-- 故事线详情 -->
    <div v-if="currentStory" class="story-card">
      <h2>{{ currentStory.name }}</h2>
      <p class="summary">{{ currentStory.summary }}</p>
      <div class="acts">
        <div class="act"><strong>第一幕</strong> {{ currentStory.act_1 }}</div>
        <div class="act"><strong>第二幕</strong> {{ currentStory.act_2 }}</div>
        <div class="act"><strong>第三幕</strong> {{ currentStory.act_3 }}</div>
      </div>
    </div>

    <!-- Boss 列表 -->
    <div class="boss-grid">
      <div
        v-for="b in storyBosses"
        :key="b.id"
        class="boss-card"
        :class="{ active: activeBoss?.id === b.id }"
        :style="{ '--accent': sectMap[b.sect_id]?.base_color || '#D4A24C' }"
        @click="activeBoss = b"
      >
        <div class="boss-head">
          <RoundPortrait
            kind="boss"
            :id="b.id"
            :size="68"
            shape="circle"
            frame="#FFD700"
            :name="b.name"
            :preview="bossPreview(b, { sect: sectMap[b.sect_id], bossMap })"
          />
          <div>
            <div class="boss-name">{{ b.name }}</div>
            <div class="boss-title">{{ b.title }} · Lv.{{ b.level }}</div>
          </div>
        </div>
        <div class="boss-sect">
          <strong>{{ b.sect_name || '散修' }}</strong>
          <span v-if="b.company" class="company">({{ b.company }})</span>
        </div>
      </div>
    </div>

    <!-- Boss 详情面板 -->
    <div v-if="activeBoss" class="boss-detail">
      <div class="detail-head">
        <RoundPortrait
          kind="boss"
          :id="activeBoss.id"
          :size="180"
          shape="card"
          frame="#FFD700"
          :name="activeBoss.name"
          :preview="bossPreview(activeBoss, { sect: sectMap[activeBoss.sect_id], bossMap })"
        />
        <div>
          <h2>{{ activeBoss.name }}</h2>
          <p class="title">{{ activeBoss.title }}</p>
          <p class="sect-line">
            所属:<strong>{{ activeBoss.sect_name || '散修(无门派)' }}</strong>
            <span v-if="activeBoss.company">({{ activeBoss.company }})</span>
          </p>
        </div>
      </div>

      <div class="lore-block">
        <h4>📖 Boss 故事</h4>
        <p>{{ activeBoss.lore }}</p>
      </div>

      <div v-if="sectMap[activeBoss.sect_id]" class="lore-block">
        <h4>🏯 宗派背景(对应 {{ sectMap[activeBoss.sect_id].company }})</h4>
        <p class="real-bg"><strong>真实背景:</strong> {{ sectMap[activeBoss.sect_id].real_background }}</p>
        <p class="sect-story"><strong>仙侠演绎:</strong> {{ sectMap[activeBoss.sect_id].sect_story }}</p>
        <p class="founded">📅 {{ sectMap[activeBoss.sect_id].founded }}</p>
      </div>

      <div v-if="activeBoss.bonds && activeBoss.bonds.length" class="lore-block">
        <h4>🔗 与其他 Boss 的羁绊</h4>
        <div class="bonds">
          <div v-for="bond in activeBoss.bonds" :key="bond.target_id" class="bond">
            <span class="bond-target" @click.stop="activeBoss = bossMap[bond.target_id]">
              → {{ bossMap[bond.target_id]?.name || bond.target_id }}
            </span>
            <p>{{ bond.desc }}</p>
          </div>
        </div>
      </div>

      <div class="lore-block">
        <h4>⚔️ 战斗信息</h4>
        <div class="stats">
          <span>HP <strong>{{ activeBoss.hp }}</strong></span>
          <span>ATK <strong>{{ activeBoss.atk }}</strong></span>
          <span>DEF <strong>{{ activeBoss.def_ }}</strong></span>
          <span>暴击 <strong>{{ Math.round(activeBoss.crit_rate * 100) }}%</strong></span>
        </div>
        <p class="skill">🗡️ 标志性招式:<strong>{{ activeBoss.signature_skill }}</strong></p>
        <button class="write-btn" @click="writeBossChapter">道君外传入墨炉</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 1100px; margin: 0 auto; padding: 20px 20px 60px; min-height: 100vh; }
.brand-bar { display: flex; justify-content: space-between; align-items: center; padding-bottom: 18px; border-bottom: 1px solid rgba(255,255,255,0.04); margin-bottom: 22px; }
.text-btn { background: none; border: 1px solid rgba(255,255,255,0.15); color: #aaa; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.text-btn:hover { color: #fff; border-color: #D4A24C; }
.header h1 { margin: 0; font-size: 24px; color: #D4A24C; letter-spacing: 4px; }
.header p { color: #888; font-size: 13px; margin: 6px 0 0; }
.write-btn { margin-top: 10px; border: 1px solid rgba(212,162,76,0.4); background: rgba(212,162,76,0.12); color: #F3E4C3; height: 34px; padding: 0 14px; cursor: pointer; }

.story-tabs { display: flex; gap: 8px; margin: 24px 0 16px; flex-wrap: wrap; }
.tab {
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  color: #aaa; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-size: 13px;
  display: flex; align-items: center; gap: 8px;
}
.tab:hover { color: #fff; border-color: #D4A24C; }
.tab.active { background: rgba(212,162,76,0.12); border-color: #D4A24C; color: #D4A24C; }
.tab-key {
  background: rgba(0,0,0,0.4); color: #FFE0A3;
  width: 22px; height: 22px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700;
}

.story-card {
  background: rgba(22,22,42,0.5);
  border: 1px solid rgba(212,162,76,0.2);
  border-radius: 12px; padding: 20px 24px; margin-bottom: 24px;
}
.story-card h2 { margin: 0 0 8px; color: #D4A24C; font-size: 20px; letter-spacing: 4px; }
.summary { color: #ccc; font-size: 14px; line-height: 1.8; margin: 0 0 14px; }
.acts { display: grid; gap: 8px; }
.act { background: rgba(0,0,0,0.25); border-left: 3px solid #D4A24C; padding: 8px 14px; font-size: 13px; color: #aaa; border-radius: 4px; }
.act strong { color: #D4A24C; margin-right: 8px; }

.boss-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 10px; margin-bottom: 24px;
}
.boss-card {
  background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px; padding: 12px 14px; cursor: pointer;
  transition: all 0.2s;
}
.boss-card:hover { transform: translateY(-2px); border-color: var(--accent); }
.boss-card.active { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent); }
.boss-head { display: flex; gap: 10px; align-items: center; margin-bottom: 6px; }
.boss-emoji { font-size: 26px; }
.boss-portrait { width: 36px; height: 36px; border-radius: 50%; object-fit: cover; border: 1px solid var(--accent); }
.boss-name { font-size: 14px; color: var(--accent); font-weight: 500; }
.boss-title { font-size: 11px; color: #888; margin-top: 2px; }
.boss-sect { font-size: 11px; color: #aaa; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 6px; }
.company { color: #7FC7E8; margin-left: 6px; font-size: 10px; }

.boss-detail {
  background: rgba(15,15,30,0.9); border: 1px solid rgba(212,162,76,0.25);
  border-radius: 14px; padding: 24px;
}
.detail-head { display: flex; gap: 18px; align-items: center; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 16px; }
.big-emoji { font-size: 60px; }
.big-portrait { width: 72px; height: 72px; border-radius: 50%; object-fit: cover; border: 2px solid #D4A24C; box-shadow: 0 0 12px rgba(212,162,76,0.3); }
.detail-head h2 { margin: 0; color: #D4A24C; font-size: 22px; letter-spacing: 2px; }
.title { margin: 4px 0 0; color: #aaa; font-size: 13px; }
.sect-line { margin: 6px 0 0; font-size: 13px; color: #ccc; }
.sect-line strong { color: #FFB454; }

.lore-block { margin: 18px 0; }
.lore-block h4 { color: #D4A24C; font-size: 13px; letter-spacing: 2px; margin: 0 0 8px; }
.lore-block p { color: #ccc; font-size: 13px; line-height: 1.8; margin: 0 0 8px; }
.real-bg { color: #aaa !important; font-style: normal; background: rgba(127,199,232,0.04); padding: 8px 12px; border-radius: 4px; }
.real-bg strong { color: #7FC7E8; }
.sect-story { background: rgba(212,162,76,0.04); padding: 8px 12px; border-radius: 4px; font-style: italic; }
.sect-story strong { color: #D4A24C; font-style: normal; }
.founded { color: #888 !important; font-size: 11px; }
.bonds { display: grid; gap: 8px; }
.bond { background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 6px; border-left: 2px solid #C03F3F; }
.bond-target { color: #FF8888; font-weight: 600; cursor: pointer; display: inline-block; margin-bottom: 4px; }
.bond-target:hover { text-decoration: underline; }
.bond p { color: #aaa; font-size: 12px; margin: 0; line-height: 1.7; }
.stats { display: flex; flex-wrap: wrap; gap: 14px; font-size: 12px; color: #888; margin-bottom: 8px; }
.stats strong { color: #fff; margin-left: 4px; }
.skill { color: #FFB454 !important; }
.skill strong { color: #FFE0A3; }

/* 故事进度概览 */
.progress-overview {
  background: rgba(22, 22, 42, 0.5);
  border: 1px solid rgba(212, 162, 76, 0.15);
  border-radius: 12px;
  padding: 18px 22px;
  margin-bottom: 24px;
}
.po-title {
  margin: 0 0 14px;
  font-size: 15px;
  color: #D4A24C;
  letter-spacing: 3px;
  font-weight: 600;
}
.po-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}
.po-card {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 12px 14px;
}
.po-name {
  font-size: 13px;
  color: #ccc;
  margin-bottom: 8px;
  letter-spacing: 1px;
}
.po-bar {
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;
}
.po-fill {
  height: 100%;
  background: linear-gradient(90deg, #D4A24C, #FFE0A3);
  border-radius: 3px;
  transition: width 0.4s ease;
}
.po-label {
  font-size: 11px;
  color: #888;
  letter-spacing: 1px;
}
</style>
