<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { exploreApi, battleApi, characterApi, fortuneApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'
import Logo from '../components/Logo.vue'
import BackButton from '../components/BackButton.vue'
import SectBackground from '../components/SectBackground.vue'
import NpcDialog from '../components/NpcDialog.vue'
import StatusBar from '../components/StatusBar.vue'
import RoundPortrait from '../components/RoundPortrait.vue'
import { formatNum } from '../utils/format.js'
import FortuneEvent from '../components/FortuneEvent.vue'
import BottomSheet from '../components/BottomSheet.vue'
import { openFeedback, vibrate } from '../utils/mobile.js'
import { enemyPreview, enemyPortraitRef, openCharacterPreview } from '../utils/characterPreview.js'

const router = useRouter()
const msg = useMessage()
const game = useGameStore()

const character = ref(null)
const enemies = ref([])
const hoveredEnemy = ref(null)
const selectedEnemy = ref(null)   // 点击锁定查看详情(用于移动端无悬停)
const playerPos = ref({ x: 50, y: 50 })
const refreshing = ref(false)
const startingBattle = ref(false)
const playerAttacking = ref(false)  // ★ 玩家冲刺/攻击动画标志
const mapPan = ref({ x: 0, y: 0 })
const panning = ref(false)
const isMobileMap = ref(false)
let panStart = null

// ★ 奇遇系统 — 60s 自动 LLM 触发
const fortuneVisible = ref(false)
const fortuneData = ref(null)
const fortuneApplied = ref({})
let fortuneTimer = null
let fortuneInterval = 60_000  // 60s 一次

// 详情面板显示的怪物:优先用「点击选中」,其次「悬停预览」
const displayEnemy = computed(() => selectedEnemy.value || hoveredEnemy.value)

const playerColor = computed(() => character.value?.sect === 'tianji' ? '#FFB454' : '#D4A24C')
const playerPortraitId = computed(() => `${character.value?.sect || 'canglan'}/${character.value?.realm || 'qi'}`)

let moveTimer = null
// 控制位置更新节奏:300ms tick,CSS transition 接管平滑过渡,
// 性能开销 = 原来的 1/3,视觉反而更顺
const TICK_MS = 300
const SPEED_SCALE = 0.35  // 后端给的 move_speed 再乘这个,统一减速

onMounted(async () => {
  syncMapLayout()
  window.addEventListener('resize', syncMapLayout)
  window.addEventListener('orientationchange', syncMapLayout)

  try {
    const { data } = await characterApi.me()
    character.value = data
    game.setCharacter(data)
  } catch {
    return router.replace('/onboarding')
  }

  await refresh()

  // 启动 60s 奇遇定时
  scheduleFortune()

  // 怪物移动循环 — 慢节奏漫游(hover / selected 的怪物原地停下)
  moveTimer = setInterval(() => {
    if (startingBattle.value) return

    enemies.value.forEach(e => {
      // ★ hover 中的怪物 / 被选中的怪物 — 原地不动,方便玩家细看
      if (e.id === hoveredEnemy.value?.id) return
      if (e.id === selectedEnemy.value?.id) return

      // 极低概率改向(每 ~33 tick = 10 秒一次平均)
      if (Math.random() < 0.015) {
        e.move_dir = Math.random() * 360
      }
      const rad = e.move_dir * Math.PI / 180
      let nx = e.spawn_x + Math.cos(rad) * e.move_speed * SPEED_SCALE
      let ny = e.spawn_y + Math.sin(rad) * e.move_speed * SPEED_SCALE

      // 边界反弹
      if (nx < 5 || nx > 95) {
        e.move_dir = 180 - e.move_dir
        nx = Math.max(5, Math.min(95, nx))
      }
      if (ny < 10 || ny > 90) {
        e.move_dir = -e.move_dir
        ny = Math.max(10, Math.min(90, ny))
      }

      e.spawn_x = nx
      e.spawn_y = ny
    })
  }, TICK_MS)
})

onUnmounted(() => {
  if (moveTimer) clearInterval(moveTimer)
  if (fortuneTimer) clearTimeout(fortuneTimer)
  window.removeEventListener('resize', syncMapLayout)
  window.removeEventListener('orientationchange', syncMapLayout)
})

function syncMapLayout() {
  if (typeof window === 'undefined') return
  isMobileMap.value = window.matchMedia('(max-width: 768px), (orientation: landscape) and (max-height: 520px)').matches
}

// ★ 奇遇:60s 后台 LLM 触发(可控:战斗中暂停,弹窗中暂停)
function scheduleFortune() {
  if (fortuneTimer) clearTimeout(fortuneTimer)
  fortuneTimer = setTimeout(async () => {
    if (startingBattle.value || fortuneVisible.value) {
      // 战斗或弹窗时延后 30s
      scheduleFortune()
      return
    }
    try {
      const visible = enemies.value.map(e => ({
        id: e.id, name: e.name, clan: e.clan, level: e.level,
      }))
      const { data } = await fortuneApi.trigger(visible)
      if (data.skipped) {
        // cooldown 或 LLM 失败,过 30s 再试
        fortuneTimer = setTimeout(scheduleFortune, 30_000)
        return
      }
      // 刷新角色(应用了 hp/exp/qi/faction 变化)
      if (data.character) game.setCharacter(data.character)
      fortuneData.value = data.fortune
      fortuneApplied.value = data.applied || {}
      fortuneVisible.value = true
    } catch (e) {
      console.warn('[fortune] 触发失败:', e.message)
    } finally {
      // 60-90s 间随机下一次
      const next = 60_000 + Math.random() * 30_000
      fortuneTimer = setTimeout(scheduleFortune, next)
    }
  }, fortuneInterval)
}

function onFortuneGotoBattle(url) {
  fortuneVisible.value = false
  router.push(url)
}
function onFortuneClose() {
  fortuneVisible.value = false
}

async function refresh() {
  refreshing.value = true
  try {
    // 5-10 只随机
    const count = 5 + Math.floor(Math.random() * 6)
    const { data } = await exploreApi.spawn(count)
    enemies.value = data
  } catch (e) {
    msg.error('刷新地图失败: ' + e.message)
  } finally {
    refreshing.value = false
  }
}

// ★ v3:不再自动开战 — 完全由玩家主动点详情面板「开战」按钮触发
//   避免:撤退后回地图,妖兽还在身边瞬间又触发新战斗的死循环

function showInfo(e, ev) {
  hoveredEnemy.value = e
}

function hideInfo() {
  hoveredEnemy.value = null
}

function openEnemyProfile(e) {
  if (!e || e.is_npc) return
  openCharacterPreview(enemyPreview(e))
}

// 点击妖兽:锁定显示详情(不直接开战)— 兼顾移动端无悬停
// ★ Round 2: NPC 点击直接弹对话框,而非展开 tooltip
function selectEnemy(e) {
  vibrate(18)
  if (e.is_npc) {
    activeNpc.value = e
    hoveredEnemy.value = null
    return
  }
  selectedEnemy.value = e
  hoveredEnemy.value = null
}

// ★ Round 2: NPC 对话框 + 战斗启动
const activeNpc = ref(null)
function onNpcBattleStart(battleId) {
  activeNpc.value = null
  router.push(`/battle/${battleId}`)
}
function onNpcDialogRefresh() {
  // 商店购买后,刷新角色数据(灵气变化)
  characterApi.me().then(r => { game.character = r.data }).catch(() => {})
}

function closeDetails() {
  selectedEnemy.value = null
}

async function engage(e) {
  if (!e || startingBattle.value) return
  // ★ Round 2: NPC 不能直接 engage,弹对话框让玩家选意图
  if (e.is_npc) {
    activeNpc.value = e
    return
  }
  startingBattle.value = true
  vibrate(40)
  if (moveTimer) { clearInterval(moveTimer); moveTimer = null }

  try {
    // ★ 步骤1:玩家平滑走到怪物身边(CSS transition 0.8s)
    // 计算目标:留 6% 距离避免直接重叠
    const dx = e.spawn_x - playerPos.value.x
    const dy = e.spawn_y - playerPos.value.y
    const dist = Math.sqrt(dx*dx + dy*dy)
    const ratio = Math.max(0, (dist - 6) / dist)
    playerPos.value = {
      x: playerPos.value.x + dx * ratio,
      y: playerPos.value.y + dy * ratio,
    }
    playerAttacking.value = true  // 触发玩家攻击动画

    // 等走到位 + 攻击动效播完
    await new Promise(r => setTimeout(r, 800))

    // ★ 步骤2:并发请求战斗 + 等冲刺动画
    const { data } = await battleApi.start(e.id)
    await new Promise(r => setTimeout(r, 200))  // 冲刺最后一帧
    router.push(`/battle/${data.battle_id}`)
  } catch (err) {
    msg.error(err.message)
    startingBattle.value = false
    playerAttacking.value = false
  }
}

function backHome() {
  router.replace('/home')
}

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n))
}

function onMapPointerDown(ev) {
  if (ev.button != null && ev.button !== 0) return
  if (ev.target?.closest?.('.enemy-marker, .head-tooltip, button')) return
  panning.value = true
  panStart = {
    x: ev.clientX,
    y: ev.clientY,
    panX: mapPan.value.x,
    panY: mapPan.value.y,
  }
  ev.currentTarget?.setPointerCapture?.(ev.pointerId)
}

function onMapPointerMove(ev) {
  if (!panning.value || !panStart) return
  ev.preventDefault()
  const dx = ev.clientX - panStart.x
  const dy = ev.clientY - panStart.y
  mapPan.value = {
    x: clamp(panStart.panX + dx, -120, 120),
    y: clamp(panStart.panY + dy, -90, 90),
  }
}

function onMapPointerUp(ev) {
  panning.value = false
  panStart = null
  ev.currentTarget?.releasePointerCapture?.(ev.pointerId)
}

function resetMapPan() {
  mapPan.value = { x: 0, y: 0 }
}

function tierColor(tier) {
  return {
    low: '#52B788',
    mid: '#FFB454',
    high: '#C03F3F',
    myth: '#B59CFF',
    boss: '#FFD700',
  }[tier] || '#888'
}

function markerPortrait(e) {
  return enemyPortraitRef(e, 'circle')
}

function markerColor(e) {
  return e?.is_npc ? '#7FC7E8' : tierColor(e?.tier)
}

function markerTitle(e) {
  if (e?.is_npc) return `${e.intent_label || '相逢'} · 单击交谈`
  return '单击选中 · 双击开战'
}

// ★ 怪物危险度评估 — 帮玩家判断能否胜
function threatLevel(enemy) {
  if (!character.value) return { label: '未知', color: '#888', icon: '❓' }
  const pLv = character.value.level || 1
  const eLv = enemy.level || 1
  const diff = eLv - pLv

  if (diff <= -10) return { label: '碾压', color: '#95D5B2', icon: '✅' }
  if (diff <= -3)  return { label: '稳胜', color: '#52B788', icon: '🟢' }
  if (diff <= 3)   return { label: '势均', color: '#FFB454', icon: '🟡' }
  if (diff <= 8)   return { label: '危险', color: '#FF8C42', icon: '🟠' }
  return { label: '必死', color: '#C03F3F', icon: '🔴' }
}
</script>

<template>
  <div class="explore-page">
    <!-- ★ 门派背景图 -->
    <SectBackground :sect-id="character?.sect || 'canglan'" overlay="normal" :opacity="0.45" />

    <div class="brand-bar">
      <!-- ★ 顶栏改为 3 段式 grid:返回 | Logo居中 | 刷新地图,彻底避免遮挡 -->
      <div class="bar-slot bar-left">
        <BackButton to="/home" label="回主城" inline />
      </div>
      <div class="bar-slot bar-center">
        <Logo :size="32" :text-size="16" />
      </div>
      <div class="bar-slot bar-right">
        <button class="text-btn" :disabled="refreshing" @click="refresh">
          {{ refreshing ? '刷新中...' : '刷新地图' }}
        </button>
        <button class="text-btn center-btn" @click="resetMapPan">回到中心</button>
      </div>
    </div>

    <div class="hint">
      {{ isMobileMap ? '点击目标查看详情,拖拽地图调整视野。' : '鼠标悬停看属性 · 单击锁定 · 双击迎战' }}
    </div>

    <!-- 地图 -->
    <div
      class="map"
      :class="{ panning }"
      @mouseleave="hideInfo"
      @pointerdown="onMapPointerDown"
      @pointermove="onMapPointerMove"
      @pointerup="onMapPointerUp"
      @pointercancel="onMapPointerUp"
    >
      <div
        class="map-world"
        :style="{ transform: `translate3d(${mapPan.x}px, ${mapPan.y}px, 0)` }"
      >
      <!-- 像素级国风地图背景:网格 + 散落地物 -->
      <div class="map-bg-pixel">
        <div class="pixel-grid"></div>
        <div class="pixel-tiles">
          <!-- 山脉(左上)-->
          <span class="tile tile-mountain" style="left: 8%;  top: 12%;">⛰</span>
          <span class="tile tile-mountain" style="left: 13%; top: 18%;">⛰</span>
          <span class="tile tile-mountain" style="left: 78%; top: 10%;">🏔</span>
          <span class="tile tile-mountain" style="left: 85%; top: 15%;">🏔</span>
          <!-- 森林分布 -->
          <span class="tile tile-tree" style="left: 24%; top: 22%;">🌲</span>
          <span class="tile tile-tree" style="left: 32%; top: 28%;">🌳</span>
          <span class="tile tile-tree" style="left: 18%; top: 38%;">🌲</span>
          <span class="tile tile-tree" style="left: 68%; top: 30%;">🌳</span>
          <span class="tile tile-tree" style="left: 74%; top: 38%;">🌲</span>
          <span class="tile tile-tree" style="left: 22%; top: 62%;">🌳</span>
          <span class="tile tile-tree" style="left: 60%; top: 65%;">🌲</span>
          <span class="tile tile-tree" style="left: 80%; top: 60%;">🌳</span>
          <span class="tile tile-tree" style="left: 12%; top: 72%;">🌲</span>
          <span class="tile tile-tree" style="left: 88%; top: 78%;">🌳</span>
          <!-- 水域(中下方) -->
          <span class="tile tile-water" style="left: 38%; top: 78%;">🌊</span>
          <span class="tile tile-water" style="left: 46%; top: 82%;">🌊</span>
          <span class="tile tile-water" style="left: 54%; top: 80%;">🌊</span>
          <!-- 岩石 -->
          <span class="tile tile-rock" style="left: 42%; top: 25%;">🪨</span>
          <span class="tile tile-rock" style="left: 68%; top: 55%;">🪨</span>
          <span class="tile tile-rock" style="left: 30%; top: 70%;">🪨</span>
          <!-- 花草点缀 -->
          <span class="tile tile-flower" style="left: 35%; top: 45%;">🌸</span>
          <span class="tile tile-flower" style="left: 64%; top: 48%;">🌼</span>
          <span class="tile tile-flower" style="left: 26%; top: 55%;">🌺</span>
          <span class="tile tile-grass" style="left: 50%; top: 38%;">🌿</span>
          <span class="tile tile-grass" style="left: 56%; top: 62%;">🍃</span>
          <span class="tile tile-grass" style="left: 44%; top: 60%;">🌾</span>
          <!-- 远处建筑 / 神秘地物 -->
          <span class="tile tile-shrine" style="left: 90%; top: 45%;">⛩️</span>
          <span class="tile tile-shrine" style="left: 6%;  top: 50%;">🏮</span>
          <!-- 中央修真台(玩家所在地)-->
          <div class="player-platform"></div>
          <!-- 区域标签(纯视觉提示) -->
          <span class="zone-label" style="left: 16%; top: 20%; color: #52B788;">初级区</span>
          <span class="zone-label" style="left: 48%; top: 50%; color: #FFB454;">中级区</span>
          <span class="zone-label" style="left: 78%; top: 75%; color: #C03F3F;">高级区</span>
        </div>
      </div>

      <!-- 玩家位置(地图中心)— 加冲刺/攻击动画 -->
      <div
        class="player-marker"
        :class="{ attacking: playerAttacking }"
        :style="{ left: playerPos.x + '%', top: playerPos.y + '%', '--color': playerColor }"
      >
        <RoundPortrait
          class="player-portrait"
          kind="player"
          :id="playerPortraitId"
          :size="52"
          shape="circle"
          :frame="playerColor"
          :name="character?.name || '执笔者'"
          :level="character?.level || ''"
        />
        <div class="p-label">{{ character?.name }} · Lv.{{ character?.level }}</div>
      </div>

      <!-- 怪物 -->
      <div
        v-for="e in enemies"
        :key="e.id"
        class="enemy-marker"
        :class="[
          'tier-' + e.tier,
          {
            selected: selectedEnemy?.id === e.id,
            hovered:  hoveredEnemy?.id === e.id,
            paused:   hoveredEnemy?.id === e.id || selectedEnemy?.id === e.id,
          },
        ]"
        :style="{ left: e.spawn_x + '%', top: e.spawn_y + '%' }"
        @mouseenter="showInfo(e, $event)"
        @mouseleave="hideInfo"
        @click="selectEnemy(e)"
        @dblclick="engage(e)"
        @pointerdown.stop
        :title="markerTitle(e)"
      >
        <!-- ★ 头顶介绍卡(hover 或 selected 时显示)-->
        <div v-if="hoveredEnemy?.id === e.id || selectedEnemy?.id === e.id"
             class="head-tooltip"
             :style="{ borderColor: markerColor(e) }">
          <div class="ht-title">
            <span class="ht-name" :style="{ color: markerColor(e) }">{{ e.name }}</span>
            <span class="ht-tier">[{{ e.tier }} · Lv.{{ e.level }}]</span>
          </div>
          <div class="ht-clan">{{ e.clan }}</div>
          <div class="ht-threat" :style="{ color: threatLevel(e).color }">
            {{ threatLevel(e).icon }} {{ threatLevel(e).label }}
          </div>
          <div class="ht-stats">
            <span>❤️ {{ formatNum(e.hp) }}</span>
            <span>⚔️ {{ formatNum(e.atk) }}</span>
            <span>🛡️ {{ formatNum(e.def_) }}</span>
            <span>💨 {{ formatNum(e.spd) }}</span>
          </div>
          <div class="ht-rewards">
            🎁 战后成章 · 灵气+{{ e.rewards.qi }}
          </div>
          <!-- ★ 攻击按钮 + 双击提示 -->
          <div class="ht-actions" v-if="selectedEnemy?.id === e.id">
            <button
              class="ht-attack-btn codex"
              :style="{ borderColor: markerColor(e), color: markerColor(e) }"
              @click.stop="openEnemyProfile(e)"
              @dblclick.stop>
              阅怪物志
            </button>
            <button
              class="ht-attack-btn"
              :style="{ borderColor: markerColor(e), color: markerColor(e) }"
              @click.stop="engage(e)"
              @dblclick.stop>
              ⚔️ 即刻迎战
            </button>
            <span class="ht-hint">或双击妖兽</span>
          </div>
          <div class="ht-arrow" :style="{ borderTopColor: markerColor(e) }"></div>
        </div>

        <div class="e-level">Lv.{{ e.level }}</div>
        <div class="marker-portrait-wrap" :class="{ 'npc-mark': e.is_npc }" :title="markerTitle(e)">
          <RoundPortrait
            class="marker-portrait"
            :kind="markerPortrait(e).kind"
            :id="markerPortrait(e).id"
            :size="e.is_npc ? 48 : 46"
            shape="circle"
            :frame="markerColor(e)"
            :name="e.name"
          />
          <span v-if="e.is_npc" class="intent-badge">{{ e.intent_icon || '会' }}</span>
        </div>
        <div class="e-name" :class="{ 'npc-name': e.is_npc }"
             :style="{ color: markerColor(e) }">{{ e.name }}</div>
	      </div>
      </div>

      <!-- ★ 已移除右下角 info-panel — 所有怪物信息显示在头顶 tooltip -->

      <div v-if="startingBattle" class="overlay">
        <div class="spinner"></div>
        <p>正在进入战斗...</p>
      </div>
    </div>

    <BottomSheet
      :show="isMobileMap && !!selectedEnemy && !selectedEnemy?.is_npc"
      :title="selectedEnemy ? `${selectedEnemy.name} · Lv.${selectedEnemy.level}` : '目标详情'"
      @close="closeDetails"
    >
      <div v-if="selectedEnemy" class="mobile-enemy-detail">
        <div class="med-head">
          <RoundPortrait
            kind="enemy"
            :id="selectedEnemy.id"
            :size="70"
            shape="circle"
            :frame="tierColor(selectedEnemy.tier)"
            :name="selectedEnemy.name"
            :preview="enemyPreview(selectedEnemy)"
          />
          <div>
            <strong :style="{ color: tierColor(selectedEnemy.tier) }">{{ selectedEnemy.name }}</strong>
            <span>{{ selectedEnemy.clan }} · {{ selectedEnemy.tier }}</span>
          </div>
        </div>
        <p class="med-desc">{{ selectedEnemy.full_lore || selectedEnemy.lore || selectedEnemy.description || '此物因果未明,仍需一战写入本命书。' }}</p>
        <div v-if="selectedEnemy.signature_skill" class="med-skill">
          <span>专属技能</span>
          <strong>{{ selectedEnemy.signature_skill.name }}</strong>
        </div>
        <div class="med-threat" :style="{ color: threatLevel(selectedEnemy).color }">
          {{ threatLevel(selectedEnemy).icon }} {{ threatLevel(selectedEnemy).label }}
        </div>
        <div class="med-stats">
          <span>气血 <strong>{{ formatNum(selectedEnemy.hp) }}</strong></span>
          <span>攻击 <strong>{{ formatNum(selectedEnemy.atk) }}</strong></span>
          <span>防御 <strong>{{ formatNum(selectedEnemy.def_) }}</strong></span>
          <span>速度 <strong>{{ formatNum(selectedEnemy.spd) }}</strong></span>
        </div>
        <div class="med-reward">战后成章 · 灵气 +{{ selectedEnemy.rewards?.qi || 0 }}</div>
      </div>
      <template #footer>
        <div class="med-actions">
          <button class="engage-btn mobile" :disabled="startingBattle" @click="engage(selectedEnemy)">
            {{ startingBattle ? '入战中...' : '迎战' }}
          </button>
          <button class="detail-feedback" @click="openEnemyProfile(selectedEnemy)">怪物志</button>
          <button class="detail-feedback" @click="openFeedback({ category: 'ui', source: 'explore_enemy_sheet', enemy: selectedEnemy?.id })">反馈遮挡</button>
        </div>
      </template>
    </BottomSheet>

    <!-- ★ 奇遇弹窗 -->
    <FortuneEvent
      :visible="fortuneVisible"
      :fortune="fortuneData"
      :applied="fortuneApplied"
      @close="onFortuneClose"
      @goto-battle="onFortuneGotoBattle"
    />

    <!-- ★ Round 2: NPC 互动对话框 -->
    <NpcDialog
      :visible="!!activeNpc"
      :npc="activeNpc"
      @close="activeNpc = null"
      @battle-start="onNpcBattleStart"
      @refresh="onNpcDialogRefresh"
    />

    <!-- ★ 底部状态条(常驻) -->
    <StatusBar />
  </div>
</template>

<style scoped>
.explore-page {
  min-height: var(--app-svh);
  min-height: 100dvh;
  padding: calc(10px + var(--safe-top)) calc(10px + var(--safe-right)) calc(88px + var(--safe-bottom)) calc(10px + var(--safe-left));
  display: flex; flex-direction: column;
}
.brand-bar {
  position: sticky;
  top: var(--safe-top);
  z-index: 60;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 10px;
  padding: 8px;
  margin: -2px -2px 8px;
  border: 1px solid rgba(212,162,76,0.16);
  border-radius: 10px;
  background: rgba(7, 8, 16, 0.72);
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 22px rgba(0,0,0,0.26);
}
.bar-slot { display: flex; align-items: center; }
.bar-left { justify-content: flex-start; }
.bar-center { justify-content: center; }
.bar-right { justify-content: flex-end; gap: 10px; }
.bar-left :deep(.back-btn-inline) {
  min-height: 40px;
  border-color: rgba(255,224,163,0.78);
  background: linear-gradient(135deg, rgba(212,162,76,0.34), rgba(212,162,76,0.12));
  box-shadow: 0 0 0 1px rgba(255,224,163,0.08), 0 8px 20px rgba(0,0,0,0.28);
}
@media (max-width: 640px) {
  .brand-bar { grid-template-columns: auto 1fr auto; gap: 8px; }
  .bar-center { justify-content: flex-start; }
}
.text-btn {
  background: none; border: 1px solid rgba(255,255,255,0.15);
  color: #aaa; padding: 6px 14px; border-radius: 6px;
  cursor: pointer; font-size: 13px;
}
.text-btn:hover:not(:disabled) { color: #fff; border-color: #D4A24C; }
.text-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.hint {
  background: rgba(127,199,232,0.06);
  border-left: 3px solid #7FC7E8;
  padding: 8px 14px; border-radius: 4px;
  color: #aaa; font-size: 12px;
  margin-bottom: 8px;
}

.map {
  position: relative;
  flex: 1;
  min-height: 600px;
  background:
    /* 多层渐变:深夜 + 山影 */
    radial-gradient(ellipse at 50% 30%, rgba(40, 60, 100, 0.4) 0%, transparent 50%),
    radial-gradient(ellipse at center, #1f2a44 0%, #0a1428 70%, #050810 100%);
  border-radius: 16px;
  border: 1px solid rgba(212,162,76,0.2);
  overflow: hidden;
  cursor: crosshair;
  touch-action: none;
}
.map.panning {
  cursor: grabbing;
}
.map-world {
  position: absolute;
  inset: 0;
  transform-origin: center;
  will-change: transform;
  transition: transform 0.06s linear;
}
/* ============ 像素级国风地图背景 ============ */
.map-bg-pixel {
  position: absolute; inset: 0;
  pointer-events: none;
  /* 双层渐变模拟地形:草地(青) → 远山(墨) + 中央光斑(修真台) */
  background:
    radial-gradient(circle at 50% 50%, rgba(212,162,76,0.05) 0%, transparent 30%),
    radial-gradient(ellipse at 50% 30%, rgba(82,183,136,0.04) 0%, transparent 40%),
    radial-gradient(ellipse at 30% 80%, rgba(127,199,232,0.03) 0%, transparent 35%);
}

/* 像素网格 — 半透明,提供"地图坐标"感 */
.pixel-grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(212,162,76,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(212,162,76,0.04) 1px, transparent 1px);
  background-size: 40px 40px;
  background-position: 0 0;
  /* 中心点深一点点,营造"修真台"中心感 */
  mask-image: radial-gradient(circle at center, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0.2) 70%);
  -webkit-mask-image: radial-gradient(circle at center, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0.2) 70%);
}

/* 地物 tile — 每个都是 emoji,半透明、不响应鼠标 */
.pixel-tiles {
  position: absolute; inset: 0;
}
.tile {
  position: absolute;
  font-size: 28px;
  opacity: 0.22;
  filter: saturate(0.6) brightness(0.9);
  transform: translate(-50%, -50%);
  user-select: none;
  pointer-events: none;
  text-shadow: 0 0 8px rgba(0,0,0,0.4);
}
.tile-mountain { font-size: 42px; opacity: 0.18; }
.tile-tree     { font-size: 30px; opacity: 0.25; }
.tile-water    {
  font-size: 26px; opacity: 0.25;
  animation: tile-wave 4s ease-in-out infinite;
}
.tile-rock     { font-size: 22px; opacity: 0.20; }
.tile-flower   { font-size: 20px; opacity: 0.30; }
.tile-grass    { font-size: 18px; opacity: 0.22; }
.tile-shrine   { font-size: 34px; opacity: 0.28; }

.zone-label {
  position: absolute;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 4px;
  opacity: 0.25;
  pointer-events: none;
  font-family: 'STKaiti', 'KaiTi', serif;
  text-shadow: 0 0 8px currentColor;
  transform: translate(-50%, -50%);
  user-select: none;
}

@keyframes tile-wave {
  0%, 100% { transform: translate(-50%, -50%) translateY(0); }
  50%      { transform: translate(-50%, -50%) translateY(-3px); }
}

/* 中央修真台:轻微辉光圈,标记玩家位置 */
.player-platform {
  position: absolute;
  left: 50%; top: 50%;
  width: 140px; height: 140px;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  border: 1px dashed rgba(212, 162, 76, 0.25);
  background: radial-gradient(circle, rgba(212, 162, 76, 0.06) 0%, transparent 70%);
  animation: platform-pulse 4s ease-in-out infinite;
}
@keyframes platform-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(212, 162, 76, 0.15); }
  50%      { box-shadow: 0 0 0 12px rgba(212, 162, 76, 0); }
}

.player-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  display: flex; flex-direction: column;
  align-items: center;
  z-index: 10;
  pointer-events: none;
  /* ★ 平滑走位 — 触发战斗时走到怪物身边 */
  transition: left 0.7s cubic-bezier(0.34, 1.2, 0.64, 1),
              top  0.7s cubic-bezier(0.34, 1.2, 0.64, 1);
}
/* ★ 攻击/冲刺动画 — 缩放+脉冲+金光环 */
.player-marker.attacking {
  z-index: 20;
}
.player-marker.attacking .player-portrait {
  animation: player-attack 0.7s ease-out;
}
.player-marker.attacking::before {
  content: '';
  position: absolute;
  top: 50%; left: 50%;
  width: 80px; height: 80px;
  margin: -40px 0 0 -40px;
  border-radius: 50%;
  border: 3px solid var(--color);
  opacity: 0;
  animation: attack-ring 0.7s ease-out forwards;
}
.player-marker.attacking::after {
  content: '出 击!';
  position: absolute;
  top: -28px; left: 50%;
  transform: translateX(-50%);
  font-size: 14px; font-weight: 700;
  letter-spacing: 4px;
  color: #FFE0A3;
  font-family: 'STKaiti', serif;
  text-shadow: 0 0 12px #D4A24C, 0 2px 4px rgba(0,0,0,0.9);
  animation: attack-text 0.8s ease-out forwards;
  white-space: nowrap;
}
@keyframes player-attack {
  0%   { transform: scale(1) rotate(0); }
  30%  { transform: scale(1.4) rotate(-8deg); filter: drop-shadow(0 0 24px #FFE0A3); }
  60%  { transform: scale(1.2) rotate(8deg); }
  100% { transform: scale(1.5); filter: drop-shadow(0 0 36px #FFD700); }
}
@keyframes attack-ring {
  0%   { opacity: 1; transform: scale(0.4); }
  100% { opacity: 0; transform: scale(2.2); }
}
@keyframes attack-text {
  0%   { opacity: 0; transform: translateX(-50%) translateY(8px) scale(0.6); }
  30%  { opacity: 1; transform: translateX(-50%) translateY(0) scale(1.1); }
  100% { opacity: 0; transform: translateX(-50%) translateY(-20px) scale(1.4); }
}

.player-portrait {
  filter: drop-shadow(0 0 12px var(--color));
  transition: filter 0.3s, transform 0.2s;
}
.p-label {
  font-size: 11px;
  color: var(--color);
  background: rgba(0,0,0,0.5);
  padding: 2px 6px; border-radius: 3px;
  margin-top: 4px;
  letter-spacing: 1px;
}

.enemy-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  display: flex; flex-direction: column;
  align-items: center;
  cursor: pointer;
  /* JS 每 300ms 改 left/top,CSS 同步 transition 让视觉平滑 60fps */
  transition: left 0.3s linear, top 0.3s linear, filter 0.2s;
  z-index: 5;
  will-change: left, top;  /* GPU 提示 */
}
.enemy-marker:hover {
  z-index: 9;
  filter: drop-shadow(0 0 12px rgba(255,255,255,0.6));
}
.enemy-marker:hover .marker-portrait-wrap {
  transform: scale(1.25);
}
.e-level {
  font-size: 10px; font-weight: 600;
  color: #fff;
  background: rgba(0,0,0,0.6);
  padding: 1px 5px; border-radius: 3px;
  margin-bottom: 2px;
}
.marker-portrait-wrap {
  position: relative;
  transition: transform 0.2s, filter 0.2s;
}
.marker-portrait {
  display: block;
}
/* NPC 以绘画头像为主体,意图只作为小角标 */
.marker-portrait-wrap.npc-mark {
  background: radial-gradient(circle, rgba(127,199,232,0.35), transparent 70%);
  border-radius: 50%;
  padding: 4px;
  animation: npc-pulse 2.4s ease-in-out infinite;
  filter: drop-shadow(0 0 6px rgba(127,199,232,0.5));
}
.intent-badge {
  position: absolute;
  right: -5px;
  bottom: -4px;
  min-width: 20px;
  height: 20px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.72);
  background: rgba(7, 12, 24, 0.92);
  color: #E8F8FF;
  font-size: 13px;
  line-height: 1;
  box-shadow: 0 4px 10px rgba(0,0,0,0.42), 0 0 10px rgba(127,199,232,0.45);
}
@keyframes npc-pulse {
  0%, 100% { transform: scale(1);    filter: drop-shadow(0 0 6px rgba(127,199,232,0.5)); }
  50%      { transform: scale(1.08); filter: drop-shadow(0 0 12px rgba(127,199,232,0.85)); }
}
.e-name.npc-name {
  background: rgba(15, 27, 46, 0.85);
  border: 1px solid rgba(127, 199, 232, 0.4);
}
.e-name {
  font-size: 10px;
  background: rgba(0,0,0,0.5);
  padding: 1px 5px; border-radius: 3px;
  margin-top: 2px;
  white-space: nowrap;
}

.tier-low .marker-portrait-wrap:not(.npc-mark) { filter: drop-shadow(0 0 4px rgba(82,183,136,0.5)); }
.tier-mid .marker-portrait-wrap:not(.npc-mark) { filter: drop-shadow(0 0 4px rgba(255,180,84,0.5)); }
.tier-high .marker-portrait-wrap:not(.npc-mark) { filter: drop-shadow(0 0 4px rgba(192,63,63,0.5)); }
.tier-myth .marker-portrait-wrap:not(.npc-mark) { filter: drop-shadow(0 0 6px rgba(181,156,255,0.7)); animation: pulse 2s infinite; }
/* ★ 被 hover/selected 的怪物 — 原地停下,不再 CSS transition 跟新位置 */
.enemy-marker.paused {
  transition: none;
  z-index: 8;
}
.enemy-marker.hovered .marker-portrait-wrap {
  transform: scale(1.35);
  filter: drop-shadow(0 0 16px rgba(255, 224, 163, 0.85));
}

/* ★ 头顶介绍卡(浮动 tooltip) */
.head-tooltip {
  position: absolute;
  left: 50%; bottom: calc(100% + 14px);
  transform: translateX(-50%);
  min-width: 180px; max-width: 240px;
  padding: 8px 12px 10px;
  background: rgba(8, 12, 24, 0.96);
  border: 1.5px solid;
  border-radius: 8px;
  backdrop-filter: blur(8px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.7);
  z-index: 30;
  /* ★ tooltip 本身不拦截鼠标(避免遮挡下方怪物 hover),但内部按钮单独开 pointer-events */
  pointer-events: none;
  animation: tooltip-in 0.18s ease-out;
  font-size: 11px;
  line-height: 1.5;
  white-space: nowrap;
}
/* ★ 攻击按钮重新拿回鼠标事件,否则点不到 */
.head-tooltip .ht-attack-btn,
.head-tooltip .ht-actions {
  pointer-events: auto;
}
@keyframes tooltip-in {
  from { opacity: 0; transform: translateX(-50%) translateY(8px); }
  to   { opacity: 1; transform: translateX(-50%) translateY(0); }
}
.ht-title {
  display: flex; gap: 6px; align-items: baseline;
  margin-bottom: 4px;
}
.ht-name {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 1px;
  font-family: 'STKaiti', 'KaiTi', serif;
}
.ht-tier {
  font-size: 10px;
  color: #888;
}
.ht-clan {
  font-size: 10px; color: #aaa;
  margin-bottom: 4px;
  letter-spacing: 1px;
}
.ht-threat {
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 4px;
  letter-spacing: 1px;
}
.ht-stats {
  display: flex; gap: 8px;
  font-size: 10px;
  color: #ccc;
  margin-bottom: 4px;
  border-top: 1px solid rgba(255,255,255,0.06);
  padding-top: 5px;
}
.ht-rewards {
  font-size: 10px;
  color: #7FC7E8;
  margin-top: 2px;
}
.ht-hint {
  margin-top: 0;
  font-size: 10px;
  color: #888;
  letter-spacing: 1px;
  white-space: nowrap;
}
.ht-actions {
  margin-top: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}
.ht-attack-btn {
  background: rgba(192, 63, 63, 0.22);
  color: #FF8888;
  border: 1.5px solid rgba(192, 63, 63, 0.8);
  padding: 6px 14px;
  border-radius: 18px;
  font-size: 12px;
  font-family: 'STKaiti', serif;
  letter-spacing: 2px;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.18s;
  box-shadow: 0 0 10px rgba(192, 63, 63, 0.35);
  animation: attack-pulse 1.4s ease-in-out infinite;
}
.ht-attack-btn:hover {
  background: rgba(192, 63, 63, 0.42);
  color: #fff;
  transform: scale(1.06);
  box-shadow: 0 0 16px rgba(192, 63, 63, 0.65);
}
.ht-attack-btn.codex {
  background: rgba(127,199,232,0.14);
  box-shadow: none;
  animation: none;
}
@keyframes attack-pulse {
  0%, 100% { box-shadow: 0 0 8px rgba(192, 63, 63, 0.3); }
  50%      { box-shadow: 0 0 18px rgba(192, 63, 63, 0.6); }
}
/* 卡片底部三角箭头指向怪物 */
.ht-arrow {
  position: absolute;
  left: 50%; bottom: -8px;
  transform: translateX(-50%);
  width: 0; height: 0;
  border: 8px solid transparent;
  border-top: 8px solid;
  border-bottom: 0;
}

/* 被点击选中的怪物:外环金光提示 */
.enemy-marker.selected {
  z-index: 8;
}
.enemy-marker.selected .marker-portrait-wrap {
  transform: scale(1.2);
  filter: drop-shadow(0 0 16px #FFE0A3) drop-shadow(0 0 6px #D4A24C);
}
.enemy-marker.selected::before {
  content: '';
  position: absolute;
  top: 50%; left: 50%;
  width: 56px; height: 56px;
  margin: -28px 0 0 -28px;
  border: 2px solid #FFE0A3;
  border-radius: 50%;
  animation: selected-pulse 1.4s ease-in-out infinite;
  pointer-events: none;
}
@keyframes selected-pulse {
  0%, 100% { transform: scale(0.9); opacity: 0.7; }
  50%      { transform: scale(1.15); opacity: 1; }
}

@keyframes pulse {
  50% { filter: drop-shadow(0 0 12px rgba(181,156,255,1)); }
}

/* 信息面板 */
.info-panel {
  position: absolute;
  bottom: 16px;
  right: 16px;
  max-width: 380px;
  background: rgba(15, 15, 30, 0.92);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(212,162,76,0.4);
  border-radius: 10px;
  padding: 14px 16px;
  z-index: 20;
  font-size: 13px;
}
.ip-head {
  display: flex; gap: 12px; align-items: center;
  margin-bottom: 10px;
}
.ip-emoji { font-size: 36px; }
.ip-name { font-size: 16px; font-weight: 600; letter-spacing: 1px; }
.ip-tier { font-size: 11px; opacity: 0.7; margin-left: 4px; }
.ip-clan { font-size: 11px; color: #888; margin-top: 2px; }
.ip-desc {
  color: #ccc; line-height: 1.6;
  margin: 0 0 8px;
}
.ip-lore {
  color: #aaa; font-style: italic;
  background: rgba(0,0,0,0.3);
  padding: 8px 10px; border-radius: 6px;
  border-left: 2px solid #D4A24C;
  font-size: 12px;
  line-height: 1.6;
  margin-bottom: 10px;
}
.ip-stats {
  display: flex; flex-wrap: wrap; gap: 10px;
  font-size: 11px; color: #888;
  border-top: 1px solid rgba(255,255,255,0.06);
  padding-top: 8px;
}
.ip-stats strong { color: #fff; margin-left: 4px; }
.ip-rewards {
  margin-top: 8px;
  font-size: 11px;
  color: #7FC7E8;
  background: rgba(127,199,232,0.05);
  padding: 6px 10px; border-radius: 4px;
}
/* 点击锁定的面板更显眼 */
.info-panel.sticky {
  border-color: #FFE0A3;
  box-shadow: 0 8px 32px rgba(212, 162, 76, 0.35);
}
.ip-close {
  position: absolute; top: 6px; right: 10px;
  background: none; border: none;
  color: #888; font-size: 20px;
  cursor: pointer; line-height: 1;
  padding: 2px 6px;
}
.ip-close:hover { color: #FFE0A3; }
.ip-actions {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(255,255,255,0.06);
  display: flex; justify-content: center;
}
.engage-btn {
  background: linear-gradient(135deg, #C03F3F, #8B2A2A);
  border: 1px solid #FF8888;
  color: #FFE0E0;
  padding: 8px 24px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 3px;
  font-family: 'STKaiti','KaiTi',serif;
  transition: all 0.2s;
  box-shadow: 0 0 16px rgba(192, 63, 63, 0.3);
  animation: engage-pulse 1.8s ease-in-out infinite;
}
.engage-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 24px rgba(192, 63, 63, 0.6);
  background: linear-gradient(135deg, #D04F4F, #A03A3A);
}
.engage-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.engage-btn.mobile {
  width: 100%;
  min-height: 44px;
  border-radius: 8px;
}
.mobile-enemy-detail {
  display: grid;
  gap: 12px;
}
.med-head {
  display: flex;
  gap: 12px;
  align-items: center;
}
.med-head strong,
.med-head span {
  display: block;
}
.med-head strong {
  font-size: 18px;
  margin-bottom: 4px;
}
.med-head span,
.med-desc {
  color: #AEB7C8;
}
.med-desc {
  margin: 0;
  line-height: 1.8;
}
.med-skill {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 10px;
  border: 1px solid rgba(212,162,76,0.2);
  background: rgba(212,162,76,0.08);
  color: #D8C6A4;
}
.med-skill span {
  color: #8E98AA;
  font-size: 12px;
}
.med-skill strong {
  color: #FFE0A3;
}
.med-threat {
  font-weight: 800;
}
.med-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.med-stats span,
.med-reward {
  padding: 9px 10px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 6px;
  background: rgba(255,255,255,0.04);
  color: #B8C7E0;
}
.med-stats strong {
  color: #FFE0A3;
  float: right;
}
.med-reward {
  color: #7FC7E8;
}
.med-actions {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
}
.detail-feedback {
  min-height: 44px;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 8px;
  background: rgba(255,255,255,0.04);
  color: #B8C7E0;
  padding: 0 12px;
}
@keyframes engage-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(192, 63, 63, 0.4); }
  50%      { box-shadow: 0 0 0 8px rgba(192, 63, 63, 0); }
}

@media (max-width: 768px) {
  .explore-page {
    padding: calc(8px + var(--safe-top)) calc(8px + var(--safe-right)) calc(136px + var(--safe-bottom)) calc(8px + var(--safe-left));
  }
  .brand-bar {
    grid-template-columns: auto minmax(0, 1fr);
    gap: 8px;
    margin: 0 0 8px;
    padding: 7px;
  }
  .bar-center {
    display: none;
  }
  .bar-right {
    grid-column: 1 / -1;
    justify-content: stretch;
  }
  .bar-right .text-btn {
    flex: 1;
  }
  .bar-left :deep(.back-label) {
    letter-spacing: 1px;
  }
  .hint {
    margin-bottom: 8px;
  }
  .map {
    min-height: calc(var(--visual-vh, 100vh) - 250px);
    border-radius: 10px;
  }
  .head-tooltip {
    display: none;
  }
  .enemy-marker {
    min-width: 44px;
    min-height: 44px;
    justify-content: center;
  }
  .tile {
    opacity: 0.18;
  }
}

@media (orientation: landscape) and (max-height: 520px) {
  .explore-page {
    min-height: var(--visual-vh);
    padding: calc(6px + var(--safe-top)) calc(6px + var(--safe-right)) calc(8px + var(--safe-bottom)) calc(76px + var(--safe-left));
  }
  .brand-bar {
    grid-template-columns: auto minmax(0, 1fr) auto;
    margin-bottom: 6px;
  }
  .bar-center {
    display: none;
  }
  .hint {
    display: none;
  }
  .map {
    min-height: calc(var(--visual-vh, 100vh) - 76px);
  }
}

.overlay {
  position: absolute; inset: 0;
  background: rgba(10,10,20,0.8);
  backdrop-filter: blur(6px);
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  color: #D4A24C;
  z-index: 100;
}
.spinner {
  width: 50px; height: 50px;
  border: 3px solid rgba(212,162,76,0.2);
  border-top-color: #D4A24C;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 12px;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
