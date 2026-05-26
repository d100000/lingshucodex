import discipleData from '../data/disciples.json'

export const SECTS = discipleData.sects
export const DISCIPLES = discipleData.disciples
export const DISCIPLE_BY_ID = Object.fromEntries(DISCIPLES.map(d => [d.id, d]))

const DB_NAME = 'lingshu_world_v1'
const DB_VERSION = 1
const WORLD_STORE = 'worlds'
const MAX_RECENT_EVENTS = 300
const MAX_CHARACTER_HISTORY = 500
const MAX_RELATION_HISTORY = 240
const SECT_IDS = Object.keys(SECTS)
const CORE_RANKS = new Set(['核心', '真传', '护法', '长老'])

const NEXT_ROUND_TARGET = { id: 'next_round', label: '下一轮' }
const NEXT_ROUND_LOCATION = { id: 'main_city', label: '主城', sect: null }
const NEXT_ROUND_STANCE = { id: 'world_tick', label: '江湖流转', risk: 1 }

const FAMILY_TEXT = [
  {
    family: 'old_debt',
    label: '旧债回响',
    templates: [
      '{a}在{place}提起旧案,{b}沉默许久,二人关系生出新的裂纹。',
      '{a}替{b}隐瞒了一段旧债,此事暂未传开。',
    ],
  },
  {
    family: 'spar',
    label: '问剑切磋',
    templates: [
      '{a}与{b}在{place}切磋三招,胜负未分,旁观弟子议论纷纷。',
      '{a}看破{b}一式破绽,没有点破,只留下一句改日再战。',
    ],
  },
  {
    family: 'rescue',
    label: '援手相救',
    templates: [
      '{a}在{place}救下被困的{b},这份人情被记入两人的关系链。',
      '{b}替{a}挡下一次暗算,五宗中有人开始重新评价他们。',
    ],
  },
  {
    family: 'secret',
    label: '暗线密信',
    templates: [
      '{a}收到一封无署名密信,信中提到了{b}和黑卷商人的旧线索。',
      '{a}在{place}发现{b}留下的暗号,却没有立刻声张。',
    ],
  },
  {
    family: 'romance',
    label: '情愫暗生',
    templates: [
      '{a}与{b}并肩避雨半夜,旁人只当偶遇,二人心中却各有波澜。',
      '{a}替{b}修好一件旧物,这份温柔在江湖传闻里悄悄发酵。',
    ],
  },
  {
    family: 'betrayal',
    label: '疑云背叛',
    templates: [
      '{a}被传私会外宗弟子,{b}选择相信,却也留下戒心。',
      '{a}误以为{b}泄露机密,两人好感骤降,真相尚未浮出。',
    ],
  },
  {
    family: 'teaching',
    label: '同修论道',
    templates: [
      '{a}与{b}共读残卷,各自修为都有寸进。',
      '{a}向{b}请教一处难题,意外牵出跨宗旧注。',
    ],
  },
  {
    family: 'injury',
    label: '伤势波动',
    templates: [
      '{a}旧伤复发,{b}送来丹药,此事在熟人圈中传开。',
      '{a}强行修炼受了内伤,{b}看在眼里,没有拆穿。',
    ],
  },
]

const PLACES = ['白石渡', '问剑台', '青澜古碑前', '中立市集', '旧藏书楼', '月下渡口', '机关廊', '寒潭边']

const RUMOR_LABELS = {
  old_debt: '旧事回响',
  spar: '人物际遇',
  rescue: '人物际遇',
  secret: '门派风波',
  romance: '关系变化',
  betrayal: '关系变化',
  teaching: '修为波动',
  injury: '人物命运',
}

const MAJOR_EVENT_ARCHETYPES = [
  { id: 'secret_leak', label: '秘辛外泄', tone: 'danger', sectDelta: -16, relationDelta: -18, outcome: '五宗信任被撕开一道口子。', template: '{trigger}牵出{relic}, {a}与{b}在{place}对质, {sourceSect}与{targetSect}的暗线关系骤然紧绷。' },
  { id: 'alliance_oath', label: '临时盟约', tone: 'good', sectDelta: 15, relationDelta: 18, outcome: '两派暂时放下旧怨,共同追查源头。', template: '{trigger}逼近{place}, {a}与{b}以{relic}为证立下短盟, {sourceSect}与{targetSect}的往来重新升温。' },
  { id: 'relic_appearance', label: '古物现世', tone: 'mystic', sectDelta: -6, relationDelta: 6, outcome: '古物归属未定,各派都派出耳目。', template: '{relic}在{place}现世, {a}和{b}先后赶到, {sourceSect}与{targetSect}都不愿退让。' },
  { id: 'siege_rescue', label: '绝境援救', tone: 'good', sectDelta: 12, relationDelta: 24, outcome: '救命之恩被写入人物关系链。', template: '{trigger}突然爆发, {a}在{place}救下{b}, 这件事让{sourceSect}与{targetSect}的旧评出现松动。' },
  { id: 'betrayal_trial', label: '叛门疑案', tone: 'danger', sectDelta: -20, relationDelta: -26, outcome: '真相未明,但猜疑已经扩散。', template: '{a}被卷入{trigger}, {b}握有{relic}残证, 两人在{place}的交锋让两派关系急转直下。' },
  { id: 'duel_summit', label: '五宗论剑', tone: 'neutral', sectDelta: 8, relationDelta: -8, outcome: '胜负只是表面,真正变化发生在旁观者心中。', template: '{sourceSect}与{targetSect}因{trigger}重开论剑, {a}和{b}在{place}一战成名。' },
  { id: 'missing_core', label: '核心失踪', tone: 'danger', sectDelta: -12, relationDelta: -12, outcome: '核心人物下落成谜,搜寻线索开始扩散。', template: '{trigger}后, {a}在{place}失去踪迹, {b}发现{relic}残痕, 两派互相怀疑。' },
  { id: 'forbidden_breakthrough', label: '禁法破境', tone: 'mystic', sectDelta: -8, relationDelta: 10, outcome: '破境是真的,代价也是真的。', template: '{a}借{relic}在{place}强行破境, {b}看见禁法痕迹, {sourceSect}与{targetSect}都被卷入追问。' },
  { id: 'marriage_pact', label: '姻缘盟约', tone: 'good', sectDelta: 18, relationDelta: 20, outcome: '这段关系既是私情,也是宗门筹码。', template: '{trigger}之后, {a}与{b}在{place}互换信物, {sourceSect}与{targetSect}出现罕见和议。' },
  { id: 'succession_storm', label: '掌印之争', tone: 'danger', sectDelta: -14, relationDelta: -16, outcome: '权柄更替的风声开始影响弟子站队。', template: '{sourceSect}因{trigger}生出掌印之争, {a}请{b}带走{relic}, {targetSect}因此被拖入漩涡。' },
  { id: 'spirit_plague', label: '灵疫风波', tone: 'danger', sectDelta: -10, relationDelta: 14, outcome: '救治、封锁与猜疑同时发生。', template: '{place}突发灵疫, {a}携{relic}求援, {b}选择冒险开阵, 两派声望随之震动。' },
  { id: 'market_assassination', label: '市集暗杀', tone: 'danger', sectDelta: -18, relationDelta: -20, outcome: '刺客未落网,嫌疑却已经有了名字。', template: '{trigger}在{place}化作暗杀, {a}险些身亡, {b}拾得{relic}, 两派暗线同时收紧。' },
]

const MAJOR_EVENT_TRIGGERS = [
  '黑卷残页重现', '林泽旧案翻出新证', '月隐名册缺失一页', '书火案证人现身',
  '天机机关锁自行开启', '青冥古碑夜半鸣响', '沧澜剑冢裂开旧封', '玄机观星盘逆转',
  '五宗密约被人篡改', '中立市集忽传悬赏', '白石渡水下现出碑文', '寒潭浮起无名剑匣',
]

const MAJOR_EVENT_RELICS = [
  '黑卷残页', '月隐名册', '青澜古碑拓片', '天机锁芯', '无名剑匣', '星盘裂针',
  '旧盟血书', '寒潭玉简', '书火灰烬', '林泽遗令', '机关残鸢', '紫灯密印',
]

const MAJOR_EVENT_PLACES = [
  '白石渡', '问剑台', '青澜古碑前', '中立市集', '旧藏书楼', '月下渡口',
  '机关廊', '寒潭边', '五宗驿亭', '断剑坡', '星盘高台', '无灯祠',
]

const MAJOR_EVENT_CONSEQUENCES = [
  '两派弟子开始互相试探,短期内外宗拜访会更敏感。',
  '相关人物的羁绊被改写,后续轶事会继续提起此事。',
  '宗门长辈暂时压下风声,但内门弟子已开始站队。',
  '旧案线索进入明面,后续更容易触发追查类轶事。',
  '一名核心人物被推到风口,关系网会围绕他继续变化。',
  '五宗坊间传闻暴涨,普通弟子也会受到余波影响。',
  '此事暂未定论,但两派关系已经留下裂痕。',
  '此事成为新的江湖锚点,人物简报会保留完整记录。',
]

export const MAJOR_EVENT_VARIANT_COUNT = MAJOR_EVENT_ARCHETYPES.length
  * MAJOR_EVENT_TRIGGERS.length
  * MAJOR_EVENT_RELICS.length
  * MAJOR_EVENT_PLACES.length
  * MAJOR_EVENT_CONSEQUENCES.length

function openDB() {
  if (typeof indexedDB === 'undefined') return Promise.resolve(null)
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(WORLD_STORE)) db.createObjectStore(WORLD_STORE, { keyPath: 'id' })
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function idbGet(key) {
  const db = await openDB()
  if (!db) return null
  return new Promise(resolve => {
    const tx = db.transaction(WORLD_STORE, 'readonly')
    const req = tx.objectStore(WORLD_STORE).get(key)
    req.onsuccess = () => resolve(req.result || null)
    req.onerror = () => resolve(null)
  })
}

async function idbPut(value) {
  const db = await openDB()
  if (!db) return null
  return new Promise(resolve => {
    const tx = db.transaction(WORLD_STORE, 'readwrite')
    tx.objectStore(WORLD_STORE).put(value)
    tx.oncomplete = () => resolve(true)
    tx.onerror = () => resolve(false)
  })
}

function hashString(text) {
  let h = 2166136261
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return h >>> 0
}

function mulberry32(seed) {
  let t = seed >>> 0
  return () => {
    t += 0x6D2B79F5
    let r = Math.imul(t ^ (t >>> 15), 1 | t)
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r)
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296
  }
}

function choice(rng, list) {
  return list[Math.floor(rng() * list.length)]
}

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n))
}

function unique(list) {
  return Array.from(new Set(list.filter(Boolean)))
}

export function worldKey(character) {
  return `world:${character?.id || character?.name || 'player'}:${character?.sect || 'unknown'}`
}

function pairKey(a, b) {
  return `${a}__${b}`
}

function sectPairKey(a, b) {
  return [a, b].sort().join('__')
}

function baseDisciples() {
  return Object.fromEntries(DISCIPLES.map(d => [
    d.id,
    {
      level: d.level,
      cultivation: 0,
      age_days: d.base_age_years * 360,
      status: [],
      story_flags: [],
      recent: [],
      history: [],
    },
  ]))
}

function seedRelationStates() {
  const relations = {}
  for (const d of DISCIPLES) {
    for (const r of d.relationships || []) {
      if (!DISCIPLE_BY_ID[r.target_id]) continue
      relations[pairKey(d.id, r.target_id)] = {
        affinity: r.affinity,
        tags: [r.relation],
        recent: [],
      }
    }
  }
  return relations
}

function seedSectRelations() {
  const relations = {}
  for (let i = 0; i < SECT_IDS.length; i += 1) {
    for (let j = i + 1; j < SECT_IDS.length; j += 1) {
      relations[sectPairKey(SECT_IDS[i], SECT_IDS[j])] = { affinity: 0, recent: [] }
    }
  }
  return relations
}

function initialFamiliarCircle(character, rng) {
  const own = DISCIPLES.filter(d => d.sect_id === character?.sect)
  const cross = DISCIPLES.filter(d => d.sect_id !== character?.sect)
  const picked = []
  for (const rank of ['外门', '内门', '核心']) {
    const pool = own.filter(d => d.rank === rank)
    if (pool.length) picked.push(choice(rng, pool).id)
  }
  while (picked.length < 5 && own.length) {
    const id = choice(rng, own).id
    if (!picked.includes(id)) picked.push(id)
  }
  while (picked.length < 8 && cross.length) {
    const id = choice(rng, cross).id
    if (!picked.includes(id)) picked.push(id)
  }
  return picked
}

function defaultSectState() {
  return Object.fromEntries(SECT_IDS.map(id => [id, { affinity: 0, tension: 0, rumors: 0, reputation: 0 }]))
}

function ensureWorldShape(world, character) {
  const seed = world?.seed || hashString(`${character?.name || 'player'}:${character?.sect || 'none'}:${character?.level || 1}`)
  const rng = mulberry32(seed)
  world.id ||= worldKey(character)
  world.version ||= 1
  world.seed = seed
  world.round ||= 0
  world.day ||= 1
  world.player ||= {
    sect_id: character?.sect || 'canglan',
    name: character?.name || '执笔者',
    local_exp_delta: 0,
    local_hp_delta: 0,
    local_qi_delta: 0,
    local_fatigue_delta: 0,
  }
  world.player.local_exp_delta ||= 0
  world.player.local_hp_delta ||= 0
  world.player.local_qi_delta ||= 0
  world.player.local_fatigue_delta ||= 0
  world.familiar_ids ||= initialFamiliarCircle(character, rng)
  world.disciples ||= {}
  const base = baseDisciples()
  for (const [id, state] of Object.entries(base)) {
    world.disciples[id] ||= state
    world.disciples[id].status ||= []
    world.disciples[id].story_flags ||= []
    world.disciples[id].recent ||= []
    world.disciples[id].history ||= []
    world.disciples[id].level ||= state.level
    world.disciples[id].cultivation ||= 0
    world.disciples[id].age_days ||= state.age_days
  }
  world.relations ||= {}
  const seededRelations = seedRelationStates()
  for (const [key, rel] of Object.entries(seededRelations)) {
    world.relations[key] ||= rel
    world.relations[key].recent ||= []
    world.relations[key].history ||= []
    world.relations[key].tags ||= rel.tags || ['初识']
  }
  world.sect_state ||= defaultSectState()
  for (const [id, state] of Object.entries(defaultSectState())) {
    world.sect_state[id] ||= state
  }
  world.sect_relations ||= seedSectRelations()
  for (const [key, rel] of Object.entries(seedSectRelations())) {
    world.sect_relations[key] ||= rel
    world.sect_relations[key].recent ||= []
    world.sect_relations[key].history ||= []
  }
  world.hooks ||= []
  world.event_log ||= []
  world.major_history ||= []
  world.major_quiet_rounds ||= 0
  world.pending_sync ||= []
  return world
}

export function createInitialWorld(character) {
  const seed = hashString(`${character?.name || 'player'}:${character?.sect || 'none'}:${character?.level || 1}`)
  const rng = mulberry32(seed)
  const familiarIds = initialFamiliarCircle(character, rng)
  return {
    id: worldKey(character),
    version: 1,
    seed,
    round: 0,
    day: 1,
    player: {
      sect_id: character?.sect || 'canglan',
      name: character?.name || '执笔者',
      local_exp_delta: 0,
      local_hp_delta: 0,
      local_qi_delta: 0,
      local_fatigue_delta: 0,
    },
    familiar_ids: familiarIds,
    disciples: baseDisciples(),
    relations: seedRelationStates(),
    sect_state: defaultSectState(),
    sect_relations: seedSectRelations(),
    major_history: [],
    major_quiet_rounds: 0,
    hooks: [
      { type: 'welcome', text: '五宗风声初动,你的入门名帖已传入各派耳中。' },
      { type: 'familiar', text: '几名同辈弟子开始留意你的第一步修行。' },
    ],
    event_log: [],
    pending_sync: [],
    last_summary: null,
  }
}

export async function loadWorld(character) {
  const key = worldKey(character)
  const found = await idbGet(key)
  if (found) return ensureWorldShape(found, character)
  const world = createInitialWorld(character)
  await saveWorld(world)
  return world
}

export async function saveWorld(world) {
  world.updated_at = new Date().toISOString()
  await idbPut(world)
  return world
}

function relationBetween(world, a, b) {
  const key = pairKey(a, b)
  if (!world.relations[key]) world.relations[key] = { affinity: 0, tags: ['初识'], recent: [] }
  return world.relations[key]
}

function sectRelationBetween(world, a, b) {
  const key = sectPairKey(a, b)
  if (!world.sect_relations[key]) world.sect_relations[key] = { affinity: 0, recent: [] }
  return world.sect_relations[key]
}

function relationLabel(affinity) {
  if (affinity >= 80) return '生死之交'
  if (affinity >= 60) return '至交'
  if (affinity >= 35) return '信重旧识'
  if (affinity >= 15) return '友善'
  if (affinity > -15) return '点头之交'
  if (affinity > -35) return '芥蒂'
  if (affinity > -60) return '争执旧识'
  if (affinity > -80) return '怨敌'
  return '宿敌'
}

function sectDeltaForFamily(family, relationDelta, rng) {
  const base = {
    old_debt: -1,
    spar: relationDelta < 0 ? -1 : 1,
    rescue: 3,
    secret: -3,
    romance: 1,
    betrayal: -5,
    teaching: 2,
    injury: 0,
  }[family] || 0
  return clamp(Math.round(relationDelta / 4 + base + rng() * 3 - 1), -8, 8)
}

function weightedActiveDisciples(world, character, rng, count = 50) {
  const scored = DISCIPLES.map(d => {
    let w = 1
    if (d.sect_id === character?.sect) w += 2
    if (world.familiar_ids.includes(d.id)) w += 7
    if ((d.relationships || []).some(r => world.familiar_ids.includes(r.target_id))) w += 2
    const state = world.disciples[d.id]
    if (state?.status?.length) w += 3
    if (Math.abs((d.level || 0) - (character?.level || 1)) <= 10) w += 2
    return { d, roll: -Math.log(Math.max(0.0001, rng())) / w }
  })
  return scored.sort((a, b) => a.roll - b.roll).slice(0, count).map(x => x.d)
}

function personalOutcome(character) {
  const hpMax = character?.max_hp || 100
  const qiMax = character?.max_qi || 600
  const hpNow = character?.hp ?? hpMax
  const qiNow = character?.qi ?? qiMax
  const fatigue = character?.fatigue || 0

  const hpDelta = Math.max(0, Math.min(hpMax - hpNow, Math.round(hpMax * 0.30)))
  const qiDelta = Math.max(0, Math.min(qiMax - qiNow, Math.round(qiMax * 0.40)))
  const fatigueDelta = -Math.max(0, fatigue)

  return {
    expDelta: 0,
    fatigueDelta,
    hpDelta,
    qiDelta,
  }
}

function addRecent(state, entry, max = 8) {
  state.recent = [entry].concat(state.recent || []).slice(0, max)
  state.history = [entry].concat(state.history || []).slice(0, MAX_CHARACTER_HISTORY)
}

function addRelationRecent(rel, entry, max = 5) {
  rel.recent = [entry].concat(rel.recent || []).slice(0, max)
  rel.history = [entry].concat(rel.history || []).slice(0, MAX_RELATION_HISTORY)
}

function compactActor(id, world) {
  const d = DISCIPLE_BY_ID[id]
  const state = world.disciples[id] || {}
  if (!d) return { id, name: id, sect_id: '', sect_name: '', level: state.level || 1, portrait_id: id }
  return {
    id,
    name: d.name,
    sect_id: d.sect_id,
    sect_name: SECTS[d.sect_id]?.name || d.sect_id,
    rank: d.rank,
    level: state.level || d.level,
    portrait_id: `${d.sect_id}/${d.id}`,
  }
}

function compactEvent(e, world) {
  return {
    id: e.id,
    day: e.day,
    is_major: !!e.is_major,
    headline: e.headline || '',
    impact: e.impact || '',
    category: e.category || '',
    tone: e.tone || '',
    variant_key: e.variant_key || '',
    family: e.family,
    label: e.label,
    importance: e.importance,
    summary: e.summary,
    place: e.place,
    actors: e.actors,
    actor_names: e.actors.map(id => DISCIPLE_BY_ID[id]?.name || id),
    actors_detail: e.actors.map(id => compactActor(id, world)),
    sects: e.sects,
    deltas: e.deltas,
    character_outcomes: e.character_outcomes,
  }
}

function isCoreDisciple(d) {
  if (!d) return false
  return CORE_RANKS.has(d.rank) || (d.level || 0) >= 60
}

function majorEventChance(world) {
  return clamp(0.18 + (world.major_quiet_rounds || 0) * 0.055, 0.18, 0.46)
}

function shouldTriggerMajorEvent(world, rng) {
  return rng() < majorEventChance(world, rng)
}

function pickCoreActor(rng, pool, excludeSect = '') {
  const core = pool.filter(d => isCoreDisciple(d) && d.sect_id !== excludeSect)
  if (core.length) return choice(rng, core)
  const fallback = DISCIPLES.filter(d => d.sect_id !== excludeSect && isCoreDisciple(d))
  return fallback.length ? choice(rng, fallback) : choice(rng, DISCIPLES.filter(d => d.sect_id !== excludeSect))
}

function applyMajorOutcome(world, event, archetype, a, b, rng) {
  const stateA = world.disciples[a.id]
  const stateB = world.disciples[b.id]
  const outcomes = []

  if (archetype.id === 'missing_core') {
    stateA.status = Array.from(new Set([...(stateA.status || []), '失踪']))
    outcomes.push({ type: 'missing', actor: a.id, label: '失踪', summary: `${a.name}失去踪迹,门内暗线开始搜寻。` })
  }
  if (archetype.id === 'forbidden_breakthrough') {
    const before = stateA.level
    stateA.level += 1
    stateA.cultivation = 0
    stateA.status = Array.from(new Set([...(stateA.status || []), '禁法反噬']))
    outcomes.push({ type: 'breakthrough', actor: a.id, before_level: before, after_level: stateA.level, label: '禁法破境', summary: `${a.name}借禁法突破至 Lv ${stateA.level},但留下反噬。` })
  }
  if (archetype.id === 'spirit_plague') {
    stateA.status = Array.from(new Set([...(stateA.status || []), '灵疫疑云']))
    stateB.status = Array.from(new Set([...(stateB.status || []), '涉入救治']))
    outcomes.push({ type: 'injury', actor: a.id, target: b.id, label: '灵疫牵连', summary: `${a.name}与${b.name}被卷入灵疫救治。` })
  }
  if (archetype.id === 'siege_rescue' || archetype.id === 'marriage_pact' || archetype.id === 'alliance_oath') {
    outcomes.push({ type: 'bond', actor: a.id, target: b.id, label: archetype.label, summary: `${a.name}与${b.name}因${archetype.label}结下新的因果。` })
  }
  if (archetype.id === 'secret_leak' || archetype.id === 'betrayal_trial' || archetype.id === 'market_assassination') {
    outcomes.push({ type: 'grudge', actor: a.id, target: b.id, label: archetype.label, summary: `${a.name}与${b.name}之间的猜疑被推到明处。` })
  }
  if (!outcomes.length && rng() < 0.45) {
    outcomes.push({ type: 'major', actor: a.id, target: b.id, label: archetype.label, summary: `${a.name}与${b.name}成为本轮轶事的核心人物。` })
  }

  event.character_outcomes = outcomes
}

function makeMajorEvent(world, rng, active, index) {
  const archetype = choice(rng, MAJOR_EVENT_ARCHETYPES)
  const trigger = choice(rng, MAJOR_EVENT_TRIGGERS)
  const relic = choice(rng, MAJOR_EVENT_RELICS)
  const place = choice(rng, MAJOR_EVENT_PLACES)
  const consequence = choice(rng, MAJOR_EVENT_CONSEQUENCES)
  const a = pickCoreActor(rng, active)
  const b = pickCoreActor(rng, active, a.sect_id)
  const sourceSect = SECTS[a.sect_id]?.name || a.sect_id
  const targetSect = SECTS[b.sect_id]?.name || b.sect_id
  const headline = `${archetype.label} · ${sourceSect} / ${targetSect}`
  const summary = archetype.template
    .replaceAll('{trigger}', trigger)
    .replaceAll('{relic}', relic)
    .replaceAll('{place}', place)
    .replaceAll('{a}', a.name)
    .replaceAll('{b}', b.name)
    .replaceAll('{sourceSect}', sourceSect)
    .replaceAll('{targetSect}', targetSect)

  const rel = relationBetween(world, a.id, b.id)
  const reverseRel = relationBetween(world, b.id, a.id)
  const beforeAffinity = rel.affinity || 0
  const relationDelta = Math.round(archetype.relationDelta + rng() * 8 - 4)
  rel.affinity = clamp(beforeAffinity + relationDelta, -100, 100)
  reverseRel.affinity = clamp((reverseRel.affinity || 0) + Math.round(relationDelta * 0.85), -100, 100)
  if (!rel.tags?.includes(archetype.label)) rel.tags = [archetype.label].concat(rel.tags || []).slice(0, 5)
  if (!reverseRel.tags?.includes(archetype.label)) reverseRel.tags = [archetype.label].concat(reverseRel.tags || []).slice(0, 5)

  const sectRel = sectRelationBetween(world, a.sect_id, b.sect_id)
  const beforeSectAffinity = sectRel.affinity || 0
  const sectDelta = Math.round(archetype.sectDelta + rng() * 6 - 3)
  sectRel.affinity = clamp(beforeSectAffinity + sectDelta, -100, 100)

  const memory = {
    day: world.day,
    event_id: `m${world.round}_${index}`,
    type: 'major',
    label: archetype.label,
    summary: `${headline}: ${summary}`,
    actors: [a.id, b.id],
    major: true,
  }
  addRecent(world.disciples[a.id], memory, 10)
  addRecent(world.disciples[b.id], memory, 10)
  addRelationRecent(rel, `第${world.day}日 ${headline}:${summary}`, 8)
  addRelationRecent(reverseRel, `第${world.day}日 ${headline}:${summary}`, 8)
  addRelationRecent(sectRel, `第${world.day}日 ${headline}`, 8)

  const event = {
    id: `m${world.round}_${index}`,
    day: world.day,
    is_major: true,
    category: 'major',
    tone: archetype.tone,
    family: archetype.id,
    label: archetype.label,
    headline,
    impact: consequence,
    importance: 100,
    summary,
    place,
    actors: [a.id, b.id],
    sects: unique([a.sect_id, b.sect_id]),
    variant_key: `${archetype.id}:${trigger}:${relic}:${place}`,
    deltas: {
      affinity: [{
        source: a.id,
        target: b.id,
        delta: relationDelta,
        before: beforeAffinity,
        after: rel.affinity,
        before_label: relationLabel(beforeAffinity),
        after_label: relationLabel(rel.affinity),
        tag: archetype.label,
        reason: summary,
      }],
      sect_affinity: [{
        source: a.sect_id,
        target: b.sect_id,
        delta: sectDelta,
        before: beforeSectAffinity,
        after: sectRel.affinity,
      }],
      cultivation: [],
    },
    character_outcomes: [],
  }
  applyMajorOutcome(world, event, archetype, a, b, rng)
  world.major_history = [compactEvent(event, world)].concat(world.major_history || []).slice(0, 80)
  return event
}

function makeEvent(world, rng, active, index, target, location, stance, character) {
  const a = choice(rng, active)
  const relationPool = (a.relationships || []).filter(r => DISCIPLE_BY_ID[r.target_id])
  let b = relationPool.length && rng() < 0.65 ? DISCIPLE_BY_ID[choice(rng, relationPool).target_id] : choice(rng, active)
  if (b.id === a.id) b = choice(rng, active.filter(d => d.id !== a.id))
  const family = choice(rng, FAMILY_TEXT)
  const template = choice(rng, family.templates)
  const place = choice(rng, PLACES)
  const summary = template
    .replaceAll('{a}', a.name)
    .replaceAll('{b}', b.name)
    .replaceAll('{place}', place)

  const rel = relationBetween(world, a.id, b.id)
  const reverseRel = relationBetween(world, b.id, a.id)
  const beforeAffinity = rel.affinity || 0
  const beforeLabel = relationLabel(beforeAffinity)
  const sign = family.family === 'betrayal' ? -1 : family.family === 'spar' && rng() < 0.45 ? -1 : 1
  const delta = Math.round((2 + rng() * 10) * sign * stance.risk)
  rel.affinity = clamp(beforeAffinity + delta, -100, 100)
  reverseRel.affinity = clamp((reverseRel.affinity || 0) + Math.round(delta * 0.85), -100, 100)
  const afterLabel = relationLabel(rel.affinity)
  const newTag = !rel.tags?.includes(family.label)
  if (newTag) rel.tags = [family.label].concat(rel.tags || []).slice(0, 4)
  if (!reverseRel.tags?.includes(family.label)) reverseRel.tags = [family.label].concat(reverseRel.tags || []).slice(0, 4)
  const memory = `第${world.day}日 ${family.label}:${summary}`
  addRelationRecent(rel, memory)
  addRelationRecent(reverseRel, memory)

  const stateA = world.disciples[a.id]
  const stateB = world.disciples[b.id]
  const beforeLevel = stateA.level
  const cultivationDelta = Math.round((4 + rng() * 28) * (family.family === 'teaching' ? 1.8 : 1))
  stateA.cultivation += cultivationDelta
  if (rng() < 0.18) stateB.cultivation += Math.round(cultivationDelta * 0.55)

  const characterOutcomes = []
  if (stateA.cultivation > 80 + stateA.level * stateA.level * 6) {
    stateA.level += 1
    stateA.cultivation = 0
    characterOutcomes.push({
      type: 'breakthrough',
      actor: a.id,
      before_level: beforeLevel,
      after_level: stateA.level,
      label: '修为突破',
      summary: `${a.name}修为突破至 Lv ${stateA.level}`,
    })
  }
  if (family.family === 'injury' && rng() < 0.25) {
    stateA.status = Array.from(new Set([...(stateA.status || []), '轻伤']))
    characterOutcomes.push({
      type: 'injury',
      actor: a.id,
      label: '受伤',
      summary: `${a.name}添了轻伤,短期内行事更谨慎。`,
    })
  }
  if (family.family === 'betrayal' && delta <= -8) {
    characterOutcomes.push({
      type: 'grudge',
      actor: a.id,
      target: b.id,
      label: '新增恩怨',
      summary: `${a.name}与${b.name}之间添了一笔难解的恩怨。`,
    })
  }
  if ((family.family === 'rescue' || family.family === 'romance') && delta >= 8) {
    characterOutcomes.push({
      type: family.family === 'rescue' ? 'bond' : 'fate',
      actor: a.id,
      target: b.id,
      label: family.family === 'rescue' ? '结缘' : '情愫',
      summary: `${a.name}与${b.name}的关系被这件事重新写下。`,
    })
  }

  const sectAffinity = []
  if (a.sect_id !== b.sect_id) {
    const sectRel = sectRelationBetween(world, a.sect_id, b.sect_id)
    const beforeSectAffinity = sectRel.affinity || 0
    const sectDelta = sectDeltaForFamily(family.family, delta, rng)
    sectRel.affinity = clamp(beforeSectAffinity + sectDelta, -100, 100)
    addRelationRecent(sectRel, `第${world.day}日 ${SECTS[a.sect_id]?.name}与${SECTS[b.sect_id]?.name}:${family.label}`)
    sectAffinity.push({
      source: a.sect_id,
      target: b.sect_id,
      delta: sectDelta,
      before: beforeSectAffinity,
      after: sectRel.affinity,
    })
  }

  const eventMemory = {
    day: world.day,
    event_id: `r${world.round}_${index}`,
    type: family.family,
    label: family.label,
    summary,
    actors: [a.id, b.id],
  }
  addRecent(stateA, eventMemory)
  addRecent(stateB, eventMemory)

  const visibleBias = world.familiar_ids.includes(a.id) || world.familiar_ids.includes(b.id) ? 42 : 0
  const storyBias = /黑卷|书火|名册|裂简|古碑|林泽/.test(`${a.story_hook}${b.story_hook}`) ? 18 : 0
  const rankBias = Math.floor((a.level + b.level) / 26)
  const relationBias = Math.abs(beforeAffinity) >= 50 || Math.abs(rel.affinity) >= 50 ? 10 : 0
  const outcomeBias = characterOutcomes.length ? 18 + characterOutcomes.length * 8 : 0
  const sectBias = sectAffinity.some(s => Math.abs(s.delta) >= 3) ? 12 : 0
  const tagBias = newTag ? 8 : 0
  const importance = clamp(
    Math.round(rng() * 38 + visibleBias + storyBias + rankBias + relationBias + outcomeBias + sectBias + tagBias),
    1,
    100,
  )

  return {
    id: `r${world.round}_${index}`,
    day: world.day,
    family: family.family,
    label: family.label,
    importance,
    summary,
    place,
    actors: [a.id, b.id],
    sects: unique([a.sect_id, b.sect_id]),
    deltas: {
      affinity: [{
        source: a.id,
        target: b.id,
        delta,
        before: beforeAffinity,
        after: rel.affinity,
        before_label: beforeLabel,
        after_label: afterLabel,
        tag: family.label,
        reason: summary,
      }],
      sect_affinity: sectAffinity,
      cultivation: [{ target: a.id, delta: cultivationDelta }],
    },
    character_outcomes: characterOutcomes,
  }
}

function summarizeSectChanges(world, events) {
  return SECT_IDS.map(id => {
    const sectEvents = events.filter(e => e.sects.includes(id))
    const high = sectEvents.filter(e => e.importance >= 70)
    const outcomes = sectEvents.flatMap(e => e.character_outcomes || [])
    const relationDeltas = {}
    let positiveRelations = 0
    let negativeRelations = 0

    for (const e of sectEvents) {
      for (const d of e.deltas.sect_affinity || []) {
        if (d.source !== id && d.target !== id) continue
        const other = d.source === id ? d.target : d.source
        relationDeltas[other] = (relationDeltas[other] || 0) + d.delta
        if (d.delta > 0) positiveRelations += d.delta
        if (d.delta < 0) negativeRelations += Math.abs(d.delta)
      }
    }

    const breakthroughCount = outcomes.filter(o => o.type === 'breakthrough').length
    const injuredCount = outcomes.filter(o => o.type === 'injury').length
    const newGrudges = outcomes.filter(o => o.type === 'grudge').length
    const newBonds = outcomes.filter(o => o.type === 'bond' || o.type === 'fate').length
    const reputationDelta = clamp(
      Math.round((positiveRelations - negativeRelations) / 10 + breakthroughCount * 0.8 + newBonds * 0.6 - injuredCount * 0.5 - newGrudges * 0.7),
      -12,
      12,
    )
    world.sect_state[id].reputation = clamp((world.sect_state[id].reputation || 0) + reputationDelta, -100, 100)

    return {
      sect_id: id,
      sect_name: SECTS[id].name,
      event_count: sectEvents.length,
      high_count: high.length,
      breakthrough_count: breakthroughCount,
      injured_count: injuredCount,
      new_grudges: newGrudges,
      new_bonds: newBonds,
      reputation_delta: reputationDelta,
      heat: clamp(Math.round(sectEvents.length / 4 + high.length * 4 + breakthroughCount * 7 + injuredCount * 4 + newGrudges * 5), 0, 100),
      relation_deltas: Object.entries(relationDeltas)
        .map(([sectId, delta]) => ({
          sect_id: sectId,
          sect_name: SECTS[sectId]?.name || sectId,
          delta,
          after: sectRelationBetween(world, id, sectId).affinity,
        }))
        .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
        .slice(0, 4),
    }
  })
}

function summarizeRankings(events, relationshipChanges, characterHighlights) {
  const actorScores = new Map()
  for (const e of events) {
    for (const actor of e.actors) {
      const current = actorScores.get(actor) || { id: actor, score: 0, count: 0, max: 0 }
      current.score += e.importance
      current.count += 1
      current.max = Math.max(current.max, e.importance)
      actorScores.set(actor, current)
    }
  }
  const topActor = Array.from(actorScores.values()).sort((a, b) => b.score - a.score)[0]
  const biggestGrudge = relationshipChanges.filter(r => r.delta < 0).sort((a, b) => a.delta - b.delta)[0]
  const topBreakthrough = characterHighlights.find(h => h.type === 'breakthrough')
  const risky = characterHighlights.find(h => h.type === 'injury' || h.type === 'grudge')
  return [
    topActor && {
      type: 'storm_actor',
      title: '本轮风云人物',
      actor_ids: [topActor.id],
      text: `${DISCIPLE_BY_ID[topActor.id]?.name || topActor.id}卷入 ${topActor.count} 起事件。`,
      score: topActor.score,
    },
    biggestGrudge && {
      type: 'largest_grudge',
      title: '本轮最大恩怨',
      actor_ids: [biggestGrudge.source, biggestGrudge.target],
      text: `${biggestGrudge.source_name}与${biggestGrudge.target_name}好感 ${biggestGrudge.before} -> ${biggestGrudge.after}。`,
      score: Math.abs(biggestGrudge.delta),
    },
    topBreakthrough && {
      type: 'fastest_breakthrough',
      title: '本轮最快突破',
      actor_ids: [topBreakthrough.actor],
      text: topBreakthrough.summary,
      score: topBreakthrough.importance,
    },
    risky && {
      type: 'dangerous_actor',
      title: '本轮危险角色',
      actor_ids: unique([risky.actor, risky.target]),
      text: risky.summary,
      score: risky.importance,
    },
  ].filter(Boolean)
}

function summarize(world, events, personal, target, location, stance) {
  const sorted = [...events].sort((a, b) => b.importance - a.importance)
  const majorEvents = sorted.filter(e => e.is_major).map(e => compactEvent(e, world))
  const coreVisible = sorted
    .filter(e => !e.is_major && e.importance >= 64 && e.actors.some(id => isCoreDisciple(DISCIPLE_BY_ID[id]) || world.familiar_ids.includes(id)))
    .slice(0, 10)
  const visible = majorEvents.length
    ? sorted.filter(e => e.is_major).concat(coreVisible).slice(0, 12)
    : coreVisible.slice(0, 8)
  const visibleIds = new Set(visible.map(e => e.id))
  const headlines = (majorEvents.length ? majorEvents : visible.slice(0, 2).map(e => compactEvent(e, world))).slice(0, 3)
  const importantEvents = (majorEvents.length ? coreVisible : visible.slice(2)).slice(0, 5).map(e => compactEvent(e, world))
  const rumors = sorted
    .filter(e => !e.is_major && e.importance >= 35 && e.importance < 70 && !visibleIds.has(e.id))
    .slice(0, 8)
    .map(e => ({
      id: e.id,
      label: RUMOR_LABELS[e.family] || e.label,
      family_label: e.label,
      importance: e.importance,
      summary: e.summary,
      actors: e.actors,
      actor_names: e.actors.map(id => DISCIPLE_BY_ID[id]?.name || id),
      sects: e.sects,
    }))

  const sectChanges = summarizeSectChanges(world, events)
  const relationshipChanges = sorted
    .filter(e => e.is_major || e.actors.some(id => isCoreDisciple(DISCIPLE_BY_ID[id]) || world.familiar_ids.includes(id)))
    .flatMap(e => (e.deltas.affinity || []).map(d => ({
      ...d,
      event_id: e.id,
      family: e.family,
      label: e.label,
      source_name: DISCIPLE_BY_ID[d.source]?.name || d.source,
      target_name: DISCIPLE_BY_ID[d.target]?.name || d.target,
      source_actor: compactActor(d.source, world),
      target_actor: compactActor(d.target, world),
      summary: e.summary,
      importance: e.importance,
    })))
    .sort((a, b) => (b.importance + Math.abs(b.delta) * 2) - (a.importance + Math.abs(a.delta) * 2))
    .slice(0, 8)

  const characterHighlights = sorted
    .filter(e => e.is_major || e.actors.some(id => isCoreDisciple(DISCIPLE_BY_ID[id]) || world.familiar_ids.includes(id)))
    .flatMap(e => (e.character_outcomes || []).map(o => ({
      ...o,
      event_id: e.id,
      importance: e.importance,
      family: e.family,
      family_label: e.label,
      actor_detail: compactActor(o.actor, world),
      target_detail: o.target ? compactActor(o.target, world) : null,
      cause: e.summary,
    })))
    .sort((a, b) => b.importance - a.importance)
    .slice(0, 6)

  const minorRipples = sorted
    .filter(e => !e.is_major && !visibleIds.has(e.id) && e.importance >= 48)
    .slice(0, 6)
    .map(e => ({
      id: e.id,
      label: RUMOR_LABELS[e.family] || e.label,
      summary: e.summary,
      actor_names: e.actors.map(id => DISCIPLE_BY_ID[id]?.name || id),
      sects: e.sects,
    }))

  const spotlightActors = unique([
    ...headlines.flatMap(e => e.actors),
    ...importantEvents.slice(0, 10).flatMap(e => e.actors),
    ...characterHighlights.flatMap(h => [h.actor, h.target]),
    ...(world.familiar_ids || []),
  ]).slice(0, 18)

  const sectLinks = []
  for (const e of sorted) {
    for (const d of e.deltas.sect_affinity || []) {
      sectLinks.push({
        source: d.source,
        target: d.target,
        delta: d.delta,
        importance: e.importance,
        label: e.label,
        summary: e.summary,
      })
    }
  }

  const displayedIds = new Set([
    ...headlines.map(e => e.id),
    ...importantEvents.map(e => e.id),
    ...rumors.map(e => e.id),
    ...minorRipples.map(e => e.id),
  ])

  return {
    round: world.round,
    day: world.day,
    from_day: Math.max(1, world.day - 1),
    selected_plan: { target, location, stance },
    personal_result: personal,
    has_major_event: majorEvents.length > 0,
    major_event_variants: MAJOR_EVENT_VARIANT_COUNT,
    major_events: majorEvents,
    world_headlines: headlines,
    important_events: importantEvents,
    sect_changes: sectChanges,
    character_highlights: characterHighlights,
    relationship_changes: relationshipChanges,
    rumors,
    minor_ripples: minorRipples,
    spotlight_actors: spotlightActors,
    spotlight_actors_detail: spotlightActors.map(id => compactActor(id, world)),
    sect_links: sectLinks.sort((a, b) => Math.abs(b.delta) + b.importance / 20 - (Math.abs(a.delta) + a.importance / 20)).slice(0, 12),
    rankings: summarizeRankings(events, relationshipChanges, characterHighlights),
    hidden_events_count: Math.max(0, events.length - displayedIds.size),
    total_events_count: events.length,
  }
}

export async function advanceWorld(character) {
  const world = ensureWorldShape(await loadWorld(character), character)
  const target = NEXT_ROUND_TARGET
  const location = NEXT_ROUND_LOCATION
  const stance = NEXT_ROUND_STANCE
  const rng = mulberry32(world.seed + world.round * 9973 + world.day * 131)
  world.round += 1
  world.day += 1
  for (const state of Object.values(world.disciples)) state.age_days += 1
  const active = weightedActiveDisciples(world, character, rng, 50)
  const events = []
  if (shouldTriggerMajorEvent(world, rng)) {
    events.push(makeMajorEvent(world, rng, active, 1))
    world.major_quiet_rounds = 0
  } else {
    world.major_quiet_rounds = (world.major_quiet_rounds || 0) + 1
  }
  for (let i = 0; i < 500; i += 1) {
    events.push(makeEvent(world, rng, active, i + 1, target, location, stance, character))
  }
  const personal = personalOutcome(character)
  world.player.local_exp_delta += personal.expDelta
  world.player.local_hp_delta += personal.hpDelta
  world.player.local_qi_delta += personal.qiDelta
  world.player.local_fatigue_delta += personal.fatigueDelta
  const summary = summarize(world, events, personal, target, location, stance)
  world.last_summary = summary
  world.event_log = events
    .filter(e => e.importance >= 60)
    .map(e => compactEvent(e, world))
    .concat(world.event_log || [])
    .slice(0, MAX_RECENT_EVENTS)
  world.pending_sync = [{
    revision: world.round,
    day: world.day,
    personal,
    visible_event_count: summary.world_headlines.length + summary.important_events.length + summary.rumors.length + summary.minor_ripples.length,
    created_at: new Date().toISOString(),
  }].concat(world.pending_sync || []).slice(0, 50)
  await saveWorld(world)
  return { world, summary, active }
}
