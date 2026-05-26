<!--
  Initiation.vue — 拜入师门 loading 仪式页
  时序:
    0s    背景揭示 + 师门徽记
    1s    "师承 XXX 派" 落下
    2s    8 属性骨架显示
    2.5s  逐个翻牌显示 attrs 值(0.4s 一个)
    +5s   显示拜入机缘(浮现)
    +2s   "成为 XX 派弟子" 确认按钮亮起
-->
<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { characterApi } from '../api/client.js'
import { useGameStore } from '../stores/game.js'

const router = useRouter()
const route = useRoute()
const msg = useMessage()
const game = useGameStore()

const sectId = route.params.sectId
const phase = ref('curtain')   // curtain → reveal → attrs → bless → done
const character = ref(null)
const showAttrs = ref([])  // 已揭示的 attr keys

const ATTR_KEYS = ['str','qi','vit','agi','wis','end','fate','ins']
const ATTR_META = {
  str: {
    name: '力', icon: '🥊', desc: '物理攻击力',
    fullName: '力量 · 刚',
    detail: '决定物理攻击的基础伤害。力量越高,每次出招造成的直接伤害越大。对以武入道的修行者尤为重要。',
    effect: '每点+2%物理伤害',
  },
  qi: {
    name: '元', icon: '💧', desc: '灵气上限',
    fullName: '元气 · 源',
    detail: '灵气是施展招式的根基。元气越高,可用灵气池越大,能连续施展更多高阶招式而不枯竭。',
    effect: '每点+3%灵气上限',
  },
  vit: {
    name: '躯', icon: '🛡️', desc: '生命上限',
    fullName: '体魄 · 命',
    detail: '肉身根基,决定能承受多少伤害。体魄高的修行者在苦战中有更大的容错空间,不易被秒杀。',
    effect: '每点+3%生命上限',
  },
  agi: {
    name: '敏', icon: '🌪️', desc: '速度闪避',
    fullName: '身法 · 灵',
    detail: '影响出手速度与闪避概率。敏捷高者先手出招,且有几率完全躲避攻击,以快打慢。',
    effect: '每点+2%速度,+1%闪避',
  },
  wis: {
    name: '意', icon: '👁️', desc: '暴击心法',
    fullName: '心意 · 明',
    detail: '洞察万物的心灵之眼。意识越高,暴击率与暴击伤害越强,一击致命的直觉也越敏锐。',
    effect: '每点+1.5%暴击率',
  },
  end: {
    name: '韧', icon: '🪨', desc: '防御疲劳',
    fullName: '坚韧 · 固',
    detail: '身心的抗压极限。韧性越高,物理与法术防御越强,疲劳上限也越高,可进行更长时间的修行。',
    effect: '每点+2%防御,+疲劳上限',
  },
  fate: {
    name: '缘', icon: '🍀', desc: '运气奇遇',
    fullName: '机缘 · 运',
    detail: '冥冥之中的气运天数。缘分越高,遭遇奇遇的概率越大,稀有掉落与特殊事件触发率提升。',
    effect: '每点+2%掉率,+奇遇概率',
  },
  ins: {
    name: '悟', icon: '📜', desc: '经验加成',
    fullName: '悟性 · 道',
    detail: '领悟天地之道的资质。悟性越高,战斗与修行获得的经验值加成越大,升级更快,境界突破更顺。',
    effect: '每点+2%经验加成',
  },
}

// ★ 机缘特性的背景故事与详细描述
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
  '顿悟之灵': { story: '天生聪颖过人,闻道一次便能理解三分,修行如有神助。', effect: '经验获取加成提升' },
  '通天之资': { story: '百年一遇的修行资质,学什么会什么,领悟速度惊人。', effect: '经验加成极高,升级飞快' },
  '笔下千秋': { story: '前世是文曲星转世,对文字与道理有超凡的理解力。', effect: '战斗经验与修行经验双重加成' },
}

function getBlessLore(note) {
  return BLESS_LORE[note] || { story: '天降异象,冥冥之中自有定数。', effect: '基础属性永久提升' }
}
const SECT_NAMES = {
  canglan: '沧澜剑派', tianji: '天机阁',
  xuanji: '玄机宗', qingming: '青冥派', yueyin: '月隐宫',
}
const sectName = computed(() => SECT_NAMES[sectId] || sectId)

onMounted(async () => {
  // 0. 背景揭示
  setTimeout(() => phase.value = 'reveal', 100)
  setTimeout(() => phase.value = 'altar', 1000)

  // 1. 后台并发创建角色(后端会随机分配 attrs + blessings)
  const q = route.query
  const baseUrl = q.base_url || 'https://bobdong.cn/v1'
  const apiKey = q.api_key
  const name = q.name || '执笔者'

  if (!apiKey) {
    msg.error('缺少 API Key,无法拜入')
    return router.replace('/onboarding')
  }

  try {
    const { data } = await characterApi.chooseSect(sectId, name, baseUrl, apiKey)
    character.value = data
    game.setCharacter(data)
  } catch (e) {
    msg.error('拜入失败: ' + e.message)
    setTimeout(() => router.replace('/sect-choose'), 2000)
    return
  }

  // 2. 8 属性逐个翻牌(0.35s 一个)
  setTimeout(() => phase.value = 'attrs', 2200)
  for (let i = 0; i < ATTR_KEYS.length; i++) {
    setTimeout(() => {
      showAttrs.value = [...showAttrs.value, ATTR_KEYS[i]]
    }, 2400 + i * 350)
  }

  // 3. 机缘揭示
  setTimeout(() => phase.value = 'bless', 2400 + ATTR_KEYS.length * 350 + 500)

  // 4. 进入按钮
  setTimeout(() => phase.value = 'done', 2400 + ATTR_KEYS.length * 350 + 2500)
})

function enterGame() {
  router.replace('/home')
}
</script>

<template>
  <div class="initiation-page">
    <!-- 仪式背景(暗色 + 飘浮粒子) -->
    <div class="bg" :class="phase"></div>
    <div class="particles" aria-hidden="true">
      <span v-for="n in 24" :key="n" class="p" :style="{
        left: (Math.random()*100) + '%',
        animationDelay: (Math.random()*10) + 's',
        animationDuration: (8 + Math.random()*8) + 's',
      }"></span>
    </div>

    <!-- 阶段 0:幕布 -->
    <Transition name="cur-fade">
      <div v-if="phase === 'curtain'" class="curtain"></div>
    </Transition>

    <!-- 阶段 1:祭坛 + 大字 -->
    <div class="altar" :class="{ shown: phase !== 'curtain' }">
      <div class="altar-circle"></div>
      <div class="altar-glow"></div>
      <h1 class="altar-text">
        <span class="t-prefix">师承</span>
        <span class="t-sect">{{ sectName }}</span>
      </h1>
      <p class="altar-sub" v-if="phase === 'altar' || phase === 'reveal'">
        ⚯ 天机推演中 · 卜算资质 ⚯
      </p>
    </div>

    <!-- 阶段 2:8 属性翻牌 -->
    <div v-if="phase === 'attrs' || phase === 'bless' || phase === 'done'" class="attrs-stage">
      <div class="stage-title">
        ★ 八 大 资 质 ★
      </div>
      <div class="attr-grid">
        <div v-for="k in ATTR_KEYS" :key="k"
             class="attr-card"
             :class="{ shown: showAttrs.includes(k) }">
          <div class="ac-icon">{{ ATTR_META[k].icon }}</div>
          <div class="ac-name">{{ ATTR_META[k].name }}</div>
          <div class="ac-value">
            <span v-if="!showAttrs.includes(k)">?</span>
            <span v-else>{{ character?.attrs?.[k] || 0 }}</span>
          </div>
          <div class="ac-desc">{{ ATTR_META[k].desc }}</div>
          <!-- ★ hover 详情浮层 -->
          <div v-if="showAttrs.includes(k)" class="attr-tooltip">
            <div class="att-header">
              <span class="att-icon">{{ ATTR_META[k].icon }}</span>
              <span class="att-fullname">{{ ATTR_META[k].fullName }}</span>
            </div>
            <p class="att-detail">{{ ATTR_META[k].detail }}</p>
            <div class="att-effect">{{ ATTR_META[k].effect }}</div>
            <div class="att-val">当前值: <strong>{{ character?.attrs?.[k] || 0 }}</strong></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 阶段 3:拜入机缘 -->
    <Transition name="bless-fade">
      <div v-if="phase === 'bless' || phase === 'done'" class="blessings">
        <div class="bless-title">📿 拜入机缘 · 天降异象</div>
        <div class="bless-row">
          <div v-for="(b, i) in (character?.blessings || [])" :key="i"
               class="bless-chip"
               :style="{ animationDelay: (i * 0.18) + 's' }">
            <span class="bc-icon">{{ b.attr_icon }}</span>
            <span class="bc-note">{{ b.note }}</span>
            <span class="bc-delta">+{{ b.delta }}</span>
            <!-- ★ hover 详情浮层 -->
            <div class="bless-tooltip">
              <div class="bt-header">
                <span class="bt-icon">{{ b.attr_icon }}</span>
                <span class="bt-name">{{ b.note }}</span>
                <span class="bt-delta">{{ b.attr_name }} +{{ b.delta }}</span>
              </div>
              <p class="bt-story">{{ getBlessLore(b.note).story }}</p>
              <div class="bt-effect">{{ getBlessLore(b.note).effect }}</div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 阶段 4:确认进入 -->
    <Transition name="enter-btn">
      <button v-if="phase === 'done'" class="enter-btn" @click="enterGame">
        <span class="eb-seal">入</span>
        <span class="eb-text">入 此 师 门 · 开 始 修 行</span>
        <span class="eb-arrow">→</span>
      </button>
    </Transition>
  </div>
</template>

<style scoped>
.initiation-page {
  position: fixed; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  background: #050810;
  color: #FFE0A3;
  font-family: 'STKaiti', 'KaiTi', serif;
  overflow: hidden;
}

/* 背景图层(优先用 loading-ceremony,fallback 黑底) */
.bg {
  position: absolute; inset: 0;
  background-image: url('/images/ui/loading-ceremony_1779617262_0.png');
  background-size: cover;
  background-position: center;
  background-color: #050810;
  opacity: 0;
  transition: opacity 2s ease, filter 2s ease;
}
.bg.reveal, .bg.altar, .bg.attrs, .bg.bless, .bg.done {
  opacity: 0.45;
}
.bg::before {
  content: ''; position: absolute; inset: 0;
  background: radial-gradient(ellipse at center, rgba(212,162,76,0.15), rgba(0,0,0,0.85));
}

/* 飘浮粒子 */
.particles { position: absolute; inset: 0; pointer-events: none; }
.p {
  position: absolute;
  bottom: -10px;
  width: 4px; height: 4px;
  border-radius: 50%;
  background: radial-gradient(circle, #FFE0A3, transparent);
  box-shadow: 0 0 6px #D4A24C;
  animation: p-rise linear infinite;
}
@keyframes p-rise {
  0%   { transform: translateY(0); opacity: 0; }
  20%  { opacity: 0.8; }
  100% { transform: translateY(-110vh); opacity: 0; }
}

/* 幕布 */
.curtain {
  position: absolute; inset: 0;
  background: #000;
  z-index: 100;
}
.cur-fade-enter-active, .cur-fade-leave-active { transition: opacity 1s; }
.cur-fade-leave-to { opacity: 0; }

/* 祭坛大字 */
.altar {
  position: relative;
  text-align: center;
  z-index: 10;
  margin-bottom: 32px;
  opacity: 0;
  transition: opacity 1.2s 0.6s, transform 1.2s 0.6s;
  transform: scale(0.85);
}
.altar.shown { opacity: 1; transform: scale(1); }
.altar-circle {
  width: 260px; height: 260px;
  margin: 0 auto 24px;
  border-radius: 50%;
  border: 2px dashed #D4A24C;
  position: relative;
  animation: altar-spin 20s linear infinite;
}
.altar-circle::before, .altar-circle::after {
  content: ''; position: absolute; inset: -8px;
  border-radius: 50%;
  border: 1px solid rgba(212,162,76,0.4);
}
.altar-circle::after { inset: -16px; opacity: 0.5; }
@keyframes altar-spin { to { transform: rotate(360deg); } }
.altar-glow {
  position: absolute;
  top: 22px; left: 50%;
  width: 220px; height: 220px;
  transform: translateX(-50%);
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 224, 163, 0.4), transparent 60%);
  animation: glow-pulse 3s ease-in-out infinite;
}
@keyframes glow-pulse {
  0%, 100% { opacity: 0.4; }
  50%      { opacity: 1; }
}
.altar-text {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  margin: 0;
  font-size: 0;
  display: flex; flex-direction: column;
  align-items: center; gap: 4px;
}
.t-prefix {
  font-size: 16px;
  letter-spacing: 12px;
  color: #aaa;
}
.t-sect {
  font-size: 36px;
  letter-spacing: 14px;
  color: #FFE0A3;
  text-shadow: 0 0 24px #D4A24C, 0 0 48px rgba(212,162,76,0.5);
}
.altar-sub {
  margin: 12px 0 0;
  font-size: 14px;
  letter-spacing: 6px;
  color: #D4A24C;
  animation: altar-sub-blink 1.5s ease-in-out infinite;
}
@keyframes altar-sub-blink {
  0%, 100% { opacity: 0.6; }
  50%      { opacity: 1; }
}

/* 8 属性翻牌 */
.attrs-stage {
  position: relative;
  z-index: 10;
  text-align: center;
}
.stage-title {
  font-size: 14px;
  letter-spacing: 10px;
  color: #FFE0A3;
  margin-bottom: 18px;
  text-shadow: 0 0 12px #D4A24C;
}
.attr-grid {
  display: grid;
  grid-template-columns: repeat(4, 130px);
  gap: 12px;
}
.attr-card {
  background:
    linear-gradient(180deg, rgba(40,28,12,0.85), rgba(8,5,2,0.95));
  border: 1.5px solid rgba(212,162,76,0.4);
  border-radius: 10px;
  padding: 14px 8px;
  text-align: center;
  opacity: 0;
  transform: rotateY(180deg) scale(0.8);
  transition: opacity 0.45s cubic-bezier(0.34, 1.56, 0.64, 1),
              transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: 0 4px 16px rgba(0,0,0,0.6);
  position: relative;
}
.attr-card.shown {
  opacity: 1;
  transform: rotateY(0) scale(1);
}
.attr-card.shown::after {
  content: '';
  position: absolute; inset: -2px;
  border-radius: 10px;
  background: linear-gradient(135deg, #D4A24C, #FFE0A3, #D4A24C) border-box;
  -webkit-mask: linear-gradient(#000 0 0) padding-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  animation: card-edge 2s ease-in-out;
}
@keyframes card-edge {
  0% { opacity: 1; }
  100% { opacity: 0.3; }
}
.ac-icon { font-size: 32px; margin-bottom: 4px; filter: drop-shadow(0 0 8px #D4A24C); }
.ac-name {
  font-size: 14px;
  color: #FFE0A3;
  letter-spacing: 4px;
  margin-bottom: 4px;
}
.ac-value {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  font-family: 'SF Mono', monospace;
  text-shadow: 0 0 12px #FFE0A3;
  margin-bottom: 4px;
}
.ac-desc {
  font-size: 10px;
  color: #aaa;
  letter-spacing: 1px;
}

/* ★ 属性 hover 详情浮层 */
.attr-tooltip {
  position: absolute;
  bottom: calc(100% + 12px);
  left: 50%;
  transform: translateX(-50%);
  width: 240px;
  background: linear-gradient(180deg, rgba(25, 18, 8, 0.98), rgba(10, 6, 2, 0.98));
  border: 1px solid rgba(212, 162, 76, 0.5);
  border-radius: 10px;
  padding: 14px 16px;
  text-align: left;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.8), 0 0 20px rgba(212, 162, 76, 0.15);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.25s, transform 0.25s;
  transform: translateX(-50%) translateY(6px);
  z-index: 50;
}
.attr-tooltip::after {
  content: '';
  position: absolute;
  bottom: -7px;
  left: 50%;
  transform: translateX(-50%);
  width: 12px; height: 12px;
  background: rgba(10, 6, 2, 0.98);
  border-right: 1px solid rgba(212, 162, 76, 0.5);
  border-bottom: 1px solid rgba(212, 162, 76, 0.5);
  transform: translateX(-50%) rotate(45deg);
}
.attr-card:hover .attr-tooltip {
  opacity: 1;
  pointer-events: auto;
  transform: translateX(-50%) translateY(0);
}
.att-header {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(212, 162, 76, 0.25);
}
.att-icon { font-size: 20px; }
.att-fullname {
  font-size: 14px;
  color: #FFE0A3;
  letter-spacing: 3px;
  font-weight: 600;
}
.att-detail {
  margin: 0 0 8px;
  font-size: 12px;
  color: #ccc;
  line-height: 1.7;
  letter-spacing: 0.5px;
  font-family: 'STKaiti', serif;
}
.att-effect {
  font-size: 11px;
  color: #95D5B2;
  background: rgba(82, 183, 136, 0.1);
  border: 1px solid rgba(82, 183, 136, 0.25);
  border-radius: 4px;
  padding: 4px 8px;
  margin-bottom: 6px;
}
.att-val {
  font-size: 11px;
  color: #aaa;
  text-align: right;
}
.att-val strong {
  color: #FFE0A3;
  font-size: 14px;
  margin-left: 4px;
}

/* 拜入机缘 */
.blessings {
  position: relative;
  z-index: 10;
  margin-top: 28px;
  text-align: center;
  max-width: 600px;
}
.bless-title {
  font-size: 13px;
  color: #D4A24C;
  letter-spacing: 6px;
  margin-bottom: 10px;
}
.bless-row {
  display: flex; flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
}
.bless-chip {
  background:
    linear-gradient(135deg, rgba(212,162,76,0.25), rgba(255,224,163,0.1));
  border: 1px solid #D4A24C;
  border-radius: 16px;
  padding: 6px 16px;
  font-size: 13px;
  color: #FFE0A3;
  letter-spacing: 2px;
  display: flex; align-items: center; gap: 6px;
  opacity: 0;
  animation: bless-pop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}
@keyframes bless-pop {
  0%   { opacity: 0; transform: scale(0.5) translateY(20px); }
  100% { opacity: 1; transform: scale(1) translateY(0); }
}
.bc-icon { font-size: 16px; }
.bc-delta { color: #95D5B2; font-weight: 700; }

/* ★ 机缘 hover 详情浮层 */
.bless-chip {
  position: relative;
  cursor: default;
}
.bless-tooltip {
  position: absolute;
  bottom: calc(100% + 12px);
  left: 50%;
  transform: translateX(-50%);
  width: 280px;
  background: linear-gradient(180deg, rgba(25, 18, 8, 0.98), rgba(10, 6, 2, 0.98));
  border: 1px solid rgba(212, 162, 76, 0.5);
  border-radius: 10px;
  padding: 14px 16px;
  text-align: left;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.8), 0 0 20px rgba(212, 162, 76, 0.15);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.25s, transform 0.25s;
  transform: translateX(-50%) translateY(6px);
  z-index: 50;
}
.bless-tooltip::after {
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
.bless-chip:hover .bless-tooltip {
  opacity: 1;
  pointer-events: auto;
  transform: translateX(-50%) translateY(0);
}
.bt-header {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(212, 162, 76, 0.25);
}
.bt-icon { font-size: 18px; }
.bt-name {
  flex: 1;
  font-size: 14px;
  color: #FFE0A3;
  letter-spacing: 2px;
  font-weight: 600;
}
.bt-delta {
  font-size: 12px;
  color: #95D5B2;
  background: rgba(82, 183, 136, 0.12);
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}
.bt-story {
  margin: 0 0 8px;
  font-size: 12px;
  color: #d4c8a8;
  line-height: 1.8;
  font-family: 'STKaiti', serif;
  font-style: italic;
  border-left: 2px solid rgba(212, 162, 76, 0.3);
  padding-left: 10px;
}
.bt-effect {
  font-size: 11px;
  color: #7FC7E8;
  background: rgba(127, 199, 232, 0.08);
  border: 1px solid rgba(127, 199, 232, 0.2);
  border-radius: 4px;
  padding: 4px 8px;
}

.bless-fade-enter-active, .bless-fade-leave-active { transition: opacity 0.6s; }
.bless-fade-enter-from { opacity: 0; }

/* 进入按钮 */
.enter-btn {
  margin-top: 36px;
  position: relative; z-index: 10;
  background: linear-gradient(135deg, #D4A24C, #8B5A1A);
  border: 2px solid #FFE0A3;
  color: #1a1a1a;
  padding: 16px 36px;
  border-radius: 12px;
  cursor: pointer;
  font-family: 'STKaiti', serif;
  font-weight: 700;
  font-size: 16px;
  letter-spacing: 6px;
  display: flex; align-items: center; gap: 14px;
  box-shadow: 0 8px 32px rgba(212,162,76,0.5);
  animation: enter-glow 2s ease-in-out infinite;
}
@keyframes enter-glow {
  0%, 100% { box-shadow: 0 8px 32px rgba(212,162,76,0.5); }
  50%      { box-shadow: 0 12px 48px rgba(212,162,76,0.9); }
}
.enter-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 16px 56px rgba(212,162,76,0.85);
}
.eb-seal {
  width: 36px; height: 36px;
  background: radial-gradient(circle, #C03F3F, #6B0F0F);
  color: #fff;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  font-weight: 700;
  transform: rotate(-10deg);
  border: 2px double rgba(255, 220, 200, 0.7);
}
.eb-arrow { font-size: 20px; animation: eb-arrow 1.2s ease-in-out infinite; }
@keyframes eb-arrow {
  0%, 100% { transform: translateX(0); }
  50%      { transform: translateX(6px); }
}

.enter-btn-enter-active { transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1); }
.enter-btn-enter-from { opacity: 0; transform: translateY(20px) scale(0.85); }

@media (max-width: 700px) {
  .attr-grid { grid-template-columns: repeat(2, 130px); }
  .t-sect { font-size: 26px; letter-spacing: 8px; }
}
</style>
