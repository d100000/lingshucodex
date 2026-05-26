<!--
  仙侠流动背景 — 纯 CSS + JS,无外链
  五层叠加:
    L1 渐变底色(深夜 + 远云)
    L2 远山剪影(底部水墨)
    L3 飘动云雾(3 层不同速度)
    L4 灵气粒子(随机上升)
    L5 飘落花瓣/灵符(从上往下漂浮 + 摇摆)

  Props:
    intensity: 'light' | 'normal' | 'rich' — 控制粒子密度
    accent: 颜色色调(默认金色,门派色可改)
-->
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  intensity: { type: String, default: 'normal' },  // light / normal / rich
  accent: { type: String, default: '#D4A24C' },
})

// 粒子数量按 intensity
const particleCount = computed(() =>
  ({ light: 20, normal: 35, rich: 55 }[props.intensity] || 35)
)
const petalCount = computed(() =>
  ({ light: 8, normal: 15, rich: 24 }[props.intensity] || 15)
)
const runeCount = computed(() =>
  ({ light: 3, normal: 6, rich: 10 }[props.intensity] || 6)
)

// 生成粒子(随机位置 + 延迟 + 速度)
const particles = ref([])
const petals = ref([])
const runes = ref([])

// 随机修真符号
const RUNE_CHARS = ['灵', '道', '仙', '玄', '一', '无', '万', '心', '剑', '念', '禅', '气', '法', '空', '元']

function rand(min, max) { return min + Math.random() * (max - min) }

function genAll() {
  particles.value = Array.from({ length: particleCount.value }, (_, i) => ({
    id: 'p' + i,
    left: rand(0, 100),
    duration: rand(8, 18),
    delay: rand(0, 15),
    size: rand(2, 5),
    drift: rand(-30, 30),  // 漂移幅度
    opacity: rand(0.3, 0.7),
  }))
  petals.value = Array.from({ length: petalCount.value }, (_, i) => ({
    id: 'f' + i,
    left: rand(-10, 110),
    duration: rand(12, 25),
    delay: rand(0, 20),
    size: rand(10, 18),
    rotate: rand(0, 360),
    type: ['🌸', '🍃', '🌺', '🌷'][i % 4],
    sway: rand(40, 100),
  }))
  runes.value = Array.from({ length: runeCount.value }, (_, i) => ({
    id: 'r' + i,
    char: RUNE_CHARS[Math.floor(Math.random() * RUNE_CHARS.length)],
    top: rand(10, 80),
    left: rand(5, 95),
    duration: rand(10, 18),
    delay: rand(0, 10),
    size: rand(40, 90),
  }))
}

onMounted(genAll)
</script>

<template>
  <div class="wuxia-bg" :style="{ '--accent': accent }">
    <!-- L1 渐变底色 -->
    <div class="layer-base"></div>

    <!-- L2 远山(底部水墨剪影) -->
    <svg class="layer-mountains" viewBox="0 0 1200 200" preserveAspectRatio="none">
      <path d="M0,200 L0,160 L100,120 L180,140 L260,90 L340,130 L420,80 L500,110 L580,70 L680,100 L780,60 L880,90 L980,75 L1080,100 L1200,80 L1200,200 Z"
            fill="rgba(15,20,40,0.85)" />
      <path d="M0,200 L0,180 L80,150 L160,165 L240,130 L320,155 L420,140 L520,160 L620,135 L720,150 L820,130 L920,145 L1020,140 L1120,155 L1200,140 L1200,200 Z"
            fill="rgba(8,10,25,0.95)" />
    </svg>

    <!-- L3 云雾(3 层不同速度) -->
    <div class="layer-mist mist-1"></div>
    <div class="layer-mist mist-2"></div>
    <div class="layer-mist mist-3"></div>

    <!-- L4 灵气粒子(从下往上) -->
    <div class="layer-particles">
      <div
        v-for="p in particles"
        :key="p.id"
        class="particle"
        :style="{
          left: p.left + '%',
          animationDuration: p.duration + 's',
          animationDelay: -p.delay + 's',
          width: p.size + 'px',
          height: p.size + 'px',
          opacity: p.opacity,
          '--drift': p.drift + 'px',
        }"
      ></div>
    </div>

    <!-- L5 飘落花瓣/灵符 -->
    <div class="layer-petals">
      <div
        v-for="f in petals"
        :key="f.id"
        class="petal"
        :style="{
          left: f.left + '%',
          animationDuration: f.duration + 's',
          animationDelay: -f.delay + 's',
          fontSize: f.size + 'px',
          '--sway': f.sway + 'px',
          '--rotate-start': f.rotate + 'deg',
        }"
      >{{ f.type }}</div>
    </div>

    <!-- L6 修真符文(渐隐) -->
    <div class="layer-runes">
      <div
        v-for="r in runes"
        :key="r.id"
        class="rune"
        :style="{
          left: r.left + '%',
          top: r.top + '%',
          animationDuration: r.duration + 's',
          animationDelay: -r.delay + 's',
          fontSize: r.size + 'px',
        }"
      >{{ r.char }}</div>
    </div>

    <!-- L7 顶部柔光晕 -->
    <div class="layer-glow"></div>
  </div>
</template>

<style scoped>
.wuxia-bg {
  position: fixed; inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

/* ===== L1 底色 ===== */
.layer-base {
  position: absolute; inset: 0;
  background:
    radial-gradient(ellipse at 30% 20%, rgba(50, 80, 140, 0.18), transparent 50%),
    radial-gradient(ellipse at 70% 80%, rgba(120, 60, 100, 0.12), transparent 50%),
    linear-gradient(180deg, #0a0a1f 0%, #14142a 40%, #0f0e1d 70%, #050810 100%);
  animation: base-shift 30s ease-in-out infinite;
}
@keyframes base-shift {
  0%, 100% { filter: hue-rotate(0deg); }
  50%      { filter: hue-rotate(15deg); }
}

/* ===== L2 远山 ===== */
.layer-mountains {
  position: absolute;
  bottom: 0; left: 0;
  width: 100%; height: 25%;
  opacity: 0.7;
}

/* ===== L3 云雾(三层不同速度叠加滚动) ===== */
.layer-mist {
  position: absolute;
  width: 200%; height: 100%;
  top: 0; left: -50%;
  background-repeat: repeat-x;
  opacity: 0.4;
}
.mist-1 {
  background-image:
    radial-gradient(ellipse 600px 100px at 10% 30%, rgba(255,255,255,0.06), transparent 60%),
    radial-gradient(ellipse 800px 120px at 40% 50%, rgba(255,255,255,0.04), transparent 60%),
    radial-gradient(ellipse 700px 90px at 70% 40%, rgba(255,255,255,0.05), transparent 60%);
  animation: mist-drift 80s linear infinite;
}
.mist-2 {
  background-image:
    radial-gradient(ellipse 500px 80px at 20% 60%, rgba(200,220,255,0.05), transparent 60%),
    radial-gradient(ellipse 650px 100px at 60% 70%, rgba(220,200,255,0.04), transparent 60%);
  animation: mist-drift 120s linear infinite reverse;
  opacity: 0.3;
}
.mist-3 {
  background-image:
    radial-gradient(ellipse 400px 60px at 15% 80%, rgba(212,162,76,0.04), transparent 60%),
    radial-gradient(ellipse 500px 70px at 55% 75%, rgba(212,162,76,0.03), transparent 60%);
  animation: mist-drift 60s linear infinite;
  opacity: 0.35;
}
@keyframes mist-drift {
  0%   { transform: translateX(0); }
  100% { transform: translateX(50%); }
}

/* ===== L4 灵气粒子 ===== */
.layer-particles {
  position: absolute; inset: 0;
}
.particle {
  position: absolute;
  bottom: -10px;
  background: radial-gradient(circle, var(--accent) 0%, transparent 70%);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--accent), 0 0 16px var(--accent);
  animation: particle-rise linear infinite;
}
@keyframes particle-rise {
  0% {
    transform: translateY(0) translateX(0);
    opacity: 0;
  }
  10% { opacity: var(--initial-opacity, 0.7); }
  90% { opacity: var(--initial-opacity, 0.7); }
  100% {
    transform: translateY(-110vh) translateX(var(--drift, 0));
    opacity: 0;
  }
}

/* ===== L5 飘落花瓣 ===== */
.layer-petals {
  position: absolute; inset: 0;
}
.petal {
  position: absolute;
  top: -30px;
  opacity: 0.55;
  animation: petal-fall linear infinite;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3)) saturate(0.7);
  text-shadow: 0 0 8px rgba(255,255,255,0.1);
}
@keyframes petal-fall {
  0% {
    transform: translateY(-30px) translateX(0) rotate(var(--rotate-start, 0));
    opacity: 0;
  }
  10% { opacity: 0.55; }
  50% { transform: translateY(50vh) translateX(var(--sway, 50px)) rotate(180deg); }
  90% { opacity: 0.45; }
  100% {
    transform: translateY(110vh) translateX(calc(var(--sway, 50px) * -0.5)) rotate(540deg);
    opacity: 0;
  }
}

/* ===== L6 修真符文 ===== */
.layer-runes {
  position: absolute; inset: 0;
}
.rune {
  position: absolute;
  font-family: 'STKaiti', 'KaiTi', 'Source Han Serif SC', serif;
  font-weight: 700;
  color: var(--accent);
  opacity: 0;
  text-shadow:
    0 0 16px var(--accent),
    0 0 32px var(--accent);
  animation: rune-pulse ease-in-out infinite;
  pointer-events: none;
  user-select: none;
}
@keyframes rune-pulse {
  0%, 100% { opacity: 0; transform: scale(0.6); filter: blur(8px); }
  40%, 60% { opacity: 0.12; transform: scale(1); filter: blur(0); }
}

/* ===== L7 顶部柔光晕 ===== */
.layer-glow {
  position: absolute;
  top: 0; left: 0; right: 0; height: 50%;
  background: radial-gradient(ellipse at 50% 0%, rgba(212,162,76,0.08), transparent 60%);
  pointer-events: none;
}
</style>
