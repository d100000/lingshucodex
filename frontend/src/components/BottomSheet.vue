<script setup>
const props = defineProps({
  show: { type: Boolean, default: false },
  title: { type: String, default: '' },
  sideOnLandscape: { type: Boolean, default: true },
  closeText: { type: String, default: '关闭' },
})
const emit = defineEmits(['close'])
</script>

<template>
  <Teleport to="body">
    <Transition name="sheet-fade">
      <div v-if="props.show" class="sheet-layer" @click.self="emit('close')">
        <section class="bottom-sheet" :class="{ side: props.sideOnLandscape }" role="dialog" aria-modal="true">
          <header class="sheet-head">
            <div class="sheet-handle"></div>
            <h3>{{ props.title }}</h3>
            <button class="sheet-close" @click="emit('close')">{{ props.closeText }}</button>
          </header>
          <div class="sheet-body">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="sheet-footer">
            <slot name="footer" />
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.sheet-layer {
  position: fixed;
  inset: 0;
  z-index: 360;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: calc(20px + var(--safe-top)) calc(12px + var(--safe-right)) calc(12px + var(--safe-bottom)) calc(12px + var(--safe-left));
  background: rgba(0, 0, 0, 0.42);
}

.bottom-sheet {
  width: min(560px, 100%);
  max-height: min(82dvh, calc(var(--visual-vh, 100vh) - 28px));
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  border: 1px solid rgba(212, 162, 76, 0.34);
  border-radius: 10px 10px 8px 8px;
  background: linear-gradient(180deg, rgba(18, 16, 27, 0.98), rgba(7, 8, 18, 0.98));
  box-shadow: 0 -16px 46px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

.sheet-head {
  position: sticky;
  top: 0;
  z-index: 1;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
  align-items: center;
  padding: 14px 14px 10px;
  border-bottom: 1px solid rgba(212, 162, 76, 0.18);
  background: rgba(12, 12, 22, 0.98);
}

.sheet-handle {
  grid-column: 1 / -1;
  justify-self: center;
  width: 42px;
  height: 4px;
  border-radius: 999px;
  background: rgba(212, 162, 76, 0.42);
}

.sheet-head h3 {
  margin: 0;
  color: #FFE0A3;
  font-size: 16px;
  letter-spacing: 2px;
}

.sheet-close {
  min-height: 32px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  color: #B8C7E0;
  padding: 0 10px;
  cursor: pointer;
}

.sheet-body {
  min-height: 0;
  overflow: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
  padding: 14px;
}

.sheet-footer {
  padding: 10px 14px calc(12px + var(--safe-bottom));
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(8, 8, 18, 0.98);
}

.sheet-fade-enter-active,
.sheet-fade-leave-active {
  transition: opacity 0.18s ease;
}
.sheet-fade-enter-from,
.sheet-fade-leave-to {
  opacity: 0;
}

@media (orientation: landscape) and (max-height: 520px) {
  .sheet-layer {
    align-items: stretch;
    justify-content: flex-end;
  }
  .bottom-sheet.side {
    width: min(420px, calc(100vw - 88px));
    max-height: 100%;
    border-radius: 8px;
    box-shadow: -16px 0 42px rgba(0, 0, 0, 0.46);
  }
}
</style>
