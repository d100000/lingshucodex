<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { adminApi, itemApi } from '../api/client.js'
import { useAuthStore } from '../stores/auth.js'
import { formatNum } from '../utils/format.js'

const router = useRouter()
const msg = useMessage()
const auth = useAuthStore()

const loading = ref(false)
const usersLoading = ref(false)
const detailLoading = ref(false)
const overview = ref(null)
const users = ref([])
const totalUsers = ref(0)
const search = ref('')
const selectedUserId = ref('')
const detail = ref(null)
const activeTab = ref('overview')
const itemOptions = ref([])
const grant = ref({ item_id: '', count: 1, reason: '' })
const granting = ref(false)

const tabs = [
  { id: 'overview', label: '概览' },
  { id: 'attrs', label: '属性' },
  { id: 'tokens', label: 'Token' },
  { id: 'inventory', label: '背包' },
  { id: 'history', label: '历史' },
  { id: 'world', label: '下一轮' },
  { id: 'raw', label: '原始' },
]

const account = computed(() => detail.value?.account || null)
const character = computed(() => detail.value?.character || null)
const attrs = computed(() => character.value?.attrs || {})
const tokenRows = computed(() => detail.value?.token_ledger || [])
const inventoryRows = computed(() => detail.value?.inventory || [])

function fmt(value) {
  return formatNum(Number(value || 0))
}

function pct(value) {
  return `${Math.round(Number(value || 0) * 100)}%`
}

function timeText(value) {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString()
}

async function loadOverview() {
  const { data } = await adminApi.overview()
  overview.value = data
}

async function loadUsers() {
  usersLoading.value = true
  try {
    const { data } = await adminApi.users({ search: search.value.trim(), limit: 80, offset: 0 })
    users.value = data.items || []
    totalUsers.value = data.total || 0
    if (!selectedUserId.value && users.value[0]) selectUser(users.value[0].id)
  } finally {
    usersLoading.value = false
  }
}

async function loadItems() {
  try {
    const { data } = await itemApi.list()
    itemOptions.value = data || []
  } catch {
    itemOptions.value = []
  }
}

async function selectUser(userId) {
  selectedUserId.value = userId
  detailLoading.value = true
  activeTab.value = 'overview'
  try {
    const { data } = await adminApi.userDetail(userId)
    detail.value = data
  } catch (e) {
    msg.error(e.message || '读取用户详情失败')
  } finally {
    detailLoading.value = false
  }
}

async function refreshAll() {
  loading.value = true
  try {
    await Promise.all([loadOverview(), loadUsers(), loadItems()])
  } finally {
    loading.value = false
  }
}

async function grantItem() {
  if (!selectedUserId.value) return
  if (!grant.value.item_id.trim()) {
    msg.warning('请选择或输入物品 ID')
    return
  }
  if (Number(grant.value.count) <= 0) {
    msg.warning('数量必须大于 0')
    return
  }
  if (!grant.value.reason.trim()) {
    msg.warning('请填写发放原因')
    return
  }
  granting.value = true
  try {
    await adminApi.grantItem(selectedUserId.value, {
      item_id: grant.value.item_id.trim(),
      count: Number(grant.value.count),
      reason: grant.value.reason.trim(),
    })
    msg.success('物品已添加到用户背包')
    grant.value = { item_id: '', count: 1, reason: '' }
    await Promise.all([selectUser(selectedUserId.value), loadUsers(), loadOverview()])
  } catch (e) {
    msg.error(e.message || '添加物品失败')
  } finally {
    granting.value = false
  }
}

function logout() {
  auth.logout()
  router.replace('/admin-console/login')
}

onMounted(refreshAll)
</script>

<template>
  <main class="admin-console">
    <aside class="side">
      <div class="brand">
        <span>灵枢笔录</span>
        <strong>管理后台</strong>
      </div>
      <button class="side-action" @click="refreshAll">刷新数据</button>
      <button class="side-action ghost" @click="logout">退出后台</button>
    </aside>

    <section class="workspace">
      <header class="topbar">
        <div>
          <p>SERVER AUTHORITATIVE USER DATA</p>
          <h1>用户运营控制台</h1>
        </div>
        <div class="admin-chip">{{ auth.user?.username }}</div>
      </header>

      <section class="stats" v-if="overview">
        <article>
          <span>注册用户</span>
          <strong>{{ fmt(overview.users_total) }}</strong>
          <small>今日新增 {{ fmt(overview.registered_today) }}</small>
        </article>
        <article>
          <span>已创角</span>
          <strong>{{ fmt(overview.characters_total) }}</strong>
          <small>管理员 {{ fmt(overview.admins_total) }}</small>
        </article>
        <article>
          <span>总 Token</span>
          <strong>{{ fmt(overview.token_total) }}</strong>
          <small>今日 {{ fmt(overview.token_today) }}</small>
        </article>
        <article>
          <span>墨炉任务</span>
          <strong>{{ Object.values(overview.cultivation_task_status || {}).reduce((a, b) => a + b, 0) }}</strong>
          <small>服务器记录</small>
        </article>
      </section>

      <section class="main-grid">
        <div class="users-panel">
          <div class="panel-head">
            <div>
              <span>用户列表</span>
              <strong>{{ fmt(totalUsers) }} 人</strong>
            </div>
            <input v-model="search" placeholder="搜索用户名 / ID" @keyup.enter="loadUsers" />
          </div>
          <div v-if="usersLoading" class="empty">读取用户中...</div>
          <template v-else>
            <button
              v-for="u in users"
              :key="u.id"
              class="user-row"
              :class="{ active: selectedUserId === u.id }"
              @click="selectUser(u.id)"
            >
              <span>
                <strong>{{ u.username }}</strong>
                <small>{{ u.id }}</small>
              </span>
              <span>
                <b>{{ u.has_character ? `${u.realm_name || '-'} Lv.${u.level || 0}` : '未创角' }}</b>
                <small>{{ fmt(u.token_total) }} token</small>
              </span>
            </button>
          </template>
        </div>

        <div class="detail-panel">
          <div v-if="detailLoading" class="empty">读取用户档案中...</div>
          <template v-else-if="detail && account">
            <div class="detail-head">
              <div>
                <span>用户档案</span>
                <h2>{{ account.username }}</h2>
                <p>{{ account.id }} · 注册 {{ timeText(account.created_at) }}</p>
              </div>
              <div class="summary-pills">
                <b>{{ character?.sect_name || '未创角' }}</b>
                <b>{{ character ? `Lv.${character.level}` : '-' }}</b>
                <b>{{ fmt(character?.token_total) }} token</b>
              </div>
            </div>

            <nav class="tabs">
              <button
                v-for="tab in tabs"
                :key="tab.id"
                :class="{ active: activeTab === tab.id }"
                @click="activeTab = tab.id"
              >
                {{ tab.label }}
              </button>
            </nav>

            <section v-if="activeTab === 'overview'" class="tab-body">
              <div class="kv-grid">
                <div><span>最后登录</span><strong>{{ timeText(account.last_login_at) }}</strong></div>
                <div><span>管理员</span><strong>{{ account.is_admin ? '是' : '否' }}</strong></div>
                <div><span>角色名</span><strong>{{ character?.name || '-' }}</strong></div>
                <div><span>境界</span><strong>{{ character?.realm_name || '-' }}</strong></div>
                <div><span>气血</span><strong>{{ fmt(character?.hp) }} / {{ fmt(character?.max_hp) }}</strong></div>
                <div><span>灵气</span><strong>{{ fmt(character?.qi) }} / {{ fmt(character?.max_qi) }}</strong></div>
                <div><span>疲劳</span><strong>{{ fmt(character?.fatigue) }} / {{ fmt(character?.max_fatigue) }}</strong></div>
                <div><span>本命书章节</span><strong>{{ fmt(character?.chapters_count) }}</strong></div>
              </div>
              <div class="note-box">
                <strong>灵脉信息</strong>
                <span>{{ character?.base_url || '-' }}</span>
                <span>Key: {{ character?.api_key_present ? character.api_key_fingerprint : '未配置' }}</span>
              </div>
            </section>

            <section v-else-if="activeTab === 'attrs'" class="tab-body">
              <div class="kv-grid">
                <div><span>攻击</span><strong>{{ fmt(character?.atk) }}</strong></div>
                <div><span>防御</span><strong>{{ fmt(character?.def_) }}</strong></div>
                <div><span>速度</span><strong>{{ fmt(character?.spd) }}</strong></div>
                <div><span>闪避</span><strong>{{ pct(character?.evasion) }}</strong></div>
                <div><span>暴击</span><strong>{{ pct(character?.crit_rate) }}</strong></div>
                <div><span>暴伤</span><strong>{{ character?.crit_dmg || '-' }}</strong></div>
                <div v-for="(v, k) in attrs" :key="k"><span>{{ k }}</span><strong>{{ v }}</strong></div>
              </div>
              <h3>创角机缘</h3>
              <div class="mini-list">
                <div v-for="(b, i) in character?.blessings || []" :key="i">
                  <span>{{ b.attr_name || b.attr }}</span>
                  <strong>+{{ b.delta }}</strong>
                  <small>{{ b.note }}</small>
                </div>
              </div>
            </section>

            <section v-else-if="activeTab === 'tokens'" class="tab-body">
              <div class="kv-grid">
                <div><span>历史总燃灵</span><strong>{{ fmt(character?.token_total) }}</strong></div>
                <div><span>今日燃灵</span><strong>{{ fmt(character?.daily_token_used) }}</strong></div>
                <div><span>本月燃灵</span><strong>{{ fmt(character?.monthly_token_used) }}</strong></div>
                <div><span>总字数</span><strong>{{ fmt(character?.novel_words_total) }}</strong></div>
              </div>
              <table>
                <thead><tr><th>时间</th><th>来源</th><th>模型</th><th>Token</th><th>输入/输出</th></tr></thead>
                <tbody>
                  <tr v-for="row in tokenRows" :key="row.id">
                    <td>{{ timeText(row.created_at) }}</td>
                    <td>{{ row.source }}</td>
                    <td>{{ row.model || '-' }}</td>
                    <td>{{ fmt(row.delta_tokens) }}</td>
                    <td>{{ fmt(row.input_tokens) }} / {{ fmt(row.output_tokens) }}</td>
                  </tr>
                </tbody>
              </table>
            </section>

            <section v-else-if="activeTab === 'inventory'" class="tab-body">
              <form class="grant-box" @submit.prevent="grantItem">
                <label>
                  <span>添加物品</span>
                  <input v-model="grant.item_id" list="item-options" placeholder="输入 item_id 或选择物品" />
                  <datalist id="item-options">
                    <option v-for="item in itemOptions" :key="item.id" :value="item.id">
                      {{ item.name }}
                    </option>
                  </datalist>
                </label>
                <label>
                  <span>数量</span>
                  <input v-model.number="grant.count" type="number" min="1" />
                </label>
                <label>
                  <span>原因</span>
                  <input v-model="grant.reason" placeholder="例如: 内测补偿 / 修复掉落异常" />
                </label>
                <button :disabled="granting">{{ granting ? '添加中...' : '添加到背包' }}</button>
              </form>

              <table>
                <thead><tr><th>物品</th><th>类型</th><th>稀有度</th><th>数量</th><th>总价值</th></tr></thead>
                <tbody>
                  <tr v-for="item in inventoryRows" :key="item.id">
                    <td><strong>{{ item.name }}</strong><small>{{ item.id }}</small></td>
                    <td>{{ item.type }}</td>
                    <td>{{ item.rarity_name }}</td>
                    <td>{{ fmt(item.count) }}</td>
                    <td>{{ fmt(item.total_value_qi) }}</td>
                  </tr>
                </tbody>
              </table>

              <h3>背包流水</h3>
              <div class="mini-list">
                <div v-for="row in detail.item_ledger || []" :key="row.id">
                  <span>{{ timeText(row.created_at) }}</span>
                  <strong>{{ row.item_id }} {{ row.delta_count > 0 ? '+' : '' }}{{ row.delta_count }}</strong>
                  <small>{{ row.reason || row.source }}</small>
                </div>
              </div>
            </section>

            <section v-else-if="activeTab === 'history'" class="tab-body">
              <h3>修行录</h3>
              <div class="mini-list">
                <div v-for="row in detail.journal || []" :key="row.id">
                  <span>{{ timeText(row.created_at) }}</span>
                  <strong>{{ row.title }}</strong>
                  <small>{{ row.detail }}</small>
                </div>
              </div>
              <h3>墨炉任务</h3>
              <div class="mini-list">
                <div v-for="task in detail.cultivation_tasks || []" :key="task.id">
                  <span>{{ task.status }}</span>
                  <strong>{{ task.title }}</strong>
                  <small>{{ fmt(task.estimated_tokens) }} token · {{ task.model || '-' }}</small>
                </div>
              </div>
              <h3>本命书章节</h3>
              <div class="mini-list">
                <div v-for="chapter in detail.novel_chapters || []" :key="chapter.id">
                  <span>第 {{ chapter.chapter_no }} 章</span>
                  <strong>{{ chapter.title }}</strong>
                  <small>{{ fmt(chapter.token_count) }} token · {{ chapter.status }}</small>
                </div>
              </div>
            </section>

            <section v-else-if="activeTab === 'world'" class="tab-body">
              <div class="kv-grid">
                <div><span>世界 revision</span><strong>{{ detail.world_save?.revision ?? '-' }}</strong></div>
                <div><span>最近更新</span><strong>{{ timeText(detail.world_save?.updated_at) }}</strong></div>
                <div><span>当前轮次</span><strong>{{ detail.world_save?.data?.round ?? '-' }}</strong></div>
                <div><span>当前天数</span><strong>{{ detail.world_save?.data?.day ?? '-' }}</strong></div>
              </div>
              <h3>下一轮同步记录</h3>
              <table>
                <thead><tr><th>时间</th><th>Revision</th><th>天数</th><th>事件</th><th>状态</th></tr></thead>
                <tbody>
                  <tr v-for="row in detail.world_round_logs || []" :key="row.id">
                    <td>{{ timeText(row.created_at) }}</td>
                    <td>{{ row.from_revision }} -> {{ row.to_revision }}</td>
                    <td>{{ row.from_day }} -> {{ row.to_day }}</td>
                    <td>{{ row.event_count }}</td>
                    <td>{{ row.status }}</td>
                  </tr>
                </tbody>
              </table>
            </section>

            <section v-else class="tab-body">
              <pre>{{ JSON.stringify(detail, null, 2) }}</pre>
            </section>
          </template>
          <div v-else class="empty">请选择一个用户查看详情</div>
        </div>
      </section>
    </section>
  </main>
</template>

<style scoped>
.admin-console {
  min-height: var(--app-svh);
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  background: #090C14;
  color: #F3E4C3;
}

.side {
  position: sticky;
  top: 0;
  height: var(--app-svh);
  padding: 22px 16px;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  background: #0D1320;
  box-sizing: border-box;
}

.brand {
  display: grid;
  gap: 6px;
  margin-bottom: 22px;
}

.brand span {
  color: #7FC7E8;
  font-size: 12px;
  letter-spacing: 2px;
}

.brand strong {
  color: #FFE0A3;
  font-size: 22px;
}

.side-action {
  width: 100%;
  min-height: 38px;
  margin-bottom: 10px;
  border: 1px solid rgba(212, 162, 76, 0.36);
  border-radius: 6px;
  background: rgba(212, 162, 76, 0.12);
  color: #FFE0A3;
  cursor: pointer;
}

.side-action.ghost {
  border-color: rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: #D8E0EE;
}

.workspace {
  min-width: 0;
  padding: 22px;
}

.topbar,
.panel-head,
.detail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.topbar p,
.detail-head span,
.panel-head span {
  margin: 0 0 4px;
  color: #7FC7E8;
  font-size: 12px;
  letter-spacing: 1.5px;
}

.topbar h1,
.detail-head h2 {
  margin: 0;
  color: #FFE0A3;
}

.admin-chip,
.summary-pills b {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid rgba(127, 199, 232, 0.28);
  border-radius: 999px;
  background: rgba(127, 199, 232, 0.08);
  color: #B8E4FF;
  font-size: 12px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 20px 0;
}

.stats article,
.users-panel,
.detail-panel {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.035);
}

.stats article {
  padding: 14px;
}

.stats span,
.kv-grid span {
  display: block;
  color: #9CA8BB;
  font-size: 12px;
  margin-bottom: 6px;
}

.stats strong {
  display: block;
  color: #FFE0A3;
  font-size: 24px;
  margin-bottom: 4px;
}

.stats small,
.detail-head p,
.user-row small,
td small,
.mini-list small {
  color: #9CA8BB;
  font-size: 12px;
}

.main-grid {
  display: grid;
  grid-template-columns: minmax(300px, 36%) minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}

.users-panel,
.detail-panel {
  min-height: 540px;
  overflow: hidden;
}

.panel-head {
  padding: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.panel-head input {
  width: min(220px, 45%);
}

input {
  box-sizing: border-box;
  min-height: 36px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.22);
  color: #F3E4C3;
  padding: 0 10px;
  font: inherit;
}

.user-row {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
  border: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.user-row.active {
  background: rgba(212, 162, 76, 0.12);
}

.user-row strong,
.user-row b {
  display: block;
  color: #FFE0A3;
}

.detail-head {
  padding: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.summary-pills {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.tabs {
  display: flex;
  gap: 1px;
  overflow-x: auto;
  padding: 0 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.tabs button {
  min-height: 42px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: #9CA8BB;
  padding: 0 12px;
  cursor: pointer;
}

.tabs button.active {
  color: #FFE0A3;
  border-bottom-color: #D4A24C;
}

.tab-body {
  padding: 16px;
}

.kv-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.kv-grid div,
.note-box,
.grant-box,
.mini-list div {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.16);
  padding: 10px;
}

.kv-grid strong {
  color: #FFE0A3;
}

.note-box {
  display: grid;
  gap: 6px;
  margin-top: 12px;
}

h3 {
  margin: 18px 0 10px;
  color: #D4A24C;
  font-size: 15px;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 12px;
}

th,
td {
  padding: 9px 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  text-align: left;
  vertical-align: top;
  font-size: 13px;
}

th {
  color: #9CA8BB;
  font-weight: 600;
}

td strong,
td small {
  display: block;
}

.grant-box {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) 90px minmax(180px, 1fr) auto;
  gap: 10px;
  align-items: end;
}

.grant-box label {
  display: grid;
  gap: 6px;
  color: #C9A876;
  font-size: 12px;
}

.grant-box button {
  min-height: 36px;
  border: 1px solid rgba(212, 162, 76, 0.42);
  border-radius: 6px;
  background: linear-gradient(135deg, #D4A24C, #B58A3E);
  color: #101522;
  font-weight: 800;
  cursor: pointer;
}

.grant-box button:disabled {
  opacity: 0.55;
  cursor: wait;
}

.mini-list {
  display: grid;
  gap: 8px;
}

.mini-list div {
  display: grid;
  grid-template-columns: 130px minmax(0, 1fr);
  gap: 8px 12px;
}

.mini-list small {
  grid-column: 2;
}

.empty {
  padding: 26px;
  color: #9CA8BB;
}

pre {
  max-height: 580px;
  overflow: auto;
  margin: 0;
  padding: 12px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.32);
  color: #D8E0EE;
  font-size: 12px;
}

@media (max-width: 980px) {
  .admin-console {
    grid-template-columns: 1fr;
  }

  .side {
    position: static;
    height: auto;
  }

  .stats,
  .main-grid,
  .kv-grid,
  .grant-box {
    grid-template-columns: 1fr;
  }

  .panel-head input {
    width: 100%;
  }
}
</style>
