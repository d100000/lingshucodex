<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { byokApi, characterApi, siteApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'
import Logo from '../components/Logo.vue'
import WuxiaBackground from '../components/WuxiaBackground.vue'
import SectFlag from '../components/SectFlag.vue'

const router = useRouter()
const route = useRoute()
const msg = useMessage()
const game = useGameStore()

// 表单
const BOBDONG_BASE_URL = 'https://bobdong.cn/v1'
const baseUrl = ref('')
const apiKey = ref('')
const characterName = ref('执笔者')
const showBobdongAds = ref(false)
const baseUrlPlaceholder = computed(() =>
  showBobdongAds.value ? BOBDONG_BASE_URL : 'https://api.openai.com/v1'
)

// 状态
const step = ref(1)              // 1=填表  2=已探测
const probing = ref(false)
const probeError = ref('')
const probeResult = ref(null)    // { ok, models, sects: [...], available_sect_ids }

const hasAvailable = computed(() =>
  probeResult.value?.available_sect_ids?.length > 0
)

onMounted(async () => {
  try {
    const { data } = await siteApi.config()
    showBobdongAds.value = !!data?.show_bobdong_ads
    if (showBobdongAds.value && !baseUrl.value) {
      baseUrl.value = BOBDONG_BASE_URL
    }
  } catch {
    showBobdongAds.value = false
  }

  // 已有角色直接进主城
  try {
    const { data } = await characterApi.me()
    if (data) {
      game.setCharacter(data)
      router.replace('/home')
      return
    }
  } catch {
    // 没角色,正常
  }

  if (route.query.reason) {
    msg.info(route.query.reason)
    router.replace({ path: '/onboarding' })
  }
})

async function probe() {
  if (!apiKey.value.trim()) {
    msg.warning('请填写 API Key')
    return
  }
  if (!baseUrl.value.trim()) {
    msg.warning('请填写 API 地址')
    return
  }

  probing.value = true
  probeError.value = ''
  probeResult.value = null

  try {
    const { data } = await byokApi.probe(baseUrl.value.trim(), apiKey.value.trim())
    probeResult.value = data
    if (!data.ok) {
      probeError.value = data.error || '探测失败'
      msg.error('探测失败: ' + probeError.value)
    } else {
      if (data.available_sect_ids.length === 0) {
        msg.warning('该 Key 暂时不能加入任何门派,请检查权限')
        step.value = 2  // 显示 fallback 卡片网格让用户看到原因
      } else {
        msg.success(`已探测到 ${data.total_models} 个可用模型,${data.available_sect_ids.length} 个门派可选`)
        // ★ probe 成功立即跳沉浸式选派 — 带 avail 让 SectChoose 按真实 model 列表判断可选
        router.push({
          path: '/sect-choose',
          query: {
            base_url: baseUrl.value.trim(),
            api_key: apiKey.value.trim(),
            name: characterName.value.trim() || '执笔者',
            avail: data.available_sect_ids.join(','),  // ★ 关键:把 probe 的可选派透传
            from: 'onboarding',
          },
        })
      }
    }
  } catch (e) {
    msg.error(e.message)
    probeError.value = e.message
  } finally {
    probing.value = false
  }
}

function pickSect(sect) {
  if (!sect.can_choose) {
    msg.warning(sect.reason || '该派不可选')
    return
  }
  router.push({
    path: `/key-verify/${sect.id}`,
    query: {
      base_url: baseUrl.value.trim(),
      api_key: apiKey.value.trim(),
      name: characterName.value.trim() || '执笔者',
      from: 'onboarding',
    },
  })
}

// ★ 跳沉浸式选派页(网游式立绘),把 key 通过 query 透传
function goImmersive() {
  // 用户主动从 fallback 卡片网格点 "沉浸式选派" 按钮 — 带 avail
  const avail = (probeResult.value?.available_sect_ids || []).join(',')
  router.push({
    path: '/sect-choose',
    query: {
      base_url: baseUrl.value.trim(),
      api_key: apiKey.value.trim(),
      name: characterName.value.trim() || '执笔者',
      avail,
      from: 'onboarding',
    },
  })
}

function backToForm() {
  step.value = 1
}
</script>

<style scoped>
/* 沉浸式选派 CTA */
.immersive-btn {
  display: flex; flex-direction: column;
  align-items: center; gap: 4px;
  width: 100%;
  margin: 20px 0 16px;
  padding: 18px;
  background: linear-gradient(135deg, rgba(212,162,76,0.20), rgba(212,162,76,0.05));
  border: 2px solid #D4A24C;
  color: #FFE0A3;
  border-radius: 12px;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 4px;
  cursor: pointer;
  font-family: 'STKaiti', 'KaiTi', serif;
  transition: all 0.25s;
  box-shadow: 0 4px 24px rgba(212,162,76,0.2);
  position: relative;
  overflow: hidden;
}
.immersive-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 32px rgba(212,162,76,0.45);
  border-color: #FFE0A3;
}
.immersive-btn::before {
  content: '';
  position: absolute; top: 0; left: -100%;
  width: 50%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,224,163,0.25), transparent);
  animation: cta-shine 3s ease-in-out infinite;
}
@keyframes cta-shine {
  0% { left: -100%; } 60%, 100% { left: 150%; }
}
.immersive-sub {
  font-size: 11px; color: #aaa;
  letter-spacing: 2px;
  font-weight: 400;
  font-family: system-ui;
}

.quick-divider {
  display: flex; align-items: center;
  margin: 14px 0;
  color: #666; font-size: 12px;
  letter-spacing: 4px;
}
.quick-divider::before, .quick-divider::after {
  content: ''; flex: 1; height: 1px;
  background: rgba(255,255,255,0.08);
}
.quick-divider span { padding: 0 14px; }
</style>

<template>
  <div class="ob-page">
    <!-- ★ 登录页高大上动态背景图(取代旧的 WuxiaBackground)-->
    <div class="ob-bg"></div>
    <div class="ob-mask"></div>

    <div class="container" style="position: relative; z-index: 2;">
      <header class="header fade-in">
        <Logo :size="80" :text-size="32" layout="vertical" />
        <p class="subtitle">Web 版 · Token 修仙游戏</p>
      </header>

      <!-- 推荐广告卡 -->
      <div v-if="step === 1 && showBobdongAds" class="ad-card fade-in">
        <div class="ad-badge">⭐ 官方推荐 · 修真界唯一指定灵脉</div>
        <div class="ad-body">
          <div class="ad-left">
            <h3 class="ad-title">bobdong.cn</h3>
            <p class="ad-slogan">「 全网源头 token,更真、更快、更强 」</p>
            <p class="ad-desc">
              · 单一网关接入 Claude / GPT 全系列<br/>
              · 一个 Key 走遍 18 大宗派<br/>
              · 国内可访问,延迟低,稳定可靠
            </p>
          </div>
          <button class="ad-btn" @click="baseUrl='https://bobdong.cn/v1'">
            立即使用 →
          </button>
        </div>
      </div>

      <!-- Step 1: 填写灵脉 -->
      <div v-if="step === 1" class="card fade-in">
        <div class="step-label">第 ① 步 · 接入灵脉</div>
        <h2>欢迎,执笔者</h2>
        <p class="lead">
          请先填入您自己的 API Key。系统会自动探测可调用的"灵脉"(模型),
          告诉您能选哪些门派。
        </p>

        <label class="field">
          <span class="lbl">道号</span>
          <input v-model="characterName" maxlength="16" placeholder="为自己取个道号..." />
        </label>

        <label class="field">
          <span class="lbl">API 地址(可自由修改)</span>
          <input v-model="baseUrl" :placeholder="baseUrlPlaceholder" />
          <div class="preset-btns">
            <button v-if="showBobdongAds" type="button" class="preset" @click="baseUrl=BOBDONG_BASE_URL">bobdong.cn(网关)</button>
            <button type="button" class="preset" @click="baseUrl='https://api.openai.com/v1'">OpenAI 官方</button>
            <button type="button" class="preset" @click="baseUrl='https://api.anthropic.com'">Anthropic 官方</button>
            <button type="button" class="preset" @click="baseUrl='https://api.deepseek.com/v1'">DeepSeek 官方</button>
            <button type="button" class="preset" @click="baseUrl='https://api.siliconflow.cn/v1'">SiliconFlow</button>
          </div>
          <span class="hint">点上方任一按钮快速填入,或直接在输入框里编辑</span>
        </label>

        <label class="field">
          <span class="lbl">API Key</span>
          <input v-model="apiKey" type="password" placeholder="API Key" />
          <span class="hint">您的 Key 仅用于本游戏战斗推理,平台不存储到数据库</span>
        </label>

        <button class="primary-btn" :disabled="probing || !apiKey || !baseUrl" @click="probe">
          <span v-if="probing">⏳ 正在探测灵脉...</span>
          <span v-else>探索灵脉</span>
        </button>

        <div v-if="probeError" class="err-banner">{{ probeError }}</div>
      </div>

      <!-- Step 2: 门派可选性 -->
      <div v-else-if="step === 2 && probeResult" class="card fade-in">
        <div class="step-label">第 ② 步 · 选择门派</div>
        <div class="probe-summary">
          <div>
            ✓ 已探测到 <strong>{{ probeResult.total_models }}</strong> 个可用模型,
            其中 <strong class="ok">{{ probeResult.available_sect_ids.length }}</strong> / 5
            个门派可加入
          </div>
          <button class="text-btn" @click="backToForm">← 重新探测</button>
        </div>

        <!-- ★ 沉浸式选派入口(网游式,大图立绘)-->
        <button class="immersive-btn" @click="goImmersive">
          🎮 沉浸式选派 · 网游式人物界面
          <span class="immersive-sub">高清立绘 + 左右切换 + 招式/数值/背景四象限</span>
        </button>

        <div class="quick-divider"><span>或快速选择</span></div>

        <div class="sect-grid">
          <div
            v-for="s in probeResult.sects"
            :key="s.id"
            class="sect-card"
            :class="{ ok: s.can_choose, locked: !s.can_choose }"
            @click="pickSect(s)"
          >
            <div class="sect-head">
              <SectFlag :sect-id="s.id" :name="s.name" :size="44" :radius="10" />
              <div>
                <div class="name">{{ s.name }}</div>
                <div class="provider">{{ s.provider_display }}</div>
              </div>
              <div class="status">
                <span v-if="s.can_choose" class="badge ok-badge">✓ 可加入</span>
                <span v-else class="badge no-badge">✗ 不可加入</span>
              </div>
            </div>

            <div class="sect-body">
              <div class="ratio-bar">
                <div class="ratio-fill" :style="{ width: s.available_ratio + '%' }"></div>
              </div>
              <div class="ratio-text">
                {{ s.have.length }} / {{ s.required.length }} 模型已开通
                ({{ s.available_ratio }}%)
              </div>

              <div v-if="s.can_choose" class="models-list">
                <div class="m-label">已就绪:</div>
                <code v-for="m in s.have" :key="m" class="m-tag ok">{{ m }}</code>
              </div>

              <div v-else class="missing">
                <div class="m-label">原因:</div>
                <div class="reason">{{ s.reason }}</div>
                <div v-if="s.missing.length" class="missing-list">
                  <code v-for="m in s.missing" :key="m" class="m-tag missing-tag">{{ m }}</code>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="!hasAvailable" class="no-available">
          ⚠️ 当前 Key 无法加入任何门派。请尝试:
          <ul>
            <li>更换有 Claude 或 GPT 权限的 Key</li>
            <li>调整 API 地址(确认官方地址或其它兼容网关)</li>
            <li><a @click="backToForm">← 返回上一步重新填写</a></li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ob-page {
  min-height: 100vh;
  padding: 40px 20px 80px;
  position: relative;
  /* 不要自己加 background,让 .ob-bg 透出来 */
}
/* ★ 登录页高大上动态背景层(普通 div,避免伪元素堆叠/裁剪坑) */
.ob-bg {
  position: fixed; inset: 0;
  z-index: 0;            /* 在内容下方(.container 是 z-index:1) */
  background:
    url('/images/ui/login-bg.jpg') center center / cover no-repeat,
    #050810;
  filter: brightness(0.7) saturate(0.85);
  animation: bg-kenburns 32s ease-in-out infinite alternate;
  pointer-events: none;
}
.ob-mask {
  position: fixed; inset: 0;
  z-index: 0;
  background:
    radial-gradient(ellipse at 50% 30%, rgba(212,162,76,0.10) 0%, transparent 50%),
    linear-gradient(180deg, rgba(5,8,16,0.45) 0%, rgba(5,8,16,0.75) 80%, rgba(5,8,16,0.92) 100%);
  pointer-events: none;
}
@keyframes bg-kenburns {
  0%   { transform: scale(1) translate(0, 0); }
  100% { transform: scale(1.08) translate(-2%, -1%); }
}
.container { max-width: 920px; margin: 0 auto; }

.header {
  text-align: center;
  margin-bottom: 40px;
  display: flex; flex-direction: column; align-items: center; gap: 8px;
}
.subtitle { color: #888; letter-spacing: 4px; font-size: 13px; margin: 0; }

.card {
  background: rgba(22,22,42,0.6);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 32px;
}
.step-label {
  display: inline-block;
  background: rgba(212,162,76,0.12);
  color: #D4A24C;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  letter-spacing: 2px;
  margin-bottom: 16px;
}
h2 {
  margin: 0 0 8px;
  font-family: 'STKaiti','KaiTi',serif;
  font-size: 26px; color: #D4A24C;
  letter-spacing: 4px;
}
.lead {
  color: #aaa; font-size: 14px; line-height: 1.8;
  margin: 0 0 24px;
}

.field { display: block; margin-bottom: 18px; }
.lbl {
  display: block; font-size: 12px; color: #aaa;
  margin-bottom: 6px; letter-spacing: 1px;
}
.field input {
  width: 100%; box-sizing: border-box;
  background: rgba(0,0,0,0.3);
  border: 1px solid rgba(255,255,255,0.1);
  color: #fff; padding: 11px 14px;
  border-radius: 6px;
  font-size: 14px; outline: none;
  font-family: 'SF Mono', Menlo, monospace;
}
.field input:focus { border-color: #D4A24C; }
.hint {
  display: block; font-size: 11px; color: #666;
  margin-top: 4px;
}
.preset-btns {
  display: flex; flex-wrap: wrap; gap: 6px;
  margin-top: 8px;
}
.preset {
  background: rgba(127,199,232,0.05);
  border: 1px solid rgba(127,199,232,0.2);
  color: #7FC7E8;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  font-family: 'SF Mono', Menlo, monospace;
}
.preset:hover {
  background: rgba(127,199,232,0.12);
  border-color: #7FC7E8;
}

/* ===== bobdong.cn 推荐广告卡 ===== */
.ad-card {
  background: linear-gradient(135deg, rgba(212,162,76,0.12) 0%, rgba(255,224,163,0.05) 50%, rgba(212,162,76,0.08) 100%);
  border: 1px solid rgba(212,162,76,0.45);
  border-radius: 14px;
  padding: 20px 24px;
  margin-bottom: 22px;
  position: relative;
  overflow: hidden;
}
.ad-card::before {
  content: '';
  position: absolute;
  top: -50%; left: -50%; width: 200%; height: 200%;
  background: radial-gradient(circle at 30% 50%, rgba(255,224,163,0.18), transparent 30%);
  pointer-events: none;
  animation: shimmer 6s linear infinite;
}
@keyframes shimmer {
  0%   { transform: translateX(0); }
  50%  { transform: translateX(20%); }
  100% { transform: translateX(0); }
}
.ad-badge {
  display: inline-block;
  background: linear-gradient(135deg, #D4A24C, #FFE0A3);
  color: #1a1a2e;
  font-size: 11px;
  letter-spacing: 2px;
  padding: 3px 10px;
  border-radius: 12px;
  font-weight: 700;
  margin-bottom: 10px;
  box-shadow: 0 2px 8px rgba(212,162,76,0.4);
}
.ad-body {
  display: flex; gap: 20px; align-items: center; justify-content: space-between;
  flex-wrap: wrap;
  position: relative; z-index: 1;
}
.ad-left { flex: 1; min-width: 260px; }
.ad-title {
  margin: 0;
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 28px;
  background: linear-gradient(135deg, #D4A24C, #FFE0A3 50%, #D4A24C);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 2px;
}
.ad-slogan {
  margin: 8px 0 12px;
  font-size: 16px;
  color: #FFE0A3;
  letter-spacing: 2px;
  font-family: 'STKaiti','KaiTi','Source Han Serif SC',serif;
  text-shadow: 0 0 12px rgba(212,162,76,0.4);
}
.ad-desc {
  margin: 0;
  color: #ccc; font-size: 13px; line-height: 1.9;
}
.ad-btn {
  background: linear-gradient(135deg, #D4A24C 0%, #B58A3E 100%);
  border: 1px solid rgba(255,224,163,0.5);
  color: #1a1a2e;
  padding: 12px 28px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  letter-spacing: 3px;
  transition: all 0.2s;
  white-space: nowrap;
  box-shadow: 0 4px 16px rgba(212,162,76,0.3);
}
.ad-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(212,162,76,0.5);
}

.primary-btn {
  width: 100%; margin-top: 8px;
  background: linear-gradient(135deg, #D4A24C 0%, #B58A3E 100%);
  border: none; color: #1a1a2e;
  padding: 14px; border-radius: 8px;
  font-size: 15px; font-weight: 600;
  cursor: pointer;
  letter-spacing: 2px;
  transition: all 0.2s;
}
.primary-btn:hover:not(:disabled) {
  box-shadow: 0 6px 24px rgba(212,162,76,0.4);
  transform: translateY(-1px);
}
.primary-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.err-banner {
  margin-top: 16px;
  background: rgba(192,63,63,0.15);
  border: 1px solid rgba(192,63,63,0.4);
  color: #FF8888;
  padding: 12px; border-radius: 8px;
  font-size: 13px;
}

/* === Step 2 === */
.probe-summary {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 18px; padding-bottom: 14px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  font-size: 14px; color: #ccc;
}
.probe-summary strong { color: #D4A24C; margin: 0 2px; }
.probe-summary .ok { color: #52B788; }

.text-btn {
  background: none; border: 1px solid rgba(255,255,255,0.15);
  color: #aaa; padding: 4px 12px;
  border-radius: 4px; cursor: pointer;
  font-size: 12px;
}
.text-btn:hover { color: #fff; border-color: #D4A24C; }

.sect-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
  margin-top: 8px;
}

.sect-card {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  padding: 16px 20px;
  background: rgba(255,255,255,0.02);
  transition: all 0.2s;
  cursor: pointer;
}
.sect-card.ok {
  border-color: rgba(82,183,136,0.35);
  background: linear-gradient(180deg, rgba(82,183,136,0.06), rgba(82,183,136,0.01));
}
.sect-card.ok:hover {
  transform: translateY(-2px);
  border-color: #52B788;
  box-shadow: 0 8px 24px rgba(82,183,136,0.18);
}
.sect-card.locked {
  opacity: 0.55;
  cursor: not-allowed;
  filter: grayscale(0.6);
}

.sect-head {
  display: flex; align-items: center; gap: 14px;
  margin-bottom: 12px;
}
.sect-head .emoji { font-size: 36px; }
.sect-head .name {
  color: #D4A24C; font-size: 17px; font-weight: 500;
  letter-spacing: 2px;
}
.sect-head .provider {
  color: #888; font-size: 12px; margin-top: 2px;
}
.sect-head .status { margin-left: auto; }

.badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
}
.ok-badge {
  background: rgba(82,183,136,0.15);
  color: #52B788;
}
.no-badge {
  background: rgba(150,150,150,0.15);
  color: #888;
}

.sect-body { font-size: 13px; }
.ratio-bar {
  height: 6px;
  background: rgba(0,0,0,0.4);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 6px;
}
.ratio-fill {
  height: 100%;
  background: linear-gradient(90deg, #B58A3E, #FFE0A3);
  transition: width 0.6s;
}
.sect-card.ok .ratio-fill {
  background: linear-gradient(90deg, #52B788, #95D5B2);
}
.ratio-text { color: #888; font-size: 12px; margin-bottom: 10px; }

.models-list, .missing { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.m-label { font-size: 12px; color: #666; margin-right: 4px; }
.m-tag {
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 3px;
}
.m-tag.ok {
  background: rgba(127,199,232,0.08);
  color: #7FC7E8;
}
.m-tag.missing-tag {
  background: rgba(192,63,63,0.1);
  color: #FF8888;
  text-decoration: line-through;
}
.reason {
  font-size: 13px; color: #FF8888;
  margin: 6px 0;
}
.missing-list { margin-top: 4px; }

.no-available {
  margin-top: 20px;
  background: rgba(255,180,84,0.08);
  border: 1px solid rgba(255,180,84,0.3);
  border-radius: 8px;
  padding: 16px;
  color: #FFB454;
  font-size: 14px;
}
.no-available ul { margin: 8px 0 0; padding-left: 24px; line-height: 1.8; }
.no-available a {
  color: #D4A24C; text-decoration: underline; cursor: pointer;
}
</style>
