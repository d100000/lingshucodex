<script setup>
import { computed, ref, watch } from 'vue'
import { getSectTheme } from '../config/sectTheme.js'

const props = defineProps({
  sectId: { type: String, default: 'canglan' },
  name: { type: String, default: '' },
  size: { type: Number, default: 40 },
  radius: { type: Number, default: 8 },
})

const broken = ref(false)
const theme = computed(() => getSectTheme(props.sectId))
const src = computed(() => theme.value.flag || `/images/sects/flags/${props.sectId || 'canglan'}.png`)
const label = computed(() => props.name || theme.value.name || '宗门旗帜')

watch(src, () => { broken.value = false })
</script>

<template>
  <span
    class="sect-flag"
    :style="{ '--flag-size': `${size}px`, '--flag-radius': `${radius}px`, '--flag-accent': theme.accent }"
  >
    <img
      v-if="src && !broken"
      :src="src"
      :alt="label"
      loading="lazy"
      decoding="async"
      @error="broken = true"
    />
    <span v-else class="sect-flag-fallback">{{ theme.emoji }}</span>
  </span>
</template>

<style scoped>
.sect-flag {
  width: var(--flag-size);
  height: var(--flag-size);
  min-width: var(--flag-size);
  display: inline-grid;
  place-items: center;
  overflow: hidden;
  border-radius: var(--flag-radius);
  background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
  box-shadow:
    inset 0 0 0 1px color-mix(in srgb, var(--flag-accent, #D4A24C) 52%, transparent),
    0 0 16px color-mix(in srgb, var(--flag-accent, #D4A24C) 18%, transparent),
    0 6px 18px rgba(0,0,0,0.30);
}

.sect-flag img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.sect-flag-fallback {
  font-size: calc(var(--flag-size) * 0.6);
  line-height: 1;
}
</style>
