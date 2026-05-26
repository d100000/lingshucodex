<!--
  欢迎页 — 首次进入游戏看到
  1. 仙侠流动背景
  2. 开场动画 2.5s 之后显示:
     - Logo(大字号)
     - 一句话描述
     - 「开始修炼」按钮
  3. 第二次访问(已有 character)则跳过欢迎,直接进 /home
-->
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { characterApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'
import Logo from '../components/Logo.vue'
import WuxiaBackground from '../components/WuxiaBackground.vue'

const router = useRouter()
const game = useGameStore()

const animPhase = ref('curtain')  // curtain → revealing → final
const isReady = ref(false)         // 主内容是否就绪可点击

onMounted(async () => {
  // 已有角色:静默跳 /home,不显示欢迎页
  try {
    const { data } = await characterApi.me()
    if (data) {
      game.setCharacter(data)
      router.replace('/home')
      return
    }
  } catch {
    // 没角色,正常显示欢迎页
  }

  // 开场动画时序:
  // 0ms       curtain(黑屏)
  // 100ms     revealing(墨色晕染展开)
  // 1500ms    final(logo / 文字 / 按钮陆续淡入)
  // 2800ms    isReady=true(按钮可点击)
  setTimeout(() => { animPhase.value = 'revealing' }, 100)
  setTimeout(() => { animPhase.value = 'final' }, 1500)
  setTimeout(() => { isReady.value = true }, 2800)
})

function startGame() {
  if (!isReady.value) return
  router.push('/onboarding')
}

function skipAnim() {
  // 用户点击空白处可跳过动画
  if (animPhase.value !== 'final') {
    animPhase.value = 'final'
    isReady.value = true
  }
}
</script>

<template>
  <div class="welcome-page" @click="skipAnim">
    <!-- 仙侠流动背景 -->
    <WuxiaBackground intensity="rich" accent="#D4A24C" />

    <!-- 开场墨色晕染遮罩 -->
    <Transition name="curtain">
      <div v-if="animPhase === 'curtain'" class="curtain"></div>
    </Transition>
    <Transition name="ink">
      <div v-if="animPhase === 'revealing'" class="ink-wash">
        <div class="ink-blot ink-1"></div>
        <div class="ink-blot ink-2"></div>
        <div class="ink-blot ink-3"></div>
      </div>
    </Transition>

    <!-- 主内容 -->
    <Transition name="main">
      <div v-if="animPhase === 'final'" class="main-content">
        <!-- 顶部装饰花纹 -->
        <div class="ornament-top"></div>

        <!-- Logo + 标题 -->
        <div class="logo-area">
          <Logo :size="140" :show-text="false" />
          <h1 class="title">灵 枢 笔 录</h1>
          <p class="title-en">LINGSHU · CODEX</p>
        </div>

        <!-- 一句话描述 -->
        <p class="tagline">
          以 <strong>笔为引</strong>, 以 <strong>道为引</strong> ——
          一卷由 <strong>AI 大模型</strong> 驱动的修仙文字传奇。
        </p>

        <!-- 开始按钮 -->
        <button
          class="start-btn"
          :disabled="!isReady"
          @click.stop="startGame"
        >
          <span class="btn-ring"></span>
          <span class="btn-text">入 道</span>
          <span class="btn-arrow">→</span>
        </button>

        <!-- 副链接(底部小字)-->
        <div class="meta-links">
          <span>v5.1 · 修真界全开 · 113 妖 · 21 Boss · 5 派</span>
        </div>

        <!-- 中央底部装饰 -->
        <div class="ornament-bottom"></div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.welcome-page {
  position: fixed; inset: 0;
  min-height: 100vh;
  overflow: hidden;
  cursor: pointer;
  background: #050810;
}

/* === 开场黑色幕布 === */
.curtain {
  position: absolute; inset: 0;
  background: #050810;
  z-index: 50;
}
.curtain-leave-active { transition: opacity 0.6s; }
.curtain-leave-to { opacity: 0; }

/* === 墨色晕染 === */
.ink-wash {
  position: absolute; inset: 0;
  z-index: 40;
  pointer-events: none;
}
.ink-blot {
  position: absolute;
  border-radius: 50%;
  filter: blur(30px);
}
.ink-1 {
  top: 30%; left: 50%;
  width: 600px; height: 600px;
  background: radial-gradient(circle, rgba(0,0,0,0.95), rgba(0,0,0,0.4) 70%, transparent);
  transform: translate(-50%, -50%);
  animation: ink-expand 1.4s ease-out forwards;
}
.ink-2 {
  top: 20%; left: 30%;
  width: 400px; height: 400px;
  background: radial-gradient(circle, rgba(20,15,30,0.8), transparent 70%);
  animation: ink-expand 1.4s ease-out 0.2s forwards;
  opacity: 0;
}
.ink-3 {
  top: 70%; left: 75%;
  width: 350px; height: 350px;
  background: radial-gradient(circle, rgba(20,15,30,0.8), transparent 70%);
  animation: ink-expand 1.4s ease-out 0.4s forwards;
  opacity: 0;
}
@keyframes ink-expand {
  0% { transform: scale(0.3) translate(-50%, -50%); opacity: 0; filter: blur(60px); }
  100% { transform: scale(2.5) translate(-20%, -20%); opacity: 0.7; filter: blur(40px); }
}
.ink-enter-active, .ink-leave-active { transition: opacity 0.6s; }
.ink-leave-to { opacity: 0; }

/* === 主内容 === */
.main-content {
  position: relative;
  z-index: 10;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  min-height: 100vh;
  padding: 40px 20px;
  text-align: center;
}
.main-enter-active { transition: opacity 0.8s; }
.main-enter-from { opacity: 0; }

/* 顶/底装饰 */
.ornament-top {
  position: absolute;
  top: 5%; left: 50%;
  width: 200px; height: 1px;
  transform: translateX(-50%);
  background: linear-gradient(90deg, transparent, #D4A24C, transparent);
  animation: orna-glow 4s ease-in-out infinite;
}
.ornament-top::before, .ornament-top::after {
  content: '';
  position: absolute;
  top: -3px;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #D4A24C;
  box-shadow: 0 0 12px #D4A24C;
}
.ornament-top::before { left: 0; }
.ornament-top::after { right: 0; }

.ornament-bottom {
  position: absolute;
  bottom: 5%; left: 50%;
  width: 360px; height: 60px;
  transform: translateX(-50%);
  background:
    radial-gradient(ellipse at center, rgba(212,162,76,0.15), transparent 70%);
  pointer-events: none;
}

@keyframes orna-glow {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

/* Logo + 标题区 */
.logo-area {
  display: flex; flex-direction: column; align-items: center;
  margin-bottom: 32px;
  animation: logo-float 4s ease-in-out infinite;
}
@keyframes logo-float {
  0%, 100% { transform: translateY(0); }
  50%      { transform: translateY(-8px); }
}

.title {
  margin: 24px 0 4px;
  font-family: 'STKaiti', 'KaiTi', 'Source Han Serif SC', serif;
  font-size: 72px;
  letter-spacing: 20px;
  font-weight: 500;
  background: linear-gradient(180deg, #FFE0A3 0%, #D4A24C 50%, #B58A3E 100%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 0 80px rgba(212, 162, 76, 0.3);
  padding-left: 20px;  /* 补 letter-spacing */
  animation: title-shimmer 4s ease-in-out infinite;
}
@keyframes title-shimmer {
  0%, 100% { filter: brightness(1); }
  50%      { filter: brightness(1.25) drop-shadow(0 0 24px rgba(255, 224, 163, 0.4)); }
}

.title-en {
  margin: 0;
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 14px;
  color: #888;
  letter-spacing: 8px;
}

/* tagline */
.tagline {
  margin: 16px 0 48px;
  font-size: 17px;
  color: #ccc;
  letter-spacing: 2px;
  max-width: 600px;
  line-height: 2;
  font-family: 'STKaiti', 'KaiTi', serif;
}
.tagline strong {
  color: #FFE0A3;
  font-weight: 500;
  background: linear-gradient(180deg, transparent 60%, rgba(212,162,76,0.25) 60%);
  padding: 0 4px;
}

/* === 开始按钮(关键) === */
.start-btn {
  position: relative;
  background: transparent;
  border: 1px solid rgba(212, 162, 76, 0.5);
  color: #FFE0A3;
  padding: 18px 64px;
  font-size: 22px;
  letter-spacing: 16px;
  font-family: 'STKaiti', 'KaiTi', serif;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s;
  border-radius: 4px;
  margin-bottom: 24px;
}
.start-btn::before {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(90deg,
    transparent, rgba(212,162,76,0.2), transparent);
  transform: translateX(-100%);
  animation: btn-shine 3s ease-in-out infinite;
}
@keyframes btn-shine {
  0%, 60%, 100% { transform: translateX(-100%); }
  30%, 50%      { transform: translateX(100%); }
}
.start-btn:hover:not(:disabled) {
  background: rgba(212, 162, 76, 0.08);
  border-color: #FFE0A3;
  box-shadow: 0 0 40px rgba(212, 162, 76, 0.5);
  transform: scale(1.04);
  letter-spacing: 20px;
  padding-right: 50px;
}
.start-btn:active {
  transform: scale(0.98);
}

.btn-ring {
  position: absolute; inset: 4px;
  border: 1px solid rgba(212, 162, 76, 0.2);
  border-radius: 2px;
  pointer-events: none;
}
.btn-text {
  position: relative;
  z-index: 1;
}
.btn-arrow {
  display: inline-block;
  margin-left: 8px;
  opacity: 0;
  transform: translateX(-12px);
  transition: all 0.3s;
}
.start-btn:hover .btn-arrow {
  opacity: 1;
  transform: translateX(0);
}
.start-btn:disabled {
  opacity: 0.5; cursor: wait;
  letter-spacing: 16px;
}

.meta-links {
  font-size: 11px;
  color: #555;
  letter-spacing: 3px;
  margin-top: 12px;
  font-family: 'SF Mono', monospace;
}

/* === 入场时序 === */
.main-content .logo-area  { animation: in-up 1s 0.0s both, logo-float 4s ease-in-out 1s infinite; }
.main-content .tagline    { animation: in-up 1s 0.4s both; }
.main-content .start-btn  { animation: in-up 1s 0.7s both; }
.main-content .meta-links { animation: in-up 1s 1.0s both; }
.main-content .ornament-top    { animation: in-up 1s 0.2s both, orna-glow 4s ease-in-out 1.2s infinite; }
.main-content .ornament-bottom { animation: in-up 1s 0.5s both; }

@keyframes in-up {
  from { opacity: 0; transform: translateY(20px); filter: blur(8px); }
  to   { opacity: 1; transform: translateY(0); filter: blur(0); }
}

/* 响应式 */
@media (max-width: 640px) {
  .title { font-size: 44px; letter-spacing: 12px; }
  .tagline { font-size: 14px; padding: 0 16px; }
  .start-btn { font-size: 18px; padding: 14px 40px; letter-spacing: 10px; }
}
</style>
