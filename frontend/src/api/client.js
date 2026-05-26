import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// ★ Phase C: 请求拦截器 — 自动附加 Authorization Bearer token
client.interceptors.request.use(
  config => {
    const token = localStorage.getItem('auth_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  },
  e => Promise.reject(e),
)

// ════════════════════════════════════════════════════════════
// 仙侠化错误文案 — 把技术错误翻译成世界观内的表达
// ════════════════════════════════════════════════════════════
const XIANXIA_ERRORS = {
  // HTTP 状态码 → 仙侠文案
  401: '灵脉令牌已失效,请重新接入灵脉',
  403: '此处禁地,道力不足以踏入',
  404: '此路不通,所寻之物已不在此处',
  408: '灵脉响应超时,天道沉默',
  429: '灵脉过载!推演频率过快,请稍候再试',
  500: '天道紊乱,后台灵阵异常',
  502: '灵脉中转失联,网关断裂',
  503: '后台灵阵正在维护,稍后再来',

  // code → 仙侠文案
  TIMEOUT: '灵脉推演超时,请检查网络是否通畅',
  NETWORK_ERROR: '无法连接灵脉,请确认后台灵阵已启动',
  MEDITATE_COOLDOWN: '调息尚未完毕,不可强行运功',
  BATTLE_NOT_FOUND: '此战局已消散,无法进入',
  NOT_VERIFIED: '灵脉尚未验证,请先完成探测',
  BYOK_PROBE_FAILED: '灵脉探测失败,请检查接入凭证',
  SECT_NOT_AVAILABLE: '该派灵脉尚未贯通',
  IMAGE_GEN_FAILED: '画卷绘制失败,灵力不足',
}

function toXianxiaMessage(code, status, rawMessage) {
  // 优先用 code 匹配
  if (code && XIANXIA_ERRORS[code]) return XIANXIA_ERRORS[code]
  // 其次用 status 匹配
  if (status && XIANXIA_ERRORS[status]) return XIANXIA_ERRORS[status]
  // 兜底:如果原始消息已经是中文(后端可能已翻译),保留
  if (rawMessage && /[一-鿿]/.test(rawMessage)) return rawMessage
  // 最终兜底
  return rawMessage || '天道异变,请稍后再试'
}

// 统一错误归一:把 axios error 包装成 { code, status, message, techDetail } 风格
client.interceptors.response.use(
  r => r.data,
  e => {
    const status = e.response?.status
    let detail = e.response?.data?.detail
    let code = 'UNKNOWN'
    let rawMessage = e.message || '请求失败'

    // FastAPI detail 可能是 string,也可能是 dict {code, message, ...}
    if (typeof detail === 'string') {
      rawMessage = detail
    } else if (detail && typeof detail === 'object') {
      code = detail.code || code
      rawMessage = detail.message || rawMessage
    }

    // 网络/超时类
    if (!e.response) {
      code = e.code === 'ECONNABORTED' ? 'TIMEOUT' : 'NETWORK_ERROR'
    } else if (status >= 500) {
      code = code === 'UNKNOWN' ? 'SERVER_ERROR' : code
    } else if (status === 404 && code === 'UNKNOWN') {
      code = 'NOT_FOUND'
    } else if (status === 401) {
      code = 'AUTH_REQUIRED'
      // ★ Phase C: 401 自动清 token + 跳 /login (避免循环触发,只在非 login 页面)
      try {
        if (typeof window !== 'undefined' && !window.location.hash.includes('/login')) {
          localStorage.removeItem('auth_token')
          localStorage.removeItem('auth_user')
          // hash 路由跳转
          window.location.hash = '#/login'
        }
      } catch (_) {}
    } else if (status === 429) {
      code = 'RATE_LIMITED'
    }

    // ★ 仙侠化错误文案(玩家友好)
    const message = toXianxiaMessage(code, status, rawMessage)

    const err = new Error(message)
    err.code = code
    err.status = status
    err.detail = detail
    err.techDetail = rawMessage  // 保留原始技术信息(调试用)
    return Promise.reject(err)
  }
)

export const sectApi = {
  list: () => client.get('/sect/list'),
  get: (id) => client.get(`/sect/${id}`),
  // ★ v2 选派页详细数据:立绘 + 招式预览 + 背景故事
  preview: (id) => client.get(`/sect/${id}/preview`),
}

export const byokApi = {
  // 探测 key 可用模型 + 各派可选性(快,只调 /v1/models)
  probe: (base_url, api_key) => client.post('/byok/probe', { base_url, api_key }),
}

export const siteApi = {
  config: () => client.get('/site/config'),
  updateConfig: (payload) => client.put('/admin/site-config', payload),
}

export const characterApi = {
  me: () => client.get('/character/me'),
  chooseSect: (sect_id, character_name = '执笔者', base_url = '', api_key = '') =>
    client.post('/character/choose-sect', {
      sect_id, character_name, base_url, api_key,
    }),
  reset: () => client.delete('/character/me'),
  // 游戏中更换 byok(verified=true 必须先在前端跑过验证)
  updateByok: (base_url, api_key, verified = false) =>
    client.post('/character/me/byok', { base_url, api_key, verified }),
  // ★ 打坐调息:恢复 HP/灵气并增加疲劳;修为由入定成章任务产生
  meditate: () => client.post('/character/meditate'),
}

export const fortuneApi = {
  // ★ 触发奇遇 — 后端 LLM 即时生成,效果立即应用到 character
  trigger: (visible_enemies = []) =>
    client.post('/fortune/trigger', { visible_enemies }),
}

export const giftApi = {
  // ★ 战斗中赠礼给怪物 — 接受率取决于物品稀有度 + 友好度 + INS + 已送次数
  give: (battle_id, item_id, gift_count_so_far = 0) =>
    client.post('/battle/give-gift', { battle_id, item_id, gift_count_so_far }),
}

export const battleApi = {
  listEnemies: () => client.get('/battle/enemies'),
  listCards: () => client.get('/battle/cards'),
  // mode: 'drama' (全 LLM 叙事,默认) / 'speed' (无 LLM,极快)
  start: (enemy_id, mode = 'drama') => client.post('/battle/start', { enemy_id, mode }),
  get: (battle_id) => client.get(`/battle/${battle_id}`),
  // ★ 卡牌伤害预览:预计伤害、命中率、暴击率、灵气余额
  cardPreview: (battle_id) => client.get(`/battle/${battle_id}/card-preview`),
}

export const exploreApi = {
  spawn: (count = 10) => client.get(`/explore/spawn?count=${count}`),
  enemiesCount: () => client.get('/enemies/count'),
}

export const worldApi = {
  save: () => client.get('/world/save'),
  sync: (revision, world, character_patch = null, client_round_id = '') =>
    client.post('/world/sync', { client_round_id, revision, world, character_patch }),
}

export const bossApi = {
  list: () => client.get('/boss/list'),
  get: (id) => client.get(`/boss/${id}`),
  chapter: (id) => client.post(`/boss/${id}/chapter`),
  listSects: () => client.get('/boss-sects/list'),
  storylines: () => client.get('/storylines'),
}

export const itemApi = {
  list: () => client.get('/items/list'),
  get: (id) => client.get(`/items/${id}`),
}

export const inventoryApi = {
  list: () => client.get('/inventory'),
  use: (id) => client.post(`/inventory/use/${id}`),
  grant: (id, count = 1) => client.post(`/inventory/grant/${id}?count=${count}`),
}

// ★ 今日修行令
export const dailyApi = {
  get: () => client.get('/daily'),
  claim: () => client.post('/daily/claim'),
}

// ★ 山海经图鉴
export const bestiaryApi = {
  list: () => client.get('/bestiary'),
  detail: (enemy_id) => client.get(`/bestiary/${enemy_id}`),
}

// ★ 炼丹炼器
export const recipeApi = {
  list: () => client.get('/recipes'),
  craft: (recipe_id) => client.post('/recipes/craft', { recipe_id }),
  usages: (item_id) => client.get(`/items/${item_id}/usages`),
}

// ★ 修行录
export const journalApi = {
  list: (limit = 20, offset = 0) => client.get(`/journal?limit=${limit}&offset=${offset}`),
}

// ★ 墨炉 / 本命书
export const cultivationApi = {
  queue: () => client.get('/cultivation/queue'),
  createTask: (task_type, payload = {}) => client.post('/cultivation/tasks', { task_type, ...payload }),
  getTask: (task_id) => client.get(`/cultivation/tasks/${task_id}`),
  pause: (task_id) => client.post(`/cultivation/tasks/${task_id}/pause`),
  resume: (task_id) => client.post(`/cultivation/tasks/${task_id}/resume`),
  cancel: (task_id) => client.post(`/cultivation/tasks/${task_id}/cancel`),
}

export const novelApi = {
  stats: () => client.get('/novel/stats'),
  volumes: () => client.get('/novel/volumes'),
  chapters: (limit = 30, offset = 0) => client.get(`/novel/chapters?limit=${limit}&offset=${offset}`),
  chapter: (id) => client.get(`/novel/chapters/${id}`),
}

// ★ Round 2: NPC 弟子互动
export const npcApi = {
  engage: (npc_id, intent, npc = null) => client.post('/npc/engage', { npc_id, intent, npc }),
  tradeBuy: (npc_id, item_id, count = 1) => client.post('/npc/trade-buy', { npc_id, item_id, count }),
}

// ★ Round 1: 技能树
export const skillApi = {
  listAll: () => client.get('/skills/all'),
  equip: (skill_ids) => client.post('/skills/equip', { skill_ids }),
  upgrade: (skill_id) => client.post('/skills/upgrade', { skill_id }),
}

// ★ Phase C: 用户认证
export const authApi = {
  register: (username, password) => client.post('/auth/register', { username, password }),
  login: (username, password) => client.post('/auth/login', { username, password }),
  me: () => client.get('/auth/me'),
  logout: () => client.post('/auth/logout'),
}

// 独立管理后台
export const adminApi = {
  bootstrapStatus: () => client.get('/admin/bootstrap/status'),
  bootstrap: (username, password) => client.post('/admin/bootstrap', { username, password }),
  login: (username, password) => client.post('/admin/auth/login', { username, password }),
  overview: () => client.get('/admin/overview'),
  users: (params = {}) => client.get('/admin/users', { params }),
  userDetail: (userId) => client.get(`/admin/users/${encodeURIComponent(userId)}`),
  grantItem: (userId, payload) => client.post(`/admin/users/${encodeURIComponent(userId)}/inventory/grant`, payload),
}

export default client
