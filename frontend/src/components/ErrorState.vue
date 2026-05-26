<script setup>
defineProps({
  title: { type: String, default: '灵脉暂断' },
  desc: { type: String, default: '当前内容加载失败,可稍后重试。' },
})
const emit = defineEmits(['retry', 'feedback'])
</script>

<template>
  <section class="error-state">
    <div>
      <p>{{ title }}</p>
      <span>{{ desc }}</span>
    </div>
    <div class="actions">
      <button @click="emit('retry')">重试</button>
      <button class="ghost" @click="emit('feedback')">反馈</button>
    </div>
  </section>
</template>

<style scoped>
.error-state {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
  padding: 14px;
  border: 1px solid rgba(255,180,84,0.3);
  border-radius: 8px;
  background: rgba(255,180,84,0.06);
}
p { margin: 0 0 4px; color: #FFE0A3; font-weight: 800; }
span { color: #B8C7E0; font-size: 13px; }
.actions { display: flex; gap: 8px; }
button {
  min-height: 34px;
  border: 1px solid rgba(212,162,76,0.42);
  border-radius: 6px;
  background: rgba(212,162,76,0.12);
  color: #FFE0A3;
  padding: 0 12px;
}
.ghost {
  border-color: rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.04);
  color: #B8C7E0;
}
@media (max-width: 520px) {
  .error-state { align-items: stretch; flex-direction: column; }
}
</style>
