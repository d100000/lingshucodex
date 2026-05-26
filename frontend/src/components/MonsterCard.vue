<!--
  MonsterCard.vue — 程序化怪物角色卡(无需图片,纯 CSS,113 普通怪通用)
  按 tier / clan / level 自动着色
-->
<script setup>
import { computed } from 'vue'

const props = defineProps({
  enemy: { type: Object, required: true },
  size: { type: String, default: 'medium' },  // small / medium / large
  highlight: { type: Boolean, default: false }, // 选中态(发光)
})

const TIER_COLOR = {
  low:  { main: '#52B788', glow: '#95D5B2', label: '凡' },
  mid:  { main: '#FFB454', glow: '#FFDEA3', label: '妖' },
  high: { main: '#C03F3F', glow: '#FF8888', label: '魔' },
  myth: { main: '#B59CFF', glow: '#D9CCFF', label: '神' },
  boss: { main: '#FFD700', glow: '#FFF5B0', label: '尊' },
}
const tier = computed(() => TIER_COLOR[props.enemy.tier] || TIER_COLOR.low)
</script>

<template>
  <div class="monster-card"
       :class="['size-' + size, 'tier-' + enemy.tier, { highlight }]"
       :style="{ '--main': tier.main, '--glow': tier.glow }">
    <div class="mc-frame-outer"></div>
    <div class="mc-frame-inner"></div>

    <!-- 顶部 banner -->
    <div class="mc-top">
      <span class="mc-tier-badge">{{ tier.label }}</span>
      <span class="mc-level">Lv.{{ enemy.level }}</span>
    </div>

    <!-- 头像(有绘画就显示绘画,否则 emoji) -->
    <div class="mc-portrait">
      <div class="mc-glow"></div>
      <img v-if="enemy.image_url" :src="enemy.image_url" class="mc-img" :alt="enemy.name" />
      <div v-else class="mc-emoji">{{ enemy.image_emoji || enemy.emoji || '👹' }}</div>
    </div>

    <!-- 名字 -->
    <div class="mc-name">{{ enemy.name }}</div>
    <div class="mc-clan">{{ enemy.clan }}</div>

    <!-- 数值条 -->
    <div class="mc-stats" v-if="size !== 'small'">
      <div class="mc-stat"><span class="mc-l">HP</span> <strong>{{ enemy.hp }}</strong></div>
      <div class="mc-stat"><span class="mc-l">攻</span> <strong>{{ enemy.atk }}</strong></div>
      <div class="mc-stat"><span class="mc-l">防</span> <strong>{{ enemy.def_ }}</strong></div>
      <div class="mc-stat"><span class="mc-l">速</span> <strong>{{ enemy.spd }}</strong></div>
    </div>

    <!-- 4 角装饰 -->
    <div class="mc-corner tl"></div>
    <div class="mc-corner tr"></div>
    <div class="mc-corner bl"></div>
    <div class="mc-corner br"></div>
  </div>
</template>

<style scoped>
.monster-card {
  position: relative;
  background:
    radial-gradient(ellipse at top, color-mix(in srgb, var(--main) 18%, transparent), transparent 60%),
    linear-gradient(180deg, rgba(15, 10, 4, 0.95), rgba(5, 3, 1, 0.98));
  border: 1.5px solid var(--main);
  border-radius: 10px;
  padding: 12px 10px;
  text-align: center;
  font-family: 'STKaiti', 'KaiTi', serif;
  box-shadow:
    0 4px 16px rgba(0, 0, 0, 0.6),
    inset 0 0 12px color-mix(in srgb, var(--main) 10%, transparent);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.monster-card.highlight {
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.8),
    0 0 32px color-mix(in srgb, var(--glow) 60%, transparent),
    inset 0 0 20px color-mix(in srgb, var(--main) 25%, transparent);
  transform: translateY(-4px);
}
.size-small  { padding: 8px 6px; }
.size-large  { padding: 16px 14px; }

/* 双层金线 */
.mc-frame-outer {
  position: absolute; inset: -3px;
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--main) 60%, transparent);
  pointer-events: none;
}
.mc-frame-inner {
  position: absolute; inset: 3px;
  border-radius: 7px;
  border: 1px dashed color-mix(in srgb, var(--main) 30%, transparent);
  pointer-events: none;
}

/* 4 角云纹 */
.mc-corner {
  position: absolute;
  width: 8px; height: 8px;
  border: 1.5px solid var(--glow);
  opacity: 0.85;
}
.mc-corner.tl { top: -2px; left: -2px; border-right: 0; border-bottom: 0; }
.mc-corner.tr { top: -2px; right: -2px; border-left: 0; border-bottom: 0; }
.mc-corner.bl { bottom: -2px; left: -2px; border-right: 0; border-top: 0; }
.mc-corner.br { bottom: -2px; right: -2px; border-left: 0; border-top: 0; }

.mc-top {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 8px;
  position: relative; z-index: 2;
}
.mc-tier-badge {
  width: 22px; height: 22px;
  background: radial-gradient(circle, var(--main), color-mix(in srgb, var(--main) 50%, #000));
  color: #fff;
  border-radius: 4px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 12px;
  font-weight: 700;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
  border: 1px solid var(--glow);
}
.mc-level {
  font-size: 11px;
  color: #FFE0A3;
  background: rgba(0,0,0,0.5);
  padding: 2px 8px;
  border-radius: 10px;
  font-family: 'SF Mono', monospace;
  letter-spacing: 1px;
}

.mc-portrait {
  position: relative;
  width: 80px; height: 80px;
  margin: 0 auto 8px;
  display: flex; align-items: center; justify-content: center;
}
.size-small .mc-portrait { width: 56px; height: 56px; }
.size-large .mc-portrait { width: 100px; height: 100px; }

.mc-glow {
  position: absolute; inset: 0;
  border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--glow) 35%, transparent), transparent 70%);
  animation: mc-glow-pulse 3s ease-in-out infinite;
}
@keyframes mc-glow-pulse {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50%      { opacity: 1; transform: scale(1.1); }
}
.mc-emoji {
  position: relative; z-index: 2;
  font-size: 52px;
  filter: drop-shadow(0 0 8px var(--glow));
}
.size-small .mc-emoji { font-size: 36px; }
.size-large .mc-emoji { font-size: 64px; }
.mc-img {
  position: relative; z-index: 2;
  width: 70%; height: 70%;
  border-radius: 50%;
  object-fit: cover;
  filter: drop-shadow(0 0 8px var(--glow));
}
.size-small .mc-img { width: 65%; height: 65%; }
.size-large .mc-img { width: 75%; height: 75%; }

.mc-name {
  font-size: 14px;
  color: var(--glow);
  font-weight: 600;
  letter-spacing: 2px;
  text-shadow: 0 0 8px color-mix(in srgb, var(--main) 80%, transparent);
  margin-bottom: 2px;
}
.size-large .mc-name { font-size: 18px; }

.mc-clan {
  font-size: 10px;
  color: #888;
  letter-spacing: 2px;
  margin-bottom: 8px;
}

.mc-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 8px;
  font-size: 11px;
  padding-top: 6px;
  border-top: 1px dashed color-mix(in srgb, var(--main) 30%, transparent);
}
.mc-stat { display: flex; justify-content: space-between; align-items: baseline; }
.mc-l { color: #aaa; font-size: 10px; }
.mc-stat strong {
  color: #fff;
  font-family: 'SF Mono', monospace;
  font-size: 12px;
}
</style>
