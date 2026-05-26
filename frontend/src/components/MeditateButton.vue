<!--
  MeditateButton.vue — 打坐按钮(无冷却 · 连击成瘾 · 数字飞溅)

  设计理念:
  - 无冷却,每次点击恢复 1% HP/QI 并增加疲劳;疲劳由下一轮清零
  - 3s 内连续点击 → 连击 streak 递增,倍率递增
  - 浮动数字效果 + 连击里程碑特效
  - 首次打坐引导浮窗
-->
<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { characterApi, cultivationApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'

const game = useGameStore()
const animating = ref(false)
const streak = ref(0)
const mult = ref(1)
const floatingNums = ref([])   // [{ id, text, type, x, y }]
const showGuide = ref(false)
const milestone = ref(null)
const milestoneShow = ref(false)
const showTranceAction = ref(false)
let floatId = 0
let milestoneTimer = null

// 首次引导判定
onMounted(() => {
  const guided = localStorage.getItem('meditate_guided')
  if (!guided) {
    showGuide.value = true
  }
})

// 连击等级 → 视觉状态
const streakTier = computed(() => {
  if (streak.value >= 50) return 'transcend'  // 金色 + 粒子
  if (streak.value >= 20) return 'golden'     // 金色光晕
  if (streak.value >= 10) return 'blazing'    // 橙色烈焰
  if (streak.value >= 5) return 'warm'        // 淡黄温暖
  return 'idle'
})

// 格式化数字(万/亿)
function formatNum(n) {
  if (n >= 100000000) return (n / 100000000).toFixed(1) + '亿'
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  return n.toString()
}

// 添加浮动数字
function addFloat(text, type) {
  const id = ++floatId
  // 随机偏移让数字不重叠
  const x = -30 + Math.random() * 60
  const y = -10 + Math.random() * 20
  floatingNums.value.push({ id, text, type, x, y })
  // 1.2s 后移除
  setTimeout(() => {
    floatingNums.value = floatingNums.value.filter(f => f.id !== id)
  }, 1200)
}

async function meditate() {
  // 关闭首次引导
  if (showGuide.value) {
    showGuide.value = false
    localStorage.setItem('meditate_guided', '1')
  }

  animating.value = true
  try {
    const { data } = await characterApi.meditate()

    // 更新连击状态
    streak.value = data.streak
    mult.value = data.mult

    // 浮动数字
    if (data.heal > 0) addFloat(`+${formatNum(data.heal)}`, 'hp')
    if (data.qi_gain > 0) addFloat(`+${formatNum(data.qi_gain)}`, 'qi')
    if (data.fatigue_gain > 0) addFloat(`+${data.fatigue_gain}`, 'fatigue')
    else if (data.fatigue_full) addFloat('疲劳已满', 'fatigue')
    else if (data.fatigue_relief > 0) addFloat(`-${data.fatigue_relief}`, 'fatigue')
    showTranceAction.value = !!data.can_enter_trance

    // 里程碑
    if (data.milestone) {
      milestone.value = data.milestone
      milestoneShow.value = true
      if (milestoneTimer) clearTimeout(milestoneTimer)
      milestoneTimer = setTimeout(() => {
        milestoneShow.value = false
      }, 2500)
    }

    // 更新 store(轻量刷新,不调 me 接口)
    game.patchCharacter({
      hp: data.hp,
      max_hp: data.max_hp,
      qi: data.qi,
      max_qi: data.max_qi,
      fatigue: data.fatigue,
      exp: data.exp,
      level: data.level,
      realm: data.realm,
      realm_name: data.realm_name,
    })
  } catch (e) {
    addFloat('失败', 'error')
  } finally {
    setTimeout(() => { animating.value = false }, 150)
  }
}

async function enterTrance() {
  try {
    await cultivationApi.createTask('meditate_inner', { theme: '灵台生墨,入定成章' })
    addFloat('内景章入墨炉', 'levelup')
    showTranceAction.value = false
  } catch (e) {
    addFloat('入定失败', 'error')
  }
}

async function longRetreat() {
  try {
    await cultivationApi.createTask('retreat_long', { theme: '墨炉长明,闭关续写', expected_tokens: 1800 })
    addFloat('闭关章入墨炉', 'levelup')
    showTranceAction.value = false
  } catch (e) {
    addFloat('闭关失败', 'error')
  }
}

onBeforeUnmount(() => {
  if (milestoneTimer) clearTimeout(milestoneTimer)
})
</script>

<template>
  <div class="meditate-wrap">
    <!-- 首次引导 -->
    <Transition name="guide-fade">
      <div v-if="showGuide" class="meditate-guide">
        <div class="guide-arrow"></div>
        <div class="guide-text">
          <span class="guide-title">吐纳调息</span>
          <span class="guide-desc">点击打坐恢复灵气与生命<br/>连续点击可获得连击加成!</span>
        </div>
      </div>
    </Transition>

    <!-- 连击指示器 -->
    <Transition name="streak-pop">
      <div v-if="streak > 1" class="streak-badge" :class="streakTier">
        <span class="streak-num">{{ streak }}</span>
        <span class="streak-label">连</span>
        <span class="streak-mult" v-if="mult > 1">x{{ mult }}</span>
      </div>
    </Transition>

    <!-- 里程碑弹窗 -->
    <Transition name="milestone-burst">
      <div v-if="milestoneShow" class="milestone-popup">
        <span class="ms-icon">&#10024;</span>
        <span class="ms-text">{{ milestone }}连 · 入定</span>
      </div>
    </Transition>

    <!-- 浮动数字 -->
    <TransitionGroup name="float-num" tag="div" class="float-container">
      <div v-for="f in floatingNums" :key="f.id"
           class="float-num" :class="f.type"
           :style="{ '--fx': f.x + 'px', '--fy': f.y + 'px' }">
        {{ f.text }}
      </div>
    </TransitionGroup>

    <!-- 主按钮 -->
    <button class="meditate-btn"
            :class="[streakTier, { animating }]"
            @click="meditate">
      <img src="/images/ui/meditate-btn.png" class="med-img" alt="打坐"
           @error="(e) => { e.target.style.display = 'none' }" />
      <span class="med-label">打坐</span>
      <span class="med-aura"></span>
      <span class="med-aura aura-2"></span>
    </button>

    <Transition name="guide-fade">
      <div v-if="showTranceAction" class="trance-panel">
        <button class="trance-btn" @click="enterTrance">入定成章</button>
        <button class="trance-btn retreat" @click="longRetreat">闭关续写</button>
        <button class="trance-close" @click="showTranceAction = false">×</button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.meditate-wrap {
  position: fixed;
  bottom: 110px;
  right: 28px;
  z-index: 40;
  width: 96px; height: 96px;
}

@media (max-width: 900px) {
  .meditate-wrap {
    right: calc(18px + var(--safe-right));
    bottom: calc(178px + var(--safe-bottom));
    width: 78px;
    height: 78px;
  }
  .meditate-btn {
    width: 78px;
    height: 78px;
  }
  .med-label {
    bottom: -18px;
    font-size: 11px;
  }
  .trance-panel {
    right: 0;
    bottom: 86px;
    flex-wrap: wrap;
    min-width: 180px;
  }
}

@media (orientation: landscape) and (max-height: 520px) {
  .meditate-wrap {
    right: calc(14px + var(--safe-right));
    bottom: calc(72px + var(--safe-bottom));
  }
}

/* ═══════════════════════════════════════════════════════
   主按钮
   ═══════════════════════════════════════════════════════ */
.meditate-btn {
  width: 96px; height: 96px;
  background: transparent;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  padding: 0;
  position: relative;
  transition: transform 0.12s cubic-bezier(0.34, 1.56, 0.64, 1),
              filter 0.3s;
  filter: drop-shadow(0 4px 20px rgba(0,0,0,0.6))
          drop-shadow(0 0 16px rgba(212,162,76,0.4));
}

.trance-panel {
  position: absolute;
  right: 0;
  bottom: 104px;
  min-width: 132px;
  padding: 8px;
  border: 1px solid rgba(212,162,76,0.45);
  background: rgba(18,18,32,0.94);
  box-shadow: 0 8px 28px rgba(0,0,0,0.35);
  display: flex;
  gap: 6px;
  align-items: center;
}

.trance-btn {
  flex: 1;
  border: none;
  background: linear-gradient(135deg, #B58A3E, #F2D28A);
  color: #1A1208;
  font-weight: 800;
  padding: 7px 10px;
  cursor: pointer;
}

.trance-btn.retreat {
  background: linear-gradient(135deg, #476A8F, #D4A24C);
  color: #FFF3D4;
}

.trance-close {
  width: 26px;
  height: 26px;
  border: 1px solid rgba(255,255,255,0.16);
  background: rgba(255,255,255,0.06);
  color: #E8D6B0;
  cursor: pointer;
}
.meditate-btn:hover {
  transform: scale(1.08);
}
.meditate-btn:active, .meditate-btn.animating {
  transform: scale(0.92);
}

/* 连击等级光效 */
.meditate-btn.warm {
  filter: drop-shadow(0 4px 20px rgba(0,0,0,0.5))
          drop-shadow(0 0 24px rgba(255,200,80,0.6));
}
.meditate-btn.blazing {
  filter: drop-shadow(0 4px 20px rgba(0,0,0,0.4))
          drop-shadow(0 0 32px rgba(255,140,0,0.8));
}
.meditate-btn.golden {
  filter: drop-shadow(0 4px 20px rgba(0,0,0,0.3))
          drop-shadow(0 0 40px rgba(255,215,0,1));
  animation: golden-pulse 0.6s ease-in-out infinite;
}
.meditate-btn.transcend {
  filter: drop-shadow(0 4px 20px rgba(0,0,0,0.2))
          drop-shadow(0 0 50px rgba(255,255,255,0.9))
          drop-shadow(0 0 80px rgba(212,162,76,0.8));
  animation: transcend-pulse 0.4s ease-in-out infinite;
}
@keyframes golden-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}
@keyframes transcend-pulse {
  0%, 100% { transform: scale(1) rotate(0deg); }
  50% { transform: scale(1.08) rotate(2deg); }
}

.med-img {
  width: 100%; height: 100%;
  display: block;
  border-radius: 50%;
  animation: med-rotate 30s linear infinite;
}
.meditate-btn.warm .med-img { animation-duration: 12s; }
.meditate-btn.blazing .med-img { animation-duration: 6s; }
.meditate-btn.golden .med-img { animation-duration: 3s; }
.meditate-btn.transcend .med-img { animation-duration: 1.5s; }

@keyframes med-rotate { to { transform: rotate(360deg); } }

.med-label {
  position: absolute;
  bottom: -22px; left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  color: #FFE0A3;
  letter-spacing: 4px;
  font-family: 'STKaiti', serif;
  background: rgba(0,0,0,0.6);
  padding: 2px 10px;
  border-radius: 10px;
  border: 1px solid rgba(212,162,76,0.4);
  white-space: nowrap;
  text-shadow: 0 0 6px #D4A24C;
}

/* 双光环脉冲 */
.med-aura {
  position: absolute;
  top: 50%; left: 50%;
  width: 100%; height: 100%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  border: 2px solid #FFE0A3;
  opacity: 0;
  pointer-events: none;
}
.meditate-btn.animating .med-aura {
  animation: med-pulse 0.6s ease-out forwards;
}
.meditate-btn.animating .aura-2 {
  animation: med-pulse 0.6s ease-out 0.1s forwards;
}
@keyframes med-pulse {
  0%   { opacity: 1; transform: translate(-50%, -50%) scale(0.6); }
  100% { opacity: 0; transform: translate(-50%, -50%) scale(2.2); }
}

/* 呼吸光 */
.meditate-btn.idle::before {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 1px solid rgba(212,162,76,0.5);
  animation: med-breathe 3s ease-in-out infinite;
  pointer-events: none;
}
@keyframes med-breathe {
  0%, 100% { transform: scale(1); opacity: 0.5; }
  50%      { transform: scale(1.12); opacity: 0.9; }
}

/* ═══════════════════════════════════════════════════════
   连击指示器
   ═══════════════════════════════════════════════════════ */
.streak-badge {
  position: absolute;
  top: -16px; left: 50%;
  transform: translateX(-50%);
  display: flex; align-items: center; gap: 2px;
  background: rgba(0,0,0,0.75);
  border: 1px solid rgba(212,162,76,0.6);
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 11px;
  color: #FFE0A3;
  font-family: 'STKaiti', serif;
  white-space: nowrap;
}
.streak-badge.warm { border-color: #FFC850; color: #FFD700; }
.streak-badge.blazing { border-color: #FF8C00; color: #FFA500; box-shadow: 0 0 8px rgba(255,140,0,0.5); }
.streak-badge.golden { border-color: #FFD700; color: #FFED8A; box-shadow: 0 0 12px rgba(255,215,0,0.7); }
.streak-badge.transcend {
  border-color: #FFF;
  color: #FFF;
  box-shadow: 0 0 16px rgba(255,255,255,0.8);
  animation: badge-glow 0.5s ease-in-out infinite;
}
@keyframes badge-glow {
  0%, 100% { box-shadow: 0 0 16px rgba(255,255,255,0.5); }
  50% { box-shadow: 0 0 24px rgba(255,215,0,1); }
}
.streak-num { font-weight: bold; font-size: 13px; }
.streak-label { font-size: 10px; opacity: 0.8; }
.streak-mult { font-size: 10px; color: #4FC3F7; margin-left: 2px; }

.streak-pop-enter-active { animation: pop-in 0.2s ease-out; }
.streak-pop-leave-active { animation: pop-out 0.15s ease-in; }
@keyframes pop-in { from { transform: translateX(-50%) scale(0.5); opacity: 0; } to { transform: translateX(-50%) scale(1); opacity: 1; } }
@keyframes pop-out { from { transform: translateX(-50%) scale(1); opacity: 1; } to { transform: translateX(-50%) scale(0.5); opacity: 0; } }

/* ═══════════════════════════════════════════════════════
   浮动数字
   ═══════════════════════════════════════════════════════ */
.float-container {
  position: absolute;
  top: 50%; left: 50%;
  width: 0; height: 0;
  pointer-events: none;
}
.float-num {
  position: absolute;
  font-weight: bold;
  font-size: 14px;
  font-family: 'STKaiti', serif;
  white-space: nowrap;
  text-shadow: 0 1px 3px rgba(0,0,0,0.8);
  transform: translate(var(--fx), var(--fy));
}
.float-num.hp { color: #66BB6A; }
.float-num.qi { color: #42A5F5; }
.float-num.fatigue { color: #AB47BC; }
.float-num.error { color: #EF5350; }
.float-num.exp { color: #FFD700; font-size: 15px; text-shadow: 0 0 8px rgba(255,215,0,0.5); }
.float-num.levelup {
  color: #FFE0A3;
  font-size: 16px;
  font-weight: bold;
  text-shadow: 0 0 12px rgba(255,200,80,0.8);
  letter-spacing: 1px;
}

.float-num-enter-active {
  animation: float-rise 1.2s ease-out forwards;
}
.float-num-leave-active {
  animation: float-fade 0.3s ease-out forwards;
}
@keyframes float-rise {
  0%   { opacity: 1; transform: translate(var(--fx), var(--fy)) translateY(0); }
  70%  { opacity: 1; }
  100% { opacity: 0; transform: translate(var(--fx), var(--fy)) translateY(-60px); }
}
@keyframes float-fade {
  to { opacity: 0; }
}

/* ═══════════════════════════════════════════════════════
   里程碑弹窗
   ═══════════════════════════════════════════════════════ */
.milestone-popup {
  position: absolute;
  top: -52px; left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, rgba(255,215,0,0.9), rgba(212,162,76,0.95));
  color: #1a0a00;
  font-size: 13px;
  font-weight: bold;
  font-family: 'STKaiti', serif;
  padding: 4px 14px;
  border-radius: 16px;
  white-space: nowrap;
  box-shadow: 0 0 20px rgba(255,215,0,0.8), 0 2px 8px rgba(0,0,0,0.4);
}
.ms-icon { font-size: 14px; margin-right: 4px; }

.milestone-burst-enter-active { animation: ms-in 0.4s cubic-bezier(0.34,1.56,0.64,1); }
.milestone-burst-leave-active { animation: ms-out 0.5s ease-in; }
@keyframes ms-in { from { transform: translateX(-50%) scale(0.3); opacity: 0; } to { transform: translateX(-50%) scale(1); opacity: 1; } }
@keyframes ms-out { from { transform: translateX(-50%) scale(1); opacity: 1; } to { transform: translateX(-50%) translateY(-10px) scale(0.8); opacity: 0; } }

/* ═══════════════════════════════════════════════════════
   首次引导
   ═══════════════════════════════════════════════════════ */
.meditate-guide {
  position: absolute;
  bottom: 110px; right: 10px;
  background: rgba(20,10,2,0.92);
  border: 1px solid rgba(212,162,76,0.7);
  border-radius: 12px;
  padding: 10px 14px;
  width: 160px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.7), 0 0 12px rgba(212,162,76,0.3);
}
.guide-arrow {
  position: absolute;
  bottom: -8px; right: 36px;
  width: 0; height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-top: 8px solid rgba(212,162,76,0.7);
}
.guide-title {
  display: block;
  font-size: 14px;
  color: #FFD700;
  font-family: 'STKaiti', serif;
  font-weight: bold;
  margin-bottom: 4px;
}
.guide-desc {
  font-size: 11px;
  color: #ccc;
  line-height: 1.5;
}

.guide-fade-enter-active { animation: guide-in 0.5s ease-out; }
.guide-fade-leave-active { animation: guide-out 0.3s ease-in; }
@keyframes guide-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
@keyframes guide-out { from { opacity: 1; } to { opacity: 0; transform: translateY(10px); } }

@media (max-width: 900px) {
  .meditate-wrap {
    right: calc(18px + var(--safe-right));
    bottom: calc(178px + var(--safe-bottom));
    width: 78px;
    height: 78px;
  }
  .meditate-btn {
    width: 78px;
    height: 78px;
  }
  .med-label {
    bottom: -18px;
    font-size: 11px;
  }
  .trance-panel {
    right: 0;
    bottom: 86px;
    flex-wrap: wrap;
    min-width: 180px;
  }
  .meditate-guide {
    bottom: 92px;
    right: 0;
  }
}

@media (orientation: landscape) and (max-height: 520px) {
  .meditate-wrap {
    right: calc(14px + var(--safe-right));
    bottom: calc(72px + var(--safe-bottom));
  }
}
</style>
