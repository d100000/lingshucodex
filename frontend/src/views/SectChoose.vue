<!--
  选派沉浸式页面 v2 — 网游式人物选择
  布局:
    顶栏 brand + 返回
    主区:左侧立绘(60%) + 右侧四象限信息(40%)
    左右切换箭头
    底部 dock(5 派切换 + 选中态)

  特性:
    - 1024x1536 人物立绘居中,彩色 / 置灰两种态
    - 不可选派:灰度 + 锁角标
    - 切换:立绘滑出滑入 + 信息淡入
    - 信息四象限:门派介绍 / 招式预览 / 数值与 buff / 宗派背景故事
    - 键盘 ← → 切换、Enter 确认
-->
<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage, useDialog } from 'naive-ui'
import { sectApi, characterApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'
import Logo from '../components/Logo.vue'
import WuxiaBackground from '../components/WuxiaBackground.vue'
import BackButton from '../components/BackButton.vue'
import SectBackground from '../components/SectBackground.vue'
import SectFlag from '../components/SectFlag.vue'

const router = useRouter()
const route = useRoute()
const msg = useMessage()
const dialog = useDialog()
const game = useGameStore()

const sects = ref([])                  // 5 派列表(from /sect/list)
const previews = ref({})               // { canglan: previewData, ... } 缓存
const currentIdx = ref(0)
const switching = ref(false)
const direction = ref('right')
const portraitLoaded = ref({})         // { canglan: true, ... } 立绘是否加载完毕

// ============== 5 派元数据(配色 / 情感 / 标志物) ==============
const SECT_META = {
  canglan: {
    emoji: '🗡️',
    accent: '#D4A24C',
    glow: '#FFE0A3',
    motto: '深思而后动 · 一击必中要害',
    portrait_fallback: '/images/portraits/sects/canglan.png',
  },
  tianji: {
    emoji: '⚙️',
    accent: '#FFB454',
    glow: '#FFDEA3',
    motto: '诸法皆通 · 万象归一',
    portrait_fallback: '/images/portraits/sects/tianji.png',
  },
  xuanji: {
    emoji: '🧠',
    accent: '#9B59B6',
    glow: '#C8A6DD',
    motto: '推演天机 · 性价比之王',
    portrait_fallback: '/images/portraits/sects/xuanji.png',
  },
  qingming: {
    emoji: '📜',
    accent: '#52B788',
    glow: '#95D5B2',
    motto: '博学根基 · 中文为本',
    portrait_fallback: '/images/portraits/sects/qingming.png',
  },
  yueyin: {
    emoji: '🌙',
    accent: '#B59CFF',
    glow: '#D9CCFF',
    motto: '千古不忘 · 月隐千年',
    portrait_fallback: '/images/portraits/sects/yueyin.png',
  },
}

const currentSect = computed(() => sects.value[currentIdx.value])
const currentMeta = computed(() => SECT_META[currentSect.value?.id] || SECT_META.canglan)
const currentPreview = computed(() => previews.value[currentSect.value?.id])

// 立绘 URL — 优先 jpg(压缩后 ~600KB),fallback png(~2.8MB)
const currentPortraitUrl = computed(() => {
  const id = currentSect.value?.id
  if (!id) return ''
  return `/images/sect-portraits/${id}.jpg`
})
// dock 缩略图 — 480x720 jpeg ~140KB,首屏总加载 = 5 × 140 = 700KB
function dockThumb(id) {
  return `/images/sect-portraits/${id}-thumb.jpg`
}

// ============== 初始化 ==============
// ★ 从 onboarding 透传的"按 API key 探测的可选派 id 列表"
// e.g. ?avail=canglan,tianji — 优先于后端 sect.available
const availableFromProbe = computed(() => {
  const q = route.query.avail
  if (!q) return null
  return String(q).split(',').filter(Boolean)
})
function isSelectable(s) {
  if (!s) return false
  if (availableFromProbe.value) return availableFromProbe.value.includes(s.id)
  return s.available === true  // fallback 后端原始字段
}

onMounted(async () => {
  // ★ v4:5 张图全挂 DOM 后,主动 decode() 进 GPU,避免首次切换 50-100ms 解码延迟
  setTimeout(() => {
    ;['canglan','tianji','xuanji','qingming','yueyin'].forEach(id => {
      const img = new Image()
      img.src = `/images/sect-portraits/${id}.jpg`
      // decode() 显式预解码 — 比 new Image() 仅下载更彻底
      if (img.decode) img.decode().catch(() => {})
      const t = new Image(); t.src = `/images/sect-portraits/${id}-thumb.jpg`
    })
  }, 50)

  // 已有角色?直接跳主城
  try {
    const { data } = await characterApi.me()
    if (data) {
      game.setCharacter(data)
      router.replace('/home')
      return
    }
  } catch {}

  if (route.query.reason) {
    msg.info(route.query.reason)
    router.replace({ path: '/sect-choose' })
  }

  try {
    const { data } = await sectApi.list()
    sects.value = data
  } catch (e) {
    msg.error('加载门派失败: ' + e.message)
  }

  // 预拉所有派 preview(并发)
  fetchAllPreviews()

  window.addEventListener('keydown', onKeyDown)
})
onUnmounted(() => window.removeEventListener('keydown', onKeyDown))

async function fetchAllPreviews() {
  const tasks = sects.value.map(async (s) => {
    try {
      const { data } = await sectApi.preview(s.id)
      previews.value[s.id] = data
    } catch (e) {
      console.warn('preview 加载失败', s.id, e.message)
    }
  })
  await Promise.allSettled(tasks)
}

function onKeyDown(e) {
  if (e.key === 'ArrowLeft') prev()
  if (e.key === 'ArrowRight') next()
  if (e.key === 'Enter') confirmJoin()
}

function next() {
  if (switching.value) return
  direction.value = 'right'
  switching.value = true
  setTimeout(() => {
    currentIdx.value = (currentIdx.value + 1) % sects.value.length
    setTimeout(() => switching.value = false, 20)
  }, 80)
}

function prev() {
  if (switching.value) return
  direction.value = 'left'
  switching.value = true
  setTimeout(() => {
    currentIdx.value = (currentIdx.value - 1 + sects.value.length) % sects.value.length
    setTimeout(() => switching.value = false, 20)
  }, 80)
}

function pickIdx(i) {
  if (i === currentIdx.value || switching.value) return
  direction.value = i > currentIdx.value ? 'right' : 'left'
  switching.value = true
  setTimeout(() => {
    currentIdx.value = i
    setTimeout(() => switching.value = false, 20)
  }, 80)
}

function confirmJoin() {
  const s = currentSect.value
  if (!s) return
  if (!isSelectable(s)) {
    msg.warning(`【${s.name}】灵脉尚未开通,本期仅可选 沧澜剑派 与 天机阁`)
    return
  }
  // ★ 从 onboarding 跳来时已带 key,直接跳 KeyVerify 并 query 透传
  const fromOnboarding = route.query.from === 'onboarding'
  const verifyQuery = fromOnboarding ? {
    base_url: route.query.base_url,
    api_key: route.query.api_key,
    name: route.query.name,
    from: 'onboarding',
  } : {}

  dialog.warning({
    title: '⚠️ 师承不可背叛',
    content: fromOnboarding
      ? `您即将拜入【${s.name}】门下(${s.provider_display})。\n\nKey 已带入,下一步系统会精细验证该派各境界对应的所有模型(5-30 秒),通过后正式入门。\n\n继续吗?`
      : `您即将拜入【${s.name}】门下(${s.provider_display})。\n\n下一步需填写您自己的 API Key,系统会并发测试该派各境界对应的所有模型(预计 5-30 秒),全部通过后方可正式入门。\n\n继续吗?`,
    positiveText: '前往灵脉验证',
    negativeText: '从入门页重新开始',
    onPositiveClick: () => router.push({ path: `/key-verify/${s.id}`, query: verifyQuery }),
    onNegativeClick: () => router.push('/onboarding'),
  })
}

function onPortraitLoad(id) {
  portraitLoaded.value[id] = true
}

// ═══════════════ 雷达图(5 维数值可视化)═══════════════
const RADAR_MAX = { hp: 140, atk: 30, def: 20, spd: 120, crit_rate: 0.3 }
const RADAR_DIMS = ['hp', 'atk', 'def', 'spd', 'crit_rate']
const RADAR_LABEL = { hp: 'HP', atk: '攻', def: '防', spd: '速', crit_rate: '暴' }
const RADAR_CX = 100, RADAR_CY = 100, RADAR_R = 70

// 多边形外环坐标(供绘背景五边形 + 轴线 + label)
const radarAxes = computed(() => RADAR_DIMS.map((d, i) => {
  const angle = (i * 72 - 90) * Math.PI / 180
  const x = RADAR_CX + Math.cos(angle) * RADAR_R
  const y = RADAR_CY + Math.sin(angle) * RADAR_R
  // label 放外面一点
  const lx = RADAR_CX + Math.cos(angle) * (RADAR_R + 16)
  const ly = RADAR_CY + Math.sin(angle) * (RADAR_R + 16)
  return { x, y, lx, ly, key: d, label: RADAR_LABEL[d] }
}))
const radarOuterPath = computed(() => radarAxes.value.map(a => `${a.x},${a.y}`).join(' '))

// 当前派的数据五边形(归一化到 0-1)
const radarDataPath = computed(() => {
  if (!currentPreview.value?.initial_stats) return ''
  const s = currentPreview.value.initial_stats
  return RADAR_DIMS.map((d, i) => {
    const val = Math.min(1, (s[d] || 0) / RADAR_MAX[d])
    const angle = (i * 72 - 90) * Math.PI / 180
    const x = RADAR_CX + Math.cos(angle) * RADAR_R * val
    const y = RADAR_CY + Math.sin(angle) * RADAR_R * val
    return `${x},${y}`
  }).join(' ')
})

// 圈圈刻度(20/40/60/80/100%)
const radarRings = [0.25, 0.5, 0.75, 1.0]
function ringPath(scale) {
  return radarAxes.value.map(a => {
    const x = RADAR_CX + (a.x - RADAR_CX) * scale
    const y = RADAR_CY + (a.y - RADAR_CY) * scale
    return `${x},${y}`
  }).join(' ')
}
function onPortraitError(id, ev) {
  // 立绘缺失链:.jpg → .png → portraits/sects fallback
  if (!ev?.target) return
  const tried = ev.target.dataset.tried || ''
  if (!tried.includes('png')) {
    ev.target.dataset.tried = tried + ',png'
    ev.target.src = `/images/sect-portraits/${id}.png`
  } else {
    ev.target.src = SECT_META[id]?.portrait_fallback || ''
    portraitLoaded.value[id] = false
  }
}
</script>

<template>
  <div class="cs-page">
    <!-- 当前派的背景图 -->
    <SectBackground :sect-id="currentSect?.id || 'canglan'" overlay="strong" :opacity="0.30" />
    <WuxiaBackground intensity="light" :accent="currentMeta.accent" />

    <!-- 顶部 brand(集成返回按钮) -->
    <header class="brand">
      <BackButton to="/onboarding" label="返回入门" inline />
      <Logo :size="36" :text-size="16" />
      <div class="brand-sub">选择门派 · 师承不可背叛</div>
    </header>

    <!-- ★ 全局飘浮金色尘埃(纯 CSS 装饰)-->
    <div class="dust-layer" aria-hidden="true">
      <span v-for="n in 14" :key="n" class="dust" :style="{
        left: (Math.random()*100) + '%',
        top: (Math.random()*100) + '%',
        animationDelay: (Math.random()*8) + 's',
        animationDuration: (12 + Math.random()*16) + 's',
      }"></span>
    </div>

    <!-- 主区域:左立绘 + 右信息 -->
    <main class="main">
      <!-- 左右切换箭头(古风圆形带书法箭头) -->
      <button class="nav-arrow nav-left" @click="prev" aria-label="上一派">
        <span class="arrow-glyph">‹</span>
        <span class="arrow-ring"></span>
      </button>
      <button class="nav-arrow nav-right" @click="next" aria-label="下一派">
        <span class="arrow-glyph">›</span>
        <span class="arrow-ring"></span>
      </button>

      <!-- === 左:人物立绘 ★ v4 性能修复:5 张全挂 DOM,纯 CSS opacity 切换,0 延迟 === -->
      <div class="portrait-stage" v-if="currentSect">
        <div
          v-for="s in sects"
          :key="s.id"
          class="portrait-frame"
          :class="{
            available: isSelectable(s),
            locked: !isSelectable(s),
            shown: currentSect.id === s.id,
          }"
          :style="{
            '--accent': SECT_META[s.id]?.accent || '#D4A24C',
            '--glow': SECT_META[s.id]?.glow || '#FFE0A3',
          }"
        >
          <div class="frame-outer-ring"></div>
          <div class="frame-inner-edge"></div>
          <div class="corner-deco tl">❖</div>
          <div class="corner-deco tr">❖</div>
          <div class="corner-deco bl">❖</div>
          <div class="corner-deco br">❖</div>

          <!-- 立绘 — 永驻 DOM,浏览器只 decode 一次 -->
          <img
            :src="`/images/sect-portraits/${s.id}.jpg`"
            :alt="s.name"
            class="portrait-img"
            fetchpriority="high"
            decoding="async"
          />

          <div v-if="!isSelectable(s)" class="lock-overlay">
            <div class="lock-seal">封</div>
            <div class="lock-text">灵脉尚未开通</div>
            <div class="lock-sub">期待后续版本</div>
          </div>
          <div v-else class="seal-stamp seal-ok">通</div>
          <div v-if="isSelectable(s)" class="portrait-aura"></div>

          <div class="portrait-banner">
            <div class="banner-bg"></div>
            <div class="banner-inner">
              <div class="banner-sect">
                <SectFlag :sect-id="s.id" :name="s.name" :size="44" :radius="10" />
                <span class="banner-name">{{ s.name }}</span>
              </div>
              <div class="banner-motto">「 {{ SECT_META[s.id]?.motto }} 」</div>
            </div>
          </div>
        </div>
      </div>

      <!-- === 右:重设计信息面板 === -->
      <Transition :name="'info-fade-' + direction" mode="out-in">
        <div v-if="currentSect && !switching" class="info-panel" :key="currentSect.id">

          <!-- ① 大标题区(匾额式) -->
          <div class="plaque">
            <div class="plaque-top-bar"></div>
            <div class="plaque-meta">
              <span class="provider-tag">{{ currentSect.provider_display }}</span>
              <span v-if="!isSelectable(currentSect)" class="status-badge locked">
                <span class="seal-mini">封</span> 灵脉未通
              </span>
              <span v-else class="status-badge ok">
                <span class="seal-mini ok-color">✓</span> 可加入
              </span>
            </div>
            <h1 class="sect-name" :style="{ color: currentMeta.accent, textShadow: `0 0 32px ${currentMeta.glow}` }">
              {{ currentSect.name }}
            </h1>
            <div class="motto-line">
              <span class="motto-dot"></span>
              <span class="motto-text">{{ currentMeta.motto }}</span>
              <span class="motto-dot"></span>
            </div>
            <p class="desc">{{ currentSect.description }}</p>
            <div class="plaque-bottom-bar"></div>
          </div>

          <!-- ② 双栏:雷达图 + 招式卡组 -->
          <div class="dual-row">
            <!-- 雷达图(五维数值) -->
            <div class="card radar-card">
              <h3 class="card-title"><span class="title-deco">◆</span> 五维属性</h3>
              <svg viewBox="0 0 200 200" class="radar" v-if="currentPreview">
                <!-- 4 层环背景 -->
                <polygon
                  v-for="(scale, i) in radarRings"
                  :key="i"
                  :points="ringPath(scale)"
                  class="radar-ring"
                />
                <!-- 5 条轴线 -->
                <line
                  v-for="(a, i) in radarAxes"
                  :key="i"
                  :x1="100" :y1="100" :x2="a.x" :y2="a.y"
                  class="radar-axis"
                />
                <!-- 数据五边形 -->
                <polygon
                  :points="radarDataPath"
                  class="radar-data"
                  :style="{ fill: currentMeta.accent + '40', stroke: currentMeta.accent }"
                />
                <!-- 顶点圆圈 -->
                <circle
                  v-for="(p, i) in radarDataPath.split(' ')"
                  :key="i"
                  :cx="p.split(',')[0]" :cy="p.split(',')[1]"
                  r="3" :fill="currentMeta.glow"
                />
                <!-- 维度标签 -->
                <text
                  v-for="(a, i) in radarAxes"
                  :key="'l'+i"
                  :x="a.lx" :y="a.ly"
                  class="radar-label"
                  text-anchor="middle"
                  dominant-baseline="middle"
                >{{ a.label }}</text>
              </svg>
              <!-- 数值标签 -->
              <div class="radar-values" v-if="currentPreview">
                <span class="rv">HP <strong>{{ currentPreview.initial_stats?.hp }}</strong></span>
                <span class="rv">攻 <strong>{{ currentPreview.initial_stats?.atk }}</strong></span>
                <span class="rv">防 <strong>{{ currentPreview.initial_stats?.def }}</strong></span>
                <span class="rv">速 <strong>{{ currentPreview.initial_stats?.spd }}</strong></span>
                <span class="rv">暴 <strong>{{ Math.round((currentPreview.initial_stats?.crit_rate || 0) * 100) }}%</strong></span>
              </div>
            </div>

            <!-- 招式卡组(扇形抽出) -->
            <div class="card skills-card">
              <h3 class="card-title"><span class="title-deco">⚔</span> 代表招式</h3>
              <div class="skills-deck" v-if="currentPreview">
                <div
                  v-for="(c, i) in (currentPreview.cards_preview || []).slice(0, 3)"
                  :key="c.id"
                  class="skill-card"
                  :style="{
                    '--c': currentMeta.accent,
                    '--i': i,
                  }"
                >
                  <div class="sc-corner-tl"></div>
                  <div class="sc-corner-tr"></div>
                  <div class="sc-icon">{{ c.icon }}</div>
                  <div class="sc-name">{{ c.name }}</div>
                  <div class="sc-cost-bar">
                    <span class="sc-cost">⚡ {{ c.qi_cost }}</span>
                    <span class="sc-power" v-if="c.power">×{{ c.power }}</span>
                  </div>
                  <div class="sc-desc">{{ c.description }}</div>
                  <div class="sc-corner-bl"></div>
                  <div class="sc-corner-br"></div>
                </div>
                <div v-if="!currentPreview.cards_preview?.length" class="skills-empty">
                  招式池待开放
                </div>
              </div>
            </div>
          </div>

          <!-- ③ 门派天赋(徽章/印记) -->
          <div class="card buffs-card" v-if="currentPreview?.buffs?.length">
            <h3 class="card-title"><span class="title-deco">✦</span> 门派天赋</h3>
            <div class="buff-row">
              <div v-for="b in (currentPreview.buffs || []).slice(0, 3)" :key="b.name"
                   class="buff-medal"
                   :style="{ '--c': currentMeta.accent, '--g': currentMeta.glow }">
                <div class="medal-ring"></div>
                <div class="medal-content">
                  <strong class="medal-name">{{ b.name }}</strong>
                  <span class="medal-desc">{{ b.desc }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- ④ 模型梯度(境界进度条) -->
          <div class="card tier-card" v-if="currentPreview?.tier_summary?.length">
            <h3 class="card-title"><span class="title-deco">⚐</span> 灵脉梯度</h3>
            <div class="tier-track">
              <div v-for="(t, i) in currentPreview.tier_summary" :key="t.model"
                   class="tier-node"
                   :style="{ '--c': currentMeta.accent, '--idx': i }">
                <div class="tier-dot"></div>
                <div class="tier-info">
                  <code class="tier-model">{{ t.model }}</code>
                  <span class="tier-cover">{{ t.label }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- ⑤ 宗派背景(古卷展开) -->
          <div class="card scroll-card" v-if="currentPreview?.background_story">
            <div class="scroll-top"></div>
            <h3 class="card-title scroll-title">
              <span class="title-deco">📜</span> 宗派背景
            </h3>
            <p class="story" v-html="currentPreview.background_story.replace(/\*\*([^*]+)\*\*/g, '<em>$1</em>')"></p>
            <div class="scroll-bottom"></div>
          </div>

          <!-- ⑥ 入门按钮(印章风格) -->
          <button class="confirm-btn"
                  :disabled="!isSelectable(currentSect)"
                  :style="{ '--c': currentMeta.accent, '--g': currentMeta.glow }"
                  @click="confirmJoin">
            <span class="btn-bg"></span>
            <span class="btn-flowline"></span>
            <span v-if="isSelectable(currentSect)" class="btn-content">
              <span class="btn-seal">入</span>
              <span class="btn-text">拜入 {{ currentSect.name }} 师门</span>
              <span class="btn-arrow">→</span>
            </span>
            <span v-else class="btn-content disabled">
              <span class="btn-seal locked">封</span>
              <span class="btn-text">灵脉未通,无法拜入</span>
            </span>
          </button>
        </div>
      </Transition>
    </main>

    <!-- 底部 dock -->
    <footer class="dock">
      <div v-for="(s, i) in sects" :key="s.id"
           :class="['dock-item', { active: i === currentIdx, disabled: !isSelectable(s) }]"
           :style="{ '--c': SECT_META[s.id]?.accent }"
           :title="isSelectable(s) ? `点击切到 ${s.name}` : `${s.name} 灵脉未通`"
           @click="pickIdx(i)">
        <img
          :src="dockThumb(s.id)"
          :alt="s.name"
          class="dock-portrait"
          loading="lazy"
          decoding="async"
          @error="(e) => { e.target.style.display = 'none' }"
        />
        <SectFlag class="dock-emoji" :sect-id="s.id" :name="s.name" :size="30" :radius="7" />
        <div class="dock-name">{{ s.name }}</div>
        <div v-if="i === currentIdx" class="dock-indicator"></div>
        <div v-if="!isSelectable(s)" class="dock-lock">🔒</div>
      </div>
    </footer>

    <!-- 操作提示 -->
    <div class="hint">
      ← → 切换 · Enter 确认 · 点击底部头像直跳
    </div>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   ★ 选派页设计语言:国风金线 + 印章 + 卷轴 + 现代信息卡
   参考:王者英雄选择 / 原神角色页 / 逆水寒选派
   ═══════════════════════════════════════════════════════════ */

.cs-page {
  position: fixed; inset: 0;
  min-height: 100vh;
  overflow: hidden;
  color: #f0e8d0;
  font-family: 'STKaiti', 'KaiTi', 'Source Han Serif SC', serif;
}

/* ════ 飘浮金色尘埃(全局氛围)════ */
.dust-layer {
  position: absolute; inset: 0;
  pointer-events: none;
  z-index: 1;
}
.dust {
  position: absolute;
  width: 3px; height: 3px;
  border-radius: 50%;
  background: radial-gradient(circle, #FFE0A3, transparent 70%);
  box-shadow: 0 0 4px #FFE0A3;
  opacity: 0;
  animation: dust-float linear infinite;
}
@keyframes dust-float {
  0%   { opacity: 0; transform: translate(0, 20px) scale(0.5); }
  20%  { opacity: 0.9; }
  80%  { opacity: 0.7; }
  100% { opacity: 0; transform: translate(20px, -200px) scale(1.2); }
}

/* ════ 顶部 brand(横向匾额式)════ */
.brand {
  position: relative; z-index: 10;
  display: flex; gap: 18px; align-items: center;
  padding: 12px 36px;
  background:
    linear-gradient(180deg, rgba(0,0,0,0.7), rgba(0,0,0,0.35));
  border-bottom: 2px solid;
  border-image: linear-gradient(90deg,
    transparent, rgba(212,162,76,0.6), rgba(212,162,76,0.9),
    rgba(212,162,76,0.6), transparent) 1;
  backdrop-filter: blur(12px);
}
.brand-sub {
  margin-left: auto;
  color: #D4A24C;
  font-size: 13px;
  letter-spacing: 6px;
  text-shadow: 0 0 12px rgba(212,162,76,0.4);
}

/* ════ 主区:两栏 grid ════ */
.main {
  position: relative; z-index: 5;
  display: grid;
  grid-template-columns: minmax(380px, 0.85fr) minmax(460px, 1fr);
  gap: 48px;
  padding: 20px 80px 30px 80px;
  align-items: start;
  min-height: calc(100vh - 180px);
}
@media (max-width: 980px) {
  .main { grid-template-columns: 1fr; gap: 24px; padding: 20px; }
}

/* ════ 左右切换箭头(金色官帽圆环)════ */
.nav-arrow {
  position: absolute;
  top: 46%;
  transform: translateY(-50%);
  width: 60px; height: 60px;
  background: radial-gradient(circle,
    rgba(20, 15, 8, 0.95) 0%,
    rgba(40, 28, 12, 0.95) 100%);
  border: 2px solid #D4A24C;
  border-radius: 50%;
  color: #FFE0A3;
  cursor: pointer;
  z-index: 20;
  font-size: 0;  /* 用内部 span 控制 */
  display: flex; align-items: center; justify-content: center;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow:
    0 0 0 4px rgba(0,0,0,0.5),
    0 0 24px rgba(212,162,76,0.35),
    inset 0 0 12px rgba(212,162,76,0.2);
}
.arrow-glyph {
  font-size: 40px; line-height: 1;
  font-family: 'STKaiti', serif;
  text-shadow: 0 0 12px rgba(255,224,163,0.8);
  position: relative; z-index: 2;
}
.arrow-ring {
  position: absolute; inset: -3px;
  border-radius: 50%;
  border: 1px dashed rgba(212,162,76,0.5);
  animation: arrow-spin 12s linear infinite;
}
@keyframes arrow-spin { to { transform: rotate(360deg); } }
.nav-arrow:hover {
  background: radial-gradient(circle, #5a3a14 0%, #2a1808 100%);
  transform: translateY(-50%) scale(1.15);
  box-shadow:
    0 0 0 4px rgba(0,0,0,0.6),
    0 0 36px rgba(255,224,163,0.7),
    inset 0 0 20px rgba(255,224,163,0.4);
}
.nav-arrow:active { transform: translateY(-50%) scale(0.95); }
.nav-left  { left: 20px; }
.nav-right { left: calc(46% - 10px); }
@media (max-width: 980px) {
  .nav-left  { left: 10px; }
  .nav-right { left: auto; right: 10px; }
}

/* ═══════════════════════════════════════════════════════
   ★ 立绘框(金色镂空 + 4 角云纹 + 印章 + 匾额)
   ═══════════════════════════════════════════════════════ */
.portrait-stage {
  position: relative;
  display: flex; align-items: center; justify-content: center;
  min-height: 580px;
  padding: 20px 0;
  align-self: center;  /* ★ 在 grid 中垂直居中,不随 info-panel 顶部对齐 */
}
/* ★ v4:5 张立绘叠加在同一位置,通过 opacity 切换(纯 GPU,0 延迟) */
.portrait-stage .portrait-frame {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%) scale(0.94);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.22s ease, transform 0.22s cubic-bezier(0.34, 1.4, 0.64, 1);
  /* 关键:GPU 提示 */
  will-change: opacity, transform;
}
.portrait-stage .portrait-frame.shown {
  opacity: 1;
  transform: translate(-50%, -50%) scale(1);
  pointer-events: auto;
  z-index: 2;
}
.portrait-frame {
  position: relative;
  width: min(440px, 92%);
  aspect-ratio: 2 / 3;
  border-radius: 12px;
  overflow: hidden;
  /* 外层金色光晕 */
  box-shadow:
    0 30px 80px rgba(0, 0, 0, 0.85),
    0 0 0 1px rgba(212,162,76,0.4),
    0 0 80px color-mix(in srgb, var(--accent, #D4A24C) 40%, transparent),
    inset 0 0 60px rgba(0,0,0,0.4);
  animation: frame-breathe 6s ease-in-out infinite;
}
@keyframes frame-breathe {
  0%, 100% { transform: translate(-50%, -50%) scale(1) translateY(0); }
  50%      { transform: translate(-50%, -50%) scale(1) translateY(-6px); }
}

/* 外层装饰金线环 */
.frame-outer-ring {
  position: absolute; inset: -8px;
  border: 1.5px solid color-mix(in srgb, var(--accent, #D4A24C) 70%, transparent);
  border-radius: 16px;
  pointer-events: none;
  z-index: 3;
  animation: outer-ring-glow 4s ease-in-out infinite;
}
@keyframes outer-ring-glow {
  0%, 100% { box-shadow: 0 0 12px color-mix(in srgb, var(--accent) 30%, transparent); }
  50%      { box-shadow: 0 0 28px color-mix(in srgb, var(--accent) 70%, transparent); }
}
.frame-inner-edge {
  position: absolute; inset: 4px;
  border: 1px dashed rgba(212,162,76,0.35);
  border-radius: 8px;
  pointer-events: none;
  z-index: 3;
}

/* 4 角云纹装饰 */
.corner-deco {
  position: absolute;
  font-size: 22px;
  color: var(--glow, #FFE0A3);
  text-shadow: 0 0 12px var(--accent);
  z-index: 4;
  pointer-events: none;
  opacity: 0.85;
}
.corner-deco.tl { top: -2px; left: -2px; transform: rotate(-45deg); }
.corner-deco.tr { top: -2px; right: -2px; transform: rotate(45deg); }
.corner-deco.bl { bottom: -2px; left: -2px; transform: rotate(-135deg); }
.corner-deco.br { bottom: -2px; right: -2px; transform: rotate(135deg); }

.portrait-frame.locked {
  filter: brightness(0.85);
  animation: none;
}
.portrait-frame.locked .frame-outer-ring,
.portrait-frame.locked .corner-deco {
  filter: grayscale(0.8);
  opacity: 0.4;
}

.portrait-img {
  width: 100%; height: 100%;
  object-fit: cover;
  object-position: center top;
  display: block;
  transition: filter 0.5s, transform 8s;
  animation: portrait-zoom 20s ease-in-out infinite alternate;
}
@keyframes portrait-zoom {
  0%   { transform: scale(1); }
  100% { transform: scale(1.05); }
}
.portrait-frame.locked .portrait-img {
  filter: grayscale(1) brightness(0.32) contrast(1.05);
}

/* 选中态光晕(只在 available 时显示) */
.portrait-aura {
  position: absolute; inset: 0;
  pointer-events: none;
  background:
    radial-gradient(ellipse at top, color-mix(in srgb, var(--glow) 18%, transparent) 0%, transparent 50%),
    radial-gradient(ellipse at bottom, color-mix(in srgb, var(--accent) 18%, transparent) 0%, transparent 60%);
  mix-blend-mode: screen;
  z-index: 2;
}

/* 印章(可选派/不可选派) */
.seal-stamp {
  position: absolute;
  top: 14px; right: 14px;
  width: 52px; height: 52px;
  border-radius: 50%;
  background: radial-gradient(circle, #C03F3F, #8B1A1A);
  border: 3px double rgba(255, 220, 200, 0.85);
  color: #FFE0E0;
  display: flex; align-items: center; justify-content: center;
  font-family: 'STKaiti', serif;
  font-size: 28px;
  font-weight: 700;
  transform: rotate(-15deg);
  box-shadow:
    0 4px 16px rgba(0, 0, 0, 0.7),
    inset 0 0 8px rgba(0, 0, 0, 0.5);
  z-index: 5;
  letter-spacing: 0;
}
.seal-stamp.seal-ok {
  background: radial-gradient(circle, #D4A24C, #8B5A1A);
  color: #FFE0A3;
  border-color: rgba(255, 224, 163, 0.7);
}

/* 锁覆盖 */
.lock-overlay {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 14px;
  background:
    radial-gradient(ellipse at center, rgba(0,0,0,0.55), rgba(0,0,0,0.85));
  backdrop-filter: blur(4px);
  pointer-events: none;
  z-index: 4;
}
.lock-seal {
  width: 110px; height: 110px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(80, 20, 20, 0.95), rgba(20, 4, 4, 0.95));
  border: 4px double rgba(255, 100, 100, 0.6);
  color: #FF8888;
  display: flex; align-items: center; justify-content: center;
  font-family: 'STKaiti', serif;
  font-size: 60px;
  font-weight: 700;
  transform: rotate(-12deg);
  text-shadow: 0 2px 8px rgba(255, 50, 50, 0.6);
  box-shadow: 0 0 24px rgba(192, 63, 63, 0.4);
}
.lock-text {
  color: #ddd;
  font-size: 20px;
  letter-spacing: 6px;
  font-family: 'STKaiti', serif;
}
.lock-sub {
  color: #888;
  font-size: 12px;
  letter-spacing: 4px;
}

/* 底部「匾额」铭牌 */
.portrait-banner {
  position: absolute; left: 0; right: 0; bottom: 0;
  padding: 0;
  z-index: 5;
}
.banner-bg {
  position: absolute; inset: 0;
  background:
    linear-gradient(180deg, transparent, rgba(0,0,0,0.92) 60%),
    linear-gradient(180deg, transparent, color-mix(in srgb, var(--accent) 40%, transparent));
  pointer-events: none;
}
.banner-inner {
  position: relative;
  padding: 60px 24px 20px;
  text-align: center;
  border-top: 1px solid color-mix(in srgb, var(--accent) 50%, transparent);
}
.banner-inner::before {
  content: '';
  position: absolute; top: -1px; left: 50%;
  transform: translateX(-50%);
  width: 60%; height: 1px;
  background: linear-gradient(90deg,
    transparent, var(--glow), transparent);
  box-shadow: 0 0 12px var(--glow);
}
.banner-sect {
  display: flex; gap: 12px; align-items: center; justify-content: center;
  margin-bottom: 4px;
}
.banner-emoji {
  font-size: 28px;
  filter: drop-shadow(0 0 8px var(--glow));
}
.banner-name {
  font-family: 'STKaiti', serif;
  font-size: 30px;
  font-weight: 600;
  letter-spacing: 6px;
  color: var(--glow);
  text-shadow:
    0 0 12px color-mix(in srgb, var(--accent) 80%, transparent),
    0 2px 4px rgba(0, 0, 0, 0.8);
}
.banner-motto {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.85);
  letter-spacing: 4px;
  font-style: italic;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.9);
}

/* ═══════════════════════════════════════════════════════
   ★ 右侧信息面板
   ═══════════════════════════════════════════════════════ */
.info-panel {
  display: flex; flex-direction: column;
  gap: 14px;
  max-height: calc(100vh - 160px);
  overflow-y: auto;
  padding: 4px 6px 20px;
  scrollbar-width: thin;
  scrollbar-color: rgba(212,162,76,0.4) transparent;
}
.info-panel::-webkit-scrollbar { width: 6px; }
.info-panel::-webkit-scrollbar-thumb { background: rgba(212,162,76,0.4); border-radius: 3px; }

/* ════ 卡片基类(国风金边)════ */
.card {
  position: relative;
  background:
    linear-gradient(180deg, rgba(20,15,8,0.85), rgba(8,5,2,0.92));
  border: 1px solid rgba(212,162,76,0.25);
  border-radius: 10px;
  padding: 14px 18px;
  backdrop-filter: blur(12px);
  box-shadow:
    0 4px 16px rgba(0,0,0,0.5),
    inset 0 1px 0 rgba(255,255,255,0.03);
}
.card::before {
  /* 顶部细金线 */
  content: '';
  position: absolute; top: 0; left: 10%; right: 10%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(212,162,76,0.6), transparent);
}
.card-title {
  font-size: 13px;
  color: #D4A24C;
  letter-spacing: 4px;
  margin: 0 0 12px;
  font-family: 'STKaiti', serif;
  display: flex; align-items: center; gap: 6px;
}
.title-deco {
  color: var(--accent, #D4A24C);
  text-shadow: 0 0 8px var(--accent, #D4A24C);
  font-size: 14px;
}

/* ════ ① 大标题匾额 ════ */
.plaque {
  position: relative;
  background:
    radial-gradient(ellipse at top, rgba(212,162,76,0.10), transparent 60%),
    linear-gradient(180deg, rgba(20,15,8,0.9), rgba(8,5,2,0.95));
  border: 1px solid rgba(212,162,76,0.4);
  border-radius: 10px;
  padding: 18px 24px;
  text-align: center;
}
.plaque-top-bar,
.plaque-bottom-bar {
  position: absolute; left: 8%; right: 8%; height: 2px;
  background: linear-gradient(90deg,
    transparent, #D4A24C 30%, #FFE0A3 50%, #D4A24C 70%, transparent);
  box-shadow: 0 0 8px rgba(212,162,76,0.6);
}
.plaque-top-bar { top: 6px; }
.plaque-bottom-bar { bottom: 6px; }
.plaque-meta {
  display: flex; gap: 10px; justify-content: center; align-items: center;
  margin-bottom: 6px;
}
.provider-tag {
  background: rgba(127,199,232,0.08);
  border: 1px solid rgba(127,199,232,0.25);
  color: #aac8e0;
  padding: 3px 12px;
  border-radius: 12px;
  font-size: 11px;
  letter-spacing: 2px;
  font-family: system-ui, sans-serif;
}
.status-badge {
  padding: 3px 12px;
  border-radius: 12px;
  font-size: 11px;
  letter-spacing: 2px;
  display: inline-flex; align-items: center; gap: 4px;
}
.status-badge.ok {
  background: rgba(82,183,136,0.16);
  border: 1px solid rgba(82,183,136,0.4);
  color: #95D5B2;
}
.status-badge.locked {
  background: rgba(127,127,127,0.15);
  border: 1px solid rgba(127,127,127,0.3);
  color: #888;
}
.seal-mini {
  display: inline-flex; align-items: center; justify-content: center;
  width: 16px; height: 16px;
  background: #C03F3F;
  color: #fff;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 700;
  font-family: 'STKaiti', serif;
  transform: rotate(-8deg);
}
.seal-mini.ok-color {
  background: #52B788;
}

.sect-name {
  margin: 4px 0 6px;
  font-family: 'STKaiti', serif;
  font-size: 42px;
  letter-spacing: 14px;
  font-weight: 500;
  padding-left: 14px;  /* 中文字距调正 */
  background: linear-gradient(180deg, currentColor, color-mix(in srgb, currentColor 50%, #fff 50%));
  -webkit-background-clip: text;
  background-clip: text;
}
.motto-line {
  display: flex; align-items: center; justify-content: center; gap: 12px;
  margin-bottom: 10px;
}
.motto-dot {
  width: 5px; height: 5px;
  background: #D4A24C;
  border-radius: 50%;
  box-shadow: 0 0 6px #D4A24C;
}
.motto-text {
  font-size: 13px;
  color: #ccc;
  font-style: italic;
  letter-spacing: 4px;
  font-family: 'STKaiti', serif;
}
.desc {
  margin: 8px 0 0;
  font-size: 13px;
  color: #bbb;
  line-height: 1.9;
  letter-spacing: 1px;
}

/* ════ ② 双栏:雷达图 + 招式卡组 ════ */
.dual-row {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 12px;
}
@media (max-width: 1100px) { .dual-row { grid-template-columns: 1fr; } }

/* ── 雷达图 ── */
.radar-card {
  display: flex; flex-direction: column;
  align-items: center;
}
.radar {
  width: 200px; height: 200px;
  filter: drop-shadow(0 0 12px color-mix(in srgb, var(--accent, #D4A24C) 30%, transparent));
}
.radar-ring {
  fill: none;
  stroke: rgba(212,162,76,0.18);
  stroke-width: 1;
}
.radar-axis {
  stroke: rgba(212,162,76,0.25);
  stroke-width: 1;
  stroke-dasharray: 2 3;
}
.radar-data {
  stroke-width: 2;
  filter: drop-shadow(0 0 6px currentColor);
  animation: radar-fade 0.6s ease-out;
}
@keyframes radar-fade {
  from { opacity: 0; transform-origin: 100px 100px; transform: scale(0.6); }
  to   { opacity: 1; transform: scale(1); }
}
.radar-label {
  fill: #D4A24C;
  font-size: 12px;
  font-family: 'STKaiti', serif;
  letter-spacing: 1px;
}
.radar-values {
  display: flex; flex-wrap: wrap; gap: 8px;
  justify-content: center;
  margin-top: 6px;
  font-size: 11px;
}
.rv {
  background: rgba(212,162,76,0.08);
  border: 1px solid rgba(212,162,76,0.2);
  padding: 2px 8px;
  border-radius: 4px;
  color: #aaa;
  letter-spacing: 1px;
}
.rv strong { color: #FFE0A3; margin-left: 3px; }

/* ── 招式卡组(扇形) ── */
.skills-card { padding: 14px 14px 16px; }
.skills-deck {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.skill-card {
  position: relative;
  background:
    linear-gradient(180deg, rgba(40,28,12,0.85), rgba(20,12,4,0.95));
  border: 1px solid color-mix(in srgb, var(--c, #D4A24C) 50%, transparent);
  border-radius: 8px;
  padding: 10px 8px;
  text-align: center;
  display: flex; flex-direction: column; gap: 4px;
  transition: all 0.25s;
  cursor: default;
  overflow: hidden;
  /* 入场扇形动画 */
  animation: deal-card 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) backwards;
  animation-delay: calc(var(--i) * 0.08s);
}
@keyframes deal-card {
  from { opacity: 0; transform: translateY(20px) rotate(calc(-5deg + var(--i) * 5deg)); }
  to   { opacity: 1; transform: translateY(0) rotate(0); }
}
.skill-card:hover {
  transform: translateY(-4px) scale(1.03);
  border-color: var(--c, #FFE0A3);
  box-shadow: 0 8px 24px color-mix(in srgb, var(--c) 30%, transparent);
}
.sc-corner-tl, .sc-corner-tr, .sc-corner-bl, .sc-corner-br {
  position: absolute;
  width: 8px; height: 8px;
  border: 1px solid var(--c, #D4A24C);
}
.sc-corner-tl { top: 3px; left: 3px; border-right: 0; border-bottom: 0; }
.sc-corner-tr { top: 3px; right: 3px; border-left: 0; border-bottom: 0; }
.sc-corner-bl { bottom: 3px; left: 3px; border-right: 0; border-top: 0; }
.sc-corner-br { bottom: 3px; right: 3px; border-left: 0; border-top: 0; }
.sc-icon {
  font-size: 28px;
  margin: 4px 0 2px;
  filter: drop-shadow(0 0 6px var(--c, #D4A24C));
}
.sc-name {
  font-size: 13px;
  color: var(--c, #FFE0A3);
  font-weight: 600;
  letter-spacing: 1px;
  font-family: 'STKaiti', serif;
}
.sc-cost-bar {
  display: flex; gap: 4px; justify-content: center;
  font-size: 10px;
  margin: 2px 0;
}
.sc-cost { color: #7FC7E8; }
.sc-power { color: #FF8888; font-weight: 600; }
.sc-desc {
  font-size: 10px;
  color: #888;
  line-height: 1.4;
  margin-top: 2px;
}
.skills-empty {
  grid-column: 1 / -1;
  color: #666;
  font-size: 12px;
  text-align: center;
  padding: 20px;
}

/* ════ ③ 门派天赋(徽章) ════ */
.buff-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
}
.buff-medal {
  position: relative;
  background:
    radial-gradient(ellipse at top, color-mix(in srgb, var(--c) 15%, transparent), transparent 70%),
    linear-gradient(180deg, rgba(20,15,8,0.85), rgba(8,5,2,0.92));
  border: 1px solid color-mix(in srgb, var(--c) 50%, transparent);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex; gap: 10px; align-items: flex-start;
  transition: all 0.3s;
}
.buff-medal:hover {
  border-color: var(--g);
  box-shadow: 0 0 16px color-mix(in srgb, var(--c) 40%, transparent);
  transform: translateY(-2px);
}
.medal-ring {
  flex-shrink: 0;
  width: 28px; height: 28px;
  border-radius: 50%;
  background:
    radial-gradient(circle, color-mix(in srgb, var(--c) 50%, transparent), transparent 70%),
    radial-gradient(circle at 30% 30%, var(--g), var(--c));
  border: 2px solid var(--c);
  position: relative;
  box-shadow:
    inset 0 0 6px rgba(0,0,0,0.4),
    0 0 12px color-mix(in srgb, var(--c) 50%, transparent);
}
.medal-ring::after {
  content: '✦';
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  color: #FFE0A3;
  font-size: 14px;
  text-shadow: 0 0 4px rgba(0,0,0,0.6);
}
.medal-content { display: flex; flex-direction: column; gap: 2px; flex: 1; }
.medal-name {
  font-size: 12px;
  letter-spacing: 1px;
  font-family: 'STKaiti', serif;
  color: var(--c);
}
.medal-desc { font-size: 10px; color: #aaa; line-height: 1.5; }

/* ════ ④ 灵脉梯度(进度条) ════ */
.tier-track {
  position: relative;
  padding: 10px 4px 4px;
}
.tier-track::before {
  /* 主轴线 */
  content: '';
  position: absolute;
  top: 22px; left: 4px; right: 4px; height: 2px;
  background: linear-gradient(90deg,
    rgba(212,162,76,0.6), rgba(255,224,163,0.8), rgba(212,162,76,0.6));
  border-radius: 1px;
  z-index: 0;
}
.tier-track {
  display: flex;
  justify-content: space-between;
  gap: 6px;
}
.tier-node {
  position: relative;
  display: flex; flex-direction: column; align-items: center;
  gap: 4px;
  flex: 1;
  text-align: center;
  z-index: 1;
}
.tier-dot {
  width: 18px; height: 18px;
  border-radius: 50%;
  background: radial-gradient(circle, var(--c) 0%, color-mix(in srgb, var(--c) 50%, #000) 100%);
  border: 2px solid color-mix(in srgb, var(--c) 70%, #fff 30%);
  box-shadow:
    0 0 12px color-mix(in srgb, var(--c) 60%, transparent),
    inset 0 0 4px rgba(0,0,0,0.4);
  position: relative;
  z-index: 2;
}
.tier-info { display: flex; flex-direction: column; gap: 2px; }
.tier-model {
  font-size: 10px;
  color: #7FC7E8;
  background: rgba(127,199,232,0.08);
  border-radius: 3px;
  padding: 1px 5px;
  font-family: 'SF Mono', monospace;
}
.tier-cover { font-size: 10px; color: #888; letter-spacing: 1px; }

/* ════ ⑤ 卷轴宗派背景 ════ */
.scroll-card {
  background:
    linear-gradient(180deg,
      rgba(40,28,12,0.5) 0%,
      rgba(18,12,6,0.85) 8%,
      rgba(18,12,6,0.85) 92%,
      rgba(40,28,12,0.5) 100%);
  border: 1px solid rgba(212,162,76,0.3);
  padding: 24px 22px;
  position: relative;
}
.scroll-top, .scroll-bottom {
  position: absolute;
  left: -4px; right: -4px;
  height: 10px;
  background:
    linear-gradient(90deg, #5a3a14, #D4A24C 20%, #FFE0A3 50%, #D4A24C 80%, #5a3a14);
  border-radius: 5px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.7);
  z-index: 2;
}
.scroll-top { top: -5px; }
.scroll-bottom { bottom: -5px; }
.scroll-title {
  font-size: 14px !important;
  margin-bottom: 14px !important;
}
.story {
  margin: 0;
  font-size: 13px;
  line-height: 2.1;
  color: #d4c8a8;
  letter-spacing: 1.5px;
  font-family: 'STKaiti', 'KaiTi', 'Source Han Serif SC', serif;
  text-align: justify;
  text-indent: 2em;  /* 段首缩进 */
}
.story :deep(em) {
  font-style: normal;
  color: #fff;
  background: linear-gradient(180deg, transparent 70%, rgba(212,162,76,0.5) 70%);
  padding: 0 2px;
  font-weight: 600;
}

/* ═══════════════════════════════════════════════════════
   ★ ⑥ 印章式入门按钮(大、有质感、有动效)
   ═══════════════════════════════════════════════════════ */
.confirm-btn {
  position: relative;
  width: 100%;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
  margin-top: 4px;
  overflow: hidden;
  border-radius: 12px;
  isolation: isolate;
}
.btn-bg {
  position: absolute; inset: 0;
  background:
    radial-gradient(ellipse at top left, color-mix(in srgb, var(--g) 30%, transparent), transparent 60%),
    linear-gradient(135deg, var(--c, #D4A24C), color-mix(in srgb, var(--c, #D4A24C) 60%, #5a3a14));
  border: 2px solid var(--g, #FFE0A3);
  border-radius: 12px;
  box-shadow:
    0 6px 24px color-mix(in srgb, var(--c) 40%, transparent),
    inset 0 1px 0 rgba(255,255,255,0.3),
    inset 0 -2px 0 rgba(0,0,0,0.3);
  transition: all 0.3s;
}
.btn-flowline {
  position: absolute;
  top: 0; left: -100%;
  width: 60%; height: 100%;
  background: linear-gradient(90deg,
    transparent, rgba(255,255,255,0.45), transparent);
  animation: btn-shine 3s ease-in-out infinite;
  z-index: 1;
}
@keyframes btn-shine {
  0%, 70%, 100% { left: -100%; }
  35% { left: 150%; }
}
.btn-content {
  position: relative;
  z-index: 2;
  display: flex; align-items: center; justify-content: center;
  gap: 14px;
  padding: 16px 24px;
  color: #1a1a2e;
  font-family: 'STKaiti', serif;
  font-weight: 700;
  letter-spacing: 6px;
  font-size: 17px;
  text-shadow: 0 1px 0 rgba(255,255,255,0.3);
}
.btn-seal {
  width: 38px; height: 38px;
  border-radius: 50%;
  background: radial-gradient(circle, #C03F3F, #6B0F0F);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px;
  font-weight: 700;
  transform: rotate(-10deg);
  border: 2px double rgba(255, 220, 200, 0.7);
  box-shadow: 0 2px 8px rgba(0,0,0,0.5);
  text-shadow: 0 1px 2px rgba(0,0,0,0.4);
}
.btn-seal.locked {
  background: radial-gradient(circle, #555, #222);
}
.btn-text { white-space: nowrap; }
.btn-arrow {
  font-size: 22px;
  font-weight: 400;
  animation: btn-arrow 1.2s ease-in-out infinite;
}
@keyframes btn-arrow {
  0%, 100% { transform: translateX(0); }
  50%      { transform: translateX(6px); }
}
.confirm-btn:hover .btn-bg {
  transform: translateY(-3px);
  box-shadow: 0 12px 36px color-mix(in srgb, var(--c) 60%, transparent),
              inset 0 1px 0 rgba(255,255,255,0.5);
}
.confirm-btn:active .btn-bg { transform: translateY(0); }
.confirm-btn:disabled { cursor: not-allowed; }
.confirm-btn:disabled .btn-bg {
  background: linear-gradient(135deg, #555, #2a2a2a);
  border-color: rgba(255,255,255,0.1);
  box-shadow: none;
}
.confirm-btn:disabled .btn-content {
  color: #888;
}
.confirm-btn:disabled .btn-flowline { display: none; }

/* ═══════════════════════════════════════════════════════
   ★ 切换过渡(立绘飞入飞出 + 信息淡入)
   ═══════════════════════════════════════════════════════ */
/* ★ v3 切换大幅加速 — 220ms enter / 120ms leave,去掉 blur 节省 GPU */
.portrait-fade-right-enter-active,
.portrait-fade-left-enter-active,
.info-fade-right-enter-active,
.info-fade-left-enter-active {
  transition: all 0.22s cubic-bezier(0.34, 1.4, 0.64, 1);
}
.portrait-fade-right-leave-active,
.portrait-fade-left-leave-active,
.info-fade-right-leave-active,
.info-fade-left-leave-active {
  transition: all 0.12s;
}
.portrait-fade-right-enter-from { opacity: 0; transform: translateX(60px) scale(0.96); }
.portrait-fade-right-leave-to   { opacity: 0; transform: translateX(-40px) scale(0.96); }
.portrait-fade-left-enter-from  { opacity: 0; transform: translateX(-60px) scale(0.96); }
.portrait-fade-left-leave-to    { opacity: 0; transform: translateX(40px) scale(0.96); }
.info-fade-right-enter-from     { opacity: 0; transform: translateX(20px); }
.info-fade-right-leave-to       { opacity: 0; transform: translateX(-20px); }
.info-fade-left-enter-from      { opacity: 0; transform: translateX(-20px); }
.info-fade-left-leave-to        { opacity: 0; transform: translateX(20px); }

/* ═══════════════════════════════════════════════════════
   ★ 底部 Dock(立体感升级)
   ═══════════════════════════════════════════════════════ */
.dock {
  position: fixed;
  bottom: 20px; left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 12px;
  padding: 10px 22px 14px;
  background:
    linear-gradient(180deg, rgba(15,10,4,0.85), rgba(8,5,2,0.95));
  border: 1px solid rgba(212,162,76,0.35);
  border-radius: 60px;
  backdrop-filter: blur(16px);
  z-index: 30;
  box-shadow:
    0 12px 36px rgba(0, 0, 0, 0.7),
    inset 0 1px 0 rgba(255,255,255,0.05);
}
.dock::before {
  content: '';
  position: absolute; top: -1px; left: 10%; right: 10%;
  height: 1px;
  background: linear-gradient(90deg,
    transparent, rgba(212,162,76,0.6), transparent);
}
.dock-item {
  position: relative;
  display: flex; flex-direction: column; align-items: center;
  padding: 4px 8px 6px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
  min-width: 64px;
  overflow: visible;
}
.dock-item:hover { background: rgba(255,255,255,0.04); }
.dock-item.active {
  background:
    radial-gradient(ellipse at top, color-mix(in srgb, var(--c) 20%, transparent), transparent 70%);
  transform: translateY(-12px) scale(1.22);
}
.dock-item.active::before {
  /* 选中态匾额顶光 */
  content: '';
  position: absolute;
  top: -6px; left: 50%;
  transform: translateX(-50%);
  width: 50%; height: 3px;
  background: var(--c);
  border-radius: 2px;
  box-shadow: 0 0 12px var(--c);
}
.dock-item.disabled {
  opacity: 0.5;
  filter: grayscale(0.8);
  cursor: not-allowed;
}
.dock-portrait {
  width: 44px; height: 64px;
  object-fit: cover;
  object-position: center top;
  border-radius: 5px;
  margin-bottom: 3px;
  border: 1px solid rgba(255,255,255,0.1);
}
.dock-item.active .dock-portrait {
  border-color: var(--c);
  box-shadow: 0 0 12px color-mix(in srgb, var(--c) 50%, transparent);
}
.dock-emoji {
  font-size: 14px;
  position: absolute; top: 0; right: 2px;
}
.dock-name {
  font-size: 10px;
  color: #aaa;
  letter-spacing: 1px;
  white-space: nowrap;
  font-family: 'STKaiti', serif;
}
.dock-item.active .dock-name {
  color: var(--c);
  font-weight: 600;
  text-shadow: 0 0 6px var(--c);
}
.dock-indicator {
  position: absolute;
  bottom: -10px; left: 50%;
  transform: translateX(-50%);
  width: 8px; height: 8px;
  background: var(--c);
  border-radius: 50%;
  box-shadow: 0 0 16px var(--c);
  animation: indicator-pulse 1.5s ease-in-out infinite;
}
@keyframes indicator-pulse {
  0%, 100% { opacity: 0.7; transform: translateX(-50%) scale(1); }
  50%      { opacity: 1; transform: translateX(-50%) scale(1.3); }
}
.dock-lock {
  position: absolute;
  top: 2px; left: 2px;
  font-size: 11px;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.8));
}

.hint {
  position: fixed;
  bottom: 110px; left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  color: #666;
  letter-spacing: 4px;
  z-index: 10;
  font-family: 'SF Mono', monospace;
  background: rgba(0,0,0,0.4);
  padding: 4px 12px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.04);
}
</style>
