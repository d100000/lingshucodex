<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { MOBILE_FEEDBACK_EVENT, readTelemetry } from '../utils/mobile.js'

const route = useRoute()
const show = ref(false)
const category = ref('ui')
const content = ref('')
const sent = ref(false)
const context = ref({})

const categories = [
  { id: 'bug', label: 'Bug' },
  { id: 'lag', label: '卡顿' },
  { id: 'chapter', label: '断章' },
  { id: 'battle', label: '战斗' },
  { id: 'ui', label: '遮挡' },
  { id: 'idea', label: '建议' },
]

const visible = computed(() => !route.meta.hideFeedback)
const preview = computed(() => ({
  route: route.fullPath,
  viewport: typeof window === 'undefined' ? '' : `${window.innerWidth}x${window.innerHeight}`,
  online: typeof navigator === 'undefined' ? true : navigator.onLine,
  logs: readTelemetry().slice(-8),
  ...context.value,
}))

function onFeedbackEvent(event) {
  open(event.detail || {})
}

function open(payload = {}) {
  context.value = payload
  category.value = payload.category || 'ui'
  content.value = ''
  sent.value = false
  show.value = true
}

function close() {
  show.value = false
}

function submit() {
  const item = {
    id: `fb_${Date.now()}`,
    category: category.value,
    content: content.value.trim(),
    context: preview.value,
    at: new Date().toISOString(),
  }
  try {
    const key = 'lingshu_feedback_buffer'
    const list = JSON.parse(localStorage.getItem(key) || '[]')
    list.push(item)
    localStorage.setItem(key, JSON.stringify(list.slice(-50)))
  } catch (_) {}
  sent.value = true
}

onMounted(() => window.addEventListener(MOBILE_FEEDBACK_EVENT, onFeedbackEvent))
onUnmounted(() => window.removeEventListener(MOBILE_FEEDBACK_EVENT, onFeedbackEvent))
</script>

<template>
  <div v-if="visible" class="feedback-entry">
    <button class="feedback-fab" @click="open({ category: 'ui' })">BETA<br>反馈</button>
  </div>

  <Teleport to="body">
    <Transition name="feedback">
      <div v-if="show" class="feedback-layer" @click.self="close">
        <section class="feedback-card">
          <header>
            <div>
              <p>BETA 内测反馈</p>
              <h3>记录一次修行异常</h3>
            </div>
            <button @click="close">关闭</button>
          </header>

          <template v-if="!sent">
            <div class="category-row">
              <button
                v-for="c in categories"
                :key="c.id"
                :class="{ active: category === c.id }"
                @click="category = c.id"
              >
                {{ c.label }}
              </button>
            </div>
            <textarea v-model="content" maxlength="600" placeholder="描述你遇到的问题,比如遮挡、卡顿、断章、战斗无法恢复等。" />
            <div class="context-box">
              <strong>自动附带</strong>
              <span>{{ preview.route }} · {{ preview.viewport }} · {{ preview.online ? '在线' : '离线' }}</span>
            </div>
            <button class="submit" :disabled="!content.trim()" @click="submit">提交到本机反馈箱</button>
          </template>

          <div v-else class="sent-box">
            <strong>已记录</strong>
            <p>反馈已保存到本机内测反馈箱,后续接入服务端后可直接同步。</p>
            <button class="submit" @click="close">知道了</button>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.feedback-entry {
  position: fixed;
  right: calc(12px + var(--safe-right));
  bottom: calc(88px + var(--safe-bottom));
  z-index: 170;
  pointer-events: none;
}

.feedback-fab {
  pointer-events: auto;
  width: 54px;
  height: 54px;
  border: 1px solid rgba(127, 199, 232, 0.42);
  border-radius: 50%;
  background: rgba(8, 18, 30, 0.88);
  color: #B8E4FF;
  font-size: 10px;
  line-height: 1.2;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.32);
}

.feedback-layer {
  position: fixed;
  inset: 0;
  z-index: 540;
  display: grid;
  place-items: center;
  padding: calc(18px + var(--safe-top)) calc(14px + var(--safe-right)) calc(18px + var(--safe-bottom)) calc(14px + var(--safe-left));
  background: rgba(0, 0, 0, 0.68);
}

.feedback-card {
  width: min(520px, 100%);
  border: 1px solid rgba(212, 162, 76, 0.34);
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(18, 18, 32, 0.98), rgba(8, 8, 18, 0.98));
  padding: 16px;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.48);
}

header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

header p {
  margin: 0 0 4px;
  color: #7FC7E8;
  font-size: 12px;
}

header h3 {
  margin: 0;
  color: #FFE0A3;
}

header button,
.category-row button,
.submit {
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  color: #D8E0EE;
  min-height: 34px;
  padding: 0 12px;
  cursor: pointer;
}

.category-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.category-row button.active {
  color: #1A1208;
  background: #D4A24C;
  border-color: #FFE0A3;
  font-weight: 800;
}

textarea {
  width: 100%;
  min-height: 128px;
  resize: vertical;
  box-sizing: border-box;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.28);
  color: #F3E4C3;
  padding: 12px;
  font: inherit;
  font-size: 16px;
}

.context-box {
  display: grid;
  gap: 4px;
  margin: 10px 0;
  padding: 10px;
  border: 1px solid rgba(127, 199, 232, 0.18);
  border-radius: 6px;
  color: #9CA8BB;
  font-size: 12px;
}

.context-box strong {
  color: #7FC7E8;
}

.submit {
  width: 100%;
  min-height: 42px;
  border-color: rgba(212, 162, 76, 0.42);
  background: rgba(212, 162, 76, 0.14);
  color: #FFE0A3;
  font-weight: 800;
}

.submit:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.sent-box {
  text-align: center;
  color: #C8D0DE;
}

.sent-box strong {
  display: block;
  color: #95D5B2;
  font-size: 20px;
  margin-bottom: 8px;
}

.feedback-enter-active,
.feedback-leave-active {
  transition: opacity 0.18s;
}
.feedback-enter-from,
.feedback-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .feedback-entry {
    bottom: calc(86px + var(--safe-bottom));
  }
}

@media (orientation: landscape) and (max-height: 480px) {
  .feedback-entry {
    left: calc(80px + var(--safe-left));
    right: auto;
    bottom: calc(10px + var(--safe-bottom));
  }
}
</style>
