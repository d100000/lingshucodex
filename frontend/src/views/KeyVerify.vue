<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { sectApi, characterApi, siteApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'
import Logo from '../components/Logo.vue'
import WuxiaBackground from '../components/WuxiaBackground.vue'
import BackButton from '../components/BackButton.vue'
import SectBackground from '../components/SectBackground.vue'
import SectFlag from '../components/SectFlag.vue'

const router = useRouter()
const route = useRoute()
const msg = useMessage()
const game = useGameStore()

const sectId = route.params.sectId
const sect = ref(null)
const characterName = ref('执笔者')
const BOBDONG_BASE_URL = 'https://bobdong.cn/v1'
const baseUrl = ref('')
const apiKey = ref('')
const showBobdongAds = ref(false)
const verifying = ref(false)
const verifyDone = ref(false)
const allOk = ref(false)
const enteringGame = ref(false)

// 待测试的模型列表(及实时状态)
// { model, label, status: 'idle'|'running'|'success'|'failed'|'retrying',
//   attempt, error, duration_ms }
const modelStates = ref([])

const sectAccent = computed(() => sect.value?.color_accent || '#D4A24C')
const baseUrlPlaceholder = computed(() =>
  showBobdongAds.value
    ? BOBDONG_BASE_URL
    : (sect.value?.byok_hint?.official_base_url || 'https://api.openai.com/v1')
)

const fromOnboarding = ref(false)

onMounted(async () => {
  try {
    const [siteResp, data] = await Promise.all([
      siteApi.config().catch(() => ({ data: { show_bobdong_ads: false } })),
      sectApi.get(sectId),
    ])
    showBobdongAds.value = !!siteResp.data?.show_bobdong_ads
    sect.value = data
    if (!data.available) {
      msg.error('该派暂未开放')
      router.replace('/onboarding')
      return
    }
    if (showBobdongAds.value && data.byok_hint?.default_base_url) {
      baseUrl.value = data.byok_hint.default_base_url
    } else if (data.byok_hint?.official_base_url) {
      baseUrl.value = data.byok_hint.official_base_url
    }

    // 从 onboarding 跳来时,query 预填 base_url / api_key / name
    if (route.query.base_url) baseUrl.value = String(route.query.base_url)
    if (route.query.api_key) apiKey.value = String(route.query.api_key)
    if (route.query.name) characterName.value = String(route.query.name)
    if (route.query.from === 'onboarding') {
      fromOnboarding.value = true
      // 自动开始验证(可选,这里让用户自己点更稳)
    }
  } catch (e) {
    msg.error('门派信息加载失败: ' + e.message)
    router.replace('/onboarding')
  }
})

async function startVerify() {
  if (!apiKey.value.trim()) {
    msg.warning('请填写 API Key')
    return
  }
  if (!baseUrl.value.trim()) {
    msg.warning('请填写 API 地址')
    return
  }

  verifying.value = true
  verifyDone.value = false
  allOk.value = false
  modelStates.value = []

  try {
    const resp = await fetch('/api/sect/verify-key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sect_id: sectId,
        base_url: baseUrl.value.trim(),
        api_key: apiKey.value.trim(),
      }),
    })

    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${resp.status}`)
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })

      // 按 SSE 切分
      const lines = buf.split('\n\n')
      buf = lines.pop()

      for (const block of lines) {
        const dataLine = block.split('\n').find(l => l.startsWith('data: '))
        if (!dataLine) continue
        try {
          const ev = JSON.parse(dataLine.slice(6))
          handleEvent(ev)
        } catch (e) {
          console.warn('parse err', e, dataLine)
        }
      }
    }
  } catch (e) {
    msg.error('验证失败: ' + e.message)
  } finally {
    verifying.value = false
  }
}

function handleEvent(ev) {
  switch (ev.event) {
    case 'start':
      // 初始化模型列表
      modelStates.value = ev.models.map(m => ({
        model: m.model,
        label: m.label,
        status: 'idle',
        attempt: 0,
        error: '',
        duration_ms: 0,
      }))
      break

    case 'testing': {
      const t = modelStates.value.find(s => s.model === ev.model)
      if (t) {
        t.status = 'running'
        t.attempt = ev.attempt
      }
      break
    }

    case 'retrying': {
      const t = modelStates.value.find(s => s.model === ev.model)
      if (t) {
        t.status = 'retrying'
        t.error = ev.error
      }
      break
    }

    case 'result': {
      const t = modelStates.value.find(s => s.model === ev.model)
      if (t) {
        t.status = ev.ok ? 'success' : 'failed'
        t.error = ev.error || ''
        t.duration_ms = ev.duration_ms || 0
        t.attempt = ev.attempt || t.attempt
      }
      break
    }

    case 'done':
      verifyDone.value = true
      allOk.value = ev.all_ok
      if (ev.all_ok) {
        msg.success('全部灵脉畅通,可以入门!')
      } else {
        msg.warning('有模型不可用,请检查后重试')
      }
      break

    case 'error':
      msg.error('验证错误: ' + ev.message)
      break
  }
}

async function enterSect() {
  if (!allOk.value) return
  enteringGame.value = true
  // ★ 改为跳 Initiation 拜入仪式页(LLM 卜算 8 属性 + 机缘),不再直接创角
  // Initiation 内部会调 chooseSect 并展示华丽过场
  router.push({
    path: `/initiation/${sectId}`,
    query: {
      base_url: baseUrl.value.trim(),
      api_key: apiKey.value.trim(),
      name: characterName.value.trim() || '执笔者',
    },
  })
  enteringGame.value = false
  return
  // 兼容旧逻辑(已不可达)
  try {
    const { data } = await characterApi.chooseSect(
      sectId, characterName.value, baseUrl.value.trim(), apiKey.value.trim()
    )
    game.setCharacter(data)
    msg.success(`欢迎,${sect.value.name}弟子!`)
    router.push('/home')
  } catch (e) {
    msg.error(e.message)
  } finally {
    enteringGame.value = false
  }
}

function goBack() {
  router.push(fromOnboarding.value ? '/onboarding' : '/sect-choose')
}

const successCount = computed(() => modelStates.value.filter(m => m.status === 'success').length)
const failedCount = computed(() => modelStates.value.filter(m => m.status === 'failed').length)
const totalCount = computed(() => modelStates.value.length)
</script>

<template>
  <div class="verify-page">
    <!-- ★ 选中门派的背景图 -->
    <SectBackground :sect-id="sectId" overlay="strong" :opacity="0.40" />

    <!-- 仙侠流动背景 -->
    <WuxiaBackground intensity="light" accent="#D4A24C" />

    <div v-if="sect" class="container" style="position: relative; z-index: 1;">
      <div class="brand-bar">
        <BackButton :label="fromOnboarding ? '返回入门' : '返回选派'" inline @click="goBack" />
        <Logo :size="32" :text-size="16" />
      </div>

      <header class="header">
        <div class="title-line" :style="{ '--accent': sectAccent }">
          <SectFlag :sect-id="sectId" :name="sect.name" :size="48" :radius="10" />
          <h1>{{ sect.name }} · 灵脉验证</h1>
        </div>
        <p class="subtitle">{{ sect.provider_display }}</p>
        <div v-if="fromOnboarding" class="from-banner">
          ✓ 已从入门探测带入 Key,可直接点击「开始验证模型」开始逐个实测
        </div>
      </header>

      <div class="form-card">
        <h3>① 填写灵脉信息</h3>
        <p class="hint">您将使用自己的 API Key 接入【{{ sect.name }}】。我们会 <strong>并行测试</strong> 该派各境界对应的所有模型(同时发出 ping 请求),全部通过后才能正式入门 — 比逐个测试快 3-5 倍。</p>

        <label class="field">
          <span>道号</span>
          <input v-model="characterName" :disabled="verifying" maxlength="16" placeholder="为自己取个道号..." />
        </label>

        <label class="field">
          <span>API 地址(灵脉)</span>
          <input v-model="baseUrl" :disabled="verifying" :placeholder="baseUrlPlaceholder" />
        </label>

        <label class="field">
          <span>API Key</span>
          <input v-model="apiKey" :disabled="verifying" type="password" :placeholder="sect.byok_hint?.key_format || 'API Key'" />
        </label>

        <div class="form-meta">
          <div v-if="showBobdongAds"><span class="meta-k">推荐 base_url:</span> <code>{{ sect.byok_hint?.default_base_url }}</code></div>
          <div><span class="meta-k">官方 base_url:</span> <code>{{ sect.byok_hint?.official_base_url }}</code></div>
        </div>

        <button class="primary-btn" :disabled="verifying || !apiKey || !baseUrl" @click="startVerify">
          {{ verifying ? '⚡ 多模型并发验证中...' : (verifyDone ? '重新验证' : '② 同时验证所有模型') }}
        </button>
      </div>

      <div v-if="modelStates.length > 0" class="result-card">
        <div class="result-header">
          <h3>③ 模型测试结果</h3>
          <div class="counter">
            <span class="ok">✓ {{ successCount }}</span>
            <span class="fail" v-if="failedCount > 0">✗ {{ failedCount }}</span>
            <span class="total">/ {{ totalCount }}</span>
          </div>
        </div>

        <div class="model-list">
          <div
            v-for="m in modelStates"
            :key="m.model"
            class="model-row"
            :class="m.status"
          >
            <div class="row-left">
              <div class="status-icon">
                <span v-if="m.status === 'idle'">⏸</span>
                <span v-else-if="m.status === 'running'" class="spin">⏳</span>
                <span v-else-if="m.status === 'retrying'" class="spin">🔄</span>
                <span v-else-if="m.status === 'success'">✅</span>
                <span v-else-if="m.status === 'failed'">❌</span>
              </div>
              <div class="row-text">
                <div class="row-model"><code>{{ m.model }}</code></div>
                <div class="row-label">境界:{{ m.label }}</div>
                <div v-if="m.error" class="row-error">{{ m.error }}</div>
              </div>
            </div>
            <div class="row-right">
              <span v-if="m.status === 'running'" class="attempt">尝试 {{ m.attempt }}</span>
              <span v-else-if="m.status === 'retrying'" class="attempt">重试中…</span>
              <span v-else-if="m.duration_ms > 0" class="duration">{{ m.duration_ms }}ms</span>
            </div>
          </div>
        </div>

        <div v-if="verifyDone" class="result-action">
          <div v-if="allOk" class="success-banner">
            🎉 全部灵脉畅通,可以入门
          </div>
          <div v-else class="fail-banner">
            ⚠️ 有模型不可用,请检查 API Key 是否有相应权限,或换 base_url
          </div>
          <button
            class="primary-btn"
            :disabled="!allOk || enteringGame"
            @click="enterSect"
          >
            {{ enteringGame ? '入门中...' : '④ 正式加入门派' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.verify-page {
  min-height: 100vh;
  background: radial-gradient(ellipse at top, #1a1a2e 0%, #0a0a14 70%);
  padding: 30px 20px 80px;
}
.container {
  max-width: 800px; margin: 0 auto;
}
.brand-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 4px 0 18px;
  margin-bottom: 18px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.header { margin-bottom: 32px; }
.back {
  background: none; border: 1px solid rgba(255,255,255,0.15);
  color: #aaa; padding: 6px 14px; border-radius: 6px;
  cursor: pointer; font-size: 13px;
}
.back:hover { color: #fff; border-color: #D4A24C; }
.title-line { display: flex; align-items: center; gap: 14px; }
.emoji { font-size: 40px; }
.title-line h1 {
  margin: 0; font-size: 28px; color: var(--accent);
  letter-spacing: 2px;
}
.subtitle { color: #888; margin: 6px 0 0 56px; }
.from-banner {
  margin: 16px 0 0 56px;
  display: inline-block;
  padding: 6px 14px;
  background: rgba(82,183,136,0.12);
  border: 1px solid rgba(82,183,136,0.3);
  color: #52B788;
  border-radius: 4px;
  font-size: 12px;
  letter-spacing: 1px;
}

.form-card, .result-card {
  background: rgba(22,22,42,0.6);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
}
.form-card h3, .result-card h3 {
  color: #D4A24C; font-size: 16px; margin: 0 0 12px;
  letter-spacing: 2px;
}
.hint {
  color: #aaa; font-size: 13px; line-height: 1.7;
  margin: 0 0 20px;
}

.field {
  display: block; margin-bottom: 16px;
}
.field span {
  display: block; font-size: 12px; color: #aaa;
  margin-bottom: 6px; letter-spacing: 1px;
}
.field input {
  width: 100%; box-sizing: border-box;
  background: rgba(0,0,0,0.3);
  border: 1px solid rgba(255,255,255,0.1);
  color: #fff; padding: 10px 14px; border-radius: 6px;
  font-size: 14px; outline: none;
  font-family: 'SF Mono', Menlo, monospace;
}
.field input:focus { border-color: #D4A24C; }
.field input:disabled { opacity: 0.5; }

.form-meta {
  display: grid; gap: 6px;
  background: rgba(0,0,0,0.2);
  padding: 10px 14px; border-radius: 6px;
  margin: 16px 0 20px;
  font-size: 12px; color: #888;
}
.meta-k { color: #aaa; }
.form-meta code {
  color: #7FC7E8;
  background: rgba(127,199,232,0.06);
  padding: 1px 6px; border-radius: 3px;
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 11px;
}

.primary-btn {
  width: 100%;
  background: linear-gradient(135deg, #D4A24C 0%, #B58A3E 100%);
  border: none; color: #1a1a2e;
  padding: 12px; border-radius: 8px;
  font-size: 15px; font-weight: 600;
  cursor: pointer;
}
.primary-btn:hover:not(:disabled) {
  box-shadow: 0 6px 24px rgba(212,162,76,0.4);
}
.primary-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.result-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px;
}
.counter { display: flex; gap: 10px; font-size: 14px; align-items: center; }
.counter .ok { color: #52B788; font-weight: 600; }
.counter .fail { color: #C03F3F; font-weight: 600; }
.counter .total { color: #666; }

.model-list { display: grid; gap: 8px; }
.model-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px;
  background: rgba(0,0,0,0.25);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 8px;
  transition: all 0.3s;
}
.model-row.running { border-color: rgba(212,162,76,0.4); background: rgba(212,162,76,0.05); }
.model-row.retrying { border-color: rgba(255,180,84,0.4); background: rgba(255,180,84,0.05); }
.model-row.success { border-color: rgba(82,183,136,0.4); background: rgba(82,183,136,0.05); }
.model-row.failed { border-color: rgba(192,63,63,0.4); background: rgba(192,63,63,0.05); }

.row-left { display: flex; gap: 12px; align-items: center; }
.status-icon { font-size: 20px; min-width: 28px; text-align: center; }
.spin { display: inline-block; animation: spin 1.2s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.row-text { display: flex; flex-direction: column; gap: 2px; }
.row-model code {
  background: rgba(127,199,232,0.08); color: #7FC7E8;
  padding: 2px 8px; border-radius: 4px;
  font-family: 'SF Mono', Menlo, monospace; font-size: 13px;
}
.row-label { font-size: 12px; color: #888; }
.row-error { font-size: 11px; color: #FF8888; margin-top: 4px; }

.row-right { font-size: 12px; color: #666; }
.attempt { color: #FFB454; }
.duration { color: #888; font-family: 'SF Mono', monospace; }

.result-action {
  margin-top: 20px; padding-top: 20px;
  border-top: 1px solid rgba(255,255,255,0.06);
}
.success-banner {
  background: rgba(82,183,136,0.15);
  border: 1px solid rgba(82,183,136,0.4);
  color: #52B788;
  padding: 12px; border-radius: 8px;
  text-align: center; margin-bottom: 12px;
  letter-spacing: 1px;
}
.fail-banner {
  background: rgba(192,63,63,0.15);
  border: 1px solid rgba(192,63,63,0.4);
  color: #FF8888;
  padding: 12px; border-radius: 8px;
  text-align: center; margin-bottom: 12px;
  font-size: 14px;
}
</style>
