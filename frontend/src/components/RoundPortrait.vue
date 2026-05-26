<!--
  RoundPortrait.vue — 统一立绘组件

  自动从约定路径加载图,加载失败 → SVG 占位符(国风水墨人影)。

  Props:
    kind: 'player' | 'disciple' | 'enemy' | 'boss' | 'sect'(必填)
    id:   对应 kind 的 ID(例: kind=player 时传 'canglan/qi', kind=enemy 时传 'fox_01')
    size: 像素值(默认 96)
    shape: 'circle' | 'square' | 'card'(默认 circle)
    frame: 边框颜色(默认 #D4A24C)
    name: 鼠标 hover/无图时显示

  用法:
    <RoundPortrait kind="enemy" id="fox_01" :size="128" />
    <RoundPortrait kind="player" id="canglan/qi" :size="96" frame="#D4A24C" />
    <RoundPortrait kind="boss" id="boss_deepmind" :size="160" shape="card" />
-->
<script setup>
import { ref, computed, watch } from 'vue'
import { openCharacterPreview } from '../utils/characterPreview.js'

const props = defineProps({
  kind:  { type: String, required: true, validator: v => ['player','disciple','enemy','boss','sect'].includes(v) },
  id:    { type: String, required: true },
  size:  { type: Number, default: 96 },
  shape: { type: String, default: 'circle', validator: v => ['circle','square','card'].includes(v) },
  frame: { type: String, default: '#D4A24C' },
  name:  { type: String, default: '' },
  // 等级数字(玩家用)
  level: { type: [Number, String], default: '' },
  preview: { type: Object, default: null },
})

const imgError = ref(false)

const imgSrc = computed(() => {
  if (props.kind === 'player') return `/images/portraits/players/${props.id}.png`   // id 形如 canglan/qi
  if (props.kind === 'disciple') return `/images/portraits/disciples/${props.id}.png`
  if (props.kind === 'enemy')  return `/images/portraits/enemies/${props.id}.png`
  if (props.kind === 'boss')   return `/images/portraits/bosses/${props.id}.png`
  if (props.kind === 'sect')   return `/images/portraits/sects/${props.id}.png`
  return ''
})

// id/kind 变了重置错误状态
watch(() => [props.kind, props.id], () => { imgError.value = false })

const sizePx = computed(() => `${props.size}px`)
const radius = computed(() => {
  if (props.shape === 'circle') return '50%'
  if (props.shape === 'square') return '8px'
  return '12px'   // card
})

const fallbackInitial = computed(() => {
  if (props.name) return props.name.charAt(0)
  if (props.id) return props.id.charAt(0).toUpperCase()
  return '?'
})

function onOpenPreview(event) {
  if (!props.preview) return
  event.stopPropagation()
  openCharacterPreview(props.preview)
}
</script>

<template>
  <div class="round-portrait" :class="{ clickable: !!preview }" :title="preview ? '查看角色志' : (name || id)" @click="onOpenPreview" :style="{
    width: sizePx, height: sizePx,
    borderRadius: radius,
    borderColor: frame,
    boxShadow: `0 0 12px ${frame}40, inset 0 0 8px ${frame}30`,
  }">
    <img
      v-if="imgSrc && !imgError"
      :src="imgSrc"
      :alt="name || id"
      class="portrait-img"
      :style="{ borderRadius: radius }"
      @error="imgError = true"
    />
    <div v-else class="portrait-fallback" :style="{ borderRadius: radius }">
      <svg viewBox="0 0 64 64" class="ink-figure">
        <!-- 国风水墨人影 SVG fallback -->
        <defs>
          <radialGradient id="rp-glow" cx="50%" cy="40%">
            <stop offset="0%" :stop-color="frame" stop-opacity="0.45" />
            <stop offset="100%" :stop-color="frame" stop-opacity="0" />
          </radialGradient>
        </defs>
        <circle cx="32" cy="32" r="28" fill="url(#rp-glow)" />
        <!-- 头 -->
        <circle cx="32" cy="24" r="9" :fill="frame" opacity="0.7" />
        <!-- 身 -->
        <path d="M 16 56 Q 16 36 32 36 Q 48 36 48 56 Z" :fill="frame" opacity="0.55" />
      </svg>
      <span class="fb-initial">{{ fallbackInitial }}</span>
    </div>
    <!-- 等级角标(玩家用) -->
    <div v-if="level" class="lv-badge" :style="{ background: frame }">
      Lv {{ level }}
    </div>
  </div>
</template>

<style scoped>
.round-portrait {
  position: relative;
  overflow: hidden;
  border-width: 2px;
  border-style: solid;
  background: linear-gradient(135deg, rgba(15, 20, 32, 0.95), rgba(8, 12, 24, 0.98));
  flex-shrink: 0;
  display: inline-block;
  vertical-align: middle;
}
.round-portrait.clickable {
  cursor: pointer;
}
.round-portrait.clickable::after {
  content: '阅';
  position: absolute;
  left: 6px;
  top: 6px;
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255,224,163,0.45);
  background: rgba(8,8,18,0.72);
  color: #FFE0A3;
  font-size: 12px;
  border-radius: 50%;
  opacity: 0;
  transform: translateY(-3px);
  transition: opacity 0.18s, transform 0.18s;
}
.round-portrait.clickable:hover::after {
  opacity: 1;
  transform: translateY(0);
}
.round-portrait.clickable:hover {
  filter: brightness(1.08);
}
.portrait-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.portrait-fallback {
  width: 100%; height: 100%;
  position: relative;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, rgba(15, 20, 32, 0.95), rgba(8, 12, 24, 0.98));
}
.ink-figure { width: 70%; height: 70%; }
.fb-initial {
  position: absolute;
  font-family: 'STKaiti', 'KaiTi', serif;
  font-weight: bold;
  font-size: 38%;
  color: #FFE0A3;
  text-shadow: 0 1px 4px rgba(0,0,0,0.8);
  letter-spacing: 1px;
}
.lv-badge {
  position: absolute;
  bottom: -2px;
  right: -2px;
  color: #0F1B2E;
  font-size: 11px;
  font-weight: bold;
  padding: 2px 7px;
  border-radius: 10px;
  border: 1.5px solid rgba(255,255,255,0.4);
  box-shadow: 0 2px 6px rgba(0,0,0,0.5);
  font-family: 'SF Mono', monospace;
}
</style>
