<!--
  FortuneEvent.vue — 奇遇弹窗(古卷展开)
-->
<script setup>
import { computed } from 'vue'
import { prettifyItem } from '../utils/items.js'
import ItemIcon from './ItemIcon.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  fortune: { type: Object, default: () => null },
  applied: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['close', 'goto-battle'])

const highlighted = computed(() => {
  const n = props.fortune?.narrative || ''
  return n.replace(/\*\*([^*]+)\*\*/g, '<em>$1</em>')
})

const effectChips = computed(() => {
  const a = props.applied || {}
  const chips = []
  if (a.hp_delta) chips.push({
    label: `❤️ HP ${a.hp_delta > 0 ? '+' : ''}${a.hp_delta}`,
    type: a.hp_delta > 0 ? 'good' : 'bad',
  })
  if (a.qi_delta) chips.push({
    label: `💧 灵气 ${a.qi_delta > 0 ? '+' : ''}${a.qi_delta}`,
    type: a.qi_delta > 0 ? 'good' : 'bad',
  })
  if (a.exp_delta) chips.push({
    label: `✨ 修为 ${a.exp_delta > 0 ? '+' : ''}${a.exp_delta}`,
    type: a.exp_delta > 0 ? 'good' : 'bad',
  })
  if (a.fatigue_delta) chips.push({
    label: `💤 疲劳 ${a.fatigue_delta > 0 ? '+' : ''}${a.fatigue_delta}`,
    type: a.fatigue_delta > 0 ? 'bad' : 'good',
  })
  if (a.drop) {
    // 优先用后端展平的 drop_name/drop_icon,fallback 走全局字典
    const icon = a.drop_icon || '🎁'
    const name = a.drop_name || prettifyItem(a.drop).replace(/^🎁 /, '')
    chips.push({ label: `获 ${name}`, iconUrl: a.drop_icon_url, emoji: icon, type: 'good' })
  }
  if (a.forced_battle) chips.push({ label: `⚔️ 突遭袭击!`, type: 'warn' })
  return chips
})
</script>

<template>
  <Transition name="fortune-fade">
    <div v-if="visible && fortune" class="fortune-overlay" @click.self="emit('close')">
      <div class="fortune-card">
        <!-- 卷轴顶轴 -->
        <div class="scroll-top"></div>

        <!-- 标题徽章 -->
        <div class="fortune-badge">🌟 奇 遇 🌟</div>
        <h2 class="fortune-name">{{ fortune.name || '路遇奇缘' }}</h2>

        <!-- 叙事正文 -->
        <p class="fortune-narrative" v-html="highlighted"></p>

        <!-- 效果 chips -->
        <div v-if="effectChips.length" class="effects">
          <span v-for="(c, i) in effectChips" :key="i" :class="['chip', 'chip-' + c.type]">
            <ItemIcon
              v-if="c.iconUrl"
              :icon-url="c.iconUrl"
              :emoji="c.emoji"
              :name="c.label"
              :size="20"
              :radius="4"
            />
            {{ c.label }}
          </span>
        </div>

        <!-- 操作按钮 -->
        <div class="actions">
          <button v-if="applied.forced_battle" class="btn-battle"
                  @click="emit('goto-battle', applied.forced_battle)">
            ⚔️ 应战
          </button>
          <button class="btn-close" @click="emit('close')">
            {{ applied.forced_battle ? '暂避' : '继续修行' }}
          </button>
        </div>

        <!-- 卷轴底轴 -->
        <div class="scroll-bottom"></div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.fortune-overlay {
  position: fixed; inset: 0;
  z-index: 200;
  display: flex; align-items: center; justify-content: center;
  background: radial-gradient(ellipse at center, rgba(0,0,0,0.7), rgba(0,0,0,0.9));
  backdrop-filter: blur(6px);
}
.fortune-card {
  position: relative;
  max-width: 520px; width: 90%;
  background-image: url('/images/ui/fortune-scroll.png');
  background-size: cover;
  background-position: center;
  background-color: rgba(40, 28, 12, 0.92);
  border: 1px solid rgba(212,162,76,0.5);
  border-radius: 8px;
  padding: 36px 36px 28px;
  color: #f0e0c0;
  font-family: 'STKaiti', 'KaiTi', serif;
  box-shadow:
    0 20px 80px rgba(0, 0, 0, 0.8),
    0 0 60px rgba(212,162,76,0.25);
  animation: fortune-in 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.fortune-card::before {
  /* 让 bg 图变暗,文字才清晰 */
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(180deg, rgba(20,12,4,0.65), rgba(20,12,4,0.85));
  border-radius: 8px;
  z-index: 0;
}
.fortune-card > * { position: relative; z-index: 1; }
@keyframes fortune-in {
  from { opacity: 0; transform: scale(0.85) translateY(20px); }
  to   { opacity: 1; transform: scale(1); }
}

.scroll-top, .scroll-bottom {
  position: absolute;
  left: -8px; right: -8px;
  height: 14px;
  background: linear-gradient(90deg,
    #5a3a14, #D4A24C 15%, #FFE0A3 50%, #D4A24C 85%, #5a3a14);
  border-radius: 7px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.7);
}
.scroll-top { top: -7px; }
.scroll-bottom { bottom: -7px; }

.fortune-badge {
  text-align: center;
  font-size: 12px;
  color: #D4A24C;
  letter-spacing: 12px;
  margin-bottom: 6px;
}
.fortune-name {
  margin: 0 0 18px;
  text-align: center;
  font-size: 32px;
  color: #FFE0A3;
  letter-spacing: 10px;
  text-shadow: 0 0 24px #D4A24C, 0 2px 6px rgba(0,0,0,0.8);
}
.fortune-narrative {
  margin: 0 0 20px;
  font-size: 16px;
  line-height: 2.1;
  color: #e0d0a8;
  letter-spacing: 1px;
  text-indent: 2em;
  text-align: justify;
}
.fortune-narrative :deep(em) {
  font-style: normal;
  color: #FFE0A3;
  font-weight: 700;
  background: linear-gradient(180deg, transparent 70%, rgba(212,162,76,0.4) 70%);
  padding: 0 3px;
}

.effects {
  display: flex; flex-wrap: wrap; gap: 8px;
  justify-content: center;
  margin: 16px 0;
  padding: 12px;
  background: rgba(0,0,0,0.4);
  border-radius: 8px;
  border: 1px dashed rgba(212,162,76,0.3);
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 14px;
  border-radius: 14px;
  font-size: 12px;
  letter-spacing: 1px;
  border: 1px solid;
}
.chip-good { background: rgba(82,183,136,0.15); color: #95D5B2; border-color: rgba(82,183,136,0.4); }
.chip-bad  { background: rgba(192,63,63,0.15);  color: #FF8888; border-color: rgba(192,63,63,0.4); }
.chip-warn { background: rgba(255,180,84,0.15); color: #FFD898; border-color: rgba(255,180,84,0.5);
             animation: chip-warn-pulse 1s ease-in-out infinite; }
@keyframes chip-warn-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255,180,84,0); }
  50%      { box-shadow: 0 0 0 4px rgba(255,180,84,0.3); }
}

.actions {
  display: flex; gap: 12px; justify-content: center;
  margin-top: 20px;
}
.btn-battle, .btn-close {
  padding: 10px 32px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  letter-spacing: 4px;
  font-family: 'STKaiti', serif;
  font-weight: 600;
}
.btn-battle {
  background: linear-gradient(135deg, #C03F3F, #8B1A1A);
  border: 1.5px solid #FF8888;
  color: #FFE0E0;
  animation: chip-warn-pulse 1.2s ease-in-out infinite;
}
.btn-battle:hover {
  background: linear-gradient(135deg, #D04F4F, #A02A2A);
  transform: translateY(-2px);
}
.btn-close {
  background: linear-gradient(135deg, #D4A24C, #8B5A1A);
  border: 1.5px solid #FFE0A3;
  color: #1a1a1a;
}
.btn-close:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(212, 162, 76, 0.5);
}

.fortune-fade-enter-active, .fortune-fade-leave-active { transition: opacity 0.3s; }
.fortune-fade-enter-from, .fortune-fade-leave-to { opacity: 0; }
</style>
