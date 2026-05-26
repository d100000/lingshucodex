<script setup>
defineProps({
  title: { type: String, default: '暂无内容' },
  desc: { type: String, default: '' },
  action: { type: String, default: '' },
})
const emit = defineEmits(['action'])
</script>

<template>
  <section class="empty-state">
    <div class="empty-mark">◇</div>
    <h3>{{ title }}</h3>
    <p v-if="desc">{{ desc }}</p>
    <button v-if="action" @click="emit('action')">{{ action }}</button>
  </section>
</template>

<style scoped>
.empty-state {
  display: grid;
  place-items: center;
  gap: 8px;
  min-height: 160px;
  padding: 28px 16px;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  background: rgba(255,255,255,0.025);
  text-align: center;
  color: #9CA8BB;
}
.empty-mark { color: #D4A24C; font-size: 30px; }
h3 { margin: 0; color: #F3E4C3; font-size: 17px; }
p { margin: 0; line-height: 1.7; }
button {
  margin-top: 6px;
  min-height: 38px;
  border: 1px solid rgba(212,162,76,0.42);
  background: rgba(212,162,76,0.12);
  color: #FFE0A3;
  border-radius: 6px;
  padding: 0 14px;
}
</style>
