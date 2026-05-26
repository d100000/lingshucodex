<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage, useDialog } from 'naive-ui'
import { characterApi, exploreApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'
import { getSectTheme, getSectCssVars } from '../config/sectTheme.js'
import Logo from '../components/Logo.vue'
import ByokSettings from '../components/ByokSettings.vue'
import SectBackground from '../components/SectBackground.vue'
import DailyCard from '../components/DailyCard.vue'
import CultivationQueueBar from '../components/CultivationQueueBar.vue'
import WorldNextRoundButton from '../components/WorldNextRoundButton.vue'
import ItemIcon from '../components/ItemIcon.vue'
import SectFlag from '../components/SectFlag.vue'
import { prettifyItem } from '../utils/items.js'
import { formatNum } from '../utils/format.js'
import { openCharacterPreview, playerPreview } from '../utils/characterPreview.js'

const router = useRouter()
const route = useRoute()
const msg = useMessage()
const dialog = useDialog()
const game = useGameStore()

const character = ref(null)
const enemyTotal = ref(0)
const clansTotal = ref(0)
const showByokModal = ref(false)

const sectTheme = computed(() => getSectTheme(character.value?.sect))
const sectCssVars = computed(() => getSectCssVars(character.value?.sect))
const sectAccent = computed(() => sectTheme.value.accent)
const playerPortraitId = computed(() => `${character.value?.sect || 'canglan'}/${character.value?.realm || 'qi'}`)
const playerPortraitSrc = computed(() => `/images/portraits/players/${playerPortraitId.value}.png`)
const nextCultivation = computed(() => character.value ? (character.value.level + 1) * 100 : 0)
const hpPct = computed(() => {
  if (!character.value?.max_hp) return 0
  return Math.min(100, Math.round(character.value.hp / character.value.max_hp * 100))
})
const qiPct = computed(() => {
  if (!character.value?.max_qi) return 0
  return Math.min(100, Math.round(character.value.qi / character.value.max_qi * 100))
})
const cultivationPct = computed(() => {
  if (!character.value || !nextCultivation.value) return 0
  return Math.min(100, Math.round(character.value.exp / nextCultivation.value * 100))
})
const fatiguePct = computed(() => {
  if (!character.value) return 0
  const max = character.value.max_fatigue || 80
  return Math.min(100, Math.round((character.value.fatigue || 0) / max * 100))
})
const fatigueTone = computed(() => {
  if (fatiguePct.value < 40) return '#52B788'
  if (fatiguePct.value < 70) return '#FFB454'
  return '#C03F3F'
})
// ★ 8 属性雷达数据(八边形)
const ATTR_KEYS = ['str','qi','vit','agi','wis','end','fate','ins']
const ATTR_META = {
  str: { name:'力', icon:'🥊', fullName:'力量·刚', detail:'物理攻击力根基,力量越高,每次出招的直接伤害越大。以武入道者必重此项。', effect:'每点+2%物理伤害' },
  qi:  { name:'元', icon:'💧', fullName:'元气·源', detail:'灵气上限与回复速度。元气充沛者可连续施展高阶招式而不枯竭。', effect:'每点+3%灵气上限' },
  vit: { name:'躯', icon:'🛡️', fullName:'体魄·命', detail:'肉身根基,决定生命上限与容错。体魄高者在苦战中有更大的生存空间。', effect:'每点+3%生命上限' },
  agi: { name:'敏', icon:'🌪️', fullName:'身法·灵', detail:'出手速度与闪避概率。身法高者先手出招,且有几率完全躲避攻击。', effect:'每点+2%速度/+1%闪避' },
  wis: { name:'意', icon:'👁️', fullName:'心意·明', detail:'暴击率与暴击伤害。心意通透者能洞察破绽,一击致命的直觉更敏锐。', effect:'每点+1.5%暴击率' },
  end: { name:'韧', icon:'🪨', fullName:'坚韧·固', detail:'身心抗压极限。韧性越高,防御越强,疲劳上限也越高,可进行更长时间修行。', effect:'每点+2%防御' },
  fate:{ name:'缘', icon:'🍀', fullName:'机缘·运', detail:'冥冥之中的气运天数。缘分越高,奇遇概率越大,稀有掉落触发率提升。', effect:'每点+2%掉率' },
  ins: { name:'悟', icon:'📜', fullName:'悟性·道', detail:'领悟天地之道的资质。悟性越高,本命书命题与章节表现越灵动。', effect:'影响成章题材与叙事倾向' },
}

// ★ 机缘背景故事(与 Initiation.vue BLESS_LORE 一致)
const BLESS_LORE = {
  '天生勇武': { story: '降生之时天雷震地,百兽俯首。自幼力大无穷,徒手可搬山石。', effect: '永久提升物理攻击基础值' },
  '气血充盈': { story: '母胎中便受天地灵气滋养,血脉中流淌着远古战神的余韵。', effect: '战斗中物理伤害更高' },
  '肉身强横': { story: '骨骼精奇,筋脉宽阔,乃千年一遇的天生武体。', effect: '物理攻击根基强于常人' },
  '灵根纯净': { story: '天生灵根三品以上,修炼灵气事半功倍,聚灵速度远超同辈。', effect: '灵气池容量更大' },
  '聚灵之体': { story: '体质特殊,行走间便能自动吸纳天地灵气,如同行走的聚灵阵。', effect: '灵气上限与回复均提升' },
  '玄气贯顶': { story: '出生时一道玄光自天灵盖贯入,打通了灵气运行的主脉络。', effect: '灵气总量提升' },
  '筋骨厚实': { story: '自幼在山间攀岩涉水,风吹日晒锻造了铜筋铁骨。', effect: '生命上限提升,更能抗击打' },
  '百毒不侵': { story: '曾误食千年灵芝,体内自此生出一股化毒真气。', effect: '生命上限与抗性提升' },
  '龟息玄功': { story: '偶得一只万年玄龟传授吐纳之法,一息可续命百年。', effect: '极大提升生命与续航能力' },
  '身轻如燕': { story: '骨骼中空如飞禽,天生适合修习轻功身法,纵跃如风。', effect: '速度与闪避率提升' },
  '御风之灵': { story: '出生时狂风大作,风灵之气灌入经脉,从此与风同行。', effect: '速度基础值大幅提升' },
  '电掣之姿': { story: '母亲怀胎时被天雷击中而安然无恙,雷之迅捷融入血脉。', effect: '出手速度极快,先手优势明显' },
  '慧眼如炬': { story: '双目天生金瞳,能看穿幻术迷阵,洞察敌人破绽所在。', effect: '暴击率提升,更易发现弱点' },
  '心如明镜': { story: '心性通透,万念不侵。战斗中心境如止水,每一击都精准无比。', effect: '暴击判定更加稳定' },
  '天眼初开': { story: '右眼偶尔闪过金光,据说是天眼未完全觉醒的征兆。', effect: '暴击率与心法领悟力提升' },
  '铁骨铮铮': { story: '祖上曾以铁水淬体,骨骼中蕴含金属精华,刀枪难入。', effect: '防御力提升,受到伤害降低' },
  '金刚不坏': { story: '师门以特殊手法锻打全身穴位,达到近乎不坏之身。', effect: '防御基础值大幅提升' },
  '韧若苍松': { story: '如山间苍松,历千年风霜而不折。身心韧性远超常人。', effect: '防御与疲劳上限双重提升' },
  '七星福运': { story: '出生时北斗七星齐明,紫微星异动,命格中自带贵人运。', effect: '奇遇概率与稀有掉落率提升' },
  '莫名机缘': { story: '走在路上都能踩到灵石,练功时天降甘露。气运之强,令人嫉妒。', effect: '随机事件中获得正面结果的概率更高' },
  '因果相牵': { story: '前世修善因无数,今世得善果环绕。所到之处皆有机缘。', effect: '掉落与奇遇的品质更高' },
  '顿悟之灵': { story: '天生聪颖过人,闻道一次便能理解三分,修行如有神助。', effect: '本命书章节更易写出顿悟感' },
  '通天之资': { story: '百年一遇的修行资质,学什么会什么,领悟速度惊人。', effect: '成章题材更偏向破境与推演' },
  '笔下千秋': { story: '前世是文曲星转世,对文字与道理有超凡的理解力。', effect: '本命书叙事更容易沉淀因果' },
}
function getBlessLore(note) {
  return BLESS_LORE[note] || { story: '天降异象,冥冥之中自有定数。', effect: '基础属性永久提升' }
}

// ★ 物品 id → 中文,统一走全局字典(util/items.js)
//   不再维护本地表,新增物品后端 items.py 加一条 → 前端自动同步
function prettifyItemId(id) {
  if (!id) return ''
  return prettifyItem(id)
}

// ★ 12 种奇遇事件描述
const EVENT_META = {
  item_drop:      { label:'拾遗', icon:'🎁', desc:'路边拾得遗宝,天赐机缘。可获得各类材料与丹方。' },
  treasure:       { label:'机缘', icon:'✨', desc:'灵药秘境、上古遗经……真正的大机缘降临。' },
  reinforcement:  { label:'援军', icon:'🐯', desc:'妖兽呼朋唤友,地图新增同族强敌。需提高警惕!' },
  boss_ambush:    { label:'强袭', icon:'👹', desc:'强大Boss突然现身!极度凶险,但击败可获珍稀掉落。' },
  wanderer:       { label:'邂逅', icon:'🚶', desc:'偶遇云游散修,可能赠物、切磋或分享见闻。' },
  stampede:       { label:'兽潮', icon:'🌪️', desc:'野兽群奔,大地震颤。被卷入会受到伤害。' },
  ghost:          { label:'亡魂', icon:'👻', desc:'曾经击败的妖兽魂魄归来。可能复仇,也可能道谢赠礼。' },
  marketplace:    { label:'墟市', icon:'🏪', desc:'山中野市突现,神秘商贩售卖奇珍异宝。' },
  hermit:         { label:'高人', icon:'👴', desc:'深山高人现身传道授业,获得属性或修为加成。' },
  sect_messenger: { label:'宗令', icon:'📜', desc:'本门密使传令。影响门派友好度与声望。' },
  weather:        { label:'天象', icon:'⛈️', desc:'天地灵气潮汐异变,或增灵气,或损体魄。' },
  trial:          { label:'心魔', icon:'🌀', desc:'心魔试炼降临。高风险高回报,消耗生命换取大量修为。' },
}

// ★ 5 派门派详细描述
const FACTION_DESC = {
  canglan:  '以剑入道,深思求真。Claude系列模型驱动,追求暴击与悟性。',
  tianji:   '机关算尽,均衡万法。GPT系列模型驱动,追求全面与速度。',
  xuanji:   '灵气为本,悟性通天。DeepSeek系列驱动,追求灵气与领悟。',
  qingming: '韧如磐石,博学多闻。Gemini系列驱动,追求防御与学识。',
  yueyin:   '迅如鬼魅,运若天命。Mistral系列驱动,追求速度与运气。',
}
const ATTR_MAX = 20
const RC = { cx: 110, cy: 110, r: 75 }
const radarAxes = computed(() => ATTR_KEYS.map((k, i) => {
  const ang = (i * 45 - 90) * Math.PI / 180
  return {
    key: k,
    x: RC.cx + Math.cos(ang) * RC.r,
    y: RC.cy + Math.sin(ang) * RC.r,
    lx: RC.cx + Math.cos(ang) * (RC.r + 18),
    ly: RC.cy + Math.sin(ang) * (RC.r + 18),
    name: ATTR_META[k].name,
  }
}))
const radarOuter = computed(() => radarAxes.value.map(a => `${a.x},${a.y}`).join(' '))
function ringPath(scale) {
  return radarAxes.value.map(a => {
    const x = RC.cx + (a.x - RC.cx) * scale
    const y = RC.cy + (a.y - RC.cy) * scale
    return `${x},${y}`
  }).join(' ')
}
const radarData = computed(() => {
  if (!character.value?.attrs) return ''
  return ATTR_KEYS.map((k, i) => {
    const val = Math.min(1, (character.value.attrs[k] || 0) / ATTR_MAX)
    const ang = (i * 45 - 90) * Math.PI / 180
    return `${RC.cx + Math.cos(ang) * RC.r * val},${RC.cy + Math.sin(ang) * RC.r * val}`
  }).join(' ')
})

// ★ 5 派友好度
const SECT_LIST = [
  { id:'canglan', name:'沧澜剑派', color:'#D4A24C' },
  { id:'tianji',  name:'天机阁',   color:'#FFB454' },
  { id:'xuanji',  name:'玄机宗',   color:'#9B59B6' },
  { id:'qingming',name:'青冥派',   color:'#52B788' },
  { id:'yueyin',  name:'月隐宫',   color:'#B59CFF' },
]
function friendlyLabel(v) {
  if (v >= 80) return '生死之交'; if (v >= 50) return '挚友'
  if (v >= 20) return '友善';     if (v >= 0) return '陌路'
  if (v >= -20) return '冷淡';    if (v >= -50) return '敌对'
  return '仇深似海'
}

onMounted(async () => {
  // 路由跳来的错误提示
  if (route.query.error) {
    const errMsg = route.query.msg || ({
      battle_not_found: '该战斗不存在或已结束',
      battle_invalid_id: '战斗编号格式不正确',
      battle_invalid: '战斗已失效',
      ws_init_failed: '无法建立战斗连接',
      ws_error: '战斗连接异常',
      ws_lost: '战斗连接丢失',
      cards_load_failed: '加载招式失败',
    }[route.query.error] || '出现了一点问题')
    msg.warning(errMsg)
    router.replace({ path: '/home' })
  }

  try {
    const { data } = await characterApi.me()
    character.value = data
    game.setCharacter(data)
  } catch (e) {
    return router.replace({ path: '/onboarding', query: { reason: e.message } })
  }

  try {
    const { data } = await exploreApi.enemiesCount()
    enemyTotal.value = data.total
    clansTotal.value = data.clans_total
  } catch {}
})

function gotoInventory() {
  router.push('/inventory')
}
function gotoItems() {
  router.push('/items')
}
function gotoExplore() {
  router.push('/explore')
}
function gotoBosses() {
  router.push('/bosses')
}
function gotoBestiary() {
  router.push('/bestiary')
}
function gotoCraft() {
  router.push('/craft')
}
function gotoJournal() {
  router.push('/journal')
}
function gotoNovel() {
  router.push('/novel')
}
function gotoSkills() {
  router.push('/skills')
}
function resetCharacter() {
  dialog.warning({
    title: '转世重修',
    content: '确认放弃当前角色,重新选择门派吗?',
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: async () => {
      await characterApi.reset()
      game.clear()
      router.replace('/onboarding')
    },
  })
}

function openByokModal() {
  showByokModal.value = true
}

function openPlayerPreview() {
  openCharacterPreview(playerPreview(character.value || {}))
}

async function onByokUpdated(data) {
  // 刷新 character
  try {
    const resp = await characterApi.me()
    character.value = resp.data
    game.setCharacter(resp.data)
  } catch {}
}

function onWorldCharacterPatch(partial) {
  if (!character.value) return
  Object.assign(character.value, partial)
  game.patchCharacter(partial)
}
</script>

<template>
  <div v-if="character" class="home" :style="sectCssVars">
    <!-- ★ 门派背景图(中度遮罩,城景仍可见) -->
    <SectBackground :sect-id="character.sect" overlay="normal" :opacity="0.5" />

    <!-- 顶栏(配置按钮已下移到 hero-actions) -->
    <div class="brand-bar">
      <Logo :size="36" :text-size="18" />
      <div class="brand-right">
        <div class="brand-sub-tag">🏯 主 城 · 修真录</div>
        <CultivationQueueBar embedded />
      </div>
    </div>

    <!-- ★ 新主城面板:大头像横幅 + 3 栏(8 属性雷达 / 友好度 / 最近事件) -->
    <div class="hero-banner" :style="{ '--accent': sectAccent }">
      <button class="hero-portrait previewable" @click="openPlayerPreview" title="查看角色志">
        <img :src="playerPortraitSrc" :alt="character.name"
             @error="(e)=>{e.target.src='/images/portraits/sects/' + character.sect + '.png'}" />
        <div class="hero-glow"></div>
      </button>
      <SectFlag class="hero-flag" :sect-id="character.sect" :name="character.sect_name" :size="72" :radius="14" />
      <div class="hero-info">
        <div class="hero-tags">
          <span class="ht-tag">{{ character.sect_name }}</span>
          <span class="ht-tag accent">{{ character.realm_name }}</span>
          <span class="ht-tag accent">Lv.{{ character.level }}</span>
        </div>
        <h2 class="hero-name" :style="{ color: sectAccent }">{{ character.name }}</h2>
        <p class="hero-motto">{{ sectTheme.motto }}</p>
      </div>
      <div class="hero-actions">
        <button class="text-btn primary-text" @click="openByokModal">⚙️ 灵脉配置</button>
        <button class="text-btn" @click="resetCharacter">转世重修</button>
      </div>
    </div>

    <section class="protagonist-status" :style="{ '--accent': sectAccent, '--fatigue-color': fatigueTone }">
      <div class="ps-head">
        <div>
          <p class="ps-eyebrow">主角状态</p>
          <h3>{{ character.name }} · {{ character.realm_name }}</h3>
        </div>
        <div class="ps-total">
          <span>本命书总修为</span>
          <strong>{{ formatNum(character.cultivation_total || character.exp || 0) }}</strong>
        </div>
      </div>

      <div class="ps-body">
        <div class="ps-vitals">
          <div class="ps-bar-row">
            <div class="ps-label">气血</div>
            <div class="ps-bar"><div class="ps-fill hp" :style="{ width: hpPct + '%' }"></div></div>
            <div class="ps-value">{{ formatNum(character.hp) }} / {{ formatNum(character.max_hp) }}</div>
          </div>
          <div class="ps-bar-row">
            <div class="ps-label">灵气</div>
            <div class="ps-bar"><div class="ps-fill qi" :style="{ width: qiPct + '%' }"></div></div>
            <div class="ps-value">{{ formatNum(character.qi) }} / {{ formatNum(character.max_qi) }}</div>
          </div>
          <div class="ps-bar-row">
            <div class="ps-label">修为</div>
            <div class="ps-bar"><div class="ps-fill exp" :style="{ width: cultivationPct + '%' }"></div></div>
            <div class="ps-value">{{ formatNum(character.exp) }} / {{ formatNum(nextCultivation) }}</div>
          </div>
          <div class="ps-bar-row">
            <div class="ps-label">疲劳</div>
            <div class="ps-bar"><div class="ps-fill fatigue" :style="{ width: fatiguePct + '%' }"></div></div>
            <div class="ps-value">{{ formatNum(character.fatigue || 0) }} / {{ formatNum(character.max_fatigue || 80) }}</div>
          </div>
        </div>

        <div class="ps-combat">
          <div class="ps-stat">
            <span>攻</span>
            <strong>{{ formatNum(character.atk) }}</strong>
          </div>
          <div class="ps-stat">
            <span>防</span>
            <strong>{{ formatNum(character.def_) }}</strong>
          </div>
          <div class="ps-stat">
            <span>速</span>
            <strong>{{ formatNum(character.spd) }}</strong>
          </div>
          <div class="ps-stat">
            <span>暴</span>
            <strong>{{ Math.round((character.crit_rate || 0) * 100) }}%</strong>
          </div>
        </div>
      </div>
    </section>

    <section class="usage-dashboard" :style="{ '--accent': sectAccent }">
      <div class="ud-copy">
        <p>燃灵消耗</p>
        <h3>Token 即修行火候</h3>
        <span>五宗本地推演不燃灵;正传战斗、本命书续写与破境成章才会进入墨炉。</span>
      </div>
      <div class="ud-metrics">
        <div class="ud-item">
          <span>今日已燃</span>
          <strong>{{ formatNum(character.daily_token_used || 0) }}</strong>
          <div class="ud-bar unlimited"><i></i></div>
          <small>无上限</small>
        </div>
        <div class="ud-item">
          <span>本月已燃</span>
          <strong>{{ formatNum(character.monthly_token_used || 0) }}</strong>
          <div class="ud-bar unlimited"><i></i></div>
          <small>无上限</small>
        </div>
        <div class="ud-item">
          <span>累计燃灵</span>
          <strong>{{ formatNum(character.token_total || 0) }}</strong>
          <div class="ud-bar total"><i style="width: 100%"></i></div>
          <small>总修为 {{ formatNum(character.cultivation_total || character.exp || 0) }}</small>
        </div>
      </div>
    </section>

    <!-- ★ 三栏:雷达 + 友好度 + 最近事件 -->
    <div class="panel-3col">
      <!-- 8 属性雷达图 -->
      <div class="info-card">
        <h3 class="ic-title"><span class="ic-deco">⚯</span> 八大资质</h3>
        <svg viewBox="0 0 220 220" class="radar">
          <polygon v-for="(scale, i) in [0.25,0.5,0.75,1.0]" :key="i"
                   :points="ringPath(scale)" class="r-ring" />
          <line v-for="(a, i) in radarAxes" :key="i"
                :x1="110" :y1="110" :x2="a.x" :y2="a.y" class="r-axis" />
          <polygon :points="radarData" class="r-data"
                   :style="{ fill: sectAccent + '40', stroke: sectAccent }" />
          <circle v-for="(p, i) in radarData.split(' ')" :key="'pt'+i"
                  :cx="p.split(',')[0]" :cy="p.split(',')[1]"
                  r="3" :fill="sectTheme.glow" />
          <text v-for="(a, i) in radarAxes" :key="'l'+i"
                :x="a.lx" :y="a.ly" class="r-label"
                text-anchor="middle" dominant-baseline="middle">{{ a.name }}</text>
        </svg>
        <div class="attr-mini">
          <span v-for="k in ATTR_KEYS" :key="k" class="attr-mini-item">
            {{ ATTR_META[k].icon }} <strong>{{ character.attrs?.[k] || 0 }}</strong>
            <div class="home-attr-tooltip">
              <div class="hat-header">
                <span class="hat-icon">{{ ATTR_META[k].icon }}</span>
                <span class="hat-fullname">{{ ATTR_META[k].fullName }}</span>
              </div>
              <p class="hat-detail">{{ ATTR_META[k].detail }}</p>
              <div class="hat-effect">{{ ATTR_META[k].effect }}</div>
              <div class="hat-val">当前值: <strong>{{ character.attrs?.[k] || 0 }}</strong></div>
            </div>
          </span>
        </div>
      </div>

      <!-- 5 派友好度 -->
      <div class="info-card">
        <h3 class="ic-title"><span class="ic-deco">⚐</span> 江湖人缘</h3>
        <div class="faction-list">
          <div v-for="s in SECT_LIST" :key="s.id" class="faction-row">
            <span class="fr-name" :style="{ color: s.color }">
              <SectFlag :sect-id="s.id" :name="s.name" :size="26" :radius="6" />
              <span>{{ s.name }}</span>
              <div class="home-faction-tooltip">
                <div class="hft-header">
                  <span class="hft-name" :style="{ color: s.color }">{{ s.name }}</span>
                </div>
                <p class="hft-desc">{{ FACTION_DESC[s.id] }}</p>
                <div class="hft-relation">当前关系: <strong>{{ friendlyLabel(character.factions?.[s.id]||0) }}</strong> ({{ character.factions?.[s.id] || 0 }})</div>
              </div>
            </span>
            <div class="fr-bar">
              <div class="fr-fill"
                   :class="{ neg: (character.factions?.[s.id]||0) < 0 }"
                   :style="{
                     width: Math.abs(character.factions?.[s.id]||0) + '%',
                     background: (character.factions?.[s.id]||0) >= 0 ? s.color : '#C03F3F',
                     left: (character.factions?.[s.id]||0) >= 0 ? '50%' : 'auto',
                     right: (character.factions?.[s.id]||0) < 0 ? '50%' : 'auto',
                   }"></div>
              <div class="fr-axis"></div>
            </div>
            <span class="fr-value" :class="{ neg: (character.factions?.[s.id]||0) < 0 }">
              {{ character.factions?.[s.id] || 0 }}
            </span>
            <span class="fr-label">{{ friendlyLabel(character.factions?.[s.id]||0) }}</span>
          </div>
        </div>
      </div>

      <!-- 最近事件 -->
      <div class="info-card">
        <h3 class="ic-title"><span class="ic-deco">📜</span> 近期奇遇</h3>
        <div class="news-list" v-if="character.fortune_log?.length">
          <div v-for="(f, i) in character.fortune_log.slice(-5).reverse()" :key="i" class="news-item">
            <div class="ni-icon">{{ EVENT_META[f.type]?.icon || '🌟' }}</div>
            <div class="ni-body">
              <div class="ni-name">
                <!-- ★ 简化:type tag 自身带 title 提示,不再用 absolute tooltip 防止遮挡邻行 -->
                <span class="ni-type-tag" v-if="EVENT_META[f.type]"
                      :title="EVENT_META[f.type].desc">
                  {{ EVENT_META[f.type].icon }} {{ EVENT_META[f.type].label }}
                </span>
                {{ f.name }}
              </div>
              <div class="ni-effects">
                <span v-if="f.applied?.hp_delta" :class="['nie', f.applied.hp_delta>0?'good':'bad']">
                  HP{{ f.applied.hp_delta>0?'+':'' }}{{ f.applied.hp_delta }}
                </span>
                <span v-if="f.applied?.exp_delta" :class="['nie', f.applied.exp_delta>0?'good':'bad']">
                  修为{{ f.applied.exp_delta>0?'+':'' }}{{ f.applied.exp_delta }}
                </span>
                <span v-if="f.applied?.drop" class="nie good">
                  <ItemIcon
                    :icon-url="f.applied.drop_icon_url"
                    :emoji="f.applied.drop_icon"
                    :name="f.applied.drop_name || prettifyItemId(f.applied.drop)"
                    :size="18"
                    :radius="4"
                  />
                  {{ f.applied.drop_name || prettifyItemId(f.applied.drop) }}
                </span>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="news-empty">
          ✨ 入江湖去探索,自会偶遇奇遇<br/>
          <span class="ne-hint">在「修行地图」停留 60 秒,系统会自动召感天机</span>
        </div>

        <!-- 拜入机缘(永久) -->
        <div v-if="character.blessings?.length" class="news-bless">
          <div class="nb-title">📿 拜入机缘</div>
          <div class="nb-list">
            <span v-for="(b, i) in character.blessings.slice(0, 4)" :key="i" class="nb-chip">
              {{ b.attr_icon }} {{ b.note }} +{{ b.delta }}
              <div class="home-bless-tooltip">
                <div class="hbt-header">
                  <span class="hbt-icon">{{ b.attr_icon }}</span>
                  <span class="hbt-name">{{ b.note }}</span>
                  <span class="hbt-delta">{{ b.attr_name }} +{{ b.delta }}</span>
                </div>
                <p class="hbt-story">{{ getBlessLore(b.note).story }}</p>
                <div class="hbt-effect">{{ getBlessLore(b.note).effect }}</div>
              </div>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- ★ 今日修行令 -->
    <DailyCard />

    <!-- 修行主界面 - 入口 -->
    <h3 class="section-title">🌿 今日修行 · 选择去处</h3>

    <div class="entry-grid">
      <div class="entry main" @click="gotoExplore">
        <div class="entry-emoji">⚔️</div>
        <div class="entry-text">
          <h3>开始修行</h3>
          <p>进入修真界地图,主动寻找妖兽对战</p>
          <span class="entry-meta">已配置 {{ enemyTotal }} 种怪物 · {{ clansTotal }} 大族群</span>
        </div>
        <div class="entry-cta">前往 →</div>
      </div>

      <div class="entry" @click="gotoInventory">
        <div class="entry-emoji">🎒</div>
        <div class="entry-text">
          <h3>背包</h3>
          <p>查看战利品 · 装备 · 已收集材料</p>
        </div>
        <div class="entry-cta">查看 →</div>
      </div>

      <div class="entry" @click="gotoItems">
        <div class="entry-emoji">💊</div>
        <div class="entry-text">
          <h3>修行物品</h3>
          <p>丹药、心法、法宝、灵宝全集</p>
        </div>
        <div class="entry-cta">查阅 →</div>
      </div>

      <div class="entry" @click="gotoBosses">
        <div class="entry-emoji">👑</div>
        <div class="entry-text">
          <h3>修真名录</h3>
          <p>21 位 Boss · 18 大宗派 · 4 条故事线</p>
        </div>
        <div class="entry-cta">阅卷 →</div>
      </div>

      <div class="entry" @click="gotoBestiary">
        <div class="entry-emoji">📖</div>
        <div class="entry-text">
          <h3>山海经图鉴</h3>
          <p>记录遭遇过的灵兽妖邪</p>
        </div>
        <div class="entry-cta">翻阅 →</div>
      </div>

      <div class="entry" @click="gotoCraft">
        <div class="entry-emoji">🔥</div>
        <div class="entry-text">
          <h3>炼丹炼器</h3>
          <p>以材料合成丹药与法宝</p>
        </div>
        <div class="entry-cta">炼制 →</div>
      </div>

      <div class="entry" @click="gotoSkills">
        <div class="entry-emoji">📜</div>
        <div class="entry-text">
          <h3>修行心法</h3>
          <p>修炼招式 · 精进境界</p>
        </div>
        <div class="entry-cta">心法 →</div>
      </div>

      <div class="entry" @click="gotoNovel">
        <div class="entry-emoji">📖</div>
        <div class="entry-text">
          <h3>本命书</h3>
          <p>阅读燃灵成章后的个人修真小说</p>
        </div>
        <div class="entry-cta">开卷 →</div>
      </div>

      <div class="entry" @click="gotoJournal">
        <div class="entry-emoji">📜</div>
        <div class="entry-text">
          <h3>修行录</h3>
          <p>一路走来的修行足迹</p>
        </div>
        <div class="entry-cta">查阅 →</div>
      </div>
    </div>

    <!-- ★ 修行日志(战斗历史摘要) -->
    <div v-if="character.battle_history?.length" class="cultivation-log">
      <h3 class="section-title">📖 修行日志</h3>
      <div class="log-stats">
        <div class="ls-stat">
          <span class="ls-num">{{ character.battle_history.length }}</span>
          <span class="ls-label">历战</span>
        </div>
        <div class="ls-stat good">
          <span class="ls-num">{{ character.battle_history.filter(b => b.result === 'victory').length }}</span>
          <span class="ls-label">胜</span>
        </div>
        <div class="ls-stat bad">
          <span class="ls-num">{{ character.battle_history.filter(b => b.result !== 'victory').length }}</span>
          <span class="ls-label">败/退</span>
        </div>
        <div class="ls-stat">
          <span class="ls-num">{{ Math.round(character.battle_history.filter(b=>b.result==='victory').length / character.battle_history.length * 100) }}%</span>
          <span class="ls-label">胜率</span>
        </div>
      </div>
      <div class="log-recent">
        <div v-for="(b, i) in character.battle_history.slice(-5).reverse()" :key="i"
             class="lr-row" :class="b.result">
          <span class="lr-result">{{ b.result === 'victory' ? '✅' : b.result === 'defeat' ? '❌' : '🏃' }}</span>
          <span class="lr-enemy">{{ b.enemy_name }}</span>
          <span class="lr-rounds">{{ b.round_count }}回合</span>
        </div>
      </div>
    </div>

    <div class="hint-bar">
      <p>💡 提示:每场战斗都会消耗您的 API token,文学化叙事由 LLM 实时生成,推理深度=境界。</p>
    </div>

    <!-- 灵脉配置 modal -->
    <ByokSettings
      :show="showByokModal"
      :character="character"
      @close="showByokModal = false"
      @updated="onByokUpdated"
    />
    <WorldNextRoundButton :character="character" @character-patch="onWorldCharacterPatch" />

  </div>
</template>

<style scoped>
.home {
  max-width: 1100px; margin: 0 auto;
  padding: 20px 20px 48px;
  min-height: var(--app-svh);
  min-height: 100dvh;
  position: relative;
  isolation: isolate;
}

.home::before,
.home::after {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
}

.home::before {
  /* SectBackground 接管了主背景,这里只保留兜底深色 */
  z-index: -20;
  background: #050810;
}

.home::after {
  z-index: -1;
  background:
    radial-gradient(ellipse at 50% 0%, color-mix(in srgb, var(--sect-accent, #D4A24C) 10%, transparent) 0%, transparent 46%),
    radial-gradient(ellipse at center, color-mix(in srgb, var(--sect-primary, #1a1a2e) 28%, transparent) 0%, transparent 72%),
    linear-gradient(180deg, rgba(5, 7, 16, 0.20) 0%, rgba(5, 7, 16, 0.48) 42%, rgba(5, 7, 16, 0.78) 100%);
}

/* 头像随门派发光 */
.avatar-circle {
  box-shadow: 0 0 32px var(--sect-aura, transparent);
  animation: avatar-pulse 4s ease-in-out infinite;
}
@keyframes avatar-pulse {
  0%, 100% { box-shadow: 0 0 24px var(--sect-aura, transparent); }
  50%      { box-shadow: 0 0 48px var(--sect-aura, transparent); }
}

/* 主入口随门派变色 */
.entry.main {
  background: linear-gradient(135deg,
    color-mix(in srgb, var(--sect-accent, #D4A24C) 15%, transparent),
    color-mix(in srgb, var(--sect-accent, #D4A24C) 2%, transparent)) !important;
  border-color: color-mix(in srgb, var(--sect-accent, #D4A24C) 50%, transparent) !important;
}
.entry-text h3 { color: var(--sect-accent, #D4A24C) !important; }
.entry-cta { color: var(--sect-accent, #D4A24C) !important; }
.brand-bar {
  display: flex; justify-content: space-between; align-items: center;
  gap: 18px;
  padding: 6px 0 18px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  margin-bottom: 22px;
}
.brand-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  min-width: 0;
}
.text-btn {
  background: none; border: 1px solid rgba(255,255,255,0.15);
  color: #aaa; padding: 6px 14px; border-radius: 6px;
  cursor: pointer; font-size: 13px;
}
.text-btn:hover { color: #fff; border-color: #D4A24C; }
.text-btn.primary-text {
  background: rgba(212,162,76,0.08);
  border-color: rgba(212,162,76,0.4);
  color: #D4A24C;
}
.text-btn.primary-text:hover {
  background: rgba(212,162,76,0.15);
}

.player-panel {
  background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  padding: 20px 24px;
  margin-bottom: 28px;
}
.avatar-block {
  display: flex; gap: 18px; align-items: center;
  margin-bottom: 18px;
}
.avatar-circle {
  width: 72px; height: 72px; border-radius: 50%;
  background: rgba(0,0,0,0.3);
  border: 2px solid;
  display: flex; align-items: center; justify-content: center;
  font-size: 36px;
}
.info h2 { margin: 0; font-size: 22px; letter-spacing: 2px; }
.sect-line { margin: 4px 0 0; color: #888; font-size: 14px; letter-spacing: 1px; }

.stats-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
  margin-bottom: 14px;
}
.stat {
  background: rgba(0,0,0,0.2);
  padding: 10px 14px;
  border-radius: 8px;
}
.stat .label {
  display: block; font-size: 11px; color: #888;
  letter-spacing: 2px; margin-bottom: 4px;
}
.bar {
  height: 6px; background: rgba(0,0,0,0.5);
  border-radius: 3px; overflow: hidden;
  margin-bottom: 4px;
}
.bar-fill { height: 100%; transition: width 0.5s; }
.bar-fill.hp { background: linear-gradient(90deg, #C03F3F, #FF6B6B); }
.bar-fill.qi { background: linear-gradient(90deg, #3A6B6E, #7FC7E8); }
.bar-fill.exp { background: linear-gradient(90deg, #B58A3E, #FFE0A3); }
.stat .value { font-size: 12px; color: #ccc; font-family: 'SF Mono', monospace; }

.extra-stats {
  display: flex; gap: 10px; flex-wrap: wrap;
}
.ext {
  background: rgba(255,255,255,0.03);
  padding: 4px 12px; border-radius: 4px;
  font-size: 12px; color: #aaa;
}
.ext strong { color: #fff; margin-left: 6px; }

.section-title {
  font-size: 17px; color: #D4A24C;
  letter-spacing: 3px;
  margin: 0 0 16px;
}

/* ★ v2 战斗模式开关 */
.battle-mode-bar {
  display: flex; align-items: center; gap: 16px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(212, 162, 76, 0.2);
  border-radius: 10px;
  padding: 12px 18px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}
.mode-label {
  color: var(--sect-accent, #D4A24C);
  font-size: 13px;
  letter-spacing: 3px;
  font-weight: 600;
  flex-shrink: 0;
}
.mode-toggle {
  display: flex; gap: 8px;
}
.mode-btn {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #aaa;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  display: flex; flex-direction: column;
  align-items: flex-start; gap: 2px;
  font-family: inherit;
  transition: all 0.2s;
}
.mode-btn:hover {
  border-color: var(--sect-accent, #D4A24C);
  color: #fff;
}
.mode-btn.active {
  background: rgba(212, 162, 76, 0.12);
  border-color: var(--sect-accent, #D4A24C);
  color: var(--sect-accent, #D4A24C);
  box-shadow: 0 0 12px rgba(212, 162, 76, 0.25);
}
.mode-icon { font-size: 18px; }
.mode-name { font-size: 13px; font-weight: 600; letter-spacing: 1px; }
.mode-desc { font-size: 10px; color: #888; letter-spacing: 1px; }
.mode-btn.active .mode-desc { color: rgba(212, 162, 76, 0.8); }
.mode-hint {
  flex: 1; min-width: 200px;
  color: #888; font-size: 11px;
  background: rgba(127, 199, 232, 0.04);
  border-left: 2px solid #7FC7E8;
  padding: 6px 12px; border-radius: 4px;
  line-height: 1.6;
}

.entry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
  margin-bottom: 24px;
}
.entry {
  background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
  display: flex; flex-direction: column; gap: 10px;
  position: relative;
  overflow: hidden;
}
.entry:hover {
  transform: translateY(-3px);
  border-color: #D4A24C;
  box-shadow: 0 8px 28px rgba(212,162,76,0.18);
}
.entry.main {
  grid-column: 1 / -1;
  flex-direction: row;
  align-items: center;
  background: linear-gradient(135deg, rgba(212,162,76,0.12), rgba(212,162,76,0.02));
  border-color: rgba(212,162,76,0.45);
  position: relative;
  overflow: hidden;
  /* 整体光晕脉冲,1.6s 一次,持续提示用户点击 */
  animation: cta-pulse 1.6s ease-in-out infinite;
}

/* 流光扫过 — 利用伪元素叠加,从左到右扫一道金光 */
.entry.main::before {
  content: '';
  position: absolute;
  top: 0; left: -100%;
  width: 50%; height: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 224, 163, 0.15) 50%,
    transparent 100%
  );
  animation: cta-sweep 2.8s ease-in-out infinite;
  pointer-events: none;
}

/* 鼠标悬停时停止动效(已经吸引到用户了),改用普通 hover */
.entry.main:hover {
  animation: none;
  border-color: #FFE0A3;
  transform: translateY(-4px);
  box-shadow: 0 12px 36px rgba(212, 162, 76, 0.45);
}
.entry.main:hover::before {
  animation: none;
}

@keyframes cta-pulse {
  0%, 100% {
    box-shadow:
      0 0 0 0 rgba(212, 162, 76, 0.5),
      0 0 24px rgba(212, 162, 76, 0.18);
    border-color: rgba(212, 162, 76, 0.45);
  }
  50% {
    box-shadow:
      0 0 0 8px rgba(212, 162, 76, 0),
      0 0 36px rgba(212, 162, 76, 0.45);
    border-color: rgba(255, 224, 163, 0.85);
  }
}

@keyframes cta-sweep {
  0%   { left: -50%; }
  100% { left: 150%; }
}

.entry-emoji { font-size: 44px; }
.entry.main .entry-emoji {
  font-size: 60px;
  /* emoji 上下浮动,3s 一个周期 */
  animation: emoji-float 2.4s ease-in-out infinite;
  filter: drop-shadow(0 0 12px rgba(212, 162, 76, 0.5));
}

@keyframes emoji-float {
  0%, 100% { transform: translateY(0) rotate(0); }
  50%      { transform: translateY(-6px) rotate(-3deg); }
}
.entry-text { flex: 1; }
.entry-text h3 { margin: 0 0 4px; font-size: 17px; color: #D4A24C; letter-spacing: 2px; }
.entry-text p { margin: 0; font-size: 13px; color: #bbb; line-height: 1.6; }
.entry-meta {
  display: inline-block; margin-top: 6px;
  font-size: 11px; color: #7FC7E8;
  background: rgba(127,199,232,0.05);
  padding: 2px 8px; border-radius: 3px;
}
.entry-cta {
  color: #D4A24C; font-size: 13px;
  letter-spacing: 2px; white-space: nowrap;
}

/* 主入口的 CTA 加箭头滑动效果 + 字体放大 */
.entry.main .entry-cta {
  font-size: 15px;
  font-weight: 600;
  color: #FFE0A3;
  text-shadow: 0 0 12px rgba(212, 162, 76, 0.5);
  /* 箭头水平滑动 */
  animation: cta-arrow 1.4s ease-in-out infinite;
  padding-right: 4px;
}
.entry.main:hover .entry-cta {
  animation: none;
  transform: translateX(8px);
  transition: transform 0.2s;
}

@keyframes cta-arrow {
  0%, 100% { transform: translateX(0); opacity: 0.85; }
  50%      { transform: translateX(6px); opacity: 1; }
}

.hint-bar {
  background: rgba(127,199,232,0.05);
  border-left: 3px solid #7FC7E8;
  padding: 10px 16px;
  border-radius: 4px;
  font-size: 12px;
  color: #aaa;
}
.hint-bar p { margin: 0; line-height: 1.7; }

.usage-dashboard {
  display: grid;
  grid-template-columns: minmax(220px, 0.72fr) 1fr;
  gap: 14px;
  align-items: stretch;
  margin: 0 0 20px;
  padding: 14px;
  border: 1px solid color-mix(in srgb, var(--accent, #D4A24C) 30%, transparent);
  border-radius: 10px;
  background:
    radial-gradient(ellipse at left, color-mix(in srgb, var(--accent, #D4A24C) 12%, transparent), transparent 62%),
    linear-gradient(180deg, rgba(15, 18, 30, 0.78), rgba(8, 8, 18, 0.92));
}

.ud-copy {
  display: grid;
  align-content: center;
  gap: 6px;
  padding: 6px 8px;
}

.ud-copy p {
  margin: 0;
  color: #7FC7E8;
  font-size: 12px;
  letter-spacing: 3px;
}

.ud-copy h3 {
  margin: 0;
  color: #FFE0A3;
  font-size: 18px;
  letter-spacing: 2px;
}

.ud-copy span {
  color: #AEB7C8;
  font-size: 12px;
  line-height: 1.7;
}

.ud-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.ud-item {
  min-width: 0;
  padding: 12px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(0,0,0,0.22);
}

.ud-item span,
.ud-item small {
  display: block;
  color: #8E98AA;
  font-size: 11px;
}

.ud-item strong {
  display: block;
  margin: 5px 0 8px;
  color: #FFE0A3;
  font-size: 20px;
  font-family: "SF Mono", Consolas, monospace;
}

.ud-bar {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  margin-bottom: 6px;
}

.ud-bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #7FC7E8, var(--accent, #D4A24C));
}

.ud-bar.total i {
  background: linear-gradient(90deg, #D4A24C, #FFE0A3);
}

.ud-bar.unlimited i {
  width: 100%;
  opacity: 0.72;
}

/* ═══════════════ ★ v3 主城精致面板 ═══════════════ */
.brand-sub-tag {
  flex: 0 0 auto;
  color: #D4A24C;
  font-size: 13px;
  letter-spacing: 6px;
  text-shadow: 0 0 12px rgba(212, 162, 76, 0.4);
  font-family: 'STKaiti', 'KaiTi', serif;
}

@media (max-width: 820px) {
  .brand-bar {
    flex-direction: column;
    align-items: stretch;
  }
  .brand-right {
    justify-content: space-between;
    align-items: center;
  }
  .brand-sub-tag {
    letter-spacing: 4px;
  }
}

@media (max-width: 640px) {
  .brand-right {
    flex-direction: column;
    align-items: stretch;
  }
  .brand-sub-tag {
    font-size: 12px;
  }
  .home {
    padding: calc(14px + var(--safe-top)) 14px calc(104px + var(--safe-bottom));
  }
  .usage-dashboard,
  .ud-metrics {
    grid-template-columns: 1fr;
  }
}

/* ── 大角色横幅 ── */
.hero-banner {
  display: grid;
  grid-template-columns: 130px 72px 1fr auto;
  gap: 24px;
  align-items: center;
  padding: 18px 24px;
  background:
    radial-gradient(ellipse at left, color-mix(in srgb, var(--accent, #D4A24C) 14%, transparent), transparent 60%),
    linear-gradient(180deg, rgba(20,15,8,0.85), rgba(8,5,2,0.95));
  border: 1px solid color-mix(in srgb, var(--accent, #D4A24C) 35%, transparent);
  border-radius: 14px;
  margin-bottom: 18px;
  position: relative;
  overflow: hidden;
}
.hero-banner::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, transparent, var(--accent, #D4A24C), transparent);
}
.hero-portrait {
  position: relative;
  width: 130px; height: 180px;
  border-radius: 10px;
  overflow: hidden;
  border: 2px solid var(--accent, #D4A24C);
  padding: 0;
  cursor: pointer;
  box-shadow:
    0 4px 20px rgba(0,0,0,0.6),
    0 0 24px color-mix(in srgb, var(--accent, #D4A24C) 30%, transparent);
}
.hero-portrait.previewable {
  background: transparent;
}
.hero-portrait.previewable::after {
  content: '查看角色志';
  position: absolute;
  left: 8px;
  right: 8px;
  bottom: 8px;
  height: 26px;
  display: grid;
  place-items: center;
  background: rgba(8,8,18,0.72);
  border: 1px solid color-mix(in srgb, var(--accent, #D4A24C) 55%, transparent);
  color: #FFE0A3;
  font-size: 12px;
  letter-spacing: 2px;
  opacity: 0;
  transform: translateY(5px);
  transition: opacity 0.18s, transform 0.18s;
}
.hero-portrait.previewable:hover::after {
  opacity: 1;
  transform: translateY(0);
}
.hero-portrait img {
  width: 100%; height: 100%;
  object-fit: cover;
  object-position: center top;
}
.hero-glow {
  position: absolute; inset: 0;
  background: radial-gradient(ellipse at bottom, color-mix(in srgb, var(--accent, #D4A24C) 25%, transparent), transparent 60%);
  pointer-events: none;
}
.hero-info { display: flex; flex-direction: column; gap: 8px; }
.hero-flag { align-self: center; }
.hero-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.ht-tag {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  color: #aaa;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  letter-spacing: 1px;
}
.ht-tag.accent {
  background: color-mix(in srgb, var(--accent, #D4A24C) 14%, transparent);
  border-color: color-mix(in srgb, var(--accent, #D4A24C) 40%, transparent);
  color: var(--accent, #D4A24C);
}
.hero-name {
  margin: 0;
  font-family: 'STKaiti', 'KaiTi', serif;
  font-size: 28px;
  letter-spacing: 6px;
  text-shadow: 0 0 18px color-mix(in srgb, var(--accent) 60%, transparent);
}
.hero-motto {
  margin: 0;
  font-size: 13px;
  color: #aaa;
  letter-spacing: 2px;
  font-style: italic;
  font-family: 'STKaiti', serif;
}
.hero-actions { display: flex; flex-direction: column; gap: 8px; }

/* ── 主角状态模块 ── */
.protagonist-status {
  margin-bottom: 18px;
  padding: 16px 18px;
  background:
    linear-gradient(180deg, rgba(20,15,8,0.72), rgba(8,5,2,0.9)),
    radial-gradient(ellipse at right, color-mix(in srgb, var(--accent, #D4A24C) 10%, transparent), transparent 62%);
  border: 1px solid color-mix(in srgb, var(--accent, #D4A24C) 28%, transparent);
  border-radius: 10px;
  position: relative;
}
.protagonist-status::before {
  content: '';
  position: absolute;
  left: 18px;
  right: 18px;
  top: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent, #D4A24C), transparent);
}
.ps-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 14px;
}
.ps-eyebrow {
  margin: 0 0 4px;
  color: var(--accent, #D4A24C);
  font-size: 11px;
  letter-spacing: 4px;
  font-family: 'STKaiti', 'KaiTi', serif;
}
.ps-head h3 {
  margin: 0;
  color: #FFE0A3;
  font-size: 17px;
  letter-spacing: 3px;
  font-family: 'STKaiti', 'KaiTi', serif;
}
.ps-total {
  text-align: right;
  min-width: 140px;
}
.ps-total span {
  display: block;
  color: #888;
  font-size: 11px;
  letter-spacing: 2px;
}
.ps-total strong {
  display: block;
  margin-top: 2px;
  color: var(--accent, #D4A24C);
  font-size: 20px;
  font-family: 'SF Mono', monospace;
}
.ps-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 18px;
  align-items: center;
}
.ps-vitals {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 16px;
}
.ps-bar-row {
  display: grid;
  grid-template-columns: 44px minmax(80px, 1fr) auto;
  gap: 10px;
  align-items: center;
  min-width: 0;
}
.ps-label {
  color: #B8C7E0;
  font-size: 12px;
  letter-spacing: 2px;
}
.ps-bar {
  height: 9px;
  min-width: 0;
  background: rgba(0,0,0,0.55);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 5px;
  overflow: hidden;
}
.ps-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.35s ease;
}
.ps-fill.hp { background: linear-gradient(90deg, #C03F3F, #FF6B6B); }
.ps-fill.qi { background: linear-gradient(90deg, #3A6B6E, #7FC7E8); }
.ps-fill.exp { background: linear-gradient(90deg, #B58A3E, #FFE0A3); }
.ps-fill.fatigue { background: var(--fatigue-color, #52B788); }
.ps-value {
  color: #ccc;
  font-family: 'SF Mono', monospace;
  font-size: 11px;
  white-space: nowrap;
}
.ps-combat {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.ps-stat {
  min-width: 0;
  padding: 8px 10px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 6px;
  text-align: center;
}
.ps-stat span {
  display: block;
  color: #888;
  font-size: 11px;
  letter-spacing: 2px;
}
.ps-stat strong {
  display: block;
  margin-top: 3px;
  color: #FFE0A3;
  font-family: 'SF Mono', monospace;
  font-size: 15px;
  white-space: nowrap;
}

/* ── 三栏 info-card ── */
.panel-3col {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 14px;
  margin-bottom: 24px;
}
@media (max-width: 980px) {
  .panel-3col { grid-template-columns: 1fr; }
  .ps-body { grid-template-columns: 1fr; }
  .ps-combat { max-width: 420px; }
}
@media (max-width: 640px) {
  .hero-banner {
    grid-template-columns: 92px 48px 1fr;
    gap: 14px;
    padding: 14px;
  }
  .hero-portrait {
    width: 92px;
    height: 128px;
  }
  .hero-actions {
    grid-column: 1 / -1;
    flex-direction: row;
    flex-wrap: wrap;
  }
  .hero-flag {
    width: 48px !important;
    height: 48px !important;
    min-width: 48px !important;
  }
  .ps-head {
    flex-direction: column;
  }
  .ps-total {
    min-width: 0;
    text-align: left;
  }
  .ps-vitals {
    grid-template-columns: 1fr;
  }
  .ps-bar-row {
    grid-template-columns: 40px minmax(80px, 1fr);
  }
  .ps-value {
    grid-column: 2;
  }
  .ps-combat {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (orientation: landscape) and (max-height: 520px) {
  .home {
    max-width: none;
    padding: calc(12px + var(--safe-top)) calc(14px + var(--safe-right)) calc(18px + var(--safe-bottom)) calc(86px + var(--safe-left));
  }
  .hero-banner {
    grid-template-columns: 100px 52px 1fr auto;
    padding: 12px 14px;
  }
  .hero-portrait {
    width: 100px;
    height: 132px;
  }
  .hero-flag {
    width: 52px !important;
    height: 52px !important;
    min-width: 52px !important;
  }
  .panel-3col {
    grid-template-columns: repeat(3, minmax(220px, 1fr));
    overflow-x: auto;
  }
}
.info-card {
  background: linear-gradient(180deg, rgba(20,15,8,0.75), rgba(8,5,2,0.92));
  border: 1px solid rgba(212,162,76,0.2);
  border-radius: 10px;
  padding: 14px 16px;
  position: relative;
}
.info-card::before {
  content: ''; position: absolute; top: 0; left: 10%; right: 10%; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(212,162,76,0.6), transparent);
}
.ic-title {
  font-size: 13px;
  color: #D4A24C;
  letter-spacing: 4px;
  margin: 0 0 12px;
  font-family: 'STKaiti', serif;
  display: flex; align-items: center; gap: 6px;
}
.ic-deco { color: #FFE0A3; text-shadow: 0 0 8px #D4A24C; }

/* ── 雷达图 ── */
.radar { width: 100%; max-width: 220px; height: 220px; display: block; margin: 0 auto; }
.r-ring { fill: none; stroke: rgba(212,162,76,0.18); stroke-width: 1; }
.r-axis { stroke: rgba(212,162,76,0.25); stroke-dasharray: 2 3; }
.r-data { stroke-width: 2; filter: drop-shadow(0 0 6px currentColor); }
.r-label { fill: #D4A24C; font-size: 12px; font-family: 'STKaiti', serif; }
.attr-mini {
  display: flex; flex-wrap: wrap; gap: 5px;
  justify-content: center;
  margin-top: 8px;
  font-size: 11px;
}
.attr-mini span {
  background: rgba(212,162,76,0.08);
  border: 1px solid rgba(212,162,76,0.2);
  padding: 2px 7px;
  border-radius: 4px;
  color: #aaa;
}
.attr-mini strong { color: #FFE0A3; margin-left: 2px; }

/* ── 友好度 ── */
.faction-list { display: flex; flex-direction: column; gap: 10px; }
.faction-row {
  display: grid;
  grid-template-columns: 112px 1fr 32px 50px;
  gap: 8px;
  align-items: center;
  font-size: 11px;
}
.fr-name {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-family: 'STKaiti', serif;
  font-size: 12px;
  letter-spacing: 1px;
  font-weight: 600;
}
.fr-bar {
  position: relative;
  height: 8px;
  background: rgba(0,0,0,0.4);
  border-radius: 4px;
  overflow: hidden;
}
.fr-axis {
  position: absolute;
  top: 0; bottom: 0;
  left: 50%;
  width: 1px;
  background: rgba(255,255,255,0.2);
}
.fr-fill {
  position: absolute;
  top: 0; bottom: 0;
  border-radius: 3px;
  transition: width 0.5s, left 0.5s, right 0.5s;
}
.fr-value {
  text-align: right;
  font-family: 'SF Mono', monospace;
  color: #95D5B2;
  font-weight: 600;
}
.fr-value.neg { color: #FF8888; }
.fr-label { color: #888; font-size: 10px; letter-spacing: 1px; }

/* ── 近期事件 ── */
.news-list { display: flex; flex-direction: column; gap: 8px; max-height: 200px; overflow-y: auto; }
.news-item {
  display: flex; gap: 10px;
  padding: 8px 10px;
  background: rgba(255,255,255,0.03);
  border-left: 2px solid #D4A24C;
  border-radius: 4px;
}
.ni-icon { font-size: 18px; }
.ni-body { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.ni-name { font-size: 12px; color: #FFE0A3; letter-spacing: 1px; font-family: 'STKaiti', serif; }
.ni-effects { display: flex; flex-wrap: wrap; gap: 4px; }
.nie {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
}
.nie.good { color: #95D5B2; background: rgba(82,183,136,0.12); }
.nie.bad  { color: #FF8888; background: rgba(192,63,63,0.12); }

.news-empty {
  color: #888; font-size: 12px;
  text-align: center;
  padding: 24px 10px;
  letter-spacing: 1px;
  font-family: 'STKaiti', serif;
}
.ne-hint { color: #555; font-size: 11px; }

.news-bless { margin-top: 12px; padding-top: 10px; border-top: 1px dashed rgba(212,162,76,0.25); }
.nb-title { font-size: 11px; color: #D4A24C; letter-spacing: 3px; margin-bottom: 6px; }
.nb-list { display: flex; flex-wrap: wrap; gap: 4px; }
.nb-chip {
  position: relative;
  cursor: default;
  background: rgba(212,162,76,0.12);
  border: 1px solid rgba(212,162,76,0.3);
  color: #FFE0A3;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 10px;
}

/* ★ 修行日志 */
.cultivation-log {
  margin-top: 28px;
  padding: 16px 20px;
  background: rgba(8, 12, 24, 0.7);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
}
.log-stats {
  display: flex; gap: 16px; justify-content: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.ls-stat { text-align: center; }
.ls-num { display: block; font-size: 22px; font-weight: 700; color: #D4A24C; }
.ls-stat.good .ls-num { color: #52B788; }
.ls-stat.bad .ls-num { color: #C03F3F; }
.ls-label { font-size: 11px; color: #888; letter-spacing: 1px; }
.log-recent { display: flex; flex-direction: column; gap: 6px; }
.lr-row {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 12px;
  background: rgba(255,255,255,0.02);
  border-radius: 6px;
  font-size: 13px;
}
.lr-row.victory { border-left: 3px solid #52B788; }
.lr-row.defeat  { border-left: 3px solid #C03F3F; }
.lr-row.flee    { border-left: 3px solid #FFB454; }
.lr-result { font-size: 16px; }
.lr-enemy { flex: 1; color: #ddd; }
.lr-rounds { color: #888; font-size: 11px; }

/* ═══════════════ ★ Hover Tooltips 共享基础样式 ═══════════════ */

/* ── 1. 属性 tooltip (雷达图下方 attr-mini) ── */
.attr-mini-item {
  position: relative;
  cursor: default;
}
.home-attr-tooltip {
  position: absolute;
  bottom: calc(100% + 12px);
  left: 50%;
  transform: translateX(-50%) translateY(6px);
  width: 220px;
  background: linear-gradient(180deg, rgba(25, 18, 8, 0.98), rgba(10, 6, 2, 0.98));
  border: 1px solid rgba(212, 162, 76, 0.5);
  border-radius: 10px;
  padding: 12px 14px;
  text-align: left;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.8), 0 0 20px rgba(212, 162, 76, 0.15);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.25s, transform 0.25s;
  z-index: 50;
}
.home-attr-tooltip::after {
  content: '';
  position: absolute;
  bottom: -7px;
  left: 50%;
  width: 12px; height: 12px;
  background: rgba(10, 6, 2, 0.98);
  border-right: 1px solid rgba(212, 162, 76, 0.5);
  border-bottom: 1px solid rgba(212, 162, 76, 0.5);
  transform: translateX(-50%) rotate(45deg);
}
.attr-mini-item:hover .home-attr-tooltip {
  opacity: 1;
  pointer-events: auto;
  transform: translateX(-50%) translateY(0);
}
.hat-header {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(212, 162, 76, 0.25);
}
.hat-icon { font-size: 18px; }
.hat-fullname {
  font-size: 13px;
  color: #FFE0A3;
  letter-spacing: 3px;
  font-weight: 600;
}
.hat-detail {
  margin: 0 0 8px;
  font-size: 11px;
  color: #ccc;
  line-height: 1.7;
  font-family: 'STKaiti', serif;
}
.hat-effect {
  font-size: 10px;
  color: #95D5B2;
  background: rgba(82, 183, 136, 0.1);
  border: 1px solid rgba(82, 183, 136, 0.25);
  border-radius: 4px;
  padding: 3px 7px;
  margin-bottom: 5px;
}
.hat-val {
  font-size: 10px;
  color: #aaa;
  text-align: right;
}
.hat-val strong {
  color: #FFE0A3;
  font-size: 13px;
  margin-left: 4px;
}

/* ── 2. 门派 tooltip (faction-row) ── */
.fr-name {
  position: relative;
  cursor: default;
}
.home-faction-tooltip {
  position: absolute;
  bottom: calc(100% + 12px);
  left: 0;
  transform: translateY(6px);
  width: 240px;
  background: linear-gradient(180deg, rgba(25, 18, 8, 0.98), rgba(10, 6, 2, 0.98));
  border: 1px solid rgba(212, 162, 76, 0.5);
  border-radius: 10px;
  padding: 12px 14px;
  text-align: left;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.8), 0 0 20px rgba(212, 162, 76, 0.15);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.25s, transform 0.25s;
  z-index: 50;
}
.home-faction-tooltip::after {
  content: '';
  position: absolute;
  bottom: -7px;
  left: 20px;
  width: 12px; height: 12px;
  background: rgba(10, 6, 2, 0.98);
  border-right: 1px solid rgba(212, 162, 76, 0.5);
  border-bottom: 1px solid rgba(212, 162, 76, 0.5);
  transform: rotate(45deg);
}
.fr-name:hover .home-faction-tooltip {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}
.hft-header {
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(212, 162, 76, 0.25);
}
.hft-name {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 3px;
}
.hft-desc {
  margin: 0 0 8px;
  font-size: 11px;
  color: #ccc;
  line-height: 1.7;
  font-family: 'STKaiti', serif;
}
.hft-relation {
  font-size: 10px;
  color: #aaa;
}
.hft-relation strong {
  color: #FFE0A3;
  margin-left: 4px;
}

/* ── 3. 奇遇事件 tooltip (fortune log news-item) ── */
.ni-name {
  position: relative;
  cursor: default;
}
.ni-type-tag {
  display: inline-block;
  font-size: 9px;
  color: #D4A24C;
  background: rgba(212, 162, 76, 0.15);
  border: 1px solid rgba(212, 162, 76, 0.3);
  padding: 1px 5px;
  border-radius: 3px;
  margin-right: 4px;
  letter-spacing: 1px;
}
/* ── ★ 奇遇类型 tag(改用原生 title 属性提示,不再用 absolute 浮窗,避免遮挡列表) ── */
.ni-type-tag {
  cursor: help;
}

/* ── 4. 机缘 tooltip (blessings nb-chip) ── */
.home-bless-tooltip {
  position: absolute;
  bottom: calc(100% + 12px);
  left: 50%;
  transform: translateX(-50%) translateY(6px);
  width: 260px;
  background: linear-gradient(180deg, rgba(25, 18, 8, 0.98), rgba(10, 6, 2, 0.98));
  border: 1px solid rgba(212, 162, 76, 0.5);
  border-radius: 10px;
  padding: 12px 14px;
  text-align: left;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.8), 0 0 20px rgba(212, 162, 76, 0.15);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.25s, transform 0.25s;
  z-index: 50;
}
.home-bless-tooltip::after {
  content: '';
  position: absolute;
  bottom: -7px;
  left: 50%;
  width: 12px; height: 12px;
  background: rgba(10, 6, 2, 0.98);
  border-right: 1px solid rgba(212, 162, 76, 0.5);
  border-bottom: 1px solid rgba(212, 162, 76, 0.5);
  transform: translateX(-50%) rotate(45deg);
}
.nb-chip:hover .home-bless-tooltip {
  opacity: 1;
  pointer-events: auto;
  transform: translateX(-50%) translateY(0);
}

@media (hover: none), (max-width: 640px) {
  .home-attr-tooltip,
  .home-faction-tooltip,
  .home-bless-tooltip {
    display: none;
  }
}

.hbt-header {
  display: flex; align-items: center; gap: 6px;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(212, 162, 76, 0.25);
}
.hbt-icon { font-size: 16px; }
.hbt-name {
  flex: 1;
  font-size: 13px;
  color: #FFE0A3;
  letter-spacing: 2px;
  font-weight: 600;
}
.hbt-delta {
  font-size: 10px;
  color: #95D5B2;
  background: rgba(82, 183, 136, 0.12);
  padding: 2px 6px;
  border-radius: 3px;
}
.hbt-story {
  margin: 0 0 8px;
  font-size: 11px;
  color: #ccc;
  line-height: 1.7;
  font-family: 'STKaiti', serif;
  font-style: italic;
}
.hbt-effect {
  font-size: 10px;
  color: #95D5B2;
  background: rgba(82, 183, 136, 0.1);
  border: 1px solid rgba(82, 183, 136, 0.25);
  border-radius: 4px;
  padding: 3px 7px;
}

</style>
