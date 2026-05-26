<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { bestiaryApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'
import { formatNum } from '../utils/format.js'
import Logo from '../components/Logo.vue'
import BackButton from '../components/BackButton.vue'
import SectBackground from '../components/SectBackground.vue'
import RoundPortrait from '../components/RoundPortrait.vue'
import ItemIcon from '../components/ItemIcon.vue'
import { enemyPreview } from '../utils/characterPreview.js'

const router = useRouter()
const msg = useMessage()
const game = useGameStore()

const clans = ref([])
const totalDiscovered = ref(0)
const totalEnemies = ref(0)
const progress = ref(0)
const loading = ref(true)

// 详情弹窗
const detailData = ref(null)
const detailLoading = ref(false)

const CLAN_COLORS = {
  '灵狐族': '#FF9B7A', '天禽族': '#7FC7E8', '蛇蜥族': '#95D5B2',
  '兽王族': '#FFB454', '虫蛊族': '#B59CFF', '魔煞族': '#FF6B6B',
  '仙灵族': '#D4A24C', '龙裔族': '#E84393', '幽冥族': '#9B59B6',
  '妖花族': '#52B788', '石魂族': '#aaa', '星兽族': '#7FC7E8',
}

function getClanColor(name) {
  return CLAN_COLORS[name] || '#aaa'
}

onMounted(async () => {
  try {
    const { data } = await bestiaryApi.list()
    clans.value = data.clans || []
    totalDiscovered.value = data.total_discovered || 0
    totalEnemies.value = data.total_enemies || 0
    progress.value = data.progress || 0
  } catch (e) {
    msg.error(e.message)
  } finally {
    loading.value = false
  }
})

async function showDetail(entry) {
  if (!entry.discovered) return
  detailLoading.value = true
  try {
    const { data } = await bestiaryApi.detail(entry.id)
    detailData.value = data
  } catch (e) {
    msg.error(e.message)
    detailData.value = null
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  detailData.value = null
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
      <h1>📖 山海经图鉴</h1>
      <p>记录你所遭遇的一切灵兽妖邪</p>
    </header>

    <!-- 总览统计 -->
    <div class="overview">
      <div class="ov-stat">
        <span class="ov-num">{{ totalDiscovered }}</span>
        <span class="ov-label">已发现</span>
      </div>
      <div class="ov-stat">
        <span class="ov-num">{{ totalEnemies }}</span>
        <span class="ov-label">全图鉴</span>
      </div>
      <div class="ov-stat accent">
        <span class="ov-num">{{ progress }}%</span>
        <span class="ov-label">完成度</span>
      </div>
      <div class="ov-progress-bar">
        <div class="ov-progress-fill" :style="{ width: progress + '%' }"></div>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="empty">
      <p>正在翻阅古卷...</p>
    </div>

    <!-- 按族展示 -->
    <div v-else class="clans-container">
      <div v-for="clan in clans" :key="clan.clan_name" class="clan-section">
        <div class="clan-header">
          <h3 class="clan-name" :style="{ color: getClanColor(clan.clan_name) }">
            {{ clan.clan_name }}
          </h3>
          <div class="clan-progress">
            <span class="cp-text">{{ clan.discovered }}/{{ clan.total }}</span>
            <div class="cp-bar">
              <div class="cp-fill" :style="{ width: clan.progress + '%', background: getClanColor(clan.clan_name) }"></div>
            </div>
          </div>
        </div>

        <div class="clan-grid">
          <div
            v-for="entry in clan.entries"
            :key="entry.id"
            class="b-card"
            :class="{ undiscovered: !entry.discovered }"
            @click="showDetail(entry)"
          >
            <RoundPortrait
              v-if="entry.discovered"
              kind="enemy"
              :id="entry.id"
              :size="56"
              shape="circle"
              :frame="getClanColor(clan.clan_name)"
              :name="entry.name"
            />
            <div v-else class="bc-locked">?</div>
            <div class="bc-info">
              <div class="bc-name" :style="{ color: entry.discovered ? getClanColor(clan.clan_name) : '#555' }">
                {{ entry.name }}
              </div>
              <div class="bc-meta" v-if="entry.discovered">
                <span class="bc-lv">Lv.{{ entry.level }}</span>
                <span v-if="entry.encountered" class="bc-enc">遇{{ entry.encountered }}</span>
                <span v-if="entry.defeated" class="bc-kill">杀{{ entry.defeated }}</span>
              </div>
              <div class="bc-meta" v-else>
                <span class="bc-lv">Lv.{{ entry.level }}</span>
                <span class="bc-unknown">未发现</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <Transition name="slide-up">
      <div v-if="detailData" class="detail-panel" @click.self="closeDetail">
        <div class="dp-content">
          <button class="dp-close" @click="closeDetail">✕</button>

          <div class="dp-header">
            <RoundPortrait
              kind="enemy"
              :id="detailData.id"
              :size="96"
              shape="circle"
              :frame="getClanColor(detailData.clan)"
              :name="detailData.name"
              :preview="enemyPreview(detailData, detailData.bestiary)"
            />
            <div>
              <h3 class="dp-name">{{ detailData.name }}</h3>
              <div class="dp-tags">
                <span class="dpt">{{ detailData.clan }}</span>
                <span class="dpt">Lv.{{ detailData.level }}</span>
              </div>
            </div>
          </div>

          <div class="dp-lore" v-if="detailData.lore">
            「 {{ detailData.full_lore || detailData.lore }} 」
          </div>

          <div class="dp-stats-grid">
            <div class="dps"><span class="dps-label">HP</span><span class="dps-val">{{ formatNum(detailData.hp) }}</span></div>
            <div class="dps"><span class="dps-label">攻击</span><span class="dps-val">{{ formatNum(detailData.atk) }}</span></div>
            <div class="dps"><span class="dps-label">防御</span><span class="dps-val">{{ formatNum(detailData.def_) }}</span></div>
            <div class="dps"><span class="dps-label">速度</span><span class="dps-val">{{ formatNum(detailData.spd) }}</span></div>
          </div>

          <div v-if="detailData.signature_skill" class="dp-section">
            <h4>专属技能</h4>
            <div class="dp-feature">
              <strong>{{ detailData.signature_skill.name }}</strong>
              <span>{{ detailData.signature_skill.tier_name || '本命招式' }}</span>
              <p>{{ detailData.signature_skill.description }}</p>
            </div>
          </div>

          <div v-if="detailData.attributes?.length" class="dp-section">
            <h4>怪物属性</h4>
            <div class="dp-chip-grid">
              <div v-for="attr in detailData.attributes" :key="attr.name" class="dp-chip">
                <span>{{ attr.name }}</span>
                <strong>{{ attr.value }}</strong>
              </div>
            </div>
          </div>

          <div v-if="detailData.traits?.length" class="dp-section">
            <h4>特性</h4>
            <div class="dp-list">
              <div v-for="trait in detailData.traits" :key="trait.name" class="dp-list-item">
                <strong>{{ trait.name }}</strong>
                <p>{{ trait.effect }}</p>
              </div>
            </div>
          </div>

          <div v-if="detailData.bonds?.length" class="dp-section">
            <h4>羁绊</h4>
            <div class="dp-list">
              <div v-for="bond in detailData.bonds" :key="bond.target_id + bond.relation" class="dp-list-item">
                <strong>{{ bond.target_name || bond.target_id }}</strong>
                <span>{{ bond.relation }}</span>
                <p>{{ bond.desc }}</p>
              </div>
            </div>
          </div>

          <!-- 图鉴统计 -->
          <div class="dp-encounter-stats" v-if="detailData.bestiary">
            <div class="des"><span>遭遇次数</span><strong>{{ detailData.bestiary.encountered }}</strong></div>
            <div class="des"><span>击杀次数</span><strong>{{ detailData.bestiary.defeated }}</strong></div>
            <div class="des"><span>成功赠礼</span><strong>{{ detailData.bestiary.gifted }}</strong></div>
            <div class="des" v-if="detailData.bestiary.first_kill_at">
              <span>首杀时间</span><strong>{{ detailData.bestiary.first_kill_at.split('T')[0] }}</strong>
            </div>
          </div>

          <!-- 已知掉落 -->
          <div class="dp-drops" v-if="detailData.drops_detail?.length">
            <h4>已知掉落</h4>
            <div class="drop-list">
              <div v-for="d in detailData.drops_detail" :key="d.id" class="drop-item">
                <ItemIcon class="di-icon" :item="d" :size="30" />
                <span class="di-name">{{ d.name }}</span>
                <span class="di-rarity">{{ d.rarity_name }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
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

/* 总览 */
.overview {
  display: flex; gap: 20px; align-items: center; flex-wrap: wrap;
  margin-bottom: 24px;
  padding: 16px 20px;
  background: rgba(20, 15, 8, 0.7);
  border: 1px solid rgba(212, 162, 76, 0.2);
  border-radius: 10px;
}
.ov-stat { text-align: center; }
.ov-num {
  display: block;
  font-size: 22px; font-weight: 700; color: #ddd;
  font-family: 'SF Mono', monospace;
}
.ov-stat.accent .ov-num { color: #D4A24C; }
.ov-label { font-size: 11px; color: #888; letter-spacing: 2px; }
.ov-progress-bar {
  flex: 1; min-width: 120px;
  height: 8px;
  background: rgba(0, 0, 0, 0.4);
  border-radius: 4px;
  overflow: hidden;
}
.ov-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #D4A24C, #FFE0A3);
  border-radius: 4px;
  transition: width 0.5s;
}

/* 族群区块 */
.clans-container { display: flex; flex-direction: column; gap: 24px; }
.clan-section {
  background: rgba(20, 15, 8, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 16px;
}
.clan-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.clan-name {
  margin: 0;
  font-size: 16px;
  letter-spacing: 3px;
  font-family: 'STKaiti', serif;
}
.clan-progress { display: flex; align-items: center; gap: 8px; }
.cp-text { font-size: 12px; color: #aaa; font-family: 'SF Mono', monospace; }
.cp-bar {
  width: 60px; height: 5px;
  background: rgba(0,0,0,0.4);
  border-radius: 3px;
  overflow: hidden;
}
.cp-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }

/* 怪物卡片网格 */
.clan-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
}
.b-card {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.b-card:hover {
  transform: translateY(-1px);
  border-color: rgba(212, 162, 76, 0.4);
  box-shadow: 0 3px 12px rgba(0,0,0,0.3);
}
.b-card.undiscovered {
  opacity: 0.45;
  cursor: default;
}
.b-card.undiscovered:hover { transform: none; border-color: rgba(255,255,255,0.06); box-shadow: none; }

.bc-icon { font-size: 26px; flex-shrink: 0; }
.bc-locked {
  width: 56px; height: 56px;
  border-radius: 50%;
  border: 2px dashed rgba(255,255,255,0.15);
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; color: #444;
  font-family: 'STKaiti', serif;
  flex-shrink: 0;
}
.bc-info { flex: 1; min-width: 0; }
.bc-name {
  font-size: 13px; font-weight: 500;
  letter-spacing: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.bc-meta { display: flex; gap: 6px; font-size: 10px; color: #777; margin-top: 2px; }
.bc-enc, .bc-kill { color: #7FC7E8; }
.bc-unknown { color: #555; font-style: italic; }

/* 空状态 */
.empty { text-align: center; padding: 60px 20px; color: #888; }

/* 详情面板 */
.detail-panel {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex; align-items: center; justify-content: center;
  z-index: 100;
  padding: 20px;
}
.dp-content {
  background: linear-gradient(180deg, #1a1520, #0d0a12);
  border: 1px solid rgba(212, 162, 76, 0.35);
  border-radius: 14px;
  padding: 24px;
  max-width: 680px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  position: relative;
}
.dp-close {
  position: absolute; top: 12px; right: 12px;
  background: none; border: none;
  color: #888; font-size: 18px; cursor: pointer;
}
.dp-close:hover { color: #fff; }
.dp-header { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; }
.dp-icon { font-size: 48px; }
.dp-name { margin: 0; font-size: 20px; color: #FFE0A3; letter-spacing: 2px; font-family: 'STKaiti', serif; }
.dp-tags { display: flex; gap: 6px; margin-top: 6px; }
.dpt {
  font-size: 11px; color: #aaa;
  padding: 2px 8px; border-radius: 4px;
  border: 1px solid rgba(255,255,255,0.15);
}
.dp-lore {
  color: #B8A98E; font-size: 12px; font-style: italic;
  line-height: 1.7; margin-bottom: 14px;
  padding: 10px 14px;
  border-left: 2px solid rgba(212,162,76,0.3);
  background: rgba(212,162,76,0.04);
  border-radius: 4px;
}
.dp-stats-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 8px; margin-bottom: 14px;
}
.dps {
  display: flex; justify-content: space-between;
  padding: 8px 12px;
  background: rgba(255,255,255,0.03);
  border-radius: 6px;
}
.dps-label { color: #888; font-size: 12px; }
.dps-val { color: #FFE0A3; font-size: 13px; font-weight: 600; font-family: 'SF Mono', monospace; }

.dp-section {
  margin-bottom: 14px;
}
.dp-section h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #D4A24C;
  letter-spacing: 2px;
}
.dp-feature,
.dp-list-item,
.dp-chip {
  border: 1px solid rgba(255,255,255,0.07);
  background: rgba(255,255,255,0.035);
  border-radius: 6px;
}
.dp-feature {
  padding: 10px 12px;
}
.dp-feature strong,
.dp-list-item strong,
.dp-chip strong {
  color: #FFE0A3;
}
.dp-feature span,
.dp-list-item span {
  float: right;
  color: #8E98AA;
  font-size: 11px;
}
.dp-feature p,
.dp-list-item p {
  clear: both;
  margin: 6px 0 0;
  color: #CDBB99;
  font-size: 12px;
  line-height: 1.7;
}
.dp-chip-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
}
.dp-chip {
  padding: 8px 10px;
}
.dp-chip span {
  display: block;
  color: #8E98AA;
  font-size: 11px;
  margin-bottom: 4px;
}
.dp-list {
  display: grid;
  gap: 8px;
}
.dp-list-item {
  padding: 9px 11px;
}

.dp-encounter-stats {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 8px; margin-bottom: 14px;
}
.des {
  display: flex; justify-content: space-between;
  padding: 6px 10px;
  font-size: 12px; color: #aaa;
  background: rgba(255,255,255,0.02);
  border-radius: 4px;
}
.des strong { color: #7FC7E8; }

.dp-drops { margin-top: 12px; }
.dp-drops h4 { margin: 0 0 8px; font-size: 13px; color: #D4A24C; letter-spacing: 2px; }
.drop-list { display: flex; flex-direction: column; gap: 6px; }
.drop-item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 10px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 6px;
  font-size: 12px;
}
.di-icon { flex-shrink: 0; }
.di-name { flex: 1; color: #ccc; }
.di-rarity { color: #888; font-size: 10px; }

/* 动画 */
.slide-up-enter-active { transition: all 0.3s ease-out; }
.slide-up-leave-active { transition: all 0.2s ease-in; }
.slide-up-enter-from { opacity: 0; transform: translateY(20px); }
.slide-up-leave-to { opacity: 0; }
</style>
