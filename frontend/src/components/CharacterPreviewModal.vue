<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import RoundPortrait from './RoundPortrait.vue'
import SectFlag from './SectFlag.vue'
import { CHARACTER_PREVIEW_EVENT } from '../utils/characterPreview.js'

const profile = ref(null)
const showArchive = ref(false)

const backgroundTitle = computed(() => {
  if (profile.value?.kind === '妖兽') return '怪物故事'
  if (profile.value?.kind === '道君') return '道君本纪'
  return '人物背景'
})

const bondsTitle = computed(() => {
  if (profile.value?.kind === '妖兽') return '怪物羁绊'
  if (profile.value?.kind === '道君') return '道君因果'
  return '人物羁绊'
})

const historyTitle = computed(() => {
  if (profile.value?.kind === '妖兽') return '怪物记录'
  return '过往记录'
})

function open(event) {
  profile.value = event.detail
  showArchive.value = false
}

function close() {
  profile.value = null
}

onMounted(() => {
  window.addEventListener(CHARACTER_PREVIEW_EVENT, open)
})

onUnmounted(() => {
  window.removeEventListener(CHARACTER_PREVIEW_EVENT, open)
})
</script>

<template>
  <Transition name="preview-fade">
    <div v-if="profile" class="preview-overlay" @click.self="close">
      <article class="preview-card" :style="{ '--accent': profile.accent }">
        <button class="close-btn" @click="close">×</button>

        <header class="preview-head">
          <RoundPortrait
            v-if="profile.portrait"
            :kind="profile.portrait.kind"
            :id="profile.portrait.id"
            :size="148"
            :shape="profile.portrait.shape || 'card'"
            :frame="profile.accent"
            :name="profile.name"
          />
          <div class="head-copy">
            <div class="kind-line">
              <p class="kind">{{ profile.kind }}</p>
              <SectFlag
                v-if="profile.sectId"
                :sect-id="profile.sectId"
                :name="profile.title"
                :size="36"
                :radius="8"
              />
            </div>
            <h2>{{ profile.name }}</h2>
            <p class="title">{{ profile.title }}</p>
            <p v-if="profile.subtitle" class="subtitle">{{ profile.subtitle }}</p>
            <div v-if="profile.tags?.length" class="tags">
              <span v-for="tag in profile.tags" :key="tag">{{ tag }}</span>
            </div>
          </div>
        </header>

        <section v-if="profile.stats?.length" class="stat-grid">
          <div v-for="stat in profile.stats" :key="stat.label" class="stat">
            <span>{{ stat.label }}</span>
            <strong>{{ stat.value }}</strong>
          </div>
        </section>

        <section v-if="profile.background" class="block">
          <h3>{{ backgroundTitle }}</h3>
          <p>{{ profile.background }}</p>
        </section>

        <section v-if="profile.bonds?.length" class="block">
          <h3>{{ bondsTitle }}</h3>
          <div class="record-list">
            <div v-for="bond in profile.bonds" :key="bond.name + bond.relation" class="record">
              <div class="record-head">
                <strong>{{ bond.name }}</strong>
                <span>{{ bond.relation }}</span>
              </div>
              <p>{{ bond.desc }}</p>
            </div>
          </div>
        </section>

        <section v-if="profile.histories?.length" class="block">
          <h3>{{ historyTitle }}</h3>
          <div class="record-list">
            <div v-for="item in profile.histories" :key="item.title + item.meta" class="record">
              <div class="record-head">
                <strong>{{ item.title }}</strong>
                <span>{{ item.meta }}</span>
              </div>
              <p>{{ item.body }}</p>
            </div>
          </div>
        </section>

        <section v-if="profile.archive?.length" class="block archive-block">
          <button class="archive-toggle" @click="showArchive = !showArchive">
            {{ showArchive ? '收起全部经历' : `展开全部经历 · ${profile.archive.length}` }}
          </button>
          <Transition name="archive-slide">
            <div v-if="showArchive" class="record-list compact archive-list">
              <div v-for="(item, index) in profile.archive" :key="item.title + item.meta + index" class="record">
                <div class="record-head">
                  <strong>{{ item.title }}</strong>
                  <span>{{ item.meta }}</span>
                </div>
                <p>{{ item.body }}</p>
              </div>
            </div>
          </Transition>
        </section>

        <section v-if="profile.interactions?.length" class="block">
          <h3>历史交互</h3>
          <div class="record-list compact">
            <div v-for="item in profile.interactions" :key="item.title + item.meta" class="record">
              <div class="record-head">
                <strong>{{ item.title }}</strong>
                <span>{{ item.meta }}</span>
              </div>
              <p>{{ item.body }}</p>
            </div>
          </div>
        </section>

        <section v-for="section in profile.sections" :key="section.title" class="block">
          <h3>{{ section.title }}</h3>
          <div class="record-list compact">
            <div v-for="item in section.items" :key="item.title" class="record">
              <div class="record-head">
                <strong>{{ item.title }}</strong>
              </div>
              <p>{{ item.body }}</p>
            </div>
          </div>
        </section>
      </article>
    </div>
  </Transition>
</template>

<style scoped>
.preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 980;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(0,0,0,0.76);
  backdrop-filter: blur(5px);
}

.preview-card {
  position: relative;
  width: min(880px, 100%);
  max-height: min(86vh, 760px);
  overflow: auto;
  padding: 24px;
  border: 1px solid color-mix(in srgb, var(--accent, #D4A24C) 55%, transparent);
  border-radius: 10px;
  background:
    radial-gradient(ellipse at 18% 0%, color-mix(in srgb, var(--accent, #D4A24C) 18%, transparent), transparent 42%),
    linear-gradient(180deg, rgba(18,16,28,0.98), rgba(8,8,18,0.99));
  color: #F3E4C3;
  box-shadow: 0 18px 60px rgba(0,0,0,0.68), 0 0 28px color-mix(in srgb, var(--accent, #D4A24C) 16%, transparent);
}

.close-btn {
  position: absolute;
  top: 12px;
  right: 14px;
  width: 34px;
  height: 34px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.04);
  color: #B8C7E0;
  cursor: pointer;
  font-size: 22px;
}

.close-btn:hover {
  color: #FFE0A3;
  border-color: color-mix(in srgb, var(--accent, #D4A24C) 55%, transparent);
}

.preview-head {
  display: grid;
  grid-template-columns: 148px minmax(0, 1fr);
  gap: 20px;
  align-items: center;
  padding-bottom: 18px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

.kind-line {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.kind {
  margin: 0;
  color: var(--accent, #D4A24C);
  font-size: 12px;
  letter-spacing: 4px;
}

h2 {
  margin: 0;
  color: #FFE0A3;
  font-family: STKaiti, "KaiTi", serif;
  font-size: 32px;
  letter-spacing: 3px;
}

.title,
.subtitle {
  margin: 6px 0 0;
  color: #AEB7C8;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 12px;
}

.tags span {
  border: 1px solid color-mix(in srgb, var(--accent, #D4A24C) 38%, transparent);
  background: color-mix(in srgb, var(--accent, #D4A24C) 12%, transparent);
  color: #E8D6B0;
  padding: 4px 8px;
  font-size: 12px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(92px, 1fr));
  gap: 8px;
  margin-top: 18px;
}

.stat {
  padding: 10px;
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.04);
}

.stat span {
  display: block;
  color: #8E98AA;
  font-size: 11px;
  margin-bottom: 4px;
}

.stat strong {
  color: #FFE0A3;
  font-family: "SF Mono", Consolas, monospace;
}

.block {
  margin-top: 20px;
}

.block h3 {
  margin: 0 0 10px;
  color: var(--accent, #D4A24C);
  font-size: 15px;
  letter-spacing: 3px;
  font-family: STKaiti, "KaiTi", serif;
}

.block > p,
.record p {
  margin: 0;
  color: #D8C6A4;
  line-height: 1.8;
}

.record-list {
  display: grid;
  gap: 8px;
}

.record-list.compact {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.record {
  padding: 10px 12px;
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.035);
}

.record-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 5px;
}

.record-head strong {
  color: #FFE0A3;
}

.record-head span {
  color: #8E98AA;
  font-size: 12px;
  white-space: nowrap;
}

.archive-block {
  border-color: color-mix(in srgb, var(--accent, #D4A24C) 28%, transparent);
}

.archive-toggle {
  width: 100%;
  border: 1px solid color-mix(in srgb, var(--accent, #D4A24C) 44%, transparent);
  background: color-mix(in srgb, var(--accent, #D4A24C) 14%, rgba(255,255,255,0.04));
  color: #FFE0A3;
  padding: 10px 12px;
  cursor: pointer;
  font-weight: 800;
  text-align: left;
}

.archive-toggle:hover {
  background: color-mix(in srgb, var(--accent, #D4A24C) 22%, rgba(255,255,255,0.06));
}

.archive-list {
  margin-top: 10px;
  max-height: 360px;
  overflow: auto;
  padding-right: 4px;
}

.archive-slide-enter-active,
.archive-slide-leave-active {
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.archive-slide-enter-from,
.archive-slide-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.preview-fade-enter-active,
.preview-fade-leave-active {
  transition: opacity 0.18s ease;
}

.preview-fade-enter-from,
.preview-fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .preview-overlay {
    align-items: flex-end;
    padding: calc(12px + var(--safe-top)) calc(10px + var(--safe-right)) calc(10px + var(--safe-bottom)) calc(10px + var(--safe-left));
  }
  .preview-card {
    width: 100%;
    max-height: min(88dvh, calc(var(--visual-vh, 100vh) - 24px));
    padding: 18px;
    border-radius: 10px 10px 8px 8px;
  }
  .preview-head {
    grid-template-columns: 1fr;
  }
}

@media (orientation: landscape) and (max-height: 520px) {
  .preview-overlay {
    justify-content: flex-end;
    align-items: stretch;
    padding-left: calc(80px + var(--safe-left));
  }
  .preview-card {
    width: min(460px, 100%);
    max-height: 100%;
    border-radius: 8px;
  }
}
</style>
