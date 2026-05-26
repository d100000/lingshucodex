<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  item: { type: Object, default: null },
  iconUrl: { type: String, default: '' },
  emoji: { type: String, default: '' },
  name: { type: String, default: '' },
  size: { type: Number, default: 40 },
  radius: { type: Number, default: 8 },
})

const broken = ref(false)

const src = computed(() => {
  if (props.iconUrl) return props.iconUrl
  if (props.item?.icon_url) return props.item.icon_url
  if (props.item?.id) return `/images/items/${props.item.id}.png`
  return ''
})

const fallback = computed(() => props.emoji || props.item?.icon || '🎁')
const altText = computed(() => props.name || props.item?.name || '物品')

watch(src, () => { broken.value = false })
</script>

<template>
  <span
    class="item-icon-art"
    :style="{ '--icon-size': `${size}px`, '--icon-radius': `${radius}px` }"
    aria-hidden="true"
  >
    <img
      v-if="src && !broken"
      :src="src"
      :alt="altText"
      loading="lazy"
      decoding="async"
      @error="broken = true"
    />
    <span v-else class="item-icon-fallback">{{ fallback }}</span>
  </span>
</template>

<style scoped>
.item-icon-art {
  width: var(--icon-size);
  height: var(--icon-size);
  min-width: var(--icon-size);
  display: inline-grid;
  place-items: center;
  overflow: hidden;
  border-radius: var(--icon-radius);
  background:
    radial-gradient(circle at 35% 22%, rgba(255,255,255,0.12), transparent 42%),
    linear-gradient(180deg, rgba(18,20,30,0.96), rgba(5,6,12,0.98));
  box-shadow:
    inset 0 0 0 1px rgba(255,255,255,0.08),
    0 4px 14px rgba(0,0,0,0.28);
}

.item-icon-art img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.item-icon-fallback {
  font-size: calc(var(--icon-size) * 0.62);
  line-height: 1;
}
</style>
