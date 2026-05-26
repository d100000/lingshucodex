<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed, watch } from 'vue'
import { useRouter, useRoute, onBeforeRouteLeave } from 'vue-router'
import { useMessage } from 'naive-ui'
import { battleApi, characterApi, inventoryApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'
import { getSectTheme, getSectCssVars } from '../config/sectTheme.js'
import Logo from '../components/Logo.vue'
import SkillCastIntro from '../components/SkillCastIntro.vue'
import BackButton from '../components/BackButton.vue'
import SectBackground from '../components/SectBackground.vue'
import { formatNum } from '../utils/format.js'
import GiftDialog from '../components/GiftDialog.vue'
import RoundPortrait from '../components/RoundPortrait.vue'
import ItemIcon from '../components/ItemIcon.vue'
import SectFlag from '../components/SectFlag.vue'
import { enemyPortraitRef, enemyPreview, playerPreview } from '../utils/characterPreview.js'
import { MOBILE_RESUME_EVENT, logTelemetry, vibrate } from '../utils/mobile.js'

const route = useRoute()
const router = useRouter()
const msg = useMessage()
const game = useGameStore()

const battleId = route.params.id
const character = computed(() => game.character)

const state = ref(null)
const cards = ref([])
const inventory = ref([])
const narration = ref('')
const ended = ref(false)
const result = ref(null)
const rewards = ref(null)
const battleCommit = ref(null)
const autoReturnCountdown = ref(0)
let countdownTimer = null
let autoReturnTimer = null

// 三栏 tab:attack / item / destiny
const activeTab = ref('attack')

// 天命降临
const destinyCharged = ref(false)
const destinySkill = ref(null)
const showDestinyAnim = ref(false)

// 战报卡(每回合数值汇总)
const battleLog = ref([])

// 屏幕反馈
const playerShake = ref(false)
const enemyShake = ref(false)
const screenShake = ref({ x: 0, y: 0 })
const flashColor = ref('')
const damageFx = ref([])

// 高亮 ** ** 关键词
function highlightNarration(text) {
  if (!text) return ''
  // ** xxx ** → <em class="hi">xxx</em>
  return text.replace(/\*\*([^*]+)\*\*/g, (_, p) => {
    // 数字 + 单位识别为"伤害",更亮的颜色
    if (/^\d/.test(p)) return `<em class="hi hi-num">${p}</em>`
    if (/暴击|致命|惊艳|绝杀|天命/.test(p)) return `<em class="hi hi-crit">${p}</em>`
    return `<em class="hi">${p}</em>`
  })
}

// 施法前摇:点击瞬间就 true,LLM 返回后才 false
const castingCard = ref(null)   // 当前正在施法的卡牌(玩家点击立即设置)
const castParticles = ref([])    // 前摇粒子
const showCastIntro = ref(false) // ★ 国风招式前摇遮罩
let castIntroMinTime = 0         // 前摇最少显示时长(ms),避免太快闪过

// ★ 卡牌伤害预览(GET /battle/:id/card-preview)
const cardPreviews = ref({})  // { card_id: { estimated_damage, crit_damage, hit_rate, crit_rate, qi_after } }

// 招式准备进度(根据 LLM 字符数 0-100)
const castProgress = ref(0)
const EXPECT_NARRATION_CHARS = 100  // 预期叙事长度(v2:短叙事),用于进度条估算

// 延迟显示 damage:前摇期间缓存,前摇结束才"落"到怪物身上
// ★ v2:数值/叙事解耦后,这两个 ref 仅供 destiny 全屏前摇用,普通招式直接立即触发
const pendingDamage = ref([])
const pendingEffects = ref([])
const showIntroAnim = ref(true)  // 战斗开场动画
const showResultAnim = ref(false)

// ★ 立绘加载失败时回退 emoji
const playerImageError = ref(false)
const enemyImageError = ref(false)

// ★ 退出/撤离 loading 文案(显示在按钮上,避免卡死体感)
const exiting = ref(false)
const exitLabel = ref('')

// ========================================================
// ★ v2 新状态:预选队列 / AI HUD / 跳过 / 章节
// ========================================================

// T2D 预选队列 — LLM 还在跑时,用户点的招式排队等
const castQueue = ref([])              // 数组:[card1, card2, ...]
const MAX_QUEUE = 3

// T1C AI 思考 HUD — narration_start/end 事件驱动
const aiHud = ref({
  active: false,            // 是否正在生成
  model: '',                // 当前调用的模型
  startTime: 0,             // 开始时间戳
  elapsedMs: 0,             // 已用时间(实时刷新)
  chars: 0,                 // 已生成字符数
  cached: false,            // 是否命中预生成池
  round: 0,                 // 哪一回合的叙事
})
let hudTimer = null         // 100ms 刷新一次 elapsedMs

// T2E 跳过 — 标记 + 发 ws skip
const narrationSkipped = ref(false)

// T3K 战后章节
const chapter = ref('')                 // 流式累积的章节文本
const chapterGenerating = ref(false)    // 是否还在 stream
const chapterShown = ref(false)         // 用户是否点开了

// ★ 新手教学提示(tutorial_hint 事件驱动) — 持久化:看过一次就不再出现
const tutorialHint = ref(null)   // { step, message }
const tutorialDismissed = ref(localStorage.getItem('battle_tutorial_seen') === '1')
function dismissTutorial() {
  tutorialHint.value = null
  tutorialDismissed.value = true
  localStorage.setItem('battle_tutorial_seen', '1')
}

// ★ 赠���系统
const showGiftDialog = ref(false)
const giftCount = ref(0)
function onGiftAccepted(data) {
  showGiftDialog.value = false
  msg.success('怪物收下礼物离去,人情章已入墨炉')
  // 战斗会自动收到 end 事件
}
function onGiftRejected(data) {
  giftCount.value++
}

// v3 战斗节奏统一方案 — 不再分 speed/drama,全 LLM 自适应
// (普通=Haiku, 暴击=Sonnet, 天命/章节=Opus,详见后端 pick_narration_model)

const sectTheme = computed(() => getSectTheme(state.value?.player?.sect_id || character.value?.sect))
const sectCssVars = computed(() => getSectCssVars(state.value?.player?.sect_id || character.value?.sect))
const sectAccent = computed(() => sectTheme.value.accent)

// ============== 头像系统:不同等级 / 境界 不同人头 ==============
// 9 个境界,2 个门派 = 18 张唯一人头
const PORTRAIT_MAP = {
  canglan: {
    qi:        { emoji: '🧑‍🎓', frame: '#888', title: '初入沧澜' },
    foundation:{ emoji: '👨‍🎤', frame: '#52B788', title: '青衫剑士' },
    golden:    { emoji: '🧙‍♂️', frame: '#4A90E2', title: '金丹剑修' },
    yuanying:  { emoji: '👨‍🏫', frame: '#8B5CF6', title: '元婴长老' },
    huashen:   { emoji: '🤴', frame: '#F59E0B', title: '化神真人' },
    hetishi:   { emoji: '👑', frame: '#EF4444', title: '合体宗师' },
    dacheng:   { emoji: '🦹', frame: '#FFD700', title: '大乘剑圣' },
    dujie:     { emoji: '😇', frame: '#FFE0A3', title: '渡劫天人' },
    feisheng:  { emoji: '🧚', frame: '#FFFFFF', title: '飞升仙尊' },
  },
  tianji: {
    qi:        { emoji: '🧑‍💻', frame: '#888', title: '机关学徒' },
    foundation:{ emoji: '👨‍🔧', frame: '#52B788', title: '青铜匠师' },
    golden:    { emoji: '🧑‍🔬', frame: '#4A90E2', title: '金丹工师' },
    yuanying:  { emoji: '👨‍💼', frame: '#8B5CF6', title: '元婴智者' },
    huashen:   { emoji: '🦸', frame: '#F59E0B', title: '化神算师' },
    hetishi:   { emoji: '🧝‍♂️', frame: '#EF4444', title: '合体阁主' },
    dacheng:   { emoji: '🦹‍♂️', frame: '#FFD700', title: '大乘机宗' },
    dujie:     { emoji: '🤴', frame: '#FFE0A3', title: '渡劫天机' },
    feisheng:  { emoji: '👁️', frame: '#FFFFFF', title: '飞升道君' },
  },
}

const playerPortrait = computed(() => {
  const sect = character.value?.sect || 'canglan'
  const realm = character.value?.realm || 'qi'
  const base = PORTRAIT_MAP[sect]?.[realm] || PORTRAIT_MAP.canglan.qi
  // ★ 玩家立绘:5 派 × 9 境界,文件名直接对应 realm
  return {
    ...base,
    image: `/images/portraits/players/${sect}/${realm}.png`,
  }
})

const enemyPortrait = computed(() => enemyPortraitRef(state.value?.enemy || {}, 'circle'))
const enemyPortraitFrame = computed(() => {
  const enemy = state.value?.enemy || {}
  if (enemy.is_npc) return '#7FC7E8'
  if (enemy.tier === 'boss' || String(enemy.id || '').startsWith('boss_')) return '#FFD700'
  return '#C03F3F'
})

// ============== 招式分级 ==============
// 根据 qi_cost 分级,影响视觉特效
function cardTier(card) {
  if (card.qi_cost >= 50) return 'ult'      // 终极
  if (card.qi_cost >= 25) return 'special'  // 高级
  if (card.qi_cost >= 12) return 'normal'   // 普通
  return 'basic'                             // 基础
}

const TIER_COLOR = {
  basic:   '#7FC7E8',
  normal:  '#52B788',
  special: '#FFB454',
  ult:     '#FFD700',
}

const TIER_LABEL = {
  basic:   '基础',
  normal:  '中级',
  special: '高阶',
  ult:     '终极',
}

const CARD_TYPE_LABEL = {
  attack: '直接伤害',
  heal: '恢复气血',
  buff: '强化状态',
  ult: '爆发终结',
}

function cardEffectText(card) {
  const preview = cardPreviews.value[card.id]
  if (card.type === 'heal') return '恢复气血,适合在对方爆发前稳住血线。'
  if (card.type === 'buff') return '提供本战或下一击强化,适合先手铺垫。'
  if (preview) {
    return `预计伤害 ${preview.estimated_damage},命中 ${Math.round(preview.hit_rate * 100)}%,暴击 ${Math.round(preview.crit_rate * 100)}%。`
  }
  return card.description || '凝聚灵气出招,根据当前属性结算效果。'
}

function cardSynergyText(card) {
  if (card.type === 'heal') return '建议搭配护体罡气、御风诀,拖长回合等待灵气恢复。'
  if (card.type === 'buff') {
    if (card.name.includes('暴击') || card.description?.includes('暴击')) return '建议接高阶/终极伤害招式,把暴击收益吃满。'
    if (card.description?.includes('速度') || card.name.includes('风')) return '建议接命中较低但威力高的招式,先手压制更稳。'
    return '建议接本门高倍率攻击招式,不要让强化回合空转。'
  }
  if (cardTier(card) === 'ult') return '建议先用凝神、剑意、推演或防御类招式铺垫,等灵气充足再终结。'
  if ((card.hit_rate || 1) < 0.9) return '建议搭配万象推演、御风类命中/速度招式,降低落空风险。'
  return '建议与增益类心法轮换使用,保持灵气消耗和输出节奏。'
}

let ws = null
let damageId = 0
let wsConnected = false
let leavingForResult = false
let reconnectTimer = null
const wsStatus = ref('connecting')
const reconnectAttempts = ref(0)

// ★ v3 战斗阶段系统:替代布尔 processing,让玩家可见当前状态
const battlePhase = ref('idle')  // 'idle' | 'casting' | 'resolving' | 'narrating' | 'enemy_turn'
const canAct = computed(() => battlePhase.value === 'idle' && !ended.value)

// Token 消耗估算(中文 ~1.3 char/token)
const estimatedTokens = computed(() => Math.ceil(aiHud.value.chars * 1.3))

// ★ 防御性 WS 发送:ws 已断时不抛错,而是 toast + 强制退出
function safeSend(action, payload = {}) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    if (!leavingForResult && !ended.value) {
      msg.warning('战斗连接暂断,已保留当前操作,正在重连')
      scheduleWsReconnect('send_failed')
    }
    return false
  }
  try {
    ws.send(JSON.stringify({ action, payload }))
    return true
  } catch (e) {
    console.warn('[ws.send] 失败', e)
    return false
  }
}

onMounted(async () => {
  // 战斗开场动画 2.5s
  setTimeout(() => { showIntroAnim.value = false }, 2500)

  try {
    const { data } = await battleApi.listCards()
    cards.value = data
  } catch (e) {
    msg.error(e.message || '加载招式失败')
    if (e.code === 'AUTH_REQUIRED' || e.code === 'NOT_FOUND') {
      return router.replace({ path: '/onboarding', query: { reason: '请先填写 API Key 并选择门派' } })
    }
    return router.replace({ path: '/home', query: { error: 'cards_load_failed', msg: e.message } })
  }

  // 加载背包丹药
  try {
    const inv = await inventoryApi.list()
    inventory.value = (inv.data.items || []).filter(i => i.type === 'consumable')
  } catch {}

  // ★ 加载卡牌伤害预览(非阻塞,失败也不影响战斗)
  battleApi.cardPreview(battleId).then(res => {
    const map = {}
    for (const p of (res.data || [])) map[p.card_id] = p
    cardPreviews.value = map
  }).catch(() => {})

  openBattleSocket()
  window.addEventListener(MOBILE_RESUME_EVENT, onMobileResume)
  window.addEventListener('beforeunload', onBeforeUnload)
})

onUnmounted(() => {
  leavingForResult = true
  if (reconnectTimer) clearTimeout(reconnectTimer)
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    try { ws.close() } catch {}
  }
  window.removeEventListener(MOBILE_RESUME_EVENT, onMobileResume)
  window.removeEventListener('beforeunload', onBeforeUnload)
  cancelAutoReturn()
})

onBeforeRouteLeave((_to, _from, next) => {
  if (!ended.value && !leavingForResult && !exiting.value) {
    const ok = window.confirm('当前战斗仍在推演,离开后可能需要重新进入战局。确定离开吗?')
    if (!ok) return next(false)
  }
  next()
})

function onBeforeUnload(event) {
  if (ended.value || leavingForResult || exiting.value) return
  event.preventDefault()
  event.returnValue = ''
}

function openBattleSocket() {
  const wsProto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsToken = localStorage.getItem('auth_token') || ''
  wsStatus.value = reconnectAttempts.value ? 'reconnecting' : 'connecting'
  try {
    ws = new WebSocket(`${wsProto}//${location.host}/ws/battle/${battleId}?token=${encodeURIComponent(wsToken)}`)
  } catch (e) {
    scheduleWsReconnect('constructor_failed')
    return
  }

  ws.onopen = () => {
    wsConnected = true
    leavingForResult = false
    wsStatus.value = 'connected'
    reconnectAttempts.value = 0
    refreshBattleSnapshot('ws_open')
  }
  ws.onmessage = (e) => {
    try {
      const m = JSON.parse(e.data)
      handleEvent(m)
    } catch {}
  }
  ws.onerror = () => {
    if (ended.value || leavingForResult) return
    wsStatus.value = 'unstable'
    logTelemetry('battle_ws_error', { battleId })
  }
  ws.onclose = (ev) => {
    console.log('[ws.onclose]', { code: ev?.code, leavingForResult, ended: ended.value, wsConnected })
    if (leavingForResult || ended.value) return
    if (!wsConnected) {
      wsStatus.value = 'failed'
      return
    }
    scheduleWsReconnect(`close_${ev?.code || 'unknown'}`)
  }
}

function scheduleWsReconnect(reason = 'unknown') {
  if (ended.value || leavingForResult) return
  if (reconnectTimer) clearTimeout(reconnectTimer)
  wsStatus.value = 'reconnecting'
  reconnectAttempts.value += 1
  logTelemetry('battle_ws_reconnect', { battleId, reason, attempt: reconnectAttempts.value })
  if (reconnectAttempts.value > 3) {
    wsStatus.value = 'failed'
    return
  }
  reconnectTimer = setTimeout(() => {
    openBattleSocket()
  }, Math.min(3000, 600 * reconnectAttempts.value))
}

async function refreshBattleSnapshot(reason = 'manual') {
  try {
    const { data } = await battleApi.get(battleId)
    if (data?.snapshot) {
      state.value = data.snapshot
      destinyCharged.value = !!data.snapshot.destiny_charged
      if (data.snapshot.destiny_skill) destinySkill.value = data.snapshot.destiny_skill
    }
    logTelemetry('battle_snapshot_refresh', { battleId, reason })
  } catch (e) {
    logTelemetry('battle_snapshot_failed', { battleId, reason, message: e.message })
    if (reason !== 'ws_open') wsStatus.value = 'failed'
  }
}

function onMobileResume(event) {
  if (ended.value) return
  refreshBattleSnapshot(event.detail?.reason || 'resume')
  if (!ws || ws.readyState === WebSocket.CLOSED) {
    scheduleWsReconnect('resume')
  }
}

function handleEvent(m) {
  switch (m.type) {
    case 'state':
      state.value = m.data
      destinyCharged.value = m.data.destiny_charged
      if (m.data.destiny_skill) destinySkill.value = m.data.destiny_skill
      break
    case 'destiny_trigger':
      destinyCharged.value = true
      destinySkill.value = m.data.skill
      showDestinyAnim.value = true
      flashColor.value = '#FFE0A3'
      setTimeout(() => flashColor.value = '', 600)
      setTimeout(() => { showDestinyAnim.value = false }, 3000)
      activeTab.value = 'destiny'
      msg.success(m.data.message || '⚡ 天命降临!', { duration: 4000 })
      break
    case 'damage_summary':
      battleLog.value.push({
        ...m.data,
        id: Date.now() + Math.random(),
      })
      if (battleLog.value.length > 6) battleLog.value.shift()
      break
    case 'action_resolved':
      // ★ v2:玩家招式确认 — 不再清 narration(叙事独立流)
      battlePhase.value = 'resolving'
      break
    case 'turn_ready':
      // ★ v3:回合可继续 — 回到 idle,然后自动消费 castQueue
      battlePhase.value = 'idle'
      castingCard.value = null
      // 自动消费预选队列(下一 tick,等 state 更新)
      nextTick(() => flushCastQueue())
      break
    case 'enemy_action':
      // ★ v3:标记敌方回合(合并叙事一次性写双方)
      battlePhase.value = 'enemy_turn'
      break
    case 'damage':
      // ★ v2:立即触发,不再等前摇
      triggerDamage(m.data)
      break
    case 'effect':
      triggerEffect(m.data)
      break

    // === ★ v2 新事件:AI HUD ===
    case 'narration_start':
      // ★ v4: 不再 set battlePhase='narrating' 来锁定 UI
      // 叙事是 fire-and-forget,turn_ready 已解锁,不应再阻塞操作
      // 叙事模型可能有 reasoning 延迟,锁 UI 体验极差
      aiHud.value = {
        active: true,
        model: m.data.model || '?',
        startTime: Date.now(),
        elapsedMs: 0,
        chars: 0,
        cached: !!m.data.cached,
        round: m.data.round || 0,
        maxTokens: m.data.max_tokens || 0,
      }
      narration.value = ''  // 新回合,清旧叙事
      narrationSkipped.value = false
      if (hudTimer) clearInterval(hudTimer)
      hudTimer = setInterval(() => {
        if (aiHud.value.active) {
          aiHud.value.elapsedMs = Date.now() - aiHud.value.startTime
        }
      }, 100)
      break

    case 'narration':
      narration.value += m.data.delta
      aiHud.value.chars = narration.value.length
      castProgress.value = Math.min(100, (narration.value.length / EXPECT_NARRATION_CHARS) * 100)
      nextTick(() => {
        const el = document.querySelector('.narration-text')
        if (el) el.scrollTop = el.scrollHeight
      })
      break

    case 'narration_end':
      aiHud.value.active = false
      if (hudTimer) { clearInterval(hudTimer); hudTimer = null }
      if (m.data?.elapsed_ms) aiHud.value.elapsedMs = m.data.elapsed_ms
      if (m.data?.cancelled) narrationSkipped.value = true
      // 不再 set processing=false,turn_ready 才解锁(避免和 LLM 节奏耦合)
      break

    // === ★ v2 新事件:战后章节 ===
    case 'chapter_start':
      chapter.value = ''
      chapterGenerating.value = true
      break
    case 'chapter':
      chapter.value += m.data.delta
      // 自动滚到底
      nextTick(() => {
        const el = document.querySelector('.chapter-body')
        if (el) el.scrollTop = el.scrollHeight
      })
      break
    case 'chapter_end':
      chapterGenerating.value = false
      break

    // === ★ 新手教学 ===
    case 'tutorial_hint':
      if (!tutorialDismissed.value) {
        tutorialHint.value = { step: m.data.step, message: m.data.message }
      }
      break

    // ★ Phase 3: 战斗内道具使用结果
    case 'item_used':
      msg.success(`使用 ${m.data.item_name},余 ${m.data.remaining_count} 个`)
      // 刷新背包显示
      inventoryApi.list().then(inv => {
        inventory.value = (inv.data.items || []).filter(i => i.type === 'consumable')
      }).catch(() => {})
      break

    case 'gift_result':
      if (m.data.accepted && m.data.gift_message) {
        msg.success(m.data.gift_message)
      }
      break

    case 'end':
      ended.value = true
      vibrate(m.data.result === 'victory' ? [30, 40, 80] : 45)
      result.value = m.data.result
      rewards.value = m.data.rewards
      battleCommit.value = m.data.commit || null
      leavingForResult = true
      showResultAnim.value = true
      // 清队列
      castQueue.value = []
      if (m.data.result === 'victory') {
        flashColor.value = '#52B788'
        setTimeout(() => flashColor.value = '', 600)
      } else if (m.data.result === 'defeat') {
        flashColor.value = '#C03F3F'
        setTimeout(() => flashColor.value = '', 600)
      }
      // 墨炉在后台成章,结算页不等待长章节。
      startAutoReturn(10)
      break

    case 'error': {
      const errMsg = m.data?.message || '战斗出错'
      msg.error(errMsg)
      battlePhase.value = 'idle'
      castingCard.value = null
      if (/不存在|已过期|已结束/.test(errMsg)) {
        leavingForResult = true
        setTimeout(() => router.replace({
          path: '/home', query: { error: 'battle_invalid', msg: errMsg },
        }), 1000)
      }
      break
    }
  }
}

function flyDamage(d) {
  const id = ++damageId
  const isPlayer = d.target === 'player'
  damageFx.value.push({
    id, amount: d.amount, isCrit: d.is_crit,
    x: isPlayer ? 28 : 72,
    y: 38,
  })
  setTimeout(() => {
    damageFx.value = damageFx.value.filter(f => f.id !== id)
  }, 1600)
}

// 触发 damage(数字飞屏 + 抖动)
function triggerDamage(d) {
  flyDamage(d)
  if (d.target === 'enemy') {
    enemyShake.value = true
    setTimeout(() => enemyShake.value = false, 400)
  } else {
    playerShake.value = true
    setTimeout(() => playerShake.value = false, 400)
  }
}

// 触发屏幕特效
function triggerEffect(d) {
  if (d.fx === 'screen_shake') shake(d.intensity || 8)
  else if (d.fx === 'flash') {
    flashColor.value = d.color || '#fff'
    setTimeout(() => flashColor.value = '', 250)
  }
}

function shake(intensity = 8) {
  let elapsed = 0
  const duration = 300
  const id = setInterval(() => {
    elapsed += 16
    if (elapsed >= duration) {
      screenShake.value = { x: 0, y: 0 }
      clearInterval(id)
      return
    }
    const decay = 1 - elapsed / duration
    screenShake.value = {
      x: (Math.random() - 0.5) * intensity * 2 * decay,
      y: (Math.random() - 0.5) * intensity * 2 * decay,
    }
  }, 16)
}

// ★ v2:出牌立即响应 + 预选队列 + 数值/叙事解耦
function castCard(card) {
  if (ended.value) return
  const isDestiny = card.id?.startsWith('destiny_')

  // 灵气检查(天命无需消耗)
  if (!isDestiny && (state.value?.player.qi || 0) < card.qi_cost) {
    msg.warning('灵气不足')
    return
  }

  // ★ T2D 预选队列:如果还不在 idle(LLM/敌方回合还没结束),加入队列
  const canCastNow = isDestiny || (battlePhase.value === 'idle' && state.value?.status === 'player_turn')
  if (!canCastNow) {
    if (castQueue.value.length >= MAX_QUEUE) {
      msg.warning(`队列已满(最多 ${MAX_QUEUE} 个)`)
      return
    }
    castQueue.value.push(card)
    msg.info(`【${card.name}】已加入队列(${castQueue.value.length})`)
    return
  }

  // 立即处理 — 数值/叙事解耦后不再有"全屏前摇阻塞"
  vibrate(cardTier(card) === 'ult' ? 55 : 24)
  castingCard.value = card
  battlePhase.value = 'casting'
  narration.value = ''
  castProgress.value = 0
  narrationSkipped.value = false

  // 招式短闪光 + 粒子(纯视觉,不阻塞)
  triggerCastBefore(card)

  // 立即发到后端 — 数值瞬间返回,LLM 异步流叙事
  if (!safeSend('cast', { card_id: card.id })) {
    // 发送失败 — 回滚 UI 状态
    battlePhase.value = 'idle'
    castingCard.value = null
  }
}

// ★ T2D 自动消费队列(turn_ready 时调用)
function flushCastQueue() {
  if (castQueue.value.length === 0) return
  if (ended.value) return
  if (state.value?.status !== 'player_turn' || battlePhase.value !== 'idle') return
  const next = castQueue.value.shift()
  // 再次检查灵气(被前一招消耗后可能不够)
  const isDestiny = next.id?.startsWith('destiny_')
  if (!isDestiny && (state.value?.player.qi || 0) < next.qi_cost) {
    msg.warning(`队列【${next.name}】灵气不足,跳过`)
    flushCastQueue()  // 继续看下一个
    return
  }
  castCard(next)
}

function clearQueue() {
  castQueue.value = []
}

function cardQueueCount(card) {
  return castQueue.value.filter(c => c.id === card.id).length
}

// ★ T2E 跳过当前 LLM 叙事(+ Phase 4: 章节阶段也支持跳过)
function skipNarration() {
  if (!aiHud.value.active && !chapterGenerating.value) return
  // 章节生成中 → 走 skip_chapter,后端会同时 cancel chapter_task
  if (chapterGenerating.value) {
    safeSend('skip_chapter')
    chapterGenerating.value = false
  } else {
    safeSend('skip')
  }
  narrationSkipped.value = true
  aiHud.value.active = false
  if (hudTimer) { clearInterval(hudTimer); hudTimer = null }
}

// 关闭前摇遮罩,带最少显示时长保护
function dismissCastIntro() {
  const now = Date.now()
  const remain = Math.max(0, castIntroMinTime - now)

  setTimeout(() => {
    showCastIntro.value = false
    castProgress.value = 100
    // ★ 释放缓存的 damage/effect 事件,真正"打到怪物身上"
    setTimeout(() => {
      pendingEffects.value.forEach(triggerEffect)
      pendingEffects.value = []
      pendingDamage.value.forEach(triggerDamage)
      pendingDamage.value = []
    }, 180)  // 略延迟,让遮罩淡出后再显示
  }, remain)
}

function triggerCastBefore(card) {
  const tier = cardTier(card)
  const color = TIER_COLOR[tier]
  // 撒一圈粒子在玩家位置
  const count = tier === 'ult' ? 24 : tier === 'special' ? 16 : tier === 'normal' ? 10 : 6
  for (let i = 0; i < count; i++) {
    const id = ++damageId
    castParticles.value.push({
      id,
      angle: (i / count) * 360,
      color,
      size: tier === 'ult' ? 6 : 4,
    })
    setTimeout(() => {
      castParticles.value = castParticles.value.filter(p => p.id !== id)
    }, 1500)
  }
  // ult 招式触发屏幕闪
  if (tier === 'ult') {
    flashColor.value = color
    setTimeout(() => flashColor.value = '', 300)
  }
}

function triggerCastRelease() {
  // 招式释放时再来一波,从玩家向敌人方向
  if (!castingCard.value) return
  const tier = cardTier(castingCard.value)
  const color = TIER_COLOR[tier]
  for (let i = 0; i < 8; i++) {
    const id = ++damageId
    castParticles.value.push({
      id,
      angle: -10 + Math.random() * 20,  // 朝右扩散
      color,
      size: tier === 'ult' ? 8 : 5,
      isRelease: true,
    })
    setTimeout(() => {
      castParticles.value = castParticles.value.filter(p => p.id !== id)
    }, 1400)
  }
}

async function useItem(item) {
  if (battlePhase.value !== 'idle') return
  // ★ Phase 3: 改走 WS use_item action,服务端原子扣物品 + 修改 BattleEngine.state
  // 后端会推 item_used + state 事件,前端自动更新
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    msg.error('战斗连接已断开')
    return
  }
  safeSend('use_item', { item_id: item.id })
  // 不在前端预扣 — 等服务端 item_used 事件再刷新背包
}

function flee() {
  if (exiting.value) return  // ★ 防重复点击
  if (ended.value) {
    exiting.value = true
    exitLabel.value = '撤离中...'
    router.replace('/explore')
    return
  }
  // 防御:ws 故障也能撤退(本地强制退出)
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    msg.warning('战斗已失效,直接返回地图')
    leavingForResult = true
    exiting.value = true
    exitLabel.value = '撤离中...'
    router.replace('/explore')
    return
  }
  leavingForResult = true
  exiting.value = true
  exitLabel.value = '撤离中...'
  safeSend('flee')
  // 服务端 flee 不持锁,正常 100-300ms 就回 end → 兜底缩到 800ms 防 ws 故障
  setTimeout(() => {
    if (!ended.value) router.replace('/explore')
  }, 800)
}

function startAutoReturn(seconds) {
  // 清掉旧定时器
  if (countdownTimer) clearInterval(countdownTimer)
  if (autoReturnTimer) clearTimeout(autoReturnTimer)

  autoReturnCountdown.value = seconds
  countdownTimer = setInterval(() => {
    autoReturnCountdown.value -= 1
    if (autoReturnCountdown.value <= 0) clearInterval(countdownTimer)
  }, 1000)
  autoReturnTimer = setTimeout(() => returnToMap(), seconds * 1000)
}

function cancelAutoReturn() {
  if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null }
  if (autoReturnTimer) { clearTimeout(autoReturnTimer); autoReturnTimer = null }
  autoReturnCountdown.value = 0
}

async function returnToMap() {
  if (exiting.value) return
  exiting.value = true
  exitLabel.value = '返回地图...'
  cancelAutoReturn()
  if (state.value && character.value) {
    character.value.hp = state.value.player.hp
    character.value.qi = state.value.player.qi
  }
  try {
    const { data } = await characterApi.me()
    game.setCharacter(data)
  } catch (_) {}
  router.replace('/explore')
}

async function backToHome() {
  if (exiting.value) return
  exiting.value = true
  exitLabel.value = '返回主城...'
  cancelAutoReturn()
  if (state.value && character.value) {
    character.value.hp = state.value.player.hp
    character.value.qi = state.value.player.qi
  }
  try {
    const { data } = await characterApi.me()
    game.setCharacter(data)
  } catch (_) {}
  router.replace('/home')
}
</script>

<template>
  <div
    class="battle"
    :style="{ transform: `translate(${screenShake.x}px, ${screenShake.y}px)`, ...sectCssVars }"
  >
    <!-- ★ 门派背景图(深遮罩,不抢戏) -->
    <SectBackground :sect-id="character?.sect || 'canglan'" overlay="strong" :opacity="0.35" />

    <!-- ★ 赠礼对话框 -->
    <GiftDialog
      :visible="showGiftDialog"
      :battle-id="battleId"
      :enemy-name="state?.enemy?.name || '敌方'"
      :gift-count="giftCount"
      @close="showGiftDialog = false"
      @accepted="onGiftAccepted"
      @rejected="onGiftRejected"
    />

    <!-- 招式前摇遮罩(国风,带能量蓄力进度) -->
    <SkillCastIntro
      :visible="showCastIntro"
      :skill="castingCard || {}"
      :sect-id="state?.player?.sect_id || character?.sect || 'canglan'"
      :progress="castProgress"
    />

    <!-- 屏幕闪光 -->
    <Transition name="flash-fade">
      <div v-if="flashColor" class="flash" :style="{ backgroundColor: flashColor }"></div>
    </Transition>

    <!-- 战斗开场动画(2.5s) -->
    <Transition name="intro">
      <div v-if="showIntroAnim" class="intro-overlay">
        <div class="intro-text-1">⚔️ 战斗触发 ⚔️</div>
        <div class="intro-text-2" v-if="state">vs {{ state.enemy.name }}</div>
        <div class="intro-line"></div>
      </div>
    </Transition>

    <!-- 顶栏 -->
    <header class="battle-header" v-if="state">
      <div class="left">
        <Logo :size="32" :show-text="false" />
        <span class="sect" :style="{ color: sectAccent }">
          <SectFlag :sect-id="state.player.sect_id" :name="state.player.sect_name" :size="28" :radius="7" />
          {{ state.player.sect_name }}
        </span>
        <span class="realm">{{ state.player.realm_name }}</span>
        <span class="model"><code>🧠 {{ state.player.model }}</code></span>
      </div>
      <div class="right">
        <span>第 <strong>{{ state.round }}</strong> 回合</span>
        <span v-if="castQueue.length" class="queue-info">
          📋 队列 {{ castQueue.length }}
          <button class="queue-clear" @click="clearQueue" title="清空队列">×</button>
        </span>
      </div>
    </header>

    <!-- ★ v2 AI 思考 HUD —— 显示模型 / 耗时 / 字数,让"等"看起来是"AI 在演算" -->
    <Transition name="hud-fade">
      <div v-if="aiHud.active || aiHud.elapsedMs > 0" class="ai-hud" :class="{ active: aiHud.active, cached: aiHud.cached }">
        <span class="hud-spinner" v-if="aiHud.active">⚡</span>
        <span class="hud-spinner done" v-else>✓</span>
        <span class="hud-model"><code>{{ aiHud.model }}</code></span>
        <span class="hud-sep">·</span>
        <span class="hud-label">{{ aiHud.active ? '推演中' : '完成' }}</span>
        <span class="hud-sep">·</span>
        <span class="hud-time">{{ (aiHud.elapsedMs / 1000).toFixed(1) }}s</span>
        <span class="hud-sep">·</span>
        <span class="hud-chars">{{ aiHud.chars }} 字</span>
        <span v-if="aiHud.active" class="hud-tokens">~{{ estimatedTokens }} tokens</span>
        <span v-if="aiHud.cached" class="hud-cached">📦 池命中</span>
        <button v-if="aiHud.active && !narrationSkipped" class="hud-skip" @click="skipNarration">
          跳过 →
        </button>
        <span v-if="narrationSkipped" class="hud-skipped">已跳过</span>
      </div>
    </Transition>

    <div v-if="wsStatus !== 'connected'" class="ws-reconnect" :class="wsStatus">
      <div>
        <strong>{{ wsStatus === 'failed' ? '战斗连接中断' : '战斗连接校准中' }}</strong>
        <span>
          {{ wsStatus === 'failed'
            ? '已保留当前战斗界面,可重试连接或返回地图。'
            : `正在重连灵脉,第 ${Math.max(1, reconnectAttempts)} 次尝试。` }}
        </span>
      </div>
      <div class="ws-actions">
        <button @click="scheduleWsReconnect('manual')">重试连接</button>
        <button class="ghost" @click="router.replace('/explore')">返回地图</button>
      </div>
    </div>

    <!-- ★ v6 战斗场景 — 大圆形立绘 + 卡片化状态栏 -->
    <div class="arena arena-v6" v-if="state">
      <!-- 玩家卡片 -->
      <div class="combat-card player-card" :class="{ shaking: playerShake }">
        <div class="card-portrait-wrap" :class="{ casting: !!castingCard }"
             :style="{ '--frame': playerPortrait.frame, '--ring': TIER_COLOR[cardTier(castingCard||{qi_cost:0})] }">
          <RoundPortrait
            kind="player"
            :id="`${character?.sect || 'canglan'}/${character?.realm || 'qi'}`"
            :size="180"
            shape="circle"
            :frame="playerPortrait.frame"
            :name="character?.name"
            :level="character?.level || 1"
            :preview="playerPreview(character || {})"
          />
          <div v-if="castingCard" class="cast-ring-anim"></div>
        </div>
        <div class="card-title-block">
          <div class="card-name">{{ character?.name || '执笔者' }}</div>
          <div class="card-sub" :style="{ color: playerPortrait.frame }">
            {{ playerPortrait.title }}
          </div>
        </div>
        <div class="card-bars">
          <div class="bar-row">
            <span class="bar-label">HP</span>
            <div class="bar bar-thin">
              <div class="bar-fill hp" :style="{ width: (state.player.hp/state.player.max_hp*100) + '%' }"></div>
            </div>
            <span class="bar-value">{{ formatNum(state.player.hp) }} / {{ formatNum(state.player.max_hp) }}</span>
          </div>
          <div class="bar-row">
            <span class="bar-label">气</span>
            <div class="bar bar-thin">
              <div class="bar-fill qi" :style="{ width: (state.player.qi/state.player.max_qi*100) + '%' }"></div>
            </div>
            <span class="bar-value">{{ formatNum(state.player.qi) }} / {{ formatNum(state.player.max_qi) }}</span>
          </div>
        </div>
      </div>

      <!-- 中央 VS 信息 -->
      <div class="arena-vs">
        <div class="vs-divider"></div>
        <div class="vs-label">交锋</div>
        <div v-if="castingCard" class="cast-info-v6">
          <div class="cast-tier-v6" :style="{ color: TIER_COLOR[cardTier(castingCard)] }">
            {{ TIER_LABEL[cardTier(castingCard)] }}
          </div>
          <div class="cast-name-v6">{{ castingCard.name }}</div>
          <div class="cast-spin">凝聚中</div>
        </div>
        <div v-else class="vs-round">回合 {{ state.round || 1 }}</div>
        <div class="vs-divider"></div>
      </div>

      <!-- 敌人卡片 -->
      <div class="combat-card enemy-card" :class="{ shaking: enemyShake }">
        <div class="card-portrait-wrap enemy">
          <RoundPortrait
            :kind="enemyPortrait.kind"
            :id="enemyPortrait.id"
            :size="180"
            shape="circle"
            :frame="enemyPortraitFrame"
            :name="state.enemy.name"
            :level="state.enemy.level || ''"
            :preview="enemyPreview(state.enemy)"
          />
        </div>
        <div class="card-title-block">
          <div class="card-name">{{ state.enemy.name }}</div>
          <div class="card-sub enemy-clan">{{ state.enemy.clan || '妖兽' }}</div>
        </div>
        <div class="card-bars">
          <div class="bar-row">
            <span class="bar-label">HP</span>
            <div class="bar bar-thin">
              <div class="bar-fill enemy-hp" :style="{ width: (state.enemy.hp/state.enemy.max_hp*100) + '%' }"></div>
            </div>
            <span class="bar-value">{{ formatNum(state.enemy.hp) }} / {{ formatNum(state.enemy.max_hp) }}</span>
          </div>
        </div>
      </div>

      <!-- 数字飞屏 -->
      <div
        v-for="fx in damageFx"
        :key="fx.id"
        class="damage-fly"
        :class="{ crit: fx.isCrit }"
        :style="{ left: fx.x + '%', top: fx.y + '%' }"
      >
        -{{ formatNum(fx.amount) }}<span v-if="fx.isCrit"> 暴击!</span>
      </div>

      <!-- 施法前摇粒子 -->
      <div
        v-for="p in castParticles"
        :key="p.id"
        class="cast-particle"
        :class="{ release: p.isRelease }"
        :style="{
          '--angle': p.angle + 'deg',
          '--color': p.color,
          '--size': p.size + 'px',
          left: '28%',
          top: '40%',
        }"
      ></div>
    </div>

    <!-- 卷轴式叙事 + 战报卡 -->
    <div class="story-zone">
      <!-- ★ v3 战斗阶段指示器 + 显眼跳过按钮 -->
      <div class="phase-indicator" :class="'phase-' + battlePhase">
        <span v-if="battlePhase === 'casting'" class="phase-text phase-casting">运功中...</span>
        <span v-else-if="battlePhase === 'resolving'" class="phase-text phase-resolving">天道结算</span>
        <span v-else-if="battlePhase === 'enemy_turn'" class="phase-text phase-enemy">妖兽反击</span>
        <span v-else-if="aiHud.active" class="phase-text phase-narrating">AI 推演<span class="typing-dots"></span></span>
        <span v-else-if="battlePhase === 'idle'" class="phase-text phase-idle">等待出招</span>
        <button
          v-if="aiHud.active && !narrationSkipped"
          class="phase-skip-btn"
          @click="skipNarration"
          title="跳过 AI 叙事,直接看下一回合"
        >
          ⏭ 跳过推演
        </button>
      </div>
      <!-- ★ 新手教学气泡 -->
      <Transition name="tutorial-fade">
        <div v-if="tutorialHint && !tutorialDismissed" class="tutorial-bubble" @click="dismissTutorial">
          <div class="tutorial-icon">💡</div>
          <div class="tutorial-msg">{{ tutorialHint.message }}</div>
          <div class="tutorial-dismiss">点击不再显示</div>
        </div>
      </Transition>

      <!-- 叙事卷轴 -->
      <div class="scroll-wrap">
        <div class="scroll-handle scroll-top"></div>
        <div class="narration">
          <div class="narration-label" v-if="castingCard && !narration">
            ⌛ 正在凝聚 <strong>{{ castingCard.name }}</strong> 之意...
          </div>
          <div
            class="narration-text"
            :class="{ casting: castingCard && !narration }"
            v-html="highlightNarration(narration) + (battlePhase !== 'idle' && narration ? '<span class=&quot;cursor&quot;>▋</span>' : '')"
          ></div>
        </div>
        <div class="scroll-handle scroll-bottom"></div>
      </div>

      <!-- 战报卡列表 -->
      <div class="battle-log" v-if="battleLog.length">
        <TransitionGroup name="log-fade">
          <div
            v-for="log in battleLog"
            :key="log.id"
            class="log-card"
            :class="[
              'attacker-' + log.attacker,
              'outcome-' + log.outcome_type,
              { destiny: log.is_destiny },
            ]"
          >
            <div class="log-head">
              <span class="log-round">第 {{ log.round }} 回</span>
              <span class="log-skill">
                {{ log.skill_icon }} {{ log.skill_name }}
                <em v-if="log.is_destiny" class="destiny-badge">天命</em>
              </span>
              <span class="log-attacker">
                {{ log.attacker === 'player' ? '你' : '敌' }}
              </span>
            </div>
            <div class="log-body">
              <span class="log-label">{{ log.outcome_label }}</span>
              <span v-if="log.damage > 0" class="log-damage" :class="{ crit: log.is_crit }">
                -{{ log.damage }}
              </span>
              <span v-else-if="log.heal > 0" class="log-heal">+{{ log.heal }}</span>
              <span v-else class="log-zero">—</span>
            </div>
          </div>
        </TransitionGroup>
      </div>
    </div>

    <!-- 天命降临特效遮罩 -->
    <Transition name="destiny">
      <div v-if="showDestinyAnim" class="destiny-overlay">
        <div class="destiny-rings">
          <div class="ring"></div>
          <div class="ring"></div>
          <div class="ring"></div>
        </div>
        <div class="destiny-text">⚡ 天 命 降 临 ⚡</div>
        <div class="destiny-sub" v-if="destinySkill">{{ destinySkill.name }}</div>
        <div class="destiny-hint">已就绪一次 — 切换到「天命」栏使用</div>
      </div>
    </Transition>

    <!-- 三栏:攻击 / 物品 / 天命 -->
    <div class="action-panel" v-if="!ended">
      <div class="tab-bar">
        <button
          :class="['tab', { active: activeTab === 'attack' }]"
          @click="activeTab = 'attack'"
        >
          ⚔️ 招式 <span class="tab-count">{{ cards.length }}</span>
        </button>
        <button
          :class="['tab', { active: activeTab === 'item' }]"
          @click="activeTab = 'item'"
        >
          💊 丹药 <span class="tab-count">{{ inventory.length }}</span>
        </button>
        <button
          :class="[
            'tab', 'tab-destiny',
            { active: activeTab === 'destiny', charged: destinyCharged, locked: !destinyCharged },
          ]"
          @click="activeTab = 'destiny'"
        >
          ⚡ 天命
          <span v-if="destinyCharged" class="tab-count destiny-ready">就绪!</span>
          <span v-else class="tab-count">未现</span>
        </button>
        <button class="tab gift-tab" :disabled="giftCount >= 3 || ended"
                @click="showGiftDialog = true"
                :title="giftCount >= 3 ? '本场已用完 3 次' : '送礼安抚怪物'">
          🎁 赠礼 <span class="tab-count">{{ 3 - giftCount }}</span>
        </button>
        <button class="tab flee-tab" :class="{ exiting }" :disabled="exiting" @click="flee">
          <span v-if="exiting"><span class="flee-spin">◐</span> {{ exitLabel || '撤离中...' }}</span>
          <span v-else>🏃 撤退</span>
        </button>
      </div>

      <!-- 攻击列表 — ★ v2:点击永不阻塞,LLM 在跑也可点(进队列) -->
      <div v-show="activeTab === 'attack'" class="card-grid skill-card-grid">
        <button
          v-for="c in cards"
          :key="c.id"
          class="card"
          :class="[
            'tier-' + cardTier(c),
            {
              disabled: (state?.player.qi || 0) < c.qi_cost,
              queued: cardQueueCount(c) > 0,
              casting: castingCard?.id === c.id,
            },
          ]"
          :disabled="(state?.player.qi || 0) < c.qi_cost || ended"
          :style="{ '--tcolor': TIER_COLOR[cardTier(c)] }"
          @click="castCard(c)"
        >
          <div class="card-tier-badge">{{ TIER_LABEL[cardTier(c)] }}</div>
          <!-- ★ T2D 队列徽章 -->
          <div v-if="cardQueueCount(c) > 0" class="queue-badge">
            排队 ×{{ cardQueueCount(c) }}
          </div>
          <div class="card-icon">{{ c.icon }}</div>
          <div class="card-name">{{ c.name }}</div>
          <div class="card-cost">⚡ {{ c.qi_cost }}</div>
          <div class="card-role">{{ CARD_TYPE_LABEL[c.type] || '招式' }} · Lv.{{ c.level || 1 }}</div>
          <!-- ★ 伤害预览 -->
          <div v-if="cardPreviews[c.id]" class="card-preview">
            <span class="cp-dmg">{{ cardPreviews[c.id].estimated_damage }}</span>
            <span class="cp-hit">{{ Math.round(cardPreviews[c.id].hit_rate * 100) }}%</span>
          </div>
          <div class="card-desc">{{ c.description }}</div>
          <div class="card-hover-tip" role="tooltip">
            <div class="tip-title">{{ c.icon }} {{ c.name }}</div>
            <div class="tip-row">
              <span>具体作用</span>
              <p>{{ cardEffectText(c) }}</p>
            </div>
            <div class="tip-row">
              <span>推荐搭配</span>
              <p>{{ cardSynergyText(c) }}</p>
            </div>
          </div>
        </button>
      </div>

      <!-- 物品列表 -->
      <div v-show="activeTab === 'item'" class="card-grid item-grid">
        <button
          v-for="it in inventory"
          :key="it.id"
          class="item-card"
          :disabled="battlePhase !== 'idle'"
          @click="useItem(it)"
        >
          <ItemIcon class="item-icon" :item="it" :size="44" />
          <div class="item-name">{{ it.name }} <span class="cnt">×{{ it.count }}</span></div>
          <div class="item-desc">{{ it.description }}</div>
        </button>
        <div v-if="inventory.length === 0" class="empty-item">
          📭 背包没有可用的丹药 — 击败妖兽获取
        </div>
      </div>

      <!-- 天命栏:1% 概率触发后才能使用,整场战斗仅 1 次 -->
      <div v-show="activeTab === 'destiny'" class="destiny-panel">
        <div v-if="!destinyCharged" class="destiny-locked">
          <div class="locked-icon">🔒</div>
          <h3>天命尚未降临</h3>
          <p>每回合有 <strong>5%</strong> 几率触发天命降临,届时可释放本宗派独家神技一次。</p>
          <p class="hint">天命降临 = 暴击 + 5x ATK + 必中,整场只能用 1 次。</p>
        </div>
        <div v-else-if="!state || !state.destiny_used" class="destiny-ready-card" @click="castCard({
          id: destinySkill.id, name: destinySkill.name, icon: destinySkill.icon,
          qi_cost: 0, power: destinySkill.power,
        })">
          <div class="destiny-ring-outer">
            <div class="destiny-ring-inner">
              <div class="destiny-icon">{{ destinySkill?.icon || '⚡' }}</div>
            </div>
          </div>
          <h2 class="destiny-name">{{ destinySkill?.name }}</h2>
          <p class="destiny-desc">{{ destinySkill?.description }}</p>
          <div class="destiny-stats">
            <span>💥 {{ destinySkill?.power }}x ATK</span>
            <span>🎯 必中</span>
            <span>💎 必暴击</span>
          </div>
          <div class="destiny-cta">点此释放 →</div>
        </div>
        <div v-else class="destiny-used">
          <div class="locked-icon">💫</div>
          <p>本场天命已用,珍重。</p>
        </div>
      </div>
    </div>

    <!-- 战斗结算 -->
    <Transition name="result">
      <div v-if="ended" class="result-overlay">
        <div class="result-card" :class="result">
          <div class="result-icon">
            {{ result === 'victory' ? '✨' : result === 'defeat' ? '💀' : '🌪️' }}
          </div>
          <h2 v-if="result === 'victory'">大获全胜!</h2>
          <h2 v-else-if="result === 'defeat'">败北而归...</h2>
          <h2 v-else>逃离战斗</h2>
          <div v-if="result === 'victory' && rewards" class="rewards">
            <div class="reward-item">
              <span class="reward-icon">📜</span>
              <span>{{ battleCommit?.cultivation_task_id ? '正传战章已入墨炉' : '战斗因果已记录' }}</span>
            </div>
            <div class="reward-item">
              <span class="reward-icon">💫</span>
              <span>灵气 +{{ rewards.qi }}</span>
            </div>
            <div v-if="rewards.drops?.length" class="reward-drops">
              <div class="drops-title">🎁 战利品</div>
              <div v-for="d in rewards.drops" :key="d.id" class="drop">
                <span>{{ d.icon }}</span>
                <span>{{ d.name }} ×{{ d.count }}</span>
              </div>
            </div>
          </div>
          <div v-else-if="battleCommit?.cultivation_task_id" class="rewards">
            <div class="reward-item">
              <span class="reward-icon">📜</span>
              <span>{{ result === 'defeat' ? '败笔章已入墨炉' : '撤离章已入墨炉' }}</span>
            </div>
          </div>

          <!-- 倒计时提示 -->
          <div v-if="autoReturnCountdown > 0" class="countdown-bar">
            <div class="countdown-progress" :style="{
              animationDuration: '4s'
            }"></div>
            <span class="countdown-text">
              {{ autoReturnCountdown }} 秒后自动返回地图
              <a class="cancel-link" @click="cancelAutoReturn">[取消]</a>
            </span>
          </div>

          <!-- ★ 本命书章节已经交给墨炉后台成章 -->
          <div class="chapter-zone">
            <button class="chapter-toggle" @click="chapterShown = !chapterShown">
              📜 本命书成章
              <span v-if="chapterGenerating" class="chapter-tag generating">续写中 · {{ chapter.length }} 字</span>
              <span v-else-if="chapter.length > 0" class="chapter-tag done">已完成 · {{ chapter.length }} 字</span>
              <span v-else-if="battleCommit?.cultivation_task_id" class="chapter-tag generating">墨炉后台燃灵</span>
              <span v-else class="chapter-tag pending">因果已记录</span>
              <span class="chapter-arrow">{{ chapterShown ? '▲' : '▼' }}</span>
            </button>
            <Transition name="chapter-fade">
              <div v-if="chapterShown && chapter.length > 0" class="chapter-body" v-html="highlightNarration(chapter) + (chapterGenerating ? '<span class=&quot;cursor&quot;>▋</span>' : '')"></div>
              <div v-else-if="chapterShown" class="chapter-body">
                本战因果已投入墨炉。你可以继续探索,章节会在后台落入本命书,燃灵 token 将实时转为修为。
              </div>
            </Transition>
          </div>

          <div class="result-actions">
            <button class="back-btn primary" :class="{ exiting }" :disabled="exiting" @click="returnToMap">
              <span v-if="exiting && exitLabel.includes('地图')"><span class="flee-spin">◐</span> {{ exitLabel }}</span>
              <span v-else>⚔️ 继续修行(回地图)</span>
            </button>
            <button class="back-btn secondary" :class="{ exiting }" :disabled="exiting" @click="backToHome">
              <span v-if="exiting && exitLabel.includes('主城')"><span class="flee-spin">◐</span> {{ exitLabel }}</span>
              <span v-else>🏠 回主城</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 该卡片占位,确保所有 transition 都在 .battle 内 -->
  </div>
</template>

<style scoped>
.battle {
  min-height: var(--app-svh);
  min-height: 100dvh;
  /* ★ 战斗页背景根据门派 CSS 变量染色 */
  background:
    radial-gradient(ellipse at top, color-mix(in srgb, var(--sect-accent, #D4A24C) 12%, transparent) 0%, transparent 50%),
    radial-gradient(ellipse at bottom, color-mix(in srgb, var(--sect-contrast, #8B5A2B) 8%, transparent) 0%, transparent 50%),
    radial-gradient(ellipse at center, var(--sect-primary, #1a1a2e) 0%, #0a0a14 80%);
  padding: calc(20px + var(--safe-top)) calc(20px + var(--safe-right)) calc(100px + var(--safe-bottom)) calc(20px + var(--safe-left));
  position: relative;
  transition: background 0.6s ease, transform 0.05s linear;
  /* 仅屏蔽水平特效溢出,允许内容向下自然滚动 */
  overflow-x: hidden;
}

/* === 屏幕闪光 === */
.flash {
  position: fixed; inset: 0;
  opacity: 0.55; z-index: 999;
  pointer-events: none;
}
.flash-fade-enter-active, .flash-fade-leave-active { transition: opacity 0.25s; }
.flash-fade-enter-from, .flash-fade-leave-to { opacity: 0; }

/* === 战斗开场 === */
.intro-overlay {
  position: fixed; inset: 0;
  background: radial-gradient(ellipse at center, rgba(0,0,0,0.8), rgba(0,0,0,1));
  z-index: 500;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 20px;
}
.intro-text-1 {
  font-size: 48px; letter-spacing: 12px;
  color: #D4A24C;
  text-shadow: 0 0 32px rgba(212,162,76,0.8);
  font-family: 'STKaiti','KaiTi',serif;
  animation: intro-zoom 1.2s ease-out;
}
.intro-text-2 {
  font-size: 24px; color: #C03F3F;
  letter-spacing: 6px;
  animation: intro-zoom 1.2s ease-out 0.3s both;
  text-shadow: 0 0 16px rgba(192,63,63,0.6);
}
.intro-line {
  width: 60%; height: 2px;
  background: linear-gradient(90deg, transparent, #D4A24C, transparent);
  animation: intro-line 1.5s ease-out 0.5s both;
}
@keyframes intro-zoom {
  0% { opacity: 0; transform: scale(2.5); letter-spacing: 30px; filter: blur(8px); }
  100% { opacity: 1; transform: scale(1); filter: blur(0); }
}
@keyframes intro-line {
  0% { width: 0; opacity: 0; }
  100% { width: 60%; opacity: 1; }
}
.intro-enter-active, .intro-leave-active { transition: opacity 0.4s; }
.intro-leave-to { opacity: 0; }

/* === 顶栏 === */
.battle-header {
  display: flex; justify-content: space-between;
  padding: 10px 18px;
  background: linear-gradient(90deg, rgba(0,0,0,0.4), rgba(0,0,0,0.2), rgba(0,0,0,0.4));
  border: 1px solid rgba(212,162,76,0.2);
  border-radius: 10px;
  margin-bottom: 10px;
  backdrop-filter: blur(4px);
}
.battle-header .left { display: flex; gap: 14px; align-items: center; flex-wrap: wrap; }
.battle-header .right { display: flex; gap: 12px; align-items: center; color: #ccc; font-size: 13px; }
.sect { display: inline-flex; align-items: center; gap: 8px; font-weight: 600; font-size: 14px; }
.realm { color: #ccc; font-size: 13px; }
.model code {
  background: linear-gradient(135deg, rgba(127,199,232,0.12), rgba(82,183,136,0.08));
  color: #7FC7E8;
  padding: 3px 10px; border-radius: 5px;
  font-family: 'SF Mono', monospace; font-size: 11px;
  border: 1px solid rgba(127,199,232,0.2);
  letter-spacing: 0.5px;
}

/* 战斗模式徽章 */
.mode-badge {
  padding: 3px 10px; border-radius: 12px;
  font-size: 11px; letter-spacing: 1px;
  border: 1px solid;
}
.mode-badge.mode-drama {
  background: rgba(212, 162, 76, 0.12);
  border-color: rgba(212, 162, 76, 0.4);
  color: #FFE0A3;
}
.mode-badge.mode-speed {
  background: rgba(82, 183, 136, 0.12);
  border-color: rgba(82, 183, 136, 0.4);
  color: #95D5B2;
}

/* 队列信息 */
.queue-info {
  display: inline-flex; align-items: center; gap: 4px;
  background: rgba(127, 199, 232, 0.1);
  border: 1px solid rgba(127, 199, 232, 0.3);
  color: #7FC7E8;
  padding: 3px 10px; border-radius: 12px;
  font-size: 12px;
}
.queue-clear {
  background: none; border: none;
  color: #FF8888; cursor: pointer;
  font-size: 14px; line-height: 1;
  margin-left: 4px; padding: 0 4px;
}
.queue-clear:hover { color: #fff; }

/* === ★ v2 AI HUD === */
.ai-hud {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 14px;
  background: linear-gradient(90deg, rgba(212, 162, 76, 0.12), rgba(127, 199, 232, 0.08));
  border: 1px solid rgba(212, 162, 76, 0.3);
  border-radius: 6px;
  margin-bottom: 12px;
  font-size: 12px;
  font-family: 'SF Mono', monospace;
  color: #FFE0A3;
}
.ai-hud.cached {
  background: linear-gradient(90deg, rgba(82, 183, 136, 0.12), rgba(127, 199, 232, 0.08));
  border-color: rgba(82, 183, 136, 0.4);
}
.hud-spinner {
  display: inline-block;
  animation: hud-spin 1.2s linear infinite;
}
.hud-spinner.done { animation: none; color: #52B788; }
@keyframes hud-spin {
  0%, 100% { transform: scale(1); opacity: 0.8; }
  50%      { transform: scale(1.2); opacity: 1; }
}
.ai-hud code {
  background: rgba(0, 0, 0, 0.4);
  padding: 1px 8px; border-radius: 3px;
  color: #7FC7E8;
}
.hud-sep { color: #555; }
.hud-label { color: #aaa; }
.hud-time { color: #FFE0A3; }
.hud-chars { color: #aaa; }
.hud-cached {
  background: rgba(82, 183, 136, 0.2);
  color: #95D5B2;
  padding: 1px 8px; border-radius: 3px;
  font-size: 11px;
}
.hud-skip {
  margin-left: auto;
  background: rgba(192, 63, 63, 0.15);
  border: 1px solid rgba(192, 63, 63, 0.4);
  color: #FF8888;
  padding: 3px 12px; border-radius: 4px;
  cursor: pointer; font-size: 11px;
  letter-spacing: 1px;
  font-family: inherit;
}
.hud-skip:hover {
  background: rgba(192, 63, 63, 0.3);
  color: #fff;
}
.hud-skipped {
  margin-left: auto; color: #888;
  font-size: 11px;
}
.hud-fade-enter-active, .hud-fade-leave-active { transition: opacity 0.3s, transform 0.3s; }
.hud-fade-enter-from { opacity: 0; transform: translateY(-6px); }
.hud-fade-leave-to { opacity: 0; transform: translateY(-6px); }

.ws-reconnect {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid rgba(255, 180, 84, 0.34);
  border-radius: 8px;
  background: rgba(28, 18, 8, 0.88);
  color: #FFE0A3;
}
.ws-reconnect strong,
.ws-reconnect span {
  display: block;
}
.ws-reconnect span {
  margin-top: 3px;
  color: #C9BCA5;
  font-size: 12px;
}
.ws-reconnect.failed {
  border-color: rgba(192, 63, 63, 0.38);
  background: rgba(32, 8, 8, 0.9);
}
.ws-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.ws-actions button {
  min-height: 34px;
  border: 1px solid rgba(212, 162, 76, 0.42);
  border-radius: 6px;
  background: rgba(212, 162, 76, 0.12);
  color: #FFE0A3;
  padding: 0 12px;
  cursor: pointer;
}
.ws-actions .ghost {
  border-color: rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.04);
  color: #B8C7E0;
}

/* === 战斗场景 === */
/* ╔════════════════════════════════════════════════════════════╗
   ★ v6 战斗场景 — 大圆形立绘 + 卡片化状态栏
   ╚════════════════════════════════════════════════════════════╝ */
.arena-v6 {
  position: relative;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 24px;
  align-items: stretch;
  padding: 28px 24px 20px;
  min-height: 360px;
  background: linear-gradient(180deg, rgba(8, 12, 24, 0.55), rgba(8, 12, 24, 0.85));
  border-bottom: 1px solid rgba(212, 162, 76, 0.18);
}
.combat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 18px 16px;
  background: linear-gradient(135deg, rgba(15, 27, 46, 0.78), rgba(8, 12, 24, 0.92));
  border: 1px solid rgba(212, 162, 76, 0.22);
  border-radius: 14px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.04);
  backdrop-filter: blur(8px);
  transition: transform 0.18s, box-shadow 0.18s;
}
.combat-card.enemy-card {
  background: linear-gradient(135deg, rgba(46, 15, 15, 0.78), rgba(24, 8, 8, 0.92));
  border-color: rgba(192, 63, 63, 0.32);
}
.combat-card.shaking { animation: arena-shake 0.4s ease-in-out; }

.card-portrait-wrap {
  position: relative;
  display: flex; align-items: center; justify-content: center;
}
.card-portrait-wrap.casting::before {
  content: '';
  position: absolute;
  inset: -8px;
  border-radius: 50%;
  border: 2px dashed var(--ring, #FFE0A3);
  animation: cast-ring-rotate 2s linear infinite;
}
@keyframes cast-ring-rotate { to { transform: rotate(360deg); } }
.cast-ring-anim {
  position: absolute;
  inset: -14px;
  border-radius: 50%;
  border: 1px solid var(--ring, #FFE0A3);
  opacity: 0.45;
  animation: cast-ring-pulse 1.4s ease-in-out infinite;
}
@keyframes cast-ring-pulse {
  0%, 100% { transform: scale(1); opacity: 0.25; }
  50%      { transform: scale(1.08); opacity: 0.6; }
}

.card-title-block {
  text-align: center;
}
.card-name {
  font-family: 'STKaiti', 'KaiTi', serif;
  font-size: 18px;
  font-weight: bold;
  color: #FFE0A3;
  letter-spacing: 2px;
  margin-bottom: 4px;
  text-shadow: 0 1px 4px rgba(0,0,0,0.7);
}
.card-sub {
  font-size: 12px;
  letter-spacing: 3px;
  font-family: 'STKaiti', serif;
}
.card-sub.enemy-clan { color: #FF8888; }

.card-bars {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.bar-row {
  display: grid;
  grid-template-columns: 18px 1fr auto;
  gap: 6px;
  align-items: center;
}
.bar-label {
  font-family: 'STKaiti', serif;
  color: #C9A876;
  font-size: 12px;
  text-align: center;
}
.bar.bar-thin {
  height: 9px;
  background: rgba(255,255,255,0.06);
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,0.04);
}
.bar-value {
  font-family: 'SF Mono', monospace;
  font-size: 11px;
  color: #E8D8B0;
}

/* 中央 VS */
.arena-vs {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-width: 100px;
}
.vs-divider {
  width: 2px;
  flex: 1;
  background: linear-gradient(180deg, transparent, rgba(212,162,76,0.45), transparent);
  min-height: 30px;
}
.vs-label {
  font-family: 'STKaiti', serif;
  color: #D4A24C;
  font-size: 14px;
  letter-spacing: 6px;
  writing-mode: horizontal-tb;
}
.vs-round {
  font-size: 11px;
  color: #888;
  letter-spacing: 2px;
}
.cast-info-v6 {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  background: rgba(255, 200, 80, 0.08);
  border: 1px solid rgba(255, 200, 80, 0.3);
  border-radius: 6px;
}
.cast-tier-v6 {
  font-size: 10px;
  letter-spacing: 2px;
  font-weight: bold;
}
.cast-name-v6 {
  font-family: 'STKaiti', serif;
  font-size: 13px;
  color: #FFE0A3;
  letter-spacing: 1px;
}
.cast-spin {
  font-size: 10px;
  color: #888;
  letter-spacing: 1px;
  animation: phase-pulse 1.5s ease-in-out infinite;
}

@media (max-width: 900px) {
  .arena-v6 {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .arena-vs { flex-direction: row; min-width: auto; padding: 4px 0; }
  .vs-divider { display: none; }
}

/* ─── 旧 .arena 保留兼容(可能其他元素引用)─── */
.arena {
  position: relative;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 30px;
  align-items: center;
  padding: 32px 30px 24px;
  min-height: 280px;
  background:
    radial-gradient(ellipse at 25% 50%, rgba(212,162,76,0.08), transparent 40%),
    radial-gradient(ellipse at 75% 50%, rgba(192,63,63,0.08), transparent 40%),
    linear-gradient(180deg, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.05) 100%);
  border: 1px solid rgba(212,162,76,0.12);
  border-radius: 16px;
  margin-bottom: 12px;
  box-shadow:
    inset 0 0 60px rgba(0,0,0,0.3),
    0 4px 32px rgba(0,0,0,0.4);
  backdrop-filter: blur(2px);
}

.combatant {
  display: flex; flex-direction: column;
  align-items: center; gap: 8px;
}
.combatant.shaking { animation: combatant-shake 0.4s; }
@keyframes combatant-shake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-10px) rotate(-3deg); filter: brightness(1.6) hue-rotate(-15deg); }
  40% { transform: translateX(10px) rotate(3deg); filter: brightness(1.6); }
  60% { transform: translateX(-6px); }
  80% { transform: translateX(6px); }
}

/* 头像 */
.portrait-wrap {
  display: flex; flex-direction: column; align-items: center;
  gap: 4px; position: relative;
}
.portrait-frame {
  width: 110px; height: 110px;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.1), rgba(0,0,0,0.5));
  border: 3px solid var(--frame, #888);
  display: flex; align-items: center; justify-content: center;
  position: relative;
  box-shadow:
    inset 0 0 20px rgba(0,0,0,0.5),
    0 0 30px color-mix(in srgb, var(--frame, #888) 30%, transparent),
    /* ★ 门派 aura */
    0 0 60px var(--sect-aura, transparent);
  animation: portrait-breath 4s ease-in-out infinite;
}
@keyframes portrait-breath {
  0%, 100% { box-shadow: inset 0 0 20px rgba(0,0,0,0.5), 0 0 30px color-mix(in srgb, var(--frame, #888) 30%, transparent), 0 0 40px var(--sect-aura, transparent); }
  50%      { box-shadow: inset 0 0 20px rgba(0,0,0,0.5), 0 0 36px color-mix(in srgb, var(--frame, #888) 40%, transparent), 0 0 72px var(--sect-aura, transparent); }
}
.portrait-emoji {
  font-size: 64px;
  filter: drop-shadow(0 4px 12px rgba(0,0,0,0.5));
}
.portrait-emoji.big { font-size: 76px; }
.portrait-img {
  width: 100%; height: 100%;
  object-fit: cover;
  border-radius: 50%;
  filter: drop-shadow(0 4px 12px rgba(0,0,0,0.5));
}
.portrait-title {
  font-size: 12px;
  background: rgba(0,0,0,0.6);
  padding: 2px 10px;
  border-radius: 4px;
  letter-spacing: 2px;
  font-weight: 600;
}
.name-tag {
  font-size: 11px;
  color: #aaa;
  letter-spacing: 1px;
}

.enemy-portrait .portrait-frame.enemy-frame {
  border-color: #C03F3F;
  box-shadow: inset 0 0 20px rgba(0,0,0,0.5), 0 0 30px rgba(192,63,63,0.3);
}
.enemy-title { color: #FF8888 !important; }

/* 施法前摇光圈 */
.casting-ring {
  position: absolute; inset: -8px;
  border-radius: 50%;
  border: 3px dashed;
  animation: cast-ring-spin 1.5s linear infinite;
  pointer-events: none;
}
@keyframes cast-ring-spin {
  100% { transform: rotate(360deg); }
}

/* HP / 灵气 条 */
.bar-block { width: 220px; text-align: center; }
.bar {
  height: 14px; background: rgba(0,0,0,0.6);
  border-radius: 7px; overflow: hidden;
  border: 1px solid rgba(255,255,255,0.08);
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.5);
}
.bar-fill { height: 100%; transition: width 0.5s; position: relative; }
.bar-fill::after {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
  animation: bar-shine 2s ease-in-out infinite;
}
@keyframes bar-shine {
  0%, 100% { opacity: 0; transform: translateX(-100%); }
  50% { opacity: 1; transform: translateX(100%); }
}
.bar-fill.hp { background: linear-gradient(90deg, #C03F3F, #FF8888); }
.bar-fill.qi { background: linear-gradient(90deg, #3A6B6E, #7FC7E8); }
.bar-fill.enemy-hp { background: linear-gradient(90deg, #8B3A3A, #C03F3F); }
.bar-text { display: block; font-size: 11px; color: #ccc; margin-top: 3px; }

/* VS 区域 */
.vs {
  display: flex; flex-direction: column; align-items: center;
  gap: 10px;
}
.vs-symbol {
  font-size: 38px;
  text-shadow: 0 0 16px #D4A24C;
  animation: vs-pulse 2s ease-in-out infinite;
}
@keyframes vs-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.15); }
}
.cast-info {
  display: flex; flex-direction: column; gap: 4px; align-items: center;
  background: rgba(0,0,0,0.6);
  padding: 6px 14px;
  border-radius: 6px;
  border: 1px solid rgba(212,162,76,0.25);
  animation: cast-info-in 0.3s ease-out;
}
@keyframes cast-info-in {
  from { opacity: 0; transform: translateY(-10px); }
  to   { opacity: 1; transform: translateY(0); }
}
.cast-tier { font-size: 11px; letter-spacing: 1px; }
.cast-name { font-size: 13px; color: #fff; font-weight: 600; }
.cast-status { font-size: 11px; color: #aaa; }

/* 数字飞屏 */
.damage-fly {
  position: absolute;
  font-size: 38px; font-weight: bold;
  color: #FF8888;
  text-shadow: 0 0 8px #000, 0 0 16px #C03F3F;
  pointer-events: none;
  animation: flyUp 1.6s ease-out forwards;
  transform: translate(-50%, -50%);
}
.damage-fly.crit {
  font-size: 60px;
  color: #FFD700;
  text-shadow: 0 0 12px #000, 0 0 24px #D4A24C;
}
@keyframes flyUp {
  0%   { opacity: 0; transform: translate(-50%, 0) scale(0.5) rotate(-8deg); }
  15%  { opacity: 1; transform: translate(-50%, -16px) scale(1.3) rotate(0deg); }
  100% { opacity: 0; transform: translate(-50%, -120px) scale(0.8) rotate(4deg); }
}

/* 施法粒子 */
.cast-particle {
  position: absolute;
  width: var(--size); height: var(--size);
  background: var(--color);
  border-radius: 50%;
  box-shadow: 0 0 12px var(--color);
  pointer-events: none;
  animation: particle-orbit 1.4s ease-out forwards;
  transform: translate(-50%, -50%) rotate(var(--angle));
}
.cast-particle.release {
  animation: particle-shoot 0.9s ease-out forwards;
}
@keyframes particle-orbit {
  0% { opacity: 0; transform: translate(-50%, -50%) rotate(var(--angle)) translate(0, 0); }
  20% { opacity: 1; transform: translate(-50%, -50%) rotate(var(--angle)) translate(50px, 0); }
  100% { opacity: 0; transform: translate(-50%, -50%) rotate(var(--angle)) translate(80px, 0); }
}
@keyframes particle-shoot {
  0%   { opacity: 1; transform: translate(-50%, -50%) translateX(0); }
  100% { opacity: 0; transform: translate(-50%, -50%) translateX(450px); }
}

/* === ★ T3K 战后章节面板 === */
.chapter-zone {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(212, 162, 76, 0.2);
}
.chapter-toggle {
  width: 100%;
  background: linear-gradient(180deg, rgba(212, 162, 76, 0.12), rgba(212, 162, 76, 0.04));
  border: 1px solid rgba(212, 162, 76, 0.3);
  color: #FFE0A3;
  padding: 10px 16px;
  border-radius: 6px;
  cursor: pointer;
  display: flex; align-items: center; gap: 10px;
  font-size: 14px;
  letter-spacing: 2px;
  font-family: 'STKaiti', 'KaiTi', serif;
}
.chapter-toggle:hover {
  background: linear-gradient(180deg, rgba(212, 162, 76, 0.2), rgba(212, 162, 76, 0.08));
}
.chapter-tag {
  margin-left: auto;
  padding: 2px 10px; border-radius: 10px;
  font-size: 11px; font-family: 'SF Mono', monospace;
  letter-spacing: 0;
}
.chapter-tag.generating {
  background: rgba(212, 162, 76, 0.2);
  color: #FFE0A3;
  animation: pulse-label 1.2s ease-in-out infinite;
}
.chapter-tag.done {
  background: rgba(82, 183, 136, 0.2);
  color: #95D5B2;
}
.chapter-tag.pending {
  background: rgba(127, 127, 127, 0.2);
  color: #888;
}
.chapter-arrow { color: #aaa; font-size: 11px; margin-left: 8px; }

.chapter-body {
  margin-top: 10px;
  padding: 18px 22px;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(212, 162, 76, 0.2);
  border-radius: 8px;
  max-height: 320px;
  overflow-y: auto;
  font-family: "Source Han Serif SC", "PingFang SC", serif;
  font-size: 14px;
  line-height: 2;
  color: #e0e0e0;
  white-space: pre-wrap;
}
.chapter-fade-enter-active, .chapter-fade-leave-active {
  transition: opacity 0.3s, max-height 0.4s ease;
}
.chapter-fade-enter-from { opacity: 0; max-height: 0; }
.chapter-fade-leave-to { opacity: 0; max-height: 0; }

/* 叙事 */
.narration {
  background: linear-gradient(180deg, rgba(0,0,0,0.5), rgba(0,0,0,0.3));
  border: 1px solid rgba(212,162,76,0.18);
  border-radius: 10px;
  padding: 18px 24px;
  min-height: 96px;
  max-height: 170px;
  overflow-y: auto;
  margin-bottom: 12px;
  position: relative;
}
.narration-label {
  font-size: 12px;
  color: #D4A24C;
  letter-spacing: 2px;
  margin-bottom: 6px;
  animation: pulse-label 1.2s ease-in-out infinite;
}
@keyframes pulse-label {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}
.narration-text {
  font-size: 15px;
  line-height: 1.9;
  color: #e0e0e0;
  font-family: "Source Han Serif SC", "PingFang SC", serif;
  white-space: pre-wrap;
}
.narration-text.casting { color: #888; font-style: italic; }
.cursor {
  display: inline-block;
  color: #D4A24C;
  animation: blink 0.8s infinite;
}
@keyframes blink { 50% { opacity: 0; } }

/* === 操作面板 === */
.action-panel {
  background: rgba(15,15,30,0.6);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  padding: 12px;
}
.tab-bar {
  display: flex; gap: 6px;
  margin-bottom: 12px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  padding-bottom: 10px;
}
.tab {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  color: #aaa;
  padding: 8px 18px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  letter-spacing: 1px;
  display: flex; align-items: center; gap: 6px;
}
.tab:hover { color: #fff; border-color: #D4A24C; }
.tab.active { background: rgba(212,162,76,0.12); border-color: #D4A24C; color: #D4A24C; }
.tab.gift-tab {
  margin-left: auto;
  color: #FFE0A3;
  border-color: rgba(212,162,76,0.4);
  background: linear-gradient(135deg, rgba(212,162,76,0.12), rgba(212,162,76,0.04));
}
.tab.gift-tab:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(212,162,76,0.22), rgba(255,224,163,0.08));
  border-color: #FFE0A3;
  box-shadow: 0 0 12px rgba(212,162,76,0.4);
}
.tab.gift-tab:disabled { opacity: 0.4; cursor: not-allowed; }
.tab.flee-tab {
  color: #FF8888;
  border-color: rgba(192,63,63,0.3);
}
.tab.flee-tab:hover { background: rgba(192,63,63,0.1); border-color: #C03F3F; }
/* ★ 撤离中:防双击 + spinner + 蓝调表示进行中 */
.tab.flee-tab.exiting,
.back-btn.exiting {
  cursor: wait;
  opacity: 0.85;
  color: #C7E5F5;
  border-color: rgba(127, 199, 232, 0.6);
  background: rgba(127, 199, 232, 0.1);
}
.tab.flee-tab.exiting:hover,
.back-btn.exiting:hover {
  background: rgba(127, 199, 232, 0.1);
  border-color: rgba(127, 199, 232, 0.6);
  transform: none;
}
.tab.flee-tab:disabled,
.back-btn:disabled {
  pointer-events: none;
}
.flee-spin {
  display: inline-block;
  animation: flee-spin-rotate 0.7s linear infinite;
  margin-right: 4px;
}
@keyframes flee-spin-rotate { to { transform: rotate(360deg); } }
.tab-count {
  background: rgba(0,0,0,0.4);
  padding: 1px 8px; border-radius: 10px;
  font-size: 11px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
}
.skill-card-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: stretch;
  gap: 12px;
  padding: 6px 4px 2px;
}

/* ★ T2D 队列徽章 + casting 高亮 */
.card.queued {
  background: linear-gradient(180deg, rgba(127, 199, 232, 0.15), rgba(127, 199, 232, 0.05));
  border-color: #7FC7E8 !important;
  box-shadow: 0 0 12px rgba(127, 199, 232, 0.3);
}
.card.casting {
  border-color: #FFE0A3 !important;
  box-shadow: 0 0 18px rgba(212, 162, 76, 0.5), inset 0 0 12px rgba(255, 224, 163, 0.2);
  animation: card-casting 0.8s ease-in-out infinite;
}
@keyframes card-casting {
  0%, 100% { transform: scale(1); }
  50%      { transform: scale(1.03); }
}
.queue-badge {
  position: absolute; top: 4px; right: 4px;
  background: linear-gradient(135deg, #4A90E2, #2E5BBA);
  color: #fff;
  padding: 2px 8px; border-radius: 10px;
  font-size: 10px; font-weight: 700;
  letter-spacing: 1px;
  box-shadow: 0 2px 6px rgba(74, 144, 226, 0.4);
  z-index: 2;
}

/* === 招式卡(分级)=== */
.card {
  background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01));
  border: 1px solid var(--tcolor, rgba(255,255,255,0.1));
  border-radius: 10px;
  padding: 14px 10px 12px;
  cursor: pointer; color: #fff; text-align: center;
  font-family: inherit;
  position: relative;
  transition: all 0.25s;
  min-height: 156px;
}
.skill-card-grid .card {
  flex: 0 1 172px;
  max-width: 190px;
  isolation: isolate;
}
.card:hover:not(:disabled),
.card:focus-visible:not(:disabled) {
  z-index: 8;
  transform: translateY(-8px) scale(1.08);
  border-color: color-mix(in srgb, var(--tcolor) 82%, #fff 18%);
  box-shadow:
    0 12px 30px color-mix(in srgb, var(--tcolor) 42%, transparent),
    inset 0 0 18px color-mix(in srgb, var(--tcolor) 16%, transparent);
  outline: none;
}
.card:disabled { opacity: 0.35; cursor: not-allowed; }

.card-tier-badge {
  position: absolute; top: 4px; right: 4px;
  font-size: 10px;
  background: color-mix(in srgb, var(--tcolor) 25%, transparent);
  color: var(--tcolor);
  padding: 1px 6px;
  border-radius: 3px;
  letter-spacing: 1px;
}

.card-icon { font-size: 30px; margin-bottom: 4px; }
.card-name { font-size: 14px; font-weight: 600; color: var(--tcolor); margin-bottom: 4px; }
.card-cost { font-size: 11px; color: #7FC7E8; margin-bottom: 4px; }
.card-role {
  display: inline-flex;
  justify-content: center;
  max-width: 100%;
  margin-bottom: 5px;
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(0,0,0,0.22);
  color: #C8D3E6;
  font-size: 10px;
  line-height: 1.4;
}
.card-preview {
  display: flex; gap: 8px; align-items: center;
  justify-content: center;
  font-size: 10px; margin-bottom: 4px;
}
.cp-dmg { color: #FF8C42; font-weight: 600; }
.cp-dmg::before { content: '⚔️ '; font-size: 9px; }
.cp-hit { color: #95D5B2; }
.cp-hit::before { content: '🎯 '; font-size: 9px; }
.card-desc { font-size: 11px; color: #aaa; min-height: 26px; line-height: 1.4; }
.card-hover-tip {
  position: absolute;
  left: 50%;
  bottom: calc(100% + 12px);
  width: min(270px, 78vw);
  padding: 12px;
  border: 1px solid color-mix(in srgb, var(--tcolor) 52%, transparent);
  border-radius: 8px;
  background: rgba(9, 9, 18, 0.96);
  box-shadow: 0 16px 36px rgba(0,0,0,0.46);
  color: #E8EEF8;
  text-align: left;
  transform: translate(-50%, 8px);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.16s ease, transform 0.16s ease;
  z-index: 20;
}
.card-hover-tip::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: -7px;
  width: 12px;
  height: 12px;
  transform: translateX(-50%) rotate(45deg);
  background: rgba(9, 9, 18, 0.96);
  border-right: 1px solid color-mix(in srgb, var(--tcolor) 52%, transparent);
  border-bottom: 1px solid color-mix(in srgb, var(--tcolor) 52%, transparent);
}
.card:hover:not(:disabled) .card-hover-tip,
.card:focus-visible:not(:disabled) .card-hover-tip {
  opacity: 1;
  transform: translate(-50%, 0);
}
.tip-title {
  color: var(--tcolor);
  font-weight: 700;
  margin-bottom: 8px;
  letter-spacing: 1px;
}
.tip-row + .tip-row {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(255,255,255,0.08);
}
.tip-row span {
  display: block;
  color: #7FC7E8;
  font-size: 11px;
  margin-bottom: 3px;
}
.tip-row p {
  margin: 0;
  color: #C8D3E6;
  font-size: 12px;
  line-height: 1.6;
}

/* 高阶招式 hover 时的光波 */
.card.tier-ult {
  background: linear-gradient(180deg, rgba(255,215,0,0.06), rgba(255,215,0,0.01));
}
.card.tier-ult::before {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(45deg, transparent 40%, rgba(255,215,0,0.15) 50%, transparent 60%);
  background-size: 200% 200%;
  animation: ult-shine 3s linear infinite;
  border-radius: 10px;
  pointer-events: none;
}
@keyframes ult-shine {
  0% { background-position: 200% 200%; }
  100% { background-position: -100% -100%; }
}
.card.tier-special {
  background: linear-gradient(180deg, rgba(255,180,84,0.05), rgba(255,180,84,0.01));
}

/* === 物品 === */
.item-card {
  background: rgba(82,183,136,0.05);
  border: 1px solid rgba(82,183,136,0.2);
  border-radius: 10px;
  padding: 12px;
  cursor: pointer; color: #fff;
  font-family: inherit; text-align: center;
}
.item-card:hover:not(:disabled) {
  transform: translateY(-3px);
  border-color: #52B788;
  box-shadow: 0 4px 16px rgba(82,183,136,0.25);
}
.item-icon { margin-bottom: 4px; }
.item-name { font-size: 13px; color: #52B788; margin-bottom: 4px; }
.cnt { color: #FFE0A3; }
.item-desc { font-size: 11px; color: #aaa; line-height: 1.5; }

.empty-item {
  grid-column: 1 / -1;
  text-align: center; padding: 30px;
  color: #666;
}

/* === 结算 === */
.result-overlay {
  position: fixed; inset: 0;
  background: rgba(10,10,20,0.92);
  backdrop-filter: blur(10px);
  display: flex; align-items: center; justify-content: center;
  z-index: 100;
}
.result-enter-active, .result-leave-active { transition: opacity 0.4s; }
.result-enter-from { opacity: 0; }
.result-card {
  background: linear-gradient(180deg, #1a1a2e, #16162a);
  border: 2px solid #D4A24C;
  border-radius: 16px;
  padding: 50px 70px;
  text-align: center;
  animation: result-pop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
  min-width: 360px;
}
@keyframes result-pop {
  from { opacity: 0; transform: scale(0.3) rotateZ(-10deg); }
  to   { opacity: 1; transform: scale(1) rotateZ(0); }
}
.result-card.victory {
  border-color: #52B788;
  box-shadow: 0 0 60px rgba(82,183,136,0.4);
}
.result-card.defeat {
  border-color: #C03F3F;
  box-shadow: 0 0 60px rgba(192,63,63,0.4);
}
.result-icon {
  font-size: 96px; margin-bottom: 12px;
  animation: result-icon-bounce 2s ease-in-out infinite;
}
@keyframes result-icon-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}
.result-card h2 {
  margin: 0 0 24px;
  font-size: 28px;
  letter-spacing: 6px;
  font-family: 'STKaiti','KaiTi',serif;
}
.rewards {
  background: rgba(0,0,0,0.4);
  border-radius: 10px;
  padding: 16px 20px;
  margin: 16px 0 24px;
  display: flex; flex-direction: column; gap: 8px;
}
.reward-item {
  display: flex; align-items: center; gap: 10px;
  color: #7FC7E8;
  font-size: 14px;
}
.reward-icon { font-size: 20px; }
.reward-drops { margin-top: 8px; border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 8px; }
.drops-title { font-size: 12px; color: #FFB454; margin-bottom: 6px; }
.drop {
  display: flex; gap: 8px; align-items: center;
  font-size: 13px; color: #ccc;
  padding: 2px 0;
}
.back-btn {
  background: linear-gradient(135deg, #D4A24C, #B58A3E);
  border: none; color: #1a1a2e;
  padding: 14px 40px; border-radius: 8px;
  font-size: 15px; font-weight: 600;
  cursor: pointer; margin-top: 12px;
  letter-spacing: 3px;
  transition: all 0.2s;
}
.back-btn:hover { box-shadow: 0 6px 24px rgba(212,162,76,0.5); transform: translateY(-2px); }

/* 倒计时进度条 */
.countdown-bar {
  margin: 12px 0;
  padding: 8px 14px;
  background: rgba(0,0,0,0.4);
  border-radius: 6px;
  position: relative;
  overflow: hidden;
}
.countdown-progress {
  position: absolute;
  bottom: 0; left: 0;
  height: 3px; width: 100%;
  background: linear-gradient(90deg, #D4A24C, #FFE0A3, #D4A24C);
  transform-origin: left center;
  animation: countdown-shrink linear forwards;
}
@keyframes countdown-shrink {
  from { transform: scaleX(1); }
  to { transform: scaleX(0); }
}
.countdown-text {
  display: block;
  font-size: 13px;
  color: #FFE0A3;
  letter-spacing: 2px;
  text-align: center;
  position: relative;
  z-index: 1;
}
.cancel-link {
  color: #aaa;
  cursor: pointer;
  text-decoration: underline;
  margin-left: 8px;
  font-size: 11px;
}
.cancel-link:hover { color: #fff; }

/* 双按钮 */
.result-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}
.result-actions .back-btn {
  flex: 1;
  margin-top: 0;
  padding: 12px 24px;
  font-size: 13px;
  letter-spacing: 2px;
}
.result-actions .back-btn.primary {
  background: linear-gradient(135deg, #D4A24C, #B58A3E);
  box-shadow: 0 0 0 0 rgba(212, 162, 76, 0.4);
  animation: btn-glow 2.5s ease-in-out infinite;
}
@keyframes btn-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(212, 162, 76, 0.5); }
  50%      { box-shadow: 0 0 0 6px rgba(212, 162, 76, 0); }
}
.result-actions .back-btn.secondary {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.15);
  color: #ccc;
}
.result-actions .back-btn.secondary:hover {
  background: rgba(255,255,255,0.1);
  border-color: #D4A24C;
  box-shadow: none;
  color: #fff;
}

/* =================== v5 新增样式 =================== */

/* ---- 关键字高亮 ---- */
.narration-text :deep(.hi) {
  font-style: normal;
  color: #FFE0A3;
  background: linear-gradient(180deg, transparent 60%, rgba(212,162,76,0.25) 60%);
  padding: 0 3px;
  font-weight: 600;
  text-shadow: 0 0 8px rgba(212,162,76,0.4);
}
.narration-text :deep(.hi-num) {
  color: #FF8888;
  background: linear-gradient(180deg, transparent 60%, rgba(255,136,136,0.25) 60%);
  text-shadow: 0 0 10px rgba(255,136,136,0.5);
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 1.05em;
}
.narration-text :deep(.hi-crit) {
  color: #FFD700;
  background: linear-gradient(180deg, transparent 60%, rgba(255,215,0,0.3) 60%);
  text-shadow: 0 0 12px rgba(255,215,0,0.7);
  font-weight: 700;
  animation: hi-crit-pulse 1.5s ease-in-out infinite;
}
@keyframes hi-crit-pulse {
  50% { text-shadow: 0 0 24px rgba(255,215,0,1); }
}

/* ---- 卷轴叙事容器 ---- */
.story-zone {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 12px;
  margin-bottom: 12px;
}
@media (max-width: 900px) {
  .story-zone { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .battle {
    min-height: var(--visual-vh);
    padding: calc(10px + var(--safe-top)) calc(10px + var(--safe-right)) calc(220px + var(--safe-bottom)) calc(10px + var(--safe-left));
    overflow-x: hidden;
  }
  .battle-header {
    align-items: flex-start;
    gap: 8px;
    padding: 8px 10px;
  }
  .battle-header .left {
    gap: 8px;
  }
  .battle-header .model {
    display: none;
  }
  .ai-hud,
  .ws-reconnect {
    flex-wrap: wrap;
    gap: 6px;
  }
  .ws-actions {
    width: 100%;
  }
  .ws-actions button {
    flex: 1;
  }
  .arena-v6 {
    min-height: 0;
    padding: 10px;
    gap: 8px;
  }
  .combat-card {
    display: grid;
    grid-template-columns: 78px minmax(0, 1fr);
    gap: 8px 10px;
    align-items: center;
    padding: 10px;
  }
  .combat-card :deep(.round-portrait),
  .card-portrait-wrap {
    width: 72px !important;
    height: 72px !important;
  }
  .card-title-block {
    text-align: left;
  }
  .card-name {
    font-size: 16px;
  }
  .card-bars {
    grid-column: 1 / -1;
  }
  .story-zone {
    grid-template-columns: 1fr;
    margin-bottom: 0;
  }
  .tab-bar { flex-wrap: wrap; gap: 4px; }
  .tab { padding: 6px 12px; font-size: 12px; }
  .tab.gift-tab { margin-left: 0; }
  .card-grid { grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 8px; }
  .scroll-wrap { padding: 12px 16px; min-height: 80px; max-height: 140px; }
  .phase-indicator { margin-bottom: 4px; }
  .tutorial-bubble { margin: 0 8px 8px; }
  .action-panel {
    position: fixed;
    left: calc(8px + var(--safe-left));
    right: calc(8px + var(--safe-right));
    bottom: calc(8px + var(--safe-bottom));
    z-index: 210;
    max-height: min(42dvh, 220px);
    overflow: auto;
    padding: 8px;
    border-color: rgba(212, 162, 76, 0.28);
    background: rgba(9, 9, 18, 0.94);
    backdrop-filter: blur(12px);
  }
  .card {
    min-height: 94px;
    padding: 10px 8px;
  }
  .card-desc {
    display: none;
  }
}

@media (orientation: landscape) and (max-height: 520px) {
  .battle {
    min-height: var(--visual-vh);
    height: var(--visual-vh);
    overflow: hidden;
    padding: calc(8px + var(--safe-top)) calc(10px + var(--safe-right)) calc(134px + var(--safe-bottom)) calc(86px + var(--safe-left));
    display: grid;
    grid-template-rows: auto auto minmax(0, 1fr);
    gap: 8px;
  }
  .battle-header {
    margin-bottom: 0;
    padding: 7px 10px;
  }
  .battle-header .model {
    display: none;
  }
  .arena-v6 {
    min-height: 0;
    padding: 8px;
    gap: 10px;
    grid-template-columns: minmax(160px, 0.9fr) 72px minmax(160px, 0.9fr);
  }
  .combat-card {
    padding: 8px;
    gap: 6px;
  }
  .combat-card :deep(.round-portrait),
  .card-portrait-wrap {
    width: 86px !important;
    height: 86px !important;
  }
  .card-name {
    font-size: 15px;
  }
  .story-zone {
    grid-template-columns: minmax(0, 1fr) 220px;
    min-height: 0;
    overflow: hidden;
  }
  .scroll-wrap,
  .battle-log {
    max-height: 100%;
    min-height: 0;
  }
  .action-panel {
    position: fixed;
    left: calc(76px + var(--safe-left));
    right: calc(8px + var(--safe-right));
    bottom: calc(8px + var(--safe-bottom));
    z-index: 210;
    max-height: 118px;
    overflow: auto;
    padding: 7px;
    background: rgba(9, 9, 18, 0.95);
    backdrop-filter: blur(10px);
  }
  .tab-bar {
    flex-wrap: nowrap;
    overflow-x: auto;
    padding-bottom: 6px;
    margin-bottom: 7px;
  }
  .tab {
    white-space: nowrap;
    padding: 6px 10px;
  }
  .card-grid {
    display: flex;
    gap: 8px;
    overflow-x: auto;
  }
  .card,
  .item-card {
    flex: 0 0 132px;
  }
  .card-desc,
  .card-preview {
    display: none;
  }
}

.scroll-wrap {
  position: relative;
  background: linear-gradient(180deg, #1c1a14, #0f0e0a);
  border-left: 4px solid #8B5A2B;
  border-right: 4px solid #8B5A2B;
  border-radius: 4px;
  padding: 16px 28px;
  min-height: 110px;
  max-height: 190px;
  overflow-y: auto;
  box-shadow: inset 0 0 24px rgba(0,0,0,0.6);
}
.scroll-handle {
  position: absolute; left: -10px; right: -10px;
  height: 10px;
  background: linear-gradient(90deg, #5a3a1a 0%, #8B5A2B 50%, #5a3a1a 100%);
  border-radius: 5px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.5);
}
.scroll-top { top: -5px; }
.scroll-bottom { bottom: -5px; }

/* ---- 战报卡列表 ---- */
.battle-log {
  display: flex; flex-direction: column;
  gap: 6px;
  max-height: 190px;
  overflow-y: auto;
}
.log-card {
  background: linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
  border: 1px solid rgba(255,255,255,0.08);
  border-left-width: 3px;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
}
.log-card.attacker-player {
  border-left-color: #7FC7E8;
  background: linear-gradient(90deg, rgba(127,199,232,0.08), transparent);
}
.log-card.attacker-enemy {
  border-left-color: #C03F3F;
  background: linear-gradient(90deg, rgba(192,63,63,0.08), transparent);
}
.log-card.outcome-crit { border-left-color: #FFD700; }
.log-card.outcome-miss { opacity: 0.6; }
.log-card.destiny {
  border-left-color: #FFE0A3;
  background: linear-gradient(90deg, rgba(255,224,163,0.15), transparent);
  box-shadow: 0 0 12px rgba(212,162,76,0.2);
}

.log-head {
  display: flex; gap: 8px; align-items: center;
  margin-bottom: 4px;
  font-size: 11px;
  color: #aaa;
}
.log-round { color: #666; }
.log-skill { color: #D4A24C; flex: 1; }
.destiny-badge {
  background: linear-gradient(135deg, #D4A24C, #FFE0A3);
  color: #1a1a2e;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 9px;
  font-style: normal;
  letter-spacing: 1px;
  margin-left: 4px;
}
.log-attacker {
  background: rgba(0,0,0,0.4);
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 10px;
}
.log-body {
  display: flex; align-items: center; gap: 10px;
}
.log-label { color: #ccc; font-size: 12px; }
.log-damage {
  font-family: 'SF Mono', monospace;
  font-weight: 600;
  color: #FF8888;
  margin-left: auto;
  font-size: 14px;
}
.log-damage.crit {
  color: #FFD700;
  font-size: 17px;
  text-shadow: 0 0 8px rgba(255,215,0,0.6);
}
.log-heal { color: #52B788; margin-left: auto; font-family: 'SF Mono', monospace; font-weight: 600; }
.log-zero { color: #666; margin-left: auto; }

/* log 进出场动画 */
.log-fade-enter-active { transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1); }
.log-fade-leave-active { transition: opacity 0.2s; }
.log-fade-enter-from { opacity: 0; transform: translateX(20px) scale(0.95); }
.log-fade-leave-to { opacity: 0; }

/* ---- 天命降临遮罩 ---- */
.destiny-overlay {
  position: fixed; inset: 0;
  background: radial-gradient(ellipse at center, rgba(0,0,0,0.6), rgba(0,0,0,0.92));
  z-index: 400;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 20px;
  pointer-events: none;
}
.destiny-rings { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; }
.destiny-rings .ring {
  position: absolute;
  border: 2px solid #FFD700;
  border-radius: 50%;
  width: 100px; height: 100px;
  animation: destiny-ring-expand 2.5s ease-out infinite;
  opacity: 0;
}
.destiny-rings .ring:nth-child(2) { animation-delay: 0.4s; }
.destiny-rings .ring:nth-child(3) { animation-delay: 0.8s; }
@keyframes destiny-ring-expand {
  0% { width: 100px; height: 100px; opacity: 1; border-color: #FFE0A3; }
  100% { width: 800px; height: 800px; opacity: 0; border-color: #FFD700; }
}
.destiny-text {
  font-size: 64px;
  letter-spacing: 24px;
  font-family: 'STKaiti','KaiTi',serif;
  background: linear-gradient(135deg, #FFE0A3, #FFD700 50%, #FFE0A3);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 0 64px rgba(255,215,0,0.8);
  animation: destiny-text-pop 1s cubic-bezier(0.34, 1.56, 0.64, 1);
  z-index: 1;
}
.destiny-sub {
  font-size: 24px; color: #FFE0A3;
  letter-spacing: 8px;
  z-index: 1;
  text-shadow: 0 0 16px rgba(255,215,0,0.6);
  animation: destiny-text-pop 1s 0.2s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
.destiny-hint {
  font-size: 14px; color: #ccc; letter-spacing: 3px;
  z-index: 1; opacity: 0.7;
  animation: destiny-text-pop 1s 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
@keyframes destiny-text-pop {
  0% { opacity: 0; transform: scale(3) translateY(-30px); letter-spacing: 60px; filter: blur(20px); }
  100% { opacity: 1; transform: scale(1) translateY(0); filter: blur(0); }
}
.destiny-enter-active, .destiny-leave-active { transition: opacity 0.4s; }
.destiny-enter-from, .destiny-leave-to { opacity: 0; }

/* ---- 天命 Tab ---- */
.tab-destiny.locked {
  color: #666;
  border-color: rgba(255,255,255,0.05);
}
.tab-destiny.charged {
  border-color: #FFE0A3;
  background: linear-gradient(135deg, rgba(212,162,76,0.2), rgba(255,224,163,0.05));
  color: #FFE0A3;
  animation: tab-destiny-pulse 1.5s ease-in-out infinite;
}
@keyframes tab-destiny-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(212,162,76,0.5); }
  50% { box-shadow: 0 0 16px 4px rgba(212,162,76,0.6); }
}
.destiny-ready { color: #FFD700; font-weight: 700; }

/* ---- 天命栏内容 ---- */
.destiny-panel {
  padding: 30px 20px;
  text-align: center;
}
.destiny-locked, .destiny-used {
  color: #888;
}
.locked-icon { font-size: 56px; margin-bottom: 12px; opacity: 0.6; }
.destiny-locked h3 { color: #D4A24C; letter-spacing: 4px; margin: 0 0 12px; font-size: 18px; }
.destiny-locked p { font-size: 13px; line-height: 1.8; margin: 4px 0; }
.destiny-locked p.hint { color: #FFB454; font-size: 12px; }
.destiny-locked strong { color: #FFE0A3; }

.destiny-ready-card {
  display: flex; flex-direction: column; align-items: center;
  padding: 30px 20px;
  background: linear-gradient(180deg, rgba(255,224,163,0.08), rgba(212,162,76,0.02));
  border: 2px solid #FFE0A3;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  animation: destiny-card-glow 2s ease-in-out infinite;
  position: relative;
  overflow: hidden;
}
.destiny-ready-card::before {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(45deg, transparent 40%, rgba(255,215,0,0.15) 50%, transparent 60%);
  background-size: 300% 300%;
  animation: destiny-shine 4s linear infinite;
  pointer-events: none;
}
@keyframes destiny-card-glow {
  0%, 100% { box-shadow: 0 0 32px rgba(255,215,0,0.3); }
  50% { box-shadow: 0 0 64px rgba(255,215,0,0.7); border-color: #FFD700; }
}
@keyframes destiny-shine {
  0% { background-position: 200% 200%; }
  100% { background-position: -100% -100%; }
}
.destiny-ready-card:hover { transform: scale(1.03); }
.destiny-ring-outer {
  width: 100px; height: 100px;
  border: 2px solid rgba(255,215,0,0.4);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  animation: destiny-rotate 12s linear infinite;
  position: relative;
}
.destiny-ring-outer::before, .destiny-ring-outer::after {
  content: ''; position: absolute; inset: -10px;
  border: 1px dashed rgba(255,215,0,0.3);
  border-radius: 50%;
}
.destiny-ring-outer::after { inset: -20px; }
.destiny-ring-inner {
  width: 72px; height: 72px;
  background: radial-gradient(circle, rgba(255,215,0,0.2), rgba(0,0,0,0.5));
  border: 2px solid #FFE0A3;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
}
.destiny-icon {
  font-size: 38px;
  filter: drop-shadow(0 0 16px rgba(255,215,0,0.8));
}
@keyframes destiny-rotate { 100% { transform: rotate(360deg); } }
.destiny-name {
  margin: 16px 0 8px;
  font-family: 'STKaiti','KaiTi',serif;
  font-size: 22px;
  background: linear-gradient(135deg, #FFE0A3, #FFD700);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 6px;
  z-index: 1; position: relative;
}
.destiny-desc {
  font-size: 13px; color: #ccc; margin: 4px 0 12px;
  font-style: italic; z-index: 1; position: relative;
}
.destiny-stats {
  display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;
  margin: 12px 0;
  z-index: 1; position: relative;
}
.destiny-stats span {
  background: rgba(255,215,0,0.1);
  border: 1px solid rgba(255,215,0,0.3);
  color: #FFE0A3;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
}
.destiny-cta {
  margin-top: 14px;
  color: #FFD700;
  font-size: 14px;
  letter-spacing: 4px;
  animation: destiny-cta-blink 1s ease-in-out infinite;
  z-index: 1; position: relative;
}
@keyframes destiny-cta-blink {
  50% { opacity: 0.6; }
}

/* === ★ v3 Token 消耗估算 === */
.hud-tokens {
  color: #666;
  font-size: 11px;
  margin-left: 2px;
}

/* === ★ v3 战斗阶段指示器 === */
.phase-indicator {
  grid-column: 1 / -1;
  text-align: center;
  margin-bottom: 6px;
  min-height: 22px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
}
.phase-skip-btn {
  background: linear-gradient(135deg, rgba(255, 200, 80, 0.18), rgba(212, 162, 76, 0.32));
  color: #FFE0A3;
  border: 1px solid rgba(255, 200, 80, 0.55);
  padding: 4px 14px;
  border-radius: 14px;
  font-size: 12px;
  font-family: 'STKaiti', 'KaiTi', serif;
  letter-spacing: 2px;
  cursor: pointer;
  transition: all 0.18s;
  animation: skip-pulse 1.6s ease-in-out infinite;
  box-shadow: 0 0 12px rgba(255, 200, 80, 0.25);
}
.phase-skip-btn:hover {
  background: linear-gradient(135deg, rgba(255, 200, 80, 0.32), rgba(212, 162, 76, 0.5));
  border-color: rgba(255, 200, 80, 0.9);
  color: #fff;
  transform: scale(1.04);
}
@keyframes skip-pulse {
  0%, 100% { box-shadow: 0 0 8px rgba(255, 200, 80, 0.2); }
  50%      { box-shadow: 0 0 18px rgba(255, 200, 80, 0.55); }
}
.phase-text {
  display: inline-block;
  font-size: 12px;
  letter-spacing: 3px;
  padding: 3px 14px;
  border-radius: 4px;
  font-family: 'STKaiti', 'KaiTi', serif;
}
.phase-idle {
  color: #888;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  animation: phase-pulse 2.5s ease-in-out infinite;
}
@keyframes phase-pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}
.phase-casting {
  color: #FFE0A3;
  background: rgba(212, 162, 76, 0.1);
  border: 1px solid rgba(212, 162, 76, 0.3);
  animation: phase-spin-glow 1.2s linear infinite;
}
@keyframes phase-spin-glow {
  0%   { box-shadow: 0 0 4px rgba(212, 162, 76, 0.3); }
  50%  { box-shadow: 0 0 12px rgba(212, 162, 76, 0.6); }
  100% { box-shadow: 0 0 4px rgba(212, 162, 76, 0.3); }
}
.phase-resolving {
  color: #FFD700;
  background: rgba(255, 215, 0, 0.1);
  border: 1px solid rgba(255, 215, 0, 0.4);
  animation: phase-flash 0.6s ease-in-out infinite;
}
@keyframes phase-flash {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.phase-narrating {
  color: #7FC7E8;
  background: rgba(127, 199, 232, 0.08);
  border: 1px solid rgba(127, 199, 232, 0.3);
}
.typing-dots::after {
  content: '';
  animation: typing-dots 1.5s steps(3) infinite;
}
@keyframes typing-dots {
  0%   { content: ''; }
  33%  { content: '.'; }
  66%  { content: '..'; }
  100% { content: '...'; }
}
.phase-enemy {
  color: #FF8888;
  background: rgba(192, 63, 63, 0.1);
  border: 1px solid rgba(192, 63, 63, 0.3);
  animation: phase-enemy-pulse 0.8s ease-in-out infinite;
}
@keyframes phase-enemy-pulse {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-2px); }
  75% { transform: translateX(2px); }
}

/* === ★ 新手教学气泡 === */
.tutorial-bubble {
  position: relative;
  margin: 0 auto 10px;
  max-width: 360px;
  background: linear-gradient(135deg, rgba(30, 60, 90, 0.95), rgba(20, 40, 60, 0.98));
  border: 1.5px solid rgba(127, 199, 232, 0.5);
  border-radius: 10px;
  padding: 12px 16px;
  cursor: pointer;
  box-shadow: 0 0 20px rgba(127, 199, 232, 0.2), inset 0 1px 0 rgba(255,255,255,0.05);
  animation: tutorial-glow 2s ease-in-out infinite;
}
.tutorial-icon {
  position: absolute;
  top: -12px;
  left: 16px;
  font-size: 20px;
  background: #1a1a2e;
  padding: 0 4px;
  border-radius: 4px;
}
.tutorial-msg {
  font-size: 13px;
  color: #d4e8f7;
  line-height: 1.6;
  letter-spacing: 0.5px;
}
.tutorial-dismiss {
  margin-top: 6px;
  font-size: 10px;
  color: #7FC7E8;
  text-align: right;
  opacity: 0.6;
}
@keyframes tutorial-glow {
  0%, 100% { box-shadow: 0 0 12px rgba(127, 199, 232, 0.15); }
  50%      { box-shadow: 0 0 24px rgba(127, 199, 232, 0.35); }
}
.tutorial-fade-enter-active { animation: tooltip-in 0.3s ease-out; }
.tutorial-fade-leave-active { animation: tooltip-in 0.2s ease-in reverse; }
</style>
