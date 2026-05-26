<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { novelApi } from '../api/client.js'
import BackButton from '../components/BackButton.vue'
import { renderMarkdown } from '../utils/markdown.js'
import ErrorState from '../components/ErrorState.vue'
import SkeletonBlock from '../components/SkeletonBlock.vue'
import { openFeedback } from '../utils/mobile.js'

const route = useRoute()
const chapter = ref(null)
const loading = ref(true)
const error = ref('')
const fontSize = ref(17)
const renderedContent = computed(() => renderMarkdown(chapter.value?.content || ''))

onMounted(async () => {
  try {
    const { data } = await novelApi.chapter(route.params.id)
    chapter.value = data.chapter
  } catch (e) {
    error.value = e.message || '章节加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="chapter-page">
    <BackButton to="/novel" label="回本命书" />
    <SkeletonBlock v-if="loading" />
    <ErrorState
      v-else-if="error"
      title="章节暂未展开"
      :desc="error"
      @retry="() => location.reload()"
      @feedback="openFeedback({ category: 'chapter', source: 'novel_chapter', chapter: route.params.id, error })"
    />
    <article v-else-if="chapter" class="reader">
      <header>
        <p>第 {{ chapter.chapter_no }} 章 · 第 {{ chapter.volume_no }} 卷</p>
        <h1>{{ chapter.title }}</h1>
        <div class="meta">
          <span>{{ chapter.chapter_type }}</span>
          <span v-if="chapter.is_partial" class="warn">断章</span>
          <span>{{ chapter.token_count }} token</span>
          <span>修为 +{{ chapter.cultivation_gained }}</span>
          <span>{{ chapter.model || '默认模型' }}</span>
        </div>
        <div class="reader-actions">
          <button :class="{ active: fontSize === 16 }" @click="fontSize = 16">小</button>
          <button :class="{ active: fontSize === 17 }" @click="fontSize = 17">中</button>
          <button :class="{ active: fontSize === 19 }" @click="fontSize = 19">大</button>
          <button v-if="chapter.is_partial" class="continue-btn" @click="openFeedback({ category: 'chapter', source: 'partial_chapter', chapter: chapter.id })">反馈断章</button>
        </div>
      </header>
      <div class="markdown-content" :style="{ fontSize: fontSize + 'px' }" v-html="renderedContent"></div>
    </article>
    <div v-else class="empty">未找到此章。</div>
  </div>
</template>

<style scoped>
.chapter-page {
  min-height: var(--app-svh);
  min-height: 100dvh;
  padding: calc(28px + var(--safe-top)) max(20px, calc((100vw - 860px) / 2)) calc(80px + var(--safe-bottom));
  background: #0B0B14;
  color: #F3E4C3;
}

.reader {
  margin-top: 24px;
}

header {
  border-bottom: 1px solid rgba(212,162,76,0.28);
  padding-bottom: 18px;
  margin-bottom: 24px;
}

header p {
  color: #D4A24C;
  margin: 0 0 8px;
}

h1 {
  margin: 0;
  font-size: 32px;
  font-family: STKaiti, "KaiTi", serif;
  letter-spacing: 0;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.meta span {
  border: 1px solid rgba(255,255,255,0.12);
  color: #B8C7E0;
  padding: 4px 8px;
  font-size: 12px;
}

.meta .warn {
  color: #FFB454;
}

.reader-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.reader-actions button {
  min-height: 34px;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 6px;
  background: rgba(255,255,255,0.04);
  color: #B8C7E0;
  padding: 0 12px;
  cursor: pointer;
}

.reader-actions button.active,
.reader-actions .continue-btn {
  color: #FFE0A3;
  border-color: rgba(212,162,76,0.42);
  background: rgba(212,162,76,0.12);
}

.markdown-content {
  line-height: 2;
  font-size: 17px;
  color: #E9D9B8;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  margin: 28px 0 12px;
  color: #FFE0A3;
  font-family: STKaiti, "KaiTi", serif;
  letter-spacing: 0;
  line-height: 1.35;
}

.markdown-content :deep(h1) { font-size: 28px; }
.markdown-content :deep(h2) { font-size: 24px; }
.markdown-content :deep(h3) { font-size: 21px; }
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) { font-size: 18px; }

.markdown-content :deep(p) {
  margin: 0 0 18px;
}

.markdown-content :deep(strong) {
  color: #FFE0A3;
  font-weight: 800;
}

.markdown-content :deep(em) {
  color: #D4A24C;
  font-style: normal;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 0 0 18px;
  padding-left: 24px;
}

.markdown-content :deep(li) {
  margin: 6px 0;
}

.markdown-content :deep(blockquote) {
  margin: 18px 0;
  padding: 10px 14px;
  border-left: 3px solid rgba(212,162,76,0.7);
  background: rgba(212,162,76,0.08);
  color: #D8C6A4;
}

.markdown-content :deep(hr) {
  border: 0;
  border-top: 1px solid rgba(212,162,76,0.28);
  margin: 28px 0;
}

.markdown-content :deep(code) {
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.06);
  color: #B8C7E0;
  padding: 2px 5px;
  font-family: "SF Mono", Consolas, monospace;
  font-size: 0.9em;
}

.markdown-content :deep(pre) {
  overflow: auto;
  margin: 18px 0;
  padding: 14px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(0,0,0,0.35);
}

.markdown-content :deep(pre code) {
  display: block;
  border: 0;
  background: transparent;
  padding: 0;
  line-height: 1.7;
}

.empty {
  margin-top: 30px;
  border: 1px solid rgba(255,255,255,0.1);
  padding: 36px 18px;
  text-align: center;
  color: #9CA8BB;
}

@media (max-width: 720px) {
  .chapter-page {
    padding: calc(18px + var(--safe-top)) 15px calc(24px + var(--safe-bottom));
  }
  .reader {
    margin-top: 18px;
  }
  h1 {
    font-size: 27px;
    line-height: 1.35;
  }
  .markdown-content {
    line-height: 1.9;
  }
}

@media (orientation: landscape) and (max-height: 520px) {
  .chapter-page {
    padding-left: calc(86px + var(--safe-left));
  }
}
</style>
