<!--
  招式前摇介绍卡 — 国风/修仙风,在 LLM 请求期间掩盖等待

  显示时序:
    0ms       全屏黑色幕布展开
    100ms     中央阵法圆展开 + 招式名书法字浮现
    400ms     招式描述淡入
    600ms     国风 loading 开始(八卦 + 灵气 + 笔法)
    LLM 第一个 chunk 到 → 立刻淡出(by parent)

  Props:
    visible: bool             — 是否显示
    skill: { name, icon, description, qi_cost, power, tier } — 招式信息
    sectId: 'canglan' | 'tianji' | ...  — 决定主题色
    loadingTip: string        — loading 阶段提示文字
-->
<script setup>
import { computed, watch, ref } from 'vue'
import { getSectTheme } from '../config/sectTheme.js'

const props = defineProps({
  visible: { type: Boolean, default: false },
  skill: { type: Object, default: () => ({}) },
  sectId: { type: String, default: 'canglan' },
  loadingTip: { type: String, default: '正在向天道借力...' },
  progress: { type: Number, default: 0 },  // 0-100 蓄力进度(基于 LLM 字符)
})

const theme = computed(() => getSectTheme(props.sectId))

// 每次显示时,随机抽 1 句 loading tip
const RANDOM_TIPS = {
  canglan: [
    '剑意已凝聚于笔尖 ⋯',
    '运笔将动,天道为之颤栗 ⋯',
    '墨痕九转,直入九霄 ⋯',
    '深思已毕,杀招将至 ⋯',
  ],
  tianji: [
    '万象齿轮飞转,演算变数 ⋯',
    '机关合数,千锋待发 ⋯',
    '诸法归元,大势已成 ⋯',
    '太极转动,布局完毕 ⋯',
  ],
  xuanji: [
    '七十二路推演完毕 ⋯',
    '幻方阵纹悄然展开 ⋯',
    '心算万千,决断已下 ⋯',
    '终南剑意正在凝聚 ⋯',
  ],
  qingming: [
    '诵典籍 · 引古剑诀 ⋯',
    '诗云剑意,自心而生 ⋯',
    '青冥学海,涌出剑芒 ⋯',
    '千年学问,自然流露 ⋯',
  ],
  yueyin: [
    '月隐千年记忆已唤醒 ⋯',
    '夜阑中,杀机藏匿 ⋯',
    '记忆碎片正在归位 ⋯',
    '银辉将动,刺向黎明 ⋯',
  ],
}

const currentTip = ref('')
watch(() => props.visible, (v) => {
  if (v) {
    const tips = RANDOM_TIPS[props.sectId] || RANDOM_TIPS.canglan
    currentTip.value = tips[Math.floor(Math.random() * tips.length)]
  }
})
</script>

<template>
  <Transition name="cast-intro">
    <div v-if="visible" class="cast-intro" :style="{
      '--c': theme.accent,
      '--g': theme.glow,
      '--p': theme.primary,
    }">

      <!-- 渐变底色幕布 -->
      <div class="curtain"></div>

      <!-- 沧澜剑派的水墨展开 -->
      <template v-if="sectId === 'canglan'">
        <div class="ink-explode">
          <div class="ink-blob blob-1"></div>
          <div class="ink-blob blob-2"></div>
          <div class="ink-blob blob-3"></div>
        </div>
      </template>

      <!-- 天机阁的齿轮转动 -->
      <template v-else-if="sectId === 'tianji'">
        <div class="gear-formation">
          <div class="gf-gear g-1">⚙️</div>
          <div class="gf-gear g-2">⚙️</div>
          <div class="gf-gear g-3">⚙️</div>
          <div class="gf-rune ring-1"></div>
          <div class="gf-rune ring-2"></div>
        </div>
      </template>

      <!-- 玄机宗的紫色波纹 -->
      <template v-else-if="sectId === 'xuanji'">
        <div class="ripple-formation">
          <div class="rp r-1"></div>
          <div class="rp r-2"></div>
          <div class="rp r-3"></div>
          <div class="floating-num n-1">π</div>
          <div class="floating-num n-2">∞</div>
          <div class="floating-num n-3">⋯</div>
        </div>
      </template>

      <!-- 青冥派的卷轴展开 -->
      <template v-else-if="sectId === 'qingming'">
        <div class="scroll-formation">
          <div class="sc-jade"></div>
          <div class="sc-char ch-1">道</div>
          <div class="sc-char ch-2">仁</div>
          <div class="sc-char ch-3">易</div>
          <div class="sc-char ch-4">思</div>
        </div>
      </template>

      <!-- 月隐宫的月光 -->
      <template v-else-if="sectId === 'yueyin'">
        <div class="moon-formation">
          <div class="mn-aura"></div>
          <div class="mn-orbit">
            <div class="mn-phase mp-1"></div>
            <div class="mn-phase mp-2"></div>
          </div>
          <div v-for="i in 12" :key="i" class="mn-star" :style="{
            left: (Math.random()*100) + '%',
            top: (Math.random()*100) + '%',
            animationDelay: (Math.random()*2) + 's',
          }"></div>
        </div>
      </template>

      <!-- 中央阵法圆 -->
      <div class="formation-circle">
        <div class="outer-ring"></div>
        <div class="mid-ring"></div>
        <div class="inner-ring"></div>
        <div class="cross-line line-h"></div>
        <div class="cross-line line-v"></div>
      </div>

      <!-- 招式核心信息 -->
      <div class="skill-core">
        <div class="skill-icon-big">{{ skill.icon || '⚔️' }}</div>
        <h1 class="skill-name">{{ skill.name }}</h1>
        <div class="skill-divider">
          <span class="d-dot"></span>
          <span class="d-line"></span>
          <span class="d-dot"></span>
        </div>
        <p class="skill-desc">{{ skill.description }}</p>
        <div class="skill-tags">
          <span v-if="skill.qi_cost" class="tag tag-qi">⚡ 灵气 {{ skill.qi_cost }}</span>
          <span v-if="skill.power" class="tag tag-power">💥 {{ skill.power }}x ATK</span>
        </div>
      </div>

      <!-- 国风 loading + 能量蓄力进度 -->
      <div class="loading-zone">
        <!-- ★ 能量蓄力条(基于 LLM 字符进度) -->
        <div class="energy-bar">
          <div class="energy-fill" :style="{ width: progress + '%' }">
            <div class="energy-shine"></div>
          </div>
          <span class="energy-pct">{{ Math.round(progress) }}%</span>
        </div>
        <!-- 灵气粒子环绕(根据进度变快) -->
        <div class="qi-orbit" :style="{ animationDuration: (4 - progress * 0.025) + 's' }">
          <div v-for="i in 8" :key="i" class="qi-dot" :style="{
            transform: `rotate(${i * 45}deg) translateX(80px)`,
            animationDelay: (i * 0.12) + 's',
          }"></div>
        </div>
        <p class="loading-tip">
          <span v-if="progress < 30">{{ currentTip }}</span>
          <span v-else-if="progress < 80">天道演算中,杀招将至 ⋯</span>
          <span v-else>气机已至,准备落笔 ⋯</span>
        </p>
      </div>

      <!-- 角落装饰 -->
      <div class="corner corner-tl"></div>
      <div class="corner corner-tr"></div>
      <div class="corner corner-bl"></div>
      <div class="corner corner-br"></div>
    </div>
  </Transition>
</template>

<style scoped>
.cast-intro {
  position: fixed; inset: 0;
  z-index: 200;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  pointer-events: none;
  overflow: hidden;
}
.cast-intro-enter-active { transition: opacity 0.35s ease-out; }
.cast-intro-leave-active { transition: opacity 0.4s ease-in; }
.cast-intro-enter-from, .cast-intro-leave-to { opacity: 0; }

/* 半透明黑幕(不全黑,保留战场可见) */
.curtain {
  position: absolute; inset: 0;
  background:
    radial-gradient(ellipse at center, transparent 0%, rgba(0,0,0,0.85) 70%),
    color-mix(in srgb, var(--p, #0a0a14) 80%, transparent);
  animation: curtain-in 0.5s ease-out;
}
@keyframes curtain-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* ============= 中央阵法圆 ============= */
.formation-circle {
  position: absolute;
  width: 600px; height: 600px;
  pointer-events: none;
}
.outer-ring, .mid-ring, .inner-ring {
  position: absolute;
  border-radius: 50%;
  inset: 0;
  border: 1px solid var(--c, #D4A24C);
  opacity: 0;
  animation: ring-expand 0.7s ease-out forwards;
}
.outer-ring {
  border-width: 2px;
  border-style: dashed;
  box-shadow: 0 0 60px var(--c, #D4A24C);
  animation: ring-expand 0.7s ease-out forwards, formation-spin 16s linear infinite 0.7s;
}
.mid-ring {
  inset: 80px;
  animation-delay: 0.15s;
  animation: ring-expand 0.7s ease-out 0.15s forwards, formation-spin 12s linear infinite reverse 0.85s;
  border-style: dotted;
  opacity: 0;
}
.inner-ring {
  inset: 170px;
  border-width: 1px;
  animation: ring-expand 0.7s ease-out 0.3s forwards;
  opacity: 0;
}
@keyframes ring-expand {
  0% { opacity: 0; transform: scale(0.4); filter: blur(8px); }
  100% { opacity: 0.6; transform: scale(1); filter: blur(0); }
}
@keyframes formation-spin {
  to { transform: rotate(360deg); }
}

.cross-line {
  position: absolute;
  background: linear-gradient(90deg, transparent, var(--c, #D4A24C), transparent);
  opacity: 0;
  animation: line-in 0.6s ease-out 0.4s forwards;
}
.line-h {
  top: 50%; left: 50%;
  width: 100%; height: 1px;
  transform: translate(-50%, -50%);
}
.line-v {
  top: 50%; left: 50%;
  width: 1px; height: 100%;
  transform: translate(-50%, -50%);
  background: linear-gradient(180deg, transparent, var(--c, #D4A24C), transparent);
}
@keyframes line-in {
  from { opacity: 0; transform: translate(-50%, -50%) scale(0.5); }
  to   { opacity: 0.4; transform: translate(-50%, -50%) scale(1); }
}

/* ============= 招式核心信息 ============= */
.skill-core {
  position: relative;
  z-index: 5;
  display: flex; flex-direction: column;
  align-items: center;
  gap: 12px;
  animation: core-pop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) 0.4s both;
}
@keyframes core-pop {
  from { opacity: 0; transform: scale(0.5) translateY(20px); filter: blur(10px); }
  to   { opacity: 1; transform: scale(1) translateY(0); filter: blur(0); }
}

.skill-icon-big {
  font-size: 88px;
  filter: drop-shadow(0 0 32px var(--g, #FFE0A3));
  animation: icon-float 2.5s ease-in-out infinite;
}
@keyframes icon-float {
  0%, 100% { transform: translateY(0) rotate(-2deg); }
  50%      { transform: translateY(-6px) rotate(2deg); }
}

.skill-name {
  margin: 0;
  font-size: 56px;
  font-family: 'STKaiti', 'KaiTi', 'Source Han Serif SC', serif;
  font-weight: 500;
  letter-spacing: 12px;
  background: linear-gradient(180deg, var(--g, #FFE0A3) 0%, var(--c, #D4A24C) 100%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 0 64px var(--g, #FFE0A3);
  padding-left: 12px;
  animation: name-shimmer 2.5s ease-in-out infinite;
}
@keyframes name-shimmer {
  0%, 100% { filter: brightness(1); }
  50%      { filter: brightness(1.3); }
}

.skill-divider {
  display: flex; align-items: center; gap: 8px;
  margin: 4px 0;
}
.d-dot {
  width: 6px; height: 6px;
  background: var(--c, #D4A24C);
  border-radius: 50%;
  box-shadow: 0 0 12px var(--c, #D4A24C);
}
.d-line {
  width: 120px; height: 1px;
  background: linear-gradient(90deg, transparent, var(--c, #D4A24C), transparent);
}

.skill-desc {
  margin: 0;
  font-size: 16px;
  color: #ccc;
  letter-spacing: 3px;
  font-family: 'STKaiti', 'KaiTi', serif;
  font-style: italic;
  max-width: 460px;
  text-align: center;
}

.skill-tags {
  display: flex; gap: 12px;
  margin-top: 4px;
}
.tag {
  background: rgba(0,0,0,0.5);
  border: 1px solid color-mix(in srgb, var(--c, #D4A24C) 40%, transparent);
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--g, #FFE0A3);
  letter-spacing: 1px;
}

/* ============= 国风 loading ============= */
.loading-zone {
  position: relative;
  z-index: 5;
  margin-top: 32px;
  display: flex; flex-direction: column;
  align-items: center;
  gap: 12px;
  animation: loading-in 0.4s ease-out 0.7s both;
}
@keyframes loading-in {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ★ 能量蓄力条(基于 LLM 字符进度) */
.energy-bar {
  position: relative;
  width: 280px; height: 12px;
  background: rgba(0,0,0,0.6);
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--c, #D4A24C) 30%, transparent);
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);
}
.energy-fill {
  position: absolute;
  top: 0; left: 0;
  height: 100%;
  background: linear-gradient(90deg,
    var(--c, #D4A24C) 0%,
    var(--g, #FFE0A3) 50%,
    var(--c, #D4A24C) 100%);
  box-shadow:
    0 0 12px var(--c, #D4A24C),
    inset 0 0 4px rgba(255,255,255,0.4);
  border-radius: 5px;
  transition: width 0.3s ease-out;
  position: relative;
  overflow: hidden;
}
.energy-shine {
  position: absolute; inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent);
  animation: energy-shine 1.2s linear infinite;
}
@keyframes energy-shine {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
.energy-pct {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  font-size: 10px;
  color: #fff;
  font-family: 'SF Mono', monospace;
  font-weight: 700;
  text-shadow: 0 0 4px #000, 0 1px 2px rgba(0,0,0,0.8);
  letter-spacing: 1px;
  z-index: 2;
}

/* 灵气环 */
.qi-orbit {
  position: relative;
  width: 160px; height: 160px;
  animation: formation-spin 4s linear infinite;
}
.qi-dot {
  position: absolute;
  top: 50%; left: 50%;
  width: 6px; height: 6px;
  background: var(--g, #FFE0A3);
  border-radius: 50%;
  box-shadow: 0 0 12px var(--c, #D4A24C);
  margin-top: -3px; margin-left: -3px;
  animation: qi-pulse 1.2s ease-in-out infinite;
}
@keyframes qi-pulse {
  0%, 100% { opacity: 0.3; }
  50%      { opacity: 1; }
}

.loading-tip {
  margin: 0;
  font-size: 14px;
  color: #ccc;
  letter-spacing: 3px;
  font-family: 'STKaiti', 'KaiTi', serif;
  animation: tip-blink 1.8s ease-in-out infinite;
}
@keyframes tip-blink {
  0%, 100% { opacity: 0.6; }
  50%      { opacity: 1; }
}

/* ============= 角落装饰 ============= */
.corner {
  position: absolute;
  width: 60px; height: 60px;
  border: 2px solid var(--c, #D4A24C);
  opacity: 0;
  animation: corner-in 0.4s ease-out 0.5s forwards;
}
.corner-tl { top: 24px; left: 24px; border-right: 0; border-bottom: 0; }
.corner-tr { top: 24px; right: 24px; border-left: 0; border-bottom: 0; }
.corner-bl { bottom: 24px; left: 24px; border-right: 0; border-top: 0; }
.corner-br { bottom: 24px; right: 24px; border-left: 0; border-top: 0; }
@keyframes corner-in {
  from { opacity: 0; transform: scale(0.5); }
  to   { opacity: 0.7; transform: scale(1); }
}

/* ============= 沧澜 - 水墨爆炸 ============= */
.ink-explode {
  position: absolute; inset: 0;
}
.ink-blob {
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(0,0,0,0.6), transparent 70%);
  filter: blur(40px);
  animation: ink-spread 0.8s ease-out forwards;
}
.blob-1 { top: 50%; left: 50%; width: 400px; height: 400px; margin-top: -200px; margin-left: -200px; }
.blob-2 { top: 30%; left: 30%; width: 250px; height: 250px; animation-delay: 0.2s; opacity: 0; }
.blob-3 { top: 60%; right: 30%; width: 250px; height: 250px; animation-delay: 0.4s; opacity: 0; }
@keyframes ink-spread {
  from { opacity: 0; transform: scale(0.2); }
  to   { opacity: 0.7; transform: scale(1); }
}

/* ============= 天机 - 齿轮阵 ============= */
.gear-formation { position: absolute; inset: 0; pointer-events: none; }
.gf-gear {
  position: absolute;
  font-size: 80px;
  filter: drop-shadow(0 0 16px var(--c, #FFB454));
  opacity: 0;
  animation: gf-in 0.5s ease-out forwards, formation-spin 6s linear infinite 0.5s;
}
.g-1 { top: 15%; left: 15%; animation-delay: 0s, 0.5s; }
.g-2 { top: 70%; right: 12%; font-size: 100px; animation-delay: 0.2s, 0.7s; }
.g-3 { top: 40%; right: 25%; font-size: 60px; animation-delay: 0.4s, 0.9s; }
@keyframes gf-in {
  from { opacity: 0; transform: scale(0.3) rotate(-180deg); }
  to   { opacity: 0.4; transform: scale(1) rotate(0); }
}

.gf-rune {
  position: absolute;
  top: 50%; left: 50%;
  border: 1px dashed var(--c, #FFB454);
  border-radius: 50%;
  opacity: 0;
  animation: ring-expand 0.6s ease-out 0.3s forwards, formation-spin 20s linear infinite 0.9s;
}
.ring-1 { width: 700px; height: 700px; margin: -350px 0 0 -350px; }
.ring-2 { width: 500px; height: 500px; margin: -250px 0 0 -250px; animation-delay: 0.5s, 1.1s; animation-direction: reverse; }

/* ============= 玄机 - 紫色波纹 ============= */
.ripple-formation { position: absolute; inset: 0; }
.rp {
  position: absolute;
  top: 50%; left: 50%;
  width: 100px; height: 100px;
  border: 2px solid #9B59B6;
  border-radius: 50%;
  margin: -50px 0 0 -50px;
  animation: ripple-wave 2.2s ease-out infinite;
}
.r-1 { animation-delay: 0s; }
.r-2 { animation-delay: 0.7s; }
.r-3 { animation-delay: 1.4s; }
@keyframes ripple-wave {
  0%   { opacity: 1; transform: scale(0.3); border-color: #C8A6DD; }
  100% { opacity: 0; transform: scale(5); border-color: rgba(155,89,182,0); }
}
.floating-num {
  position: absolute;
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 40px;
  color: #C8A6DD;
  text-shadow: 0 0 16px #9B59B6;
  font-weight: 700;
  animation: num-float 2.5s ease-in-out infinite;
}
.n-1 { top: 20%; left: 15%; }
.n-2 { top: 30%; right: 18%; animation-delay: 0.8s; }
.n-3 { bottom: 25%; left: 22%; animation-delay: 1.4s; }
@keyframes num-float {
  0%, 100% { opacity: 0.4; transform: translateY(0); }
  50%      { opacity: 1; transform: translateY(-12px); }
}

/* ============= 青冥 - 古字浮现 ============= */
.scroll-formation { position: absolute; inset: 0; }
.sc-jade {
  position: absolute;
  top: 50%; left: 50%;
  width: 500px; height: 500px;
  margin: -250px 0 0 -250px;
  background: radial-gradient(circle, rgba(82,183,136,0.3), transparent 70%);
  border-radius: 50%;
  animation: jade-glow 3s ease-in-out infinite;
}
@keyframes jade-glow {
  0%, 100% { transform: scale(1); opacity: 0.4; }
  50%      { transform: scale(1.1); opacity: 0.7; }
}
.sc-char {
  position: absolute;
  font-family: 'STKaiti', 'KaiTi', serif;
  font-size: 56px;
  color: #95D5B2;
  text-shadow: 0 0 24px #52B788;
  font-weight: 500;
  animation: char-fade 3s ease-in-out infinite;
}
.ch-1 { top: 15%; left: 20%; animation-delay: 0s; }
.ch-2 { top: 25%; right: 18%; animation-delay: 0.7s; }
.ch-3 { bottom: 30%; left: 16%; animation-delay: 1.4s; }
.ch-4 { bottom: 20%; right: 22%; animation-delay: 2.1s; }
@keyframes char-fade {
  0%, 100% { opacity: 0; transform: translateY(20px) scale(0.8); }
  50%      { opacity: 0.8; transform: translateY(0) scale(1); }
}

/* ============= 月隐 - 月光星辰 ============= */
.moon-formation { position: absolute; inset: 0; }
.mn-aura {
  position: absolute;
  top: 50%; left: 50%;
  width: 500px; height: 500px;
  margin: -250px 0 0 -250px;
  background: radial-gradient(circle, rgba(181,156,255,0.4), transparent 70%);
  border-radius: 50%;
  animation: jade-glow 4s ease-in-out infinite;
}
.mn-orbit {
  position: absolute;
  top: 50%; left: 50%;
  width: 400px; height: 400px;
  margin: -200px 0 0 -200px;
  animation: formation-spin 15s linear infinite;
}
.mn-phase {
  position: absolute;
  width: 20px; height: 20px;
  background: linear-gradient(90deg, #fff 50%, transparent 50%);
  border-radius: 50%;
  box-shadow: 0 0 16px rgba(217,204,255,0.8);
}
.mp-1 { top: 0; left: 50%; transform: translateX(-50%); }
.mp-2 { bottom: 0; left: 50%; transform: translateX(-50%); background: linear-gradient(90deg, transparent 50%, #fff 50%); }
.mn-star {
  position: absolute;
  width: 3px; height: 3px;
  background: #fff;
  border-radius: 50%;
  box-shadow: 0 0 8px #D9CCFF;
  animation: tip-blink 2s ease-in-out infinite;
}

/* === 响应式 === */
@media (max-width: 640px) {
  .skill-name { font-size: 38px; letter-spacing: 8px; }
  .skill-icon-big { font-size: 64px; }
  .formation-circle { width: 400px; height: 400px; }
  .mid-ring { inset: 60px; }
  .inner-ring { inset: 120px; }
}
</style>
