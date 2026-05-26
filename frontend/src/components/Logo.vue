<!--
  灵枢笔录 · 游戏 LOGO
  - icon: 鎏金圆形徽章 + 中央篆刻"笔"字 + 八方装饰
  - text: 标题中英文(可隐藏)
  - 完全 SVG,矢量无损,缩放任意尺寸
-->
<script setup>
defineProps({
  size: { type: Number, default: 48 },
  showText: { type: Boolean, default: true },
  textSize: { type: Number, default: 22 },
  layout: { type: String, default: 'horizontal' }, // 'horizontal' | 'vertical'
})
</script>

<template>
  <div class="logo" :class="layout">
    <svg class="logo-icon" :width="size" :height="size" viewBox="0 0 100 100" aria-label="灵枢笔录 logo">
      <defs>
        <linearGradient :id="`logoGold-${size}`" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#B58A3E"/>
          <stop offset="35%" stop-color="#D4A24C"/>
          <stop offset="55%" stop-color="#FFE0A3"/>
          <stop offset="80%" stop-color="#D4A24C"/>
          <stop offset="100%" stop-color="#B58A3E"/>
        </linearGradient>
        <radialGradient :id="`logoBg-${size}`" cx="50%" cy="40%" r="60%">
          <stop offset="0%" stop-color="#27273f"/>
          <stop offset="80%" stop-color="#0F0F14"/>
        </radialGradient>
        <filter :id="`logoGlow-${size}`" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="1.5" result="b"/>
          <feMerge>
            <feMergeNode in="b"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>

      <!-- 外圈 -->
      <circle cx="50" cy="50" r="47" :fill="`url(#logoBg-${size})`" :stroke="`url(#logoGold-${size})`" stroke-width="2"/>
      <circle cx="50" cy="50" r="42" fill="none" :stroke="`url(#logoGold-${size})`" stroke-width="0.5" opacity="0.6"/>

      <!-- 八方装饰小线 -->
      <g :stroke="`url(#logoGold-${size})`" stroke-width="0.6" opacity="0.5">
        <line x1="50" y1="6"  x2="50" y2="14"/>
        <line x1="50" y1="86" x2="50" y2="94"/>
        <line x1="6"  y1="50" x2="14" y2="50"/>
        <line x1="86" y1="50" x2="94" y2="50"/>
        <line x1="20" y1="20" x2="25" y2="25"/>
        <line x1="80" y1="20" x2="75" y2="25"/>
        <line x1="20" y1="80" x2="25" y2="75"/>
        <line x1="80" y1="80" x2="75" y2="75"/>
      </g>

      <!-- 中央"笔"字 -->
      <text x="50" y="67" text-anchor="middle"
        font-family="'STKaiti','Kaiti SC','KaiTi','Source Han Serif SC',serif"
        font-size="50" font-weight="700"
        :fill="`url(#logoGold-${size})`"
        :filter="`url(#logoGlow-${size})`">笔</text>

      <!-- 四角墨点 -->
      <circle cx="22" cy="22" r="1.4" fill="#D4A24C" opacity="0.7"/>
      <circle cx="78" cy="22" r="1.0" fill="#D4A24C" opacity="0.55"/>
      <circle cx="22" cy="78" r="1.0" fill="#D4A24C" opacity="0.55"/>
      <circle cx="78" cy="78" r="1.4" fill="#D4A24C" opacity="0.7"/>
    </svg>

    <div v-if="showText" class="logo-text" :style="{ '--text-size': textSize + 'px' }">
      <div class="title-cn">灵枢笔录</div>
      <div class="title-en">LINGSHU CODEX</div>
    </div>
  </div>
</template>

<style scoped>
.logo {
  display: inline-flex;
  align-items: center;
  gap: 14px;
}
.logo.vertical {
  flex-direction: column;
  gap: 10px;
  text-align: center;
}
.logo-icon {
  flex-shrink: 0;
  filter: drop-shadow(0 4px 16px rgba(212, 162, 76, 0.25));
}
.logo-text {
  line-height: 1.1;
}
.logo.vertical .logo-text {
  text-align: center;
}
.title-cn {
  font-family: 'STKaiti','Kaiti SC','KaiTi','Source Han Serif SC',serif;
  font-size: var(--text-size);
  background: linear-gradient(135deg, #D4A24C 0%, #FFE0A3 50%, #D4A24C 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 0.3em;
  padding-left: 0.3em; /* 补偿 letter-spacing 把字符推到右边 */
  font-weight: 500;
}
.title-en {
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: calc(var(--text-size) * 0.36);
  color: #666;
  letter-spacing: 0.35em;
  padding-left: 0.35em;
  margin-top: 4px;
}
</style>
