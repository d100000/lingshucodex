<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { worldApi } from '../api/client.js'
import { DISCIPLE_BY_ID, SECTS, advanceWorld, loadWorld, saveWorld } from '../utils/worldSimulation.js'
import { disciplePreview } from '../utils/characterPreview.js'
import { formatNum } from '../utils/format.js'
import RoundPortrait from './RoundPortrait.vue'
import SectFlag from './SectFlag.vue'

const props = defineProps({
  character: { type: Object, required: true },
})
const emit = defineEmits(['character-patch'])

const PHASES = [
  { id: 'time', label: '时序' },
  { id: 'sects', label: '五宗' },
  { id: 'actors', label: '人物' },
  { id: 'result', label: '轶事' },
]

const SECT_POSITIONS = {
  canglan: { x: 23, y: 34 },
  tianji: { x: 73, y: 30 },
  xuanji: { x: 52, y: 54 },
  qingming: { x: 27, y: 72 },
  yueyin: { x: 78, y: 74 },
}

const world = ref(null)
const summary = ref(null)
const loading = ref(false)
const replayOpen = ref(false)
const phase = ref('idle')
const activeTab = ref('overview')
const errorText = ref('')
const replayFromDay = ref(1)
const replayToDay = ref(2)
const timers = []

const accent = computed(() => {
  const color = SECTS[props.character?.sect]?.color
  return color ? `rgb(${color.join(',')})` : '#D4A24C'
})

const currentDay = computed(() => world.value?.day || 1)
const dayAdvanceText = computed(() => {
  if (summary.value) return `第 ${summary.value.from_day} 日 -> 第 ${summary.value.day} 日`
  if (replayOpen.value) return `第 ${replayFromDay.value} 日 -> 第 ${replayToDay.value} 日`
  return `第 ${currentDay.value} 日 -> 第 ${currentDay.value + 1} 日`
})
const phaseIndex = computed(() => PHASES.findIndex(p => p.id === phase.value))
const phaseCopy = computed(() => ({
  time: '主城灯火渐暗,一日江湖自行流过。',
  sects: '五宗热区亮起,只记录真正值得留意的波动。',
  actors: '核心人物与熟人掠过卷宗,他们的经历会留在人物志里。',
  result: '本轮江湖轶事已整理,大事优先,余波归档。',
  error: '本轮轶事未能写入卷宗。',
}[phase.value] || '江湖正在流转。'))

const sectChanges = computed(() => {
  const changes = summary.value?.sect_changes || []
  return Object.keys(SECTS).map(id => changes.find(s => s.sect_id === id) || {
    sect_id: id,
    sect_name: SECTS[id].name,
    event_count: 0,
    high_count: 0,
    breakthrough_count: 0,
    injured_count: 0,
    new_grudges: 0,
    new_bonds: 0,
    reputation_delta: 0,
    heat: 18,
    relation_deltas: [],
  })
})

const hotSects = computed(() => [...sectChanges.value].sort((a, b) => b.heat - a.heat).slice(0, 3))
const hasMajorEvent = computed(() => !!summary.value?.has_major_event)
const leadEvent = computed(() => summary.value?.major_events?.[0] || summary.value?.world_headlines?.[0] || null)
const leadActors = computed(() => leadEvent.value?.actors_detail || [])
const leadTitle = computed(() => {
  if (!summary.value) return '江湖风声未定'
  if (leadEvent.value?.headline) return leadEvent.value.headline
  return '本轮没有震动五宗的大事'
})
const leadSummary = computed(() => {
  if (hasMajorEvent.value && leadEvent.value?.summary) return leadEvent.value.summary
  if (!hasMajorEvent.value && quietRipples.value[0]?.summary) return quietRipples.value[0].summary
  return '各派暗线照常流动,普通弟子的经历已写入本地卷宗。'
})
const leadImpact = computed(() => {
  if (leadEvent.value?.impact) return leadEvent.value.impact
  return hasMajorEvent.value ? '此事会在后续轶事中继续回响。' : '没有大事发生时,系统只展示少量值得留意的余波。'
})

const keySectChanges = computed(() => [...sectChanges.value]
  .sort((a, b) => {
    const scoreA = Math.abs(a.reputation_delta || 0) * 4 + (a.high_count || 0) * 2 + (a.relation_deltas?.length || 0) * 3
    const scoreB = Math.abs(b.reputation_delta || 0) * 4 + (b.high_count || 0) * 2 + (b.relation_deltas?.length || 0) * 3
    return scoreB - scoreA
  })
  .slice(0, 3))

const keyPeople = computed(() => {
  const highlights = summary.value?.character_highlights || []
  const core = highlights.filter(item => ['核心', '真传', '护法', '长老'].includes(item.actor_detail?.rank))
  return (core.length ? core : highlights).slice(0, 4)
})
const keyRelations = computed(() => (summary.value?.relationship_changes || [])
  .filter(rel => rel.before_label !== rel.after_label || Math.abs(rel.delta || 0) >= 10)
  .slice(0, 4))
const quietRipples = computed(() => {
  const items = []
  items.push(...(summary.value?.important_events || []))
  items.push(...(summary.value?.minor_ripples || []))
  items.push(...(summary.value?.rumors || []))
  return items.slice(0, 8)
})

const tabs = computed(() => [
  { id: 'overview', label: '总览' },
  { id: 'sects', label: '五宗' },
  { id: 'people', label: '人物' },
  { id: 'ripples', label: '余波' },
])

const actorStream = computed(() => {
  const detail = summary.value?.spotlight_actors_detail
  if (detail?.length) return detail
  const familiar = world.value?.familiar_ids || []
  return familiar.map(actorBrief).filter(Boolean).slice(0, 12)
})

const recoveryStats = computed(() => {
  const personal = summary.value?.personal_result || { hpDelta: 0, qiDelta: 0, fatigueDelta: 0, expDelta: 0 }
  return [
    { label: '气血', value: `+${formatNum(personal.hpDelta || 0)}`, tone: 'good' },
    { label: '灵气', value: `+${formatNum(personal.qiDelta || 0)}`, tone: 'good' },
    { label: '疲劳', value: `${personal.fatigueDelta || 0}`, tone: 'cool' },
    { label: '修为', value: '不变', tone: 'still' },
  ]
})

function actorBrief(id) {
  const d = DISCIPLE_BY_ID[id]
  const state = world.value?.disciples?.[id]
  if (!d) return null
  return {
    id,
    name: d.name,
    sect_id: d.sect_id,
    sect_name: SECTS[d.sect_id]?.name || d.sect_id,
    rank: d.rank,
    level: state?.level || d.level,
    portrait_id: `${d.sect_id}/${d.id}`,
  }
}

function sectColor(id, alpha = 1) {
  const color = SECTS[id]?.color || [212, 162, 76]
  return alpha === 1 ? `rgb(${color.join(',')})` : `rgba(${color.join(',')}, ${alpha})`
}

function deltaText(value) {
  const n = Number(value || 0)
  if (n > 0) return `+${n}`
  return `${n}`
}

function deltaClass(value) {
  const n = Number(value || 0)
  if (n > 0) return 'positive'
  if (n < 0) return 'negative'
  return 'neutral'
}

function previewFor(actorOrId) {
  const id = typeof actorOrId === 'string' ? actorOrId : actorOrId?.id
  return disciplePreview(id, world.value)
}

function clearTimers() {
  while (timers.length) clearTimeout(timers.pop())
}

async function refreshWorld() {
  try {
    const { data } = await worldApi.save()
    if (data?.data) {
      world.value = data.data
      await saveWorld(data.data)
      return
    }
  } catch (_) {}
  world.value = await loadWorld(props.character)
}

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n))
}

function schedulePhase(nextPhase, delay) {
  timers.push(setTimeout(() => {
    phase.value = nextPhase
  }, delay))
}

function closeReplay() {
  replayOpen.value = false
  phase.value = 'idle'
  summary.value = null
  errorText.value = ''
  activeTab.value = 'overview'
  clearTimers()
}

async function runNextRound() {
  if (loading.value) return
  clearTimers()
  loading.value = true
  replayOpen.value = true
  summary.value = null
  errorText.value = ''
  activeTab.value = 'overview'
  replayFromDay.value = currentDay.value
  replayToDay.value = currentDay.value + 1
  phase.value = 'time'
  const startedAt = Date.now()

  schedulePhase('sects', 900)
  schedulePhase('actors', 2300)

  try {
    const result = await advanceWorld(props.character)
    world.value = result.world

    const c = props.character
    const personal = result.summary.personal_result
    const characterPatch = {
      hp: clamp((c.hp || 0) + personal.hpDelta, 1, c.max_hp || 100),
      qi: clamp((c.qi || 0) + personal.qiDelta, 0, c.max_qi || 600),
      fatigue: clamp((c.fatigue || 0) + personal.fatigueDelta, 0, c.max_fatigue || 80),
    }
    const clientRoundId = `round_${Date.now()}_${result.world.round}`
    const { data: synced } = await worldApi.sync(result.world.round, result.world, characterPatch, clientRoundId)
    const serverWorld = synced?.world || synced?.data || result.world
    world.value = serverWorld
    await saveWorld(serverWorld)
    emit('character-patch', synced?.character || synced?.character_status || characterPatch)

    const revealDelay = Math.max(4800 - (Date.now() - startedAt), 700)
    timers.push(setTimeout(() => {
      summary.value = result.summary
      phase.value = 'result'
      loading.value = false
    }, revealDelay))
  } catch (error) {
    errorText.value = error?.message || '江湖轶事写入失败'
    phase.value = 'error'
    loading.value = false
  }
}

onMounted(refreshWorld)
onBeforeUnmount(clearTimers)
</script>

<template>
  <div class="next-round-dock" :style="{ '--accent': accent }">
    <button class="next-round-btn" :disabled="loading" @click="runNextRound">
      <span>{{ loading ? '流转中' : '下一轮' }}</span>
      <small>第 {{ currentDay }} 日</small>
    </button>

    <Teleport to="body">
      <Transition name="jianghu-replay">
        <section
          v-if="replayOpen"
          class="jianghu-replay"
          role="dialog"
          aria-modal="true"
          :style="{ '--accent': accent }"
        >
          <div class="replay-backdrop"></div>

          <div class="replay-shell" :class="`phase-${phase}`">
            <header class="replay-topbar">
              <div class="replay-title">
                <span>江湖轶事</span>
                <strong>{{ dayAdvanceText }}</strong>
              </div>
              <div class="phase-track" aria-label="轶事整理进度">
                <span
                  v-for="(item, index) in PHASES"
                  :key="item.id"
                  :class="{ active: phase === item.id, done: phaseIndex > index || phase === 'result' }"
                >
                  {{ item.label }}
                </span>
              </div>
            </header>

            <div class="replay-body">
              <section class="jianghu-map" aria-label="五宗江湖图">
                <div class="map-grid"></div>
                <div class="map-river"></div>
                <div
                  v-for="link in (summary?.sect_links || []).slice(0, 6)"
                  :key="`${link.source}-${link.target}-${link.summary}`"
                  class="sect-link"
                  :class="deltaClass(link.delta)"
                ></div>

                <article
                  v-for="sect in sectChanges"
                  :key="sect.sect_id"
                  class="sect-node"
                  :class="{ hot: phase === 'sects' || phase === 'result' }"
                  :style="{
                    '--x': `${SECT_POSITIONS[sect.sect_id]?.x || 50}%`,
                    '--y': `${SECT_POSITIONS[sect.sect_id]?.y || 50}%`,
                    '--sect-color': sectColor(sect.sect_id),
                    '--heat': `${Math.max(22, sect.heat || 18)}px`,
                  }"
                >
                  <span class="node-pulse"></span>
                  <SectFlag :sect-id="sect.sect_id" :name="sect.sect_name" :size="42" :radius="9" />
                  <strong>{{ sect.sect_name }}</strong>
                  <em>{{ summary ? (hasMajorEvent && sect.heat >= 70 ? '风波炽盛' : (sect.high_count ? '余波流动' : '暗流归档')) : '风声未定' }}</em>
                </article>

                <div class="time-sigil">
                  <span>{{ phase === 'result' ? '成卷' : '流转' }}</span>
                  <strong>{{ dayAdvanceText }}</strong>
                </div>
              </section>

              <aside class="replay-aside">
                <section class="phase-panel">
                  <span>本轮风声</span>
                  <strong>{{ phaseCopy }}</strong>
                </section>

                <section class="actor-panel">
                  <div class="panel-head">
                    <span>核心掠影</span>
                    <strong>{{ actorStream.length }}</strong>
                  </div>
                  <div class="actor-stream" :class="{ running: phase === 'actors' || loading }">
                    <div
                      v-for="(actor, index) in actorStream.slice(0, 12)"
                      :key="actor.id"
                      class="actor-chip"
                      :style="{ '--delay': `${index * 0.08}s`, '--actor-color': sectColor(actor.sect_id) }"
                    >
                      <RoundPortrait
                        kind="disciple"
                        :id="actor.portrait_id"
                        :name="actor.name"
                        :size="48"
                        :frame="sectColor(actor.sect_id)"
                        :preview="previewFor(actor)"
                      />
                      <span>{{ actor.name }}</span>
                    </div>
                  </div>
                </section>

                <section v-if="summary" class="personal-panel">
                  <div v-for="stat in recoveryStats" :key="stat.label" :class="['recover-stat', stat.tone]">
                    <span>{{ stat.label }}</span>
                    <strong>{{ stat.value }}</strong>
                  </div>
                </section>
              </aside>
            </div>

            <Transition name="result-rise">
              <section v-if="summary && phase === 'result'" class="result-sheet">
                <header class="result-head">
                  <div>
                    <span>{{ hasMajorEvent ? '本轮大事件' : '本轮无大事' }}</span>
                    <strong>{{ leadTitle }}</strong>
                    <p>{{ leadImpact }}</p>
                  </div>
                  <div class="result-seal" :class="{ quiet: !hasMajorEvent }">
                    {{ hasMajorEvent ? '大事' : '轶闻' }}
                  </div>
                </header>

                <section class="result-focus">
                  <article class="lead-incident" :class="{ quiet: !hasMajorEvent }">
                    <div class="incident-meta">
                      <span>{{ hasMajorEvent ? leadEvent?.label : '江湖余波' }}</span>
                      <em>{{ hasMajorEvent ? '优先成卷' : '未触发大事件' }}</em>
                    </div>
                    <p>{{ leadSummary }}</p>
                    <div class="lead-actors" v-if="leadActors.length">
                      <div v-for="actor in leadActors" :key="actor.id" class="lead-actor">
                        <RoundPortrait
                          kind="disciple"
                          :id="actor.portrait_id"
                          :name="actor.name"
                          :size="56"
                          :frame="sectColor(actor.sect_id)"
                          :preview="previewFor(actor)"
                        />
                        <div>
                          <strong>{{ actor.name }}</strong>
                          <span>{{ actor.sect_name }} · {{ actor.rank }}</span>
                        </div>
                      </div>
                    </div>
                  </article>

                  <div class="focus-column">
                    <section class="focus-card">
                      <div class="focus-head">
                        <span>{{ hasMajorEvent ? '门派震动' : '门派余波' }}</span>
                        <strong>{{ keySectChanges[0]?.sect_name || '五宗平稳' }}</strong>
                      </div>
                      <div class="sect-pulse-list">
                        <div v-for="sect in keySectChanges" :key="sect.sect_id" class="sect-pulse">
                          <SectFlag :sect-id="sect.sect_id" :name="sect.sect_name" :size="32" :radius="7" />
                          <div>
                            <strong>{{ sect.sect_name }}</strong>
                            <span>声望 <em :class="deltaClass(sect.reputation_delta)">{{ deltaText(sect.reputation_delta) }}</em></span>
                          </div>
                        </div>
                      </div>
                    </section>

                    <section class="focus-card">
                      <div class="focus-head">
                        <span>核心人物</span>
                        <strong>{{ keyPeople.length ? `${keyPeople.length} 人有变` : '暂无剧变' }}</strong>
                      </div>
                      <div v-if="keyPeople.length" class="people-strip">
                        <div v-for="item in keyPeople.slice(0, 4)" :key="`${item.event_id}-${item.actor}-${item.type}`">
                          <RoundPortrait
                            kind="disciple"
                            :id="item.actor_detail.portrait_id"
                            :name="item.actor_detail.name"
                            :size="44"
                            :frame="sectColor(item.actor_detail.sect_id)"
                            :preview="previewFor(item.actor_detail)"
                          />
                          <span>{{ item.label }}</span>
                        </div>
                      </div>
                      <p v-else class="muted-copy">本轮核心人物没有明显命运转折。</p>
                    </section>
                  </div>
                </section>

                <nav class="result-tabs" aria-label="江湖轶事分类">
                  <button
                    v-for="tab in tabs"
                    :key="tab.id"
                    :class="{ active: activeTab === tab.id }"
                    @click="activeTab = tab.id"
                  >
                    {{ tab.label }}
                  </button>
                </nav>

                <section class="detail-panel">
                  <div v-if="activeTab === 'overview'" class="overview-grid">
                    <article v-for="rel in keyRelations" :key="`${rel.event_id}-${rel.source}-${rel.target}`" class="relation-brief">
                      <div class="relation-faces">
                        <RoundPortrait
                          kind="disciple"
                          :id="rel.source_actor.portrait_id"
                          :name="rel.source_name"
                          :size="42"
                          :frame="sectColor(rel.source_actor.sect_id)"
                          :preview="previewFor(rel.source_actor)"
                        />
                        <strong :class="deltaClass(rel.delta)">{{ deltaText(rel.delta) }}</strong>
                        <RoundPortrait
                          kind="disciple"
                          :id="rel.target_actor.portrait_id"
                          :name="rel.target_name"
                          :size="42"
                          :frame="sectColor(rel.target_actor.sect_id)"
                          :preview="previewFor(rel.target_actor)"
                        />
                      </div>
                      <p>{{ rel.source_name }}与{{ rel.target_name }}: {{ rel.before_label }} -> {{ rel.after_label }}</p>
                    </article>
                    <article v-for="item in quietRipples.slice(0, 4)" :key="item.id" class="ripple-brief">
                      <span>{{ item.label }}</span>
                      <p>{{ item.summary }}</p>
                    </article>
                  </div>

                  <div v-else-if="activeTab === 'sects'" class="sect-change-grid">
                    <article
                      v-for="sect in sectChanges"
                      :key="sect.sect_id"
                      class="sect-change-card"
                      :style="{ '--sect-color': sectColor(sect.sect_id) }"
                    >
                      <div class="sect-card-head">
                        <SectFlag :sect-id="sect.sect_id" :name="sect.sect_name" :size="38" :radius="8" />
                        <div>
                          <strong>{{ sect.sect_name }}</strong>
                          <span>声望 <em :class="deltaClass(sect.reputation_delta)">{{ deltaText(sect.reputation_delta) }}</em></span>
                        </div>
                      </div>
                      <div class="sect-stat-row">
                        <span>突破 {{ sect.breakthrough_count }}</span>
                        <span>受伤 {{ sect.injured_count }}</span>
                        <span>恩怨 {{ sect.new_grudges }}</span>
                      </div>
                      <div class="sect-relations" v-if="sect.relation_deltas?.length">
                        <div v-for="rel in sect.relation_deltas.slice(0, 3)" :key="rel.sect_id">
                          <span>与{{ rel.sect_name }}</span>
                          <strong :class="deltaClass(rel.delta)">{{ deltaText(rel.delta) }}</strong>
                        </div>
                      </div>
                    </article>
                  </div>

                  <div v-else-if="activeTab === 'people'" class="fate-card-grid">
                    <article
                      v-for="item in keyPeople"
                      :key="`${item.event_id}-${item.actor}-${item.type}`"
                      class="fate-card"
                    >
                      <RoundPortrait
                        kind="disciple"
                        :id="item.actor_detail.portrait_id"
                        :name="item.actor_detail.name"
                        :size="58"
                        :frame="sectColor(item.actor_detail.sect_id)"
                        :preview="previewFor(item.actor_detail)"
                      />
                      <div>
                        <span>{{ item.label }} · {{ item.family_label }}</span>
                        <strong>{{ item.summary }}</strong>
                        <p>{{ item.cause }}</p>
                      </div>
                    </article>
                    <p v-if="!keyPeople.length" class="muted-copy">核心人物本轮无明显变化,普通弟子的经历已归档到各自人物志。</p>
                  </div>

                  <div v-else class="ripple-flow">
                    <article v-for="item in quietRipples" :key="item.id" class="ripple-row">
                      <span>{{ item.label }}</span>
                      <p>{{ item.summary }}</p>
                      <em>{{ item.actor_names?.join(' / ') }}</em>
                    </article>
                  </div>
                </section>

                <footer class="result-actions">
                  <span>普通推演已在后台结算并写入人物记忆。</span>
                  <button class="confirm-btn" @click="closeReplay">确认知晓</button>
                </footer>
              </section>
            </Transition>

            <section v-if="phase === 'error'" class="error-sheet">
              <strong>轶事未成卷</strong>
              <p>{{ errorText }}</p>
              <button class="confirm-btn" @click="closeReplay">返回主城</button>
            </section>
          </div>
        </section>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.next-round-dock {
  position: fixed;
  right: calc(92px + var(--safe-right));
  bottom: calc(28px + var(--safe-bottom));
  z-index: 170;
  pointer-events: none;
}

.next-round-btn {
  pointer-events: auto;
  width: 132px;
  height: 132px;
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, var(--accent), white 18%);
  background:
    radial-gradient(circle at 35% 25%, rgba(255,255,255,0.18), transparent 32%),
    radial-gradient(circle, color-mix(in srgb, var(--accent), transparent 16%), color-mix(in srgb, var(--accent), #0A0D18 72%) 72%);
  color: #1A1308;
  box-shadow: 0 18px 42px rgba(0,0,0,0.46), 0 0 26px color-mix(in srgb, var(--accent), transparent 38%);
  cursor: pointer;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 5px;
  font-family: 'STKaiti', 'KaiTi', serif;
  transition: transform 0.18s ease, filter 0.18s ease;
}

.next-round-btn span {
  font-size: 28px;
  font-weight: 900;
  letter-spacing: 0;
}

.next-round-btn small {
  color: rgba(20, 14, 6, 0.72);
  font-size: 12px;
  font-weight: 800;
}

.next-round-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  filter: brightness(1.08);
}

.next-round-btn:disabled {
  cursor: wait;
  opacity: 0.78;
}

.jianghu-replay {
  position: fixed;
  inset: 0;
  z-index: 800;
  color: #F4E8C8;
  font-family: 'STKaiti', 'KaiTi', serif;
}

.replay-backdrop {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(3, 6, 13, 0.94), rgba(8, 10, 18, 0.98)),
    url('/images/home-city-bg.png') center / cover no-repeat;
  filter: saturate(0.78);
}

.replay-shell {
  position: relative;
  z-index: 1;
  width: min(1220px, calc(100vw - 28px));
  height: min(900px, calc(100dvh - 28px));
  margin: 14px auto;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 14px;
  overflow: hidden;
}

.replay-topbar,
.jianghu-map,
.replay-aside,
.result-sheet,
.error-sheet {
  border: 1px solid rgba(255, 224, 163, 0.18);
  border-radius: 12px;
  background: rgba(8, 13, 24, 0.88);
  box-shadow: 0 22px 60px rgba(0,0,0,0.34);
}

.replay-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 14px 16px;
}

.replay-title span,
.phase-panel span,
.panel-head span,
.result-head span,
.incident-meta,
.focus-head span,
.sect-card-head span,
.fate-card span,
.ripple-row span,
.ripple-brief span {
  color: rgba(255, 224, 163, 0.72);
  font-size: 12px;
  letter-spacing: 1px;
}

.replay-title strong {
  display: block;
  margin-top: 3px;
  color: #FFE0A3;
  font-size: 25px;
  letter-spacing: 0;
}

.phase-track {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.phase-track span,
.result-tabs button {
  min-width: 58px;
  padding: 8px 10px;
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 8px;
  text-align: center;
  color: rgba(255,255,255,0.56);
  background: rgba(255,255,255,0.04);
  font-size: 13px;
}

.phase-track span.active,
.phase-track span.done,
.result-tabs button.active {
  color: #121018;
  border-color: color-mix(in srgb, var(--accent), white 16%);
  background: color-mix(in srgb, var(--accent), #FFE6B0 20%);
  box-shadow: 0 0 18px color-mix(in srgb, var(--accent), transparent 48%);
}

.replay-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 14px;
  min-height: 0;
  transition: opacity 0.24s ease, transform 0.24s ease;
}

.phase-result .replay-body {
  opacity: 0.22;
  transform: scale(0.985);
}

.jianghu-map {
  position: relative;
  min-height: 420px;
  overflow: hidden;
  background:
    linear-gradient(120deg, rgba(15, 33, 42, 0.92), rgba(14, 14, 30, 0.94)),
    url('/images/sect-bg-canglan.png') center / cover no-repeat;
}

.map-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px);
  background-size: 54px 54px;
  opacity: 0.34;
}

.map-river {
  position: absolute;
  left: 7%;
  right: 9%;
  top: 48%;
  height: 28%;
  border-top: 2px solid rgba(158, 207, 224, 0.24);
  border-bottom: 1px solid rgba(158, 207, 224, 0.14);
  transform: rotate(-8deg);
}

.sect-link {
  position: absolute;
  left: 28%;
  top: 50%;
  width: 44%;
  height: 2px;
  background: rgba(255,255,255,0.18);
  transform-origin: center;
  animation: link-flash 1.4s ease-in-out infinite;
}

.sect-link:nth-of-type(3n) { transform: rotate(22deg); }
.sect-link:nth-of-type(3n + 1) { transform: rotate(-18deg); }
.sect-link:nth-of-type(3n + 2) { transform: rotate(4deg); }
.sect-link.positive { background: rgba(255, 214, 116, 0.50); }
.sect-link.negative { background: rgba(255, 93, 93, 0.46); }

.sect-node {
  position: absolute;
  left: var(--x);
  top: var(--y);
  width: 128px;
  min-height: 102px;
  transform: translate(-50%, -50%);
  display: grid;
  place-items: center;
  gap: 5px;
  padding: 10px 8px;
  text-align: center;
  border: 1px solid color-mix(in srgb, var(--sect-color), transparent 36%);
  border-radius: 10px;
  background: rgba(8, 12, 22, 0.72);
  box-shadow: 0 12px 38px rgba(0,0,0,0.34);
}

.sect-node.hot {
  animation: node-rise 1.7s ease-in-out infinite;
}

.node-pulse {
  position: absolute;
  inset: calc(var(--heat) * -0.25);
  border: 1px solid color-mix(in srgb, var(--sect-color), transparent 20%);
  border-radius: 14px;
  opacity: 0;
  animation: pulse-border 1.8s ease-out infinite;
}

.sect-node strong {
  color: #FFF3CC;
  font-size: 16px;
  letter-spacing: 0;
}

.sect-node em,
.result-actions span {
  color: rgba(255,255,255,0.58);
  font-size: 12px;
  font-style: normal;
}

.time-sigil {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 168px;
  height: 168px;
  transform: translate(-50%, -50%);
  border: 1px solid color-mix(in srgb, var(--accent), transparent 38%);
  border-radius: 50%;
  background: rgba(7, 10, 18, 0.76);
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  text-align: center;
  box-shadow: inset 0 0 38px rgba(255,255,255,0.05), 0 0 46px color-mix(in srgb, var(--accent), transparent 62%);
  animation: sigil-breathe 2s ease-in-out infinite;
}

.time-sigil span {
  color: #FFE0A3;
  font-size: 30px;
  font-weight: 900;
}

.time-sigil strong {
  max-width: 132px;
  color: rgba(255,255,255,0.68);
  font-size: 13px;
  font-weight: 600;
}

.replay-aside {
  min-width: 0;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: auto;
}

.phase-panel,
.actor-panel,
.personal-panel,
.focus-card,
.lead-incident,
.relation-brief,
.ripple-brief,
.sect-change-card,
.fate-card,
.ripple-row {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  background: rgba(255,255,255,0.045);
}

.phase-panel,
.actor-panel {
  padding: 12px;
}

.phase-panel strong {
  display: block;
  margin-top: 8px;
  color: #FFF2CA;
  font-size: 18px;
  line-height: 1.55;
  letter-spacing: 0;
}

.panel-head,
.sect-pulse,
.sect-card-head,
.lead-actor {
  display: flex;
  align-items: center;
  gap: 10px;
}

.panel-head,
.focus-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.panel-head strong,
.focus-head strong {
  color: #FFE0A3;
}

.actor-stream {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.actor-chip {
  min-width: 0;
  display: grid;
  justify-items: center;
  gap: 5px;
  padding: 8px 4px;
  border: 1px solid color-mix(in srgb, var(--actor-color), transparent 60%);
  border-radius: 9px;
  background: rgba(0,0,0,0.16);
}

.actor-stream.running .actor-chip {
  animation: actor-flicker 1.1s ease-in-out infinite;
  animation-delay: var(--delay);
}

.actor-chip span,
.lead-actor span,
.people-strip span {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgba(255,255,255,0.66);
  font-size: 12px;
}

.personal-panel {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  padding: 10px;
}

.recover-stat {
  min-width: 0;
  padding: 9px 10px;
  border-radius: 8px;
  background: rgba(255,255,255,0.05);
}

.recover-stat span {
  display: block;
  color: rgba(255,255,255,0.54);
  font-size: 12px;
}

.recover-stat strong {
  display: block;
  margin-top: 3px;
  color: #fff;
  font-size: 17px;
}

.recover-stat.good strong { color: #87E5AF; }
.recover-stat.cool strong { color: #A8D8FF; }
.recover-stat.still strong { color: #FFE0A3; }

.result-sheet {
  position: absolute;
  left: 0;
  right: 0;
  top: 96px;
  bottom: 0;
  padding: 18px 20px;
  overflow: auto;
  background: linear-gradient(180deg, rgba(15, 22, 38, 0.985), rgba(7, 10, 18, 0.995));
}

.result-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 82px;
  gap: 16px;
  align-items: center;
  margin-bottom: 14px;
}

.result-head strong {
  display: block;
  margin-top: 4px;
  color: #FFE0A3;
  font-size: clamp(24px, 3vw, 38px);
  line-height: 1.15;
  letter-spacing: 0;
}

.result-head p {
  margin: 8px 0 0;
  max-width: 820px;
  color: rgba(255,255,255,0.70);
  line-height: 1.6;
}

.result-seal {
  width: 74px;
  height: 74px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #171018;
  background: color-mix(in srgb, var(--accent), #FFE6B0 28%);
  font-size: 18px;
  font-weight: 900;
  box-shadow: 0 0 24px color-mix(in srgb, var(--accent), transparent 55%);
}

.result-seal.quiet {
  color: rgba(255,255,255,0.72);
  background: rgba(255,255,255,0.08);
}

.result-focus {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(300px, 0.8fr);
  gap: 12px;
  margin-bottom: 12px;
}

.lead-incident {
  padding: 16px;
  border-top: 3px solid var(--accent);
  min-height: 230px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.lead-incident.quiet {
  border-top-color: rgba(255,255,255,0.22);
}

.incident-meta {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.incident-meta em {
  color: rgba(255,255,255,0.48);
  font-style: normal;
}

.lead-incident p {
  margin: 12px 0;
  color: #F7EBCB;
  font-size: clamp(17px, 2vw, 24px);
  line-height: 1.65;
}

.lead-actors {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.lead-actor {
  min-width: min(240px, 100%);
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(0,0,0,0.18);
}

.lead-actor strong,
.sect-pulse strong,
.sect-card-head strong {
  display: block;
  color: #FFF2CA;
}

.focus-column {
  display: grid;
  gap: 12px;
}

.focus-card {
  padding: 13px;
}

.sect-pulse-list {
  display: grid;
  gap: 8px;
}

.sect-pulse {
  padding: 7px;
  border-radius: 8px;
  background: rgba(255,255,255,0.04);
}

.sect-pulse span,
.sect-card-head span {
  color: rgba(255,255,255,0.58);
  font-size: 12px;
}

.positive {
  color: #88E2A8;
}

.negative {
  color: #FF8C8C;
}

.neutral {
  color: rgba(255,255,255,0.60);
}

.people-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.people-strip > div {
  min-width: 0;
  display: grid;
  justify-items: center;
  gap: 5px;
  padding: 8px 4px;
  border-radius: 9px;
  background: rgba(0,0,0,0.15);
}

.muted-copy {
  margin: 0;
  color: rgba(255,255,255,0.55);
  line-height: 1.6;
}

.result-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.result-tabs button {
  min-width: 86px;
  cursor: pointer;
}

.detail-panel {
  min-height: 190px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.relation-brief,
.ripple-brief,
.ripple-row {
  padding: 11px 12px;
}

.relation-faces {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.relation-faces > strong {
  min-width: 44px;
  text-align: center;
  padding: 4px 7px;
  border-radius: 999px;
  background: rgba(255,255,255,0.06);
}

.relation-brief p,
.ripple-brief p,
.ripple-row p,
.fate-card p {
  margin: 0;
  color: rgba(255,255,255,0.70);
  line-height: 1.55;
}

.sect-change-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 9px;
}

.sect-change-card {
  padding: 11px;
  border-top: 3px solid var(--sect-color);
}

.sect-stat-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 10px 0;
}

.sect-stat-row span {
  padding: 5px 7px;
  border-radius: 999px;
  background: rgba(255,255,255,0.055);
  color: rgba(255,255,255,0.62);
  font-size: 12px;
}

.sect-relations {
  display: grid;
  gap: 5px;
}

.sect-relations div {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  color: rgba(255,255,255,0.64);
  font-size: 12px;
}

.fate-card-grid {
  display: grid;
  gap: 8px;
}

.fate-card {
  display: flex;
  gap: 12px;
  padding: 11px;
  border-left: 3px solid var(--accent);
}

.fate-card strong {
  display: block;
  color: #FFF2CA;
  font-size: 15px;
  line-height: 1.45;
  letter-spacing: 0;
}

.fate-card p {
  margin-top: 5px;
  color: rgba(255,255,255,0.56);
}

.ripple-flow {
  display: grid;
  gap: 8px;
}

.ripple-row {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr) 150px;
  gap: 12px;
  align-items: center;
}

.ripple-row em {
  color: rgba(255,255,255,0.42);
  font-size: 12px;
  font-style: normal;
  text-align: right;
}

.result-actions {
  position: sticky;
  bottom: -18px;
  margin: 12px -20px -18px;
  padding: 12px 20px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: linear-gradient(180deg, rgba(7,10,18,0), rgba(7,10,18,0.98) 28%);
}

.confirm-btn {
  min-width: 138px;
  border: 1px solid color-mix(in srgb, var(--accent), white 16%);
  border-radius: 8px;
  padding: 11px 18px;
  background: color-mix(in srgb, var(--accent), #FFE6B0 18%);
  color: #151018;
  font-weight: 900;
  cursor: pointer;
}

.error-sheet {
  position: absolute;
  left: 50%;
  top: 50%;
  width: min(420px, calc(100vw - 40px));
  transform: translate(-50%, -50%);
  padding: 20px;
  text-align: center;
}

.error-sheet strong {
  color: #FFE0A3;
  font-size: 24px;
}

.error-sheet p {
  color: rgba(255,255,255,0.68);
  line-height: 1.6;
}

.jianghu-replay-enter-active,
.jianghu-replay-leave-active,
.result-rise-enter-active,
.result-rise-leave-active {
  transition: opacity 0.24s ease, transform 0.24s ease;
}

.jianghu-replay-enter-from,
.jianghu-replay-leave-to {
  opacity: 0;
}

.result-rise-enter-from,
.result-rise-leave-to {
  opacity: 0;
  transform: translateY(18px);
}

@keyframes sigil-breathe {
  0%, 100% { transform: translate(-50%, -50%) scale(1); }
  50% { transform: translate(-50%, -50%) scale(1.035); }
}

@keyframes node-rise {
  0%, 100% { transform: translate(-50%, -50%) translateY(0); }
  50% { transform: translate(-50%, -50%) translateY(-4px); }
}

@keyframes pulse-border {
  0% { opacity: 0.72; transform: scale(0.88); }
  100% { opacity: 0; transform: scale(1.18); }
}

@keyframes actor-flicker {
  0%, 100% { transform: translateY(0); filter: brightness(1); }
  50% { transform: translateY(-5px); filter: brightness(1.24); }
}

@keyframes link-flash {
  0%, 100% { opacity: 0.18; }
  50% { opacity: 0.72; }
}

@media (max-width: 980px) {
  .replay-shell {
    height: calc(100dvh - 20px);
    width: calc(100vw - 20px);
    margin: 10px auto;
  }
  .replay-body,
  .result-focus {
    grid-template-columns: 1fr;
  }
  .jianghu-map {
    min-height: 430px;
  }
  .result-sheet {
    top: 88px;
  }
  .sect-change-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .next-round-dock {
    right: calc(78px + var(--safe-right));
    bottom: calc(var(--mobile-bottom-nav-h) + 18px + var(--safe-bottom));
  }
  .next-round-btn {
    width: 104px;
    height: 104px;
  }
  .next-round-btn span {
    font-size: 23px;
  }
  .replay-topbar,
  .result-head,
  .overview-grid {
    grid-template-columns: 1fr;
  }
  .phase-track {
    justify-content: start;
  }
  .jianghu-map {
    min-height: 390px;
  }
  .sect-node {
    width: 104px;
    min-height: 92px;
  }
  .sect-node strong {
    font-size: 14px;
  }
  .time-sigil {
    width: 132px;
    height: 132px;
  }
  .time-sigil span {
    font-size: 24px;
  }
  .sect-change-grid {
    grid-template-columns: 1fr;
  }
  .ripple-row {
    grid-template-columns: 1fr;
    gap: 4px;
  }
  .ripple-row em {
    text-align: left;
  }
  .result-actions {
    align-items: stretch;
    flex-direction: column;
  }
}

@media (orientation: landscape) and (max-height: 560px) {
  .next-round-dock {
    right: calc(14px + var(--safe-right));
    bottom: calc(14px + var(--safe-bottom));
  }
  .next-round-btn {
    width: 92px;
    height: 92px;
  }
  .replay-shell {
    height: calc(100dvh - 12px);
    margin: 6px auto;
  }
}
</style>
