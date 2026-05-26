<!--
  SectBackground.vue — 宗门全屏背景图层(带候选 URL fallback)

  按候选顺序探测:
    1. /images/sect-bg-{sectId}.png       (横版专用,放高清图时用)
    2. /images/portraits/sects/{sectId}.png (复用现有的肖像图)
    3. /images/home-city-bg.png            (终极兜底)
  用 <img onerror> 真正检测加载失败 — Vite SPA fallback 会让任何不存在的路径返回 HTML
  导致 `background-image: url()` 静默失败,所以必须主动探测。

  使用:
    <SectBackground :sect-id="character.sect" />
    <SectBackground sect-id="canglan" overlay="strong" :opacity="0.4" />
-->
<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  sectId: { type: String, default: 'canglan' },
  opacity: { type: Number, default: 0.45 },
  overlay: { type: String, default: 'normal' }, // normal / strong / light
})

const candidates = computed(() => [
  // ★ 优先 jpg(压缩后 ~600KB,比 png 小 75%)
  `/images/sect-bg-${props.sectId}.jpg`,
  `/images/sect-bg-${props.sectId}.png`,
  `/images/portraits/sects/${props.sectId}.png`,
  `/images/home-city-bg.png`,
])

const resolvedUrl = ref('')
const probing = ref(false)

/** 真探测:加载一张 image 看 onload/onerror */
function probe(url) {
  return new Promise((resolve) => {
    const img = new Image()
    let settled = false
    const finish = (ok) => {
      if (!settled) { settled = true; resolve(ok) }
    }
    img.onload = () => {
      // Vite SPA fallback 给 HTML 返回时,有些浏览器仍触发 onload
      // 用图片实际尺寸过滤:< 50px 的多半是错误占位
      finish(img.naturalWidth > 50 && img.naturalHeight > 50)
    }
    img.onerror = () => finish(false)
    img.src = url
    setTimeout(() => finish(false), 4000)
  })
}

async function resolve() {
  probing.value = true
  for (const url of candidates.value) {
    if (await probe(url)) {
      resolvedUrl.value = url
      probing.value = false
      return
    }
  }
  // 全失败,留空 — 仅显示遮罩
  resolvedUrl.value = ''
  probing.value = false
}

watch(() => props.sectId, resolve, { immediate: true })
</script>

<template>
  <div class="sect-bg" :data-sect="sectId" aria-hidden="true">
    <!-- 1. 背景图本体 -->
    <div
      v-if="resolvedUrl"
      class="sect-bg-image"
      :style="{
        backgroundImage: `url('${resolvedUrl}')`,
        opacity: opacity,
      }"
    ></div>
    <!-- 2. 暗化遮罩 -->
    <div class="sect-bg-overlay" :class="'overlay-' + overlay"></div>
    <!-- 3. 门派色晕 -->
    <div class="sect-bg-tint"></div>
  </div>
</template>

<style scoped>
.sect-bg {
  position: fixed; inset: 0;
  z-index: -10;
  pointer-events: none;
  overflow: hidden;
}

.sect-bg-image {
  position: absolute; inset: 0;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  filter: saturate(0.82) brightness(0.85);
  transition: opacity 0.6s ease, background-image 0.6s ease, filter 0.6s ease;
  animation: bg-breathe 24s ease-in-out infinite;
}
@keyframes bg-breathe {
  0%, 100% { transform: scale(1); }
  50%      { transform: scale(1.04); }
}

.sect-bg-overlay {
  position: absolute; inset: 0;
  transition: background 0.5s ease;
}
.overlay-light {
  background:
    radial-gradient(ellipse at center, rgba(5, 8, 16, 0.18) 0%, rgba(5, 8, 16, 0.55) 100%);
}
.overlay-normal {
  background:
    radial-gradient(ellipse at center, rgba(5, 8, 16, 0.45) 0%, rgba(5, 8, 16, 0.78) 100%),
    linear-gradient(180deg, rgba(5, 8, 16, 0.28) 0%, rgba(5, 8, 16, 0.50) 100%);
}
.overlay-strong {
  background:
    radial-gradient(ellipse at center, rgba(5, 8, 16, 0.62) 0%, rgba(5, 8, 16, 0.88) 100%),
    linear-gradient(180deg, rgba(5, 8, 16, 0.45) 0%, rgba(5, 8, 16, 0.72) 100%);
}

.sect-bg-tint {
  position: absolute; inset: 0;
  background:
    radial-gradient(ellipse at 50% 0%, color-mix(in srgb, var(--sect-accent, #D4A24C) 8%, transparent) 0%, transparent 45%),
    radial-gradient(ellipse at 50% 100%, color-mix(in srgb, var(--sect-primary, #1a1a2e) 25%, transparent) 0%, transparent 60%);
}
</style>
