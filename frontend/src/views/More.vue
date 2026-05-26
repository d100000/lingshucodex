<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game.js'
import { useAuthStore } from '../stores/auth.js'
import { formatNum } from '../utils/format.js'
import { openFeedback } from '../utils/mobile.js'

const router = useRouter()
const game = useGameStore()
const auth = useAuthStore()
const character = computed(() => game.character || {})

const sections = [
  {
    title: '修行资料',
    items: [
      { icon: '💊', label: '修行物品', desc: '丹药、材料、法宝资料', to: '/items' },
      { icon: '📖', label: '山海经图鉴', desc: '妖兽遭遇与掉落记录', to: '/bestiary' },
      { icon: '👑', label: '修真名录', desc: '道君、Boss 与故事线', to: '/bosses' },
      { icon: '📜', label: '修行录', desc: '战斗、奇遇、成章足迹', to: '/journal' },
    ],
  },
  {
    title: '养成管理',
    items: [
      { icon: '🔥', label: '炼丹炼器', desc: '材料合成与配方管理', to: '/craft' },
      { icon: '⚔', label: '修行心法', desc: '招式学习与装备', to: '/skills' },
      { icon: '🎒', label: '背包', desc: '查看战利品和消耗品', to: '/inventory' },
    ],
  },
]

function go(item) {
  if (item.to) router.push(item.to)
}
</script>

<template>
  <main class="more-page">
    <header class="more-head">
      <div>
        <p>BETA 内测</p>
        <h1>更多</h1>
      </div>
      <button class="feedback-btn" @click="openFeedback({ category: 'idea', source: 'more' })">提反馈</button>
    </header>

    <section class="usage-card">
      <div>
        <span>今日已燃</span>
        <strong>{{ formatNum(character.daily_token_used || 0) }}</strong>
      </div>
      <div>
        <span>本月已燃</span>
        <strong>{{ formatNum(character.monthly_token_used || 0) }}</strong>
      </div>
      <div>
        <span>总燃灵</span>
        <strong>{{ formatNum(character.token_total || 0) }}</strong>
      </div>
    </section>

    <section v-for="section in sections" :key="section.title" class="more-section">
      <h2>{{ section.title }}</h2>
      <div class="more-grid">
        <button v-for="item in section.items" :key="item.label" class="more-item" @click="go(item)">
          <span class="mi-icon">{{ item.icon }}</span>
          <span class="mi-copy">
            <strong>{{ item.label }}</strong>
            <small>{{ item.desc }}</small>
          </span>
          <span class="mi-arrow">›</span>
        </button>
      </div>
    </section>

    <section class="more-section beta-section">
      <h2>内测服务</h2>
      <button v-if="auth.isAdmin" class="more-item" @click="router.push('/admin-console')">
        <span class="mi-icon">⚙</span>
        <span class="mi-copy">
          <strong>管理后台</strong>
          <small>站点展示、广告开关与内测配置</small>
        </span>
        <span class="mi-arrow">›</span>
      </button>
      <button class="more-item" @click="openFeedback({ category: 'bug', source: 'more_beta' })">
        <span class="mi-icon">β</span>
        <span class="mi-copy">
          <strong>内测反馈</strong>
          <small>提交 Bug、卡顿、断章或遮挡问题</small>
        </span>
        <span class="mi-arrow">›</span>
      </button>
      <div class="version-note">
        当前版本为 BETA 内测。不会设置氪金项目,所有成长围绕 token 消耗、墨炉成章和修为累积展开。
      </div>
    </section>
  </main>
</template>

<style scoped>
.more-page {
  min-height: var(--app-svh);
  padding: calc(22px + var(--safe-top)) max(16px, calc((100vw - 980px) / 2)) calc(96px + var(--safe-bottom));
  background: #0B0B14;
  color: #F3E4C3;
}

.more-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-end;
  margin-bottom: 16px;
}

.more-head p {
  margin: 0 0 4px;
  color: #7FC7E8;
  font-size: 12px;
  letter-spacing: 2px;
}

.more-head h1 {
  margin: 0;
  color: #FFE0A3;
  font-size: 30px;
  font-family: STKaiti, "KaiTi", serif;
}

.feedback-btn {
  min-height: 38px;
  border: 1px solid rgba(127,199,232,0.4);
  border-radius: 6px;
  background: rgba(127,199,232,0.1);
  color: #B8E4FF;
  padding: 0 12px;
  cursor: pointer;
}

.usage-card {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  margin-bottom: 18px;
  border: 1px solid rgba(212,162,76,0.28);
  background: rgba(212,162,76,0.16);
}

.usage-card > div {
  padding: 14px;
  background: rgba(15,15,28,0.94);
}

.usage-card span {
  display: block;
  margin-bottom: 6px;
  color: #9CA8BB;
  font-size: 12px;
}

.usage-card strong {
  color: #FFE0A3;
  font-size: 20px;
}

.more-section {
  margin-top: 18px;
}

.more-section h2 {
  margin: 0 0 10px;
  color: #D4A24C;
  font-size: 15px;
  letter-spacing: 2px;
}

.more-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.more-item {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  min-height: 72px;
  padding: 12px;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  background: rgba(255,255,255,0.035);
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.mi-icon {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: rgba(212,162,76,0.12);
  color: #FFE0A3;
  font-weight: 800;
}

.mi-copy {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.mi-copy strong {
  color: #FFE0A3;
}

.mi-copy small {
  color: #9CA8BB;
  line-height: 1.5;
}

.mi-arrow {
  color: #D4A24C;
  font-size: 24px;
}

.version-note {
  margin-top: 10px;
  padding: 12px;
  border: 1px solid rgba(127,199,232,0.18);
  border-radius: 8px;
  background: rgba(127,199,232,0.06);
  color: #B8C7E0;
  line-height: 1.7;
  font-size: 13px;
}

@media (max-width: 640px) {
  .more-grid,
  .usage-card {
    grid-template-columns: 1fr;
  }
}

@media (orientation: landscape) and (max-height: 480px) {
  .more-page {
    padding-left: calc(86px + var(--safe-left));
  }
  .more-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
