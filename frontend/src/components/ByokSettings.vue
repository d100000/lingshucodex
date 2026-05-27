<!--
  灵脉配置编辑器 — 可在主城任意时刻打开,修改 base_url + api_key
  强制流程:
    输入新配置 → 点[验证] → 后端逐个测当前角色门派的模型 → 全过才能[保存]
-->
<script setup>
import { ref, computed, watch } from 'vue'
import { useMessage } from 'naive-ui'
import { characterApi, siteApi } from '../api/client.js'

const props = defineProps({
  show: { type: Boolean, default: false },
  character: { type: Object, default: null },
})
const emit = defineEmits(['close', 'updated'])

const msg = useMessage()

const BOBDONG_BASE_URL = 'https://bobdong.cn/v1'
const baseUrl = ref('')
const apiKey = ref('')
const showBobdongAds = ref(false)

// ★ 模式:'verify' = 验证当前已有灵脉(无需输入), 'replace' = 输入新 key 替换
const mode = ref('verify')

// 验证状态
const verifying = ref(false)
const verified = ref(false)
const verifyResults = ref([])
const verifyError = ref('')
const saving = ref(false)
const baseUrlPlaceholder = computed(() =>
  showBobdongAds.value ? BOBDONG_BASE_URL : 'https://api.openai.com/v1'
)

async function loadSiteConfig() {
  try {
    const { data } = await siteApi.config()
    showBobdongAds.value = !!data?.show_bobdong_ads
  } catch {
    showBobdongAds.value = false
  }
}

watch(() => props.show, async (v) => {
  if (v && props.character) {
    await loadSiteConfig()
    // ★ 默认填入用户当前的 base_url(主城进来就有了,免重输)
    baseUrl.value = props.character.base_url || (showBobdongAds.value ? BOBDONG_BASE_URL : '')
    apiKey.value = ''
    mode.value = 'verify'  // 默认进入"验证当前"模式
    verified.value = false
    verifyResults.value = []
    verifyError.value = ''
  }
})

function switchToReplace() {
  mode.value = 'replace'
  verified.value = false
  verifyResults.value = []
  verifyError.value = ''
}

function switchToVerify() {
  mode.value = 'verify'
  apiKey.value = ''
  verified.value = false
  verifyResults.value = []
  verifyError.value = ''
}

// 一旦用户改了输入,自动清掉验证状态
watch([baseUrl, apiKey], () => {
  verified.value = false
})

const canSave = computed(() => verified.value && !saving.value)

const allModelsOk = computed(() =>
  verifyResults.value.length > 0 &&
  verifyResults.value.every(m => m.status === 'success')
)

async function verifyCurrent() {
  /** ★ 复用 character 已存的 base_url + api_key 验证,不需要重填 */
  if (!props.character?.sect) { msg.error('角色信息缺失'); return }
  verifying.value = true
  verified.value = false
  verifyResults.value = []
  verifyError.value = ''
  try {
    const { authApi } = await import('../api/client.js')
    const token = localStorage.getItem('auth_token') || ''
    const resp = await fetch('/api/sect/verify-current', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    })
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${resp.status}`)
    }
    await readSseStream(resp)
  } catch (e) {
    verifyError.value = e.message
    msg.error('验证失败: ' + e.message)
  } finally {
    verifying.value = false
  }
}

async function readSseStream(resp) {
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const blocks = buf.split('\n\n')
    buf = blocks.pop()
    for (const block of blocks) {
      const line = block.split('\n').find(l => l.startsWith('data: '))
      if (!line) continue
      try { handleEvent(JSON.parse(line.slice(6))) } catch {}
    }
  }
}

async function startVerify() {
  if (!apiKey.value.trim()) {
    msg.warning('请填写新的 API Key')
    return
  }
  if (!baseUrl.value.trim()) {
    msg.warning('请填写 API 地址')
    return
  }
  if (!props.character?.sect) {
    msg.error('角色信息缺失')
    return
  }

  verifying.value = true
  verified.value = false
  verifyResults.value = []
  verifyError.value = ''

  try {
    const token = localStorage.getItem('auth_token') || ''
    const resp = await fetch('/api/sect/verify-key', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        sect_id: props.character.sect,
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
      const blocks = buf.split('\n\n')
      buf = blocks.pop()
      for (const block of blocks) {
        const line = block.split('\n').find(l => l.startsWith('data: '))
        if (!line) continue
        try {
          const ev = JSON.parse(line.slice(6))
          handleEvent(ev)
        } catch {}
      }
    }
  } catch (e) {
    verifyError.value = e.message
    msg.error('验证失败: ' + e.message)
  } finally {
    verifying.value = false
  }
}

function handleEvent(ev) {
  switch (ev.event) {
    case 'start':
      verifyResults.value = ev.models.map(m => ({
        model: m.model, label: m.label,
        status: 'idle', error: '', duration_ms: 0,
      }))
      break
    case 'testing': {
      const t = verifyResults.value.find(s => s.model === ev.model)
      if (t) { t.status = 'running'; t.attempt = ev.attempt }
      break
    }
    case 'retrying': {
      const t = verifyResults.value.find(s => s.model === ev.model)
      if (t) { t.status = 'retrying'; t.error = ev.error }
      break
    }
    case 'result': {
      const t = verifyResults.value.find(s => s.model === ev.model)
      if (t) {
        t.status = ev.ok ? 'success' : 'failed'
        t.error = ev.error || ''
        t.duration_ms = ev.duration_ms || 0
      }
      break
    }
    case 'done':
      if (ev.all_ok) {
        verified.value = true
        msg.success('全部模型可用,现在可以保存了')
      } else {
        verified.value = false
        msg.warning('有模型不可用,无法保存')
      }
      break
    case 'error':
      verifyError.value = ev.message
      break
  }
}

async function save() {
  if (!verified.value) {
    msg.warning('请先验证模型可用性')
    return
  }
  saving.value = true
  try {
    const { data } = await characterApi.updateByok(
      baseUrl.value.trim(),
      apiKey.value.trim(),
      true,
    )
    msg.success(`灵脉已更换:${data.old_api_key_masked} → ${data.new_api_key_masked}`)
    emit('updated', data)
    emit('close')
  } catch (e) {
    msg.error('保存失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

function close() {
  if (verifying.value) return  // 验证中不允许关闭
  emit('close')
}

function presetUrl(url) {
  baseUrl.value = url
}
</script>

<template>
  <Transition name="modal-fade">
    <div v-if="show" class="modal-backdrop" @click.self="close">
      <div class="modal">
        <div class="modal-head">
          <h2>⚙️ 更换灵脉</h2>
          <button class="close-btn" @click="close" :disabled="verifying">✕</button>
        </div>

        <!-- bobdong.cn 推荐条 -->
        <div v-if="showBobdongAds" class="ad-strip" @click="presetUrl(BOBDONG_BASE_URL)">
          <span class="ad-tag">⭐ 官方推荐</span>
          <strong>bobdong.cn</strong>
          <span class="slogan">「 全网源头 token,更真、更快、更强 」</span>
          <span class="ad-cta">点此使用 →</span>
        </div>

        <div v-if="mode === 'replace'" class="warn-bar">
          ⚠️ 切换灵脉后,旧 Key 立刻停用。**保存前必须通过模型验证**,
          否则后端拒绝写入。
        </div>

        <!-- 当前配置 -->
        <div class="current">
          <div>当前 API 地址:<code>{{ character?.base_url || '-' }}</code></div>
          <div>当前 API Key:<code>{{ character?.api_key_masked || '-' }}</code></div>
          <div>当前门派:<strong>{{ character?.sect_name }}</strong></div>
        </div>

        <!-- ★ 模式切换 tab -->
        <div class="mode-tabs">
          <button
            class="mtab"
            :class="{ active: mode === 'verify' }"
            :disabled="verifying"
            @click="switchToVerify"
          >
            🔄 验证当前灵脉
          </button>
          <button
            class="mtab"
            :class="{ active: mode === 'replace' }"
            :disabled="verifying"
            @click="switchToReplace"
          >
            🔧 更换为新灵脉
          </button>
        </div>

        <!-- 模式 1: 验证当前灵脉(不需要重填) -->
        <div v-if="mode === 'verify'" class="verify-current-panel">
          <p class="mode-desc">
            ✨ 复用入门时填写的灵脉,无需再次输入 Key。
            <br/>
            点击下方按钮,系统会用当前角色的 <code>{{ character?.api_key_masked || '已存 Key' }}</code> 测试可用性。
          </p>
          <button
            class="big-verify-btn"
            :disabled="verifying"
            @click="verifyCurrent"
          >
            {{ verifying ? '⏳ 验证中...' : '✓ 立即验证当前灵脉' }}
          </button>
        </div>

        <!-- 模式 2: 输入新 key 替换 -->
        <div v-else>
          <label class="field">
            <span>新 API 地址</span>
            <input v-model="baseUrl" :disabled="verifying" :placeholder="baseUrlPlaceholder" />
            <div class="presets">
              <button v-if="showBobdongAds" class="preset" @click="presetUrl(BOBDONG_BASE_URL)">bobdong.cn(推荐)</button>
              <button class="preset" @click="presetUrl('https://api.openai.com/v1')">OpenAI</button>
              <button class="preset" @click="presetUrl('https://api.anthropic.com')">Anthropic</button>
            </div>
          </label>

          <label class="field">
            <span>新 API Key</span>
            <input v-model="apiKey" :disabled="verifying" type="password" placeholder="API Key" />
          </label>

          <div class="action-row">
            <button
              class="verify-btn"
              :disabled="verifying || !apiKey || !baseUrl"
              @click="startVerify"
            >
              {{ verifying ? '⏳ 验证中...' : (verified ? '🔄 重新验证' : '① 验证可用性') }}
            </button>
            <button
              class="save-btn"
              :disabled="!canSave"
              @click="save"
            >
              {{ saving ? '⏳ 保存中...' : '② 保存配置' }}
            </button>
          </div>
        </div>

        <!-- 验证结果 -->
        <div v-if="verifyResults.length" class="result-list">
          <div class="result-head">
            <h4>{{ character?.sect_name }} · 模型测试结果</h4>
            <span :class="{ ok: allModelsOk, fail: !allModelsOk }">
              {{ verifyResults.filter(r => r.status === 'success').length }} / {{ verifyResults.length }}
            </span>
          </div>
          <div
            v-for="r in verifyResults"
            :key="r.model"
            class="result"
            :class="r.status"
          >
            <span class="r-icon">
              <template v-if="r.status === 'idle'">⏸</template>
              <template v-else-if="r.status === 'running'">⏳</template>
              <template v-else-if="r.status === 'retrying'">🔄</template>
              <template v-else-if="r.status === 'success'">✅</template>
              <template v-else>❌</template>
            </span>
            <div class="r-info">
              <code>{{ r.model }}</code>
              <span class="r-label">{{ r.label }}</span>
              <span v-if="r.error" class="r-err">{{ r.error }}</span>
            </div>
            <span v-if="r.duration_ms" class="r-time">{{ r.duration_ms }}ms</span>
          </div>
        </div>

        <div v-if="verifyError" class="err-banner">{{ verifyError }}</div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(10,10,20,0.75);
  backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  z-index: 200;
  padding: 20px;
}
.modal {
  background: linear-gradient(180deg, #1a1a2e, #14142a);
  border: 1px solid rgba(212,162,76,0.3);
  border-radius: 14px;
  width: 100%; max-width: 640px;
  max-height: 90vh; overflow-y: auto;
  padding: 24px 28px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.6);
}
.modal-head {
  display: flex; justify-content: space-between; align-items: center;
  padding-bottom: 12px; margin-bottom: 16px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.modal-head h2 { margin: 0; font-size: 18px; color: #D4A24C; letter-spacing: 3px; }
.close-btn {
  background: none; border: 1px solid rgba(255,255,255,0.15);
  color: #aaa; width: 30px; height: 30px; border-radius: 4px;
  cursor: pointer; font-size: 14px;
}
.close-btn:hover:not(:disabled) { color: #fff; border-color: #C03F3F; }
.close-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* 广告条 */
.ad-strip {
  background: linear-gradient(90deg, rgba(212,162,76,0.18), rgba(255,224,163,0.08));
  border: 1px solid rgba(212,162,76,0.4);
  padding: 10px 14px; border-radius: 8px;
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  margin-bottom: 14px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
}
.ad-strip:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(212,162,76,0.25); }
.ad-tag {
  background: linear-gradient(135deg, #D4A24C, #FFE0A3);
  color: #1a1a2e;
  padding: 2px 8px; border-radius: 8px;
  font-size: 10px; font-weight: 700; letter-spacing: 1px;
}
.ad-strip strong { color: #FFE0A3; font-family: 'SF Mono', monospace; }
.slogan {
  color: #D4A24C;
  font-family: 'STKaiti','KaiTi',serif;
  letter-spacing: 1px; font-size: 13px;
}
.ad-cta { margin-left: auto; color: #FFB454; font-size: 12px; letter-spacing: 1px; }

.warn-bar {
  background: rgba(255,180,84,0.08);
  border-left: 3px solid #FFB454;
  padding: 8px 14px;
  border-radius: 4px;
  font-size: 12px;
  color: #FFB454;
  line-height: 1.7;
  margin-bottom: 14px;
}

.current {
  background: rgba(0,0,0,0.3);
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 12px;
  color: #aaa;
  margin-bottom: 14px;
}
.current div { padding: 3px 0; }
.current code {
  color: #7FC7E8;
  background: rgba(127,199,232,0.06);
  padding: 1px 6px; border-radius: 3px;
  font-family: 'SF Mono', monospace;
}
.current strong { color: #FFB454; }

/* ★ 模式 tab */
.mode-tabs {
  display: flex; gap: 8px; margin-bottom: 16px;
  border-bottom: 1px dashed rgba(212,162,76,0.2);
  padding-bottom: 12px;
}
.mtab {
  flex: 1;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  color: #888;
  padding: 9px 12px; border-radius: 6px;
  cursor: pointer; font-size: 12px;
  letter-spacing: 2px; font-family: 'STKaiti', serif;
  transition: all 0.2s;
}
.mtab:hover:not(:disabled) { border-color: #D4A24C; color: #FFE0A3; }
.mtab.active {
  background: linear-gradient(135deg, rgba(212,162,76,0.25), rgba(212,162,76,0.05));
  color: #FFE0A3;
  border-color: #D4A24C;
}
.mtab:disabled { opacity: 0.4; cursor: not-allowed; }

/* 验证当前灵脉面板 */
.verify-current-panel { text-align: center; padding: 8px 0 4px; }
.mode-desc {
  color: #aaa; font-size: 12px; line-height: 1.8;
  font-family: 'STKaiti', serif;
  margin: 0 0 18px;
}
.mode-desc code {
  color: #7FC7E8;
  background: rgba(127,199,232,0.08);
  padding: 2px 8px; border-radius: 4px;
  font-family: 'SF Mono', monospace; font-size: 11px;
}
.big-verify-btn {
  background: linear-gradient(135deg, #D4A24C, #B58A3E);
  color: #1a1a2e;
  border: none;
  padding: 14px 32px; border-radius: 8px;
  font-size: 15px; font-weight: 600;
  letter-spacing: 4px; font-family: 'STKaiti', serif;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(212,162,76,0.3);
  transition: all 0.2s;
}
.big-verify-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(212,162,76,0.5);
}
.big-verify-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.field { display: block; margin-bottom: 14px; }
.field span {
  display: block; font-size: 12px; color: #aaa;
  margin-bottom: 6px; letter-spacing: 1px;
}
.field input {
  width: 100%; box-sizing: border-box;
  background: rgba(0,0,0,0.3);
  border: 1px solid rgba(255,255,255,0.1);
  color: #fff; padding: 10px 14px; border-radius: 6px;
  font-size: 13px; outline: none;
  font-family: 'SF Mono', Menlo, monospace;
}
.field input:focus { border-color: #D4A24C; }
.field input:disabled { opacity: 0.5; }

.presets { display: flex; gap: 6px; margin-top: 6px; flex-wrap: wrap; }
.preset {
  background: rgba(127,199,232,0.05);
  border: 1px solid rgba(127,199,232,0.2);
  color: #7FC7E8; padding: 3px 8px;
  border-radius: 3px; font-size: 11px;
  cursor: pointer; font-family: 'SF Mono', monospace;
}
.preset:hover { background: rgba(127,199,232,0.12); }

.action-row {
  display: flex; gap: 10px; margin: 16px 0 14px;
}
.verify-btn, .save-btn {
  flex: 1;
  padding: 12px; border-radius: 6px;
  font-size: 13px; font-weight: 600;
  cursor: pointer; letter-spacing: 2px;
  border: none;
  transition: all 0.2s;
}
.verify-btn {
  background: rgba(127,199,232,0.12);
  color: #7FC7E8;
  border: 1px solid rgba(127,199,232,0.4);
}
.verify-btn:hover:not(:disabled) { background: rgba(127,199,232,0.2); }
.save-btn {
  background: linear-gradient(135deg, #D4A24C, #B58A3E);
  color: #1a1a2e;
}
.save-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(212,162,76,0.4); }
.verify-btn:disabled, .save-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.result-list {
  background: rgba(0,0,0,0.3);
  border-radius: 8px; padding: 12px 14px;
  margin-top: 14px;
}
.result-head {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 10px;
}
.result-head h4 { margin: 0; color: #D4A24C; font-size: 13px; letter-spacing: 2px; }
.result-head .ok { color: #52B788; font-weight: 600; }
.result-head .fail { color: #C03F3F; font-weight: 600; }
.result {
  display: flex; gap: 10px; align-items: center;
  padding: 8px 10px; border-radius: 6px;
  background: rgba(255,255,255,0.02);
  margin-bottom: 4px;
  font-size: 12px;
  border: 1px solid transparent;
}
.result.running { border-color: rgba(212,162,76,0.4); background: rgba(212,162,76,0.06); }
.result.retrying { border-color: rgba(255,180,84,0.4); background: rgba(255,180,84,0.05); }
.result.success { border-color: rgba(82,183,136,0.3); background: rgba(82,183,136,0.05); }
.result.failed { border-color: rgba(192,63,63,0.4); background: rgba(192,63,63,0.05); }
.r-icon { font-size: 16px; min-width: 22px; text-align: center; }
.r-info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.r-info code {
  background: rgba(127,199,232,0.08);
  color: #7FC7E8;
  padding: 1px 6px; border-radius: 3px;
  font-family: 'SF Mono', monospace; font-size: 11px;
  align-self: flex-start;
}
.r-label { color: #888; font-size: 11px; }
.r-err { color: #FF8888; font-size: 10px; }
.r-time { color: #888; font-family: 'SF Mono', monospace; font-size: 11px; }

.err-banner {
  background: rgba(192,63,63,0.12);
  border: 1px solid rgba(192,63,63,0.4);
  color: #FF8888;
  padding: 10px 14px; border-radius: 6px;
  font-size: 12px;
  margin-top: 12px;
}

.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.25s; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }
.modal-fade-enter-active .modal, .modal-fade-leave-active .modal {
  transition: transform 0.25s;
}
.modal-fade-enter-from .modal { transform: translateY(20px); }
</style>
