<template>
  <div class="skeleton-block">
    <span></span>
    <span></span>
    <span></span>
  </div>
</template>

<style scoped>
.skeleton-block {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.025);
}
span {
  height: 14px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(255,255,255,0.06), rgba(255,255,255,0.13), rgba(255,255,255,0.06));
  background-size: 220% 100%;
  animation: shimmer 1.2s ease-in-out infinite;
}
span:nth-child(2) { width: 76%; }
span:nth-child(3) { width: 52%; }
@keyframes shimmer {
  to { background-position: -220% 0; }
}
</style>
