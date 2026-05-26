<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { novelApi } from '../api/client.js'
import BackButton from '../components/BackButton.vue'
import { stripMarkdown } from '../utils/markdown.js'
import EmptyState from '../components/EmptyState.vue'
import ErrorState from '../components/ErrorState.vue'
import SkeletonBlock from '../components/SkeletonBlock.vue'
import { openFeedback } from '../utils/mobile.js'

const router = useRouter()
const loading = ref(true)
const stats = ref(null)
const chapters = ref([])
const volumes = ref([])
const typeFilter = ref('all')
const volumeFilter = ref('all')
const error = ref('')

const filteredChapters = computed(() => chapters.value.filter(ch => {
  if (typeFilter.value !== 'all' && ch.chapter_type !== typeFilter.value) return false
  if (volumeFilter.value !== 'all' && ch.volume_no !== Number(volumeFilter.value)) return false
  return true
}))

const chapterTypes = computed(() => {
  const s = new Set(chapters.value.map(ch => ch.chapter_type))
  return [...s]
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const s = await novelApi.stats()
    stats.value = s.data
    const [v, c] = await Promise.all([novelApi.volumes(), novelApi.chapters(120, 0)])
    volumes.value = v.data.volumes || []
    chapters.value = c.data.chapters || []
  } catch (e) {
    error.value = e.message || '本命书加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="novel-page">
    <BackButton to="/home" label="回主城" />
    <header class="book-head">
      <div>
        <p class="eyebrow">本命书</p>
        <h1>灵枢本命书</h1>
      </div>
      <button class="refresh" @click="load">刷新</button>
    </header>

    <section class="stats-band" v-if="stats">
      <div>
        <span>总修为</span>
        <strong>{{ stats.cultivation_total }}</strong>
      </div>
      <div>
        <span>燃灵 token</span>
        <strong>{{ stats.token_total }}</strong>
      </div>
      <div>
        <span>章节</span>
        <strong>{{ stats.chapters_count }}</strong>
      </div>
      <div>
        <span>总字数</span>
        <strong>{{ stats.word_total || stats.novel_words_total }}</strong>
      </div>
    </section>

    <main class="chapter-list">
      <div v-if="chapters.length" class="filters">
        <select v-model="volumeFilter">
          <option value="all">全部卷</option>
          <option v-for="v in volumes" :key="v.volume_no" :value="v.volume_no">第 {{ v.volume_no }} 卷</option>
        </select>
        <select v-model="typeFilter">
          <option value="all">全部章型</option>
          <option v-for="t in chapterTypes" :key="t" :value="t">{{ t }}</option>
        </select>
      </div>
      <SkeletonBlock v-if="loading" />
      <ErrorState
        v-else-if="error"
        title="本命书暂未翻开"
        :desc="error"
        @retry="load"
        @feedback="openFeedback({ category: 'chapter', source: 'novel_list', error })"
      />
      <EmptyState
        v-else-if="chapters.length === 0"
        title="墨炉尚未落下第一章"
        desc="去战斗,或打坐后入定成章。"
        action="去地图"
        @action="router.push('/explore')"
      />
      <button v-for="ch in filteredChapters" :key="ch.id" class="chapter-row" :class="{ partial: ch.is_partial }" @click="router.push(`/novel/chapter/${ch.id}`)">
        <div>
          <div class="chapter-title">
            第 {{ ch.chapter_no }} 章 · {{ ch.title }}
            <span v-if="ch.is_partial" class="partial-tag">断章</span>
          </div>
          <div class="chapter-summary">{{ stripMarkdown(ch.summary) }}</div>
        </div>
        <div class="chapter-meta">
          <span>卷 {{ ch.volume_no }}</span>
          <span>{{ ch.token_count }} token</span>
          <span>修为 +{{ ch.cultivation_gained }}</span>
        </div>
      </button>
    </main>
  </div>
</template>

<style scoped>
.novel-page {
  min-height: var(--app-svh);
  min-height: 100dvh;
  padding: calc(28px + var(--safe-top)) max(20px, calc((100vw - 1040px) / 2)) calc(90px + var(--safe-bottom));
  background: #0B0B14;
  color: #F3E4C3;
}

.book-head {
  display: flex;
  justify-content: space-between;
  align-items: end;
  margin: 22px 0 20px;
}

.eyebrow {
  color: #D4A24C;
  margin: 0 0 6px;
  font-size: 13px;
}

h1 {
  margin: 0;
  font-size: 34px;
  font-family: STKaiti, "KaiTi", serif;
  letter-spacing: 0;
}

.refresh {
  height: 34px;
  border: 1px solid rgba(212,162,76,0.4);
  background: rgba(212,162,76,0.12);
  color: #F3E4C3;
  padding: 0 14px;
  cursor: pointer;
}

.stats-band {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  border: 1px solid rgba(212,162,76,0.28);
  background: rgba(212,162,76,0.18);
  margin-bottom: 18px;
}

.stats-band > div {
  background: rgba(15,15,28,0.94);
  padding: 16px;
}

.stats-band span {
  display: block;
  color: #9CA8BB;
  font-size: 12px;
  margin-bottom: 6px;
}

.stats-band strong {
  font-size: 22px;
}

.chapter-list {
  display: grid;
  gap: 10px;
}

.filters {
  display: flex;
  gap: 10px;
  margin-bottom: 4px;
}

.filters select {
  height: 34px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.06);
  color: #F3E4C3;
  padding: 0 10px;
}

.chapter-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  text-align: left;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(255,255,255,0.035);
  color: inherit;
  padding: 14px 16px;
  cursor: pointer;
}

.chapter-row:hover {
  border-color: rgba(212,162,76,0.46);
  background: rgba(212,162,76,0.08);
}

.chapter-row.partial {
  border-color: rgba(255,180,84,0.32);
}

.partial-tag {
  margin-left: 8px;
  color: #FFB454;
  font-size: 12px;
  font-weight: 700;
}

.chapter-title {
  font-weight: 800;
  margin-bottom: 6px;
}

.chapter-summary {
  color: #AEB7C8;
  font-size: 13px;
  line-height: 1.6;
  max-height: 42px;
  overflow: hidden;
}

.chapter-meta {
  display: flex;
  flex-direction: column;
  gap: 5px;
  color: #D4A24C;
  font-size: 12px;
  white-space: nowrap;
  text-align: right;
}

.empty {
  border: 1px solid rgba(255,255,255,0.1);
  padding: 36px 18px;
  text-align: center;
  color: #9CA8BB;
}

@media (max-width: 720px) {
  .novel-page {
    padding: calc(18px + var(--safe-top)) 14px calc(104px + var(--safe-bottom));
  }
  .book-head {
    align-items: start;
    margin-top: 16px;
  }
  h1 {
    font-size: 28px;
  }
  .stats-band {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .filters {
    overflow-x: auto;
    padding-bottom: 4px;
  }
  .filters select {
    flex: 0 0 auto;
    min-width: 128px;
    border-radius: 999px;
  }
  .chapter-row {
    grid-template-columns: 1fr;
    border-radius: 8px;
  }
  .chapter-meta {
    flex-direction: row;
    flex-wrap: wrap;
    text-align: left;
  }
}

@media (orientation: landscape) and (max-height: 520px) {
  .novel-page {
    padding-left: calc(86px + var(--safe-left));
    padding-bottom: calc(24px + var(--safe-bottom));
  }
}
</style>
