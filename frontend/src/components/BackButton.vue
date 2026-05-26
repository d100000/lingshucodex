<!--
  统一返回按钮 — 固定在左上角,鎏金高对比,一眼可见

  使用方式:
    <BackButton @click="myBack" label="回主城" />
    <BackButton to="/home" />                    <!-- 直接给 router path -->
    <BackButton :confirm="'确定离开?'" to="/" />   <!-- 带确认弹窗 -->
-->
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDialog } from 'naive-ui'

const router = useRouter()
const dialog = useDialog()

const props = defineProps({
  to: { type: String, default: '' },
  label: { type: String, default: '返回' },
  loadingLabel: { type: String, default: '撤离中...' },
  confirm: { type: String, default: '' },
  icon: { type: String, default: '←' },
  // inline=true → 不再 fixed,可放在顶栏内
  inline: { type: Boolean, default: false },
  // 外部驱动 loading(战斗页之类的异步退出)
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['click'])

const internalLoading = ref(false)
// 实际 loading 状态:外部 props 或内部点击触发
const isLoading = ref(false)

function handle() {
  if (isLoading.value) return  // ★ 防止重复点击
  const doIt = () => {
    internalLoading.value = true
    isLoading.value = true
    emit('click')
    if (props.to) {
      // 路由跳转,组件即将销毁,loading 自然消失
      router.push(props.to).catch(() => {
        internalLoading.value = false
        isLoading.value = false
      })
    } else {
      // 父组件控制跳转 — 800ms 后兜底解锁(防止父组件忘了关 loading)
      setTimeout(() => {
        internalLoading.value = false
        isLoading.value = props.loading
      }, 800)
    }
  }
  if (props.confirm) {
    dialog.warning({
      title: '提示',
      content: props.confirm,
      positiveText: '确定',
      negativeText: '取消',
      onPositiveClick: doIt,
    })
  } else {
    doIt()
  }
}
// 监听外部 loading
import { watch } from 'vue'
watch(() => props.loading, v => { isLoading.value = v || internalLoading.value })
</script>

<template>
  <button :class="['back-btn', { 'back-btn-inline': inline, 'is-loading': isLoading }]"
          :disabled="isLoading"
          @click="handle">
    <span class="back-arrow">
      <span v-if="isLoading" class="back-spinner">◐</span>
      <span v-else>{{ icon }}</span>
    </span>
    <span class="back-label">{{ isLoading ? loadingLabel : label }}</span>
    <span class="back-shine"></span>
  </button>
</template>

<style scoped>
.back-btn {
  position: fixed;
  top: 18px;
  left: 18px;
  z-index: 100;
  display: inline-flex;
  align-items: center;
  gap: 8px;

  background: linear-gradient(135deg, rgba(212, 162, 76, 0.18), rgba(212, 162, 76, 0.06));
  border: 1.5px solid rgba(212, 162, 76, 0.6);
  color: #FFE0A3;
  padding: 10px 18px 10px 14px;
  border-radius: 24px;

  font-size: 14px;
  font-weight: 500;
  letter-spacing: 3px;
  font-family: 'STKaiti', 'KaiTi', 'Source Han Serif SC', system-ui, sans-serif;
  cursor: pointer;
  overflow: hidden;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);

  /* 默认就有金色光晕,确保显眼 */
  box-shadow:
    0 4px 16px rgba(0, 0, 0, 0.4),
    0 0 0 0 rgba(212, 162, 76, 0.5);
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);

  /* 持续脉动光环,引导用户视觉 */
  animation: back-pulse 2.4s ease-in-out infinite;
}
/* ★ inline 模式:嵌入顶栏使用,避免与 Logo 重叠 — 用 !important 强制覆盖 fixed */
.back-btn.back-btn-inline {
  position: static !important;
  top: auto !important;
  left: auto !important;
  right: auto !important;
  bottom: auto !important;
  z-index: auto !important;
  padding: 7px 14px 7px 10px;
  font-size: 12px;
  letter-spacing: 2px;
  margin: 0;
  /* 内联场景下也保留脉动光圈,但取消默认外阴影避免视觉跑到外面 */
  flex-shrink: 0;
}

@keyframes back-pulse {
  0%, 100% {
    box-shadow:
      0 4px 16px rgba(0, 0, 0, 0.4),
      0 0 0 0 rgba(212, 162, 76, 0.5);
  }
  50% {
    box-shadow:
      0 4px 20px rgba(0, 0, 0, 0.5),
      0 0 0 6px rgba(212, 162, 76, 0);
  }
}

.back-arrow {
  display: inline-block;
  font-size: 18px;
  font-weight: 700;
  color: #FFE0A3;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(212, 162, 76, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  text-shadow: 0 0 8px rgba(255, 224, 163, 0.6);
  transition: transform 0.3s;
}

.back-label {
  position: relative;
  z-index: 2;
}

/* 流光扫过(每 3s 一次)*/
.back-shine {
  position: absolute;
  top: 0;
  left: -50%;
  width: 40%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 224, 163, 0.4),
    transparent
  );
  animation: back-shine 3s ease-in-out infinite;
  pointer-events: none;
}
@keyframes back-shine {
  0%, 60%, 100% { left: -50%; }
  30% { left: 110%; }
}

/* === Hover === */
.back-btn:hover {
  background: linear-gradient(135deg, rgba(212, 162, 76, 0.35), rgba(255, 224, 163, 0.15));
  border-color: #FFE0A3;
  transform: translateX(-3px);
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.5),
    0 0 24px rgba(212, 162, 76, 0.4);
  animation-play-state: paused;
}

.back-btn:hover .back-arrow {
  transform: translateX(-3px) scale(1.15);
  background: rgba(255, 224, 163, 0.4);
}

.back-btn:active {
  transform: translateX(-5px) scale(0.97);
}

/* ★ loading 态:暗化 + 禁用脉动 + spinner 旋转 */
.back-btn.is-loading {
  cursor: wait;
  opacity: 0.75;
  animation: none;
  background: linear-gradient(135deg, rgba(127, 199, 232, 0.18), rgba(127, 199, 232, 0.06));
  border-color: rgba(127, 199, 232, 0.7);
  color: #C7E5F5;
}
.back-btn.is-loading:hover {
  transform: none;
  background: linear-gradient(135deg, rgba(127, 199, 232, 0.18), rgba(127, 199, 232, 0.06));
}
.back-btn.is-loading .back-arrow {
  background: rgba(127, 199, 232, 0.25);
}
.back-btn.is-loading .back-shine {
  animation: none;
  display: none;
}
.back-spinner {
  display: inline-block;
  animation: back-spin 0.8s linear infinite;
  font-size: 16px;
  color: #C7E5F5;
}
@keyframes back-spin { to { transform: rotate(360deg); } }
.back-btn:disabled {
  pointer-events: none;
}

/* 小屏幕:简化样式但保持显眼 */
@media (max-width: 640px) {
  .back-btn {
    padding: 8px 14px 8px 10px;
    font-size: 13px;
    letter-spacing: 2px;
  }
  .back-arrow {
    width: 20px;
    height: 20px;
    font-size: 16px;
  }
}
</style>
