<!--
  StatusBar.vue — 地图底部角色状态条
  显示:HP / 灵气 / 修为 / 疲劳 + 8 属性弹出面板
-->
<script setup>
import { ref, computed } from 'vue'
import { useGameStore } from '../stores/game.js'
import { formatNum } from '../utils/format.js'

const props = defineProps({
  compact: { type: Boolean, default: false },
})
const game = useGameStore()
const char = computed(() => game.character)
const showAttrs = ref(false)

const ATTR_META = {
  str: { name: '力', icon: '🥊', desc: '物理攻击力 / 武器威力' },
  qi:  { name: '元', icon: '💧', desc: '灵气上限 / 法术加成' },
  vit: { name: '躯', icon: '🛡️', desc: '生命上限 / 抗性' },
  agi: { name: '敏', icon: '🌪️', desc: '速度 / 闪避' },
  wis: { name: '意', icon: '👁️', desc: '暴击率 / 心法领悟' },
  end: { name: '韧', icon: '🪨', desc: '防御 / 疲劳上限' },
  fate:{ name: '缘', icon: '🍀', desc: '运气 / 奇遇 / 掉落' },
  ins: { name: '悟', icon: '📜', desc: '成章领悟' },
}
const ATTR_KEYS = ['str','qi','vit','agi','wis','end','fate','ins']

const hpPct  = computed(() => char.value ? Math.round(char.value.hp / char.value.max_hp * 100) : 0)
const qiPct  = computed(() => char.value ? Math.round(char.value.qi / char.value.max_qi * 100) : 0)
const expPct = computed(() => {
  if (!char.value) return 0
  const need = (char.value.level + 1) * 100
  return Math.min(100, Math.round(char.value.exp / need * 100))
})
const fatPct = computed(() => {
  if (!char.value) return 0
  const max = char.value.max_fatigue || 80
  return Math.round((char.value.fatigue || 0) / max * 100)
})
const fatigueColor = computed(() => {
  const p = fatPct.value
  if (p < 40) return '#52B788'  // 健康
  if (p < 70) return '#FFB454'  // 警戒
  return '#C03F3F'              // 力竭
})
</script>

<template>
  <div v-if="char" class="status-bar" :class="{ compact }">
    <!-- 左:头像 + 名 + 境界 -->
    <div class="ident">
      <div class="avatar">{{ {canglan:'🗡️',tianji:'⚙️',xuanji:'🧠',qingming:'📜',yueyin:'🌙'}[char.sect] || '🧝' }}</div>
      <div class="ident-text">
        <div class="ident-name">{{ char.name }}</div>
        <div class="ident-sect">{{ char.sect_name }} · {{ char.realm_name }} · Lv.{{ char.level }}</div>
      </div>
    </div>

    <!-- 中:4 条状态(HP/灵气/修为/疲劳)-->
    <div class="bars">
      <div class="bar-row" :title="`HP: ${char.hp} / ${char.max_hp}`">
        <span class="bar-label">❤️</span>
        <div class="bar"><div class="bar-fill hp" :style="{ width: hpPct + '%' }"></div></div>
        <span class="bar-value">{{ formatNum(char.hp) }}/{{ formatNum(char.max_hp) }}</span>
      </div>
      <div class="bar-row" :title="`灵气: ${char.qi} / ${char.max_qi}`">
        <span class="bar-label">💧</span>
        <div class="bar"><div class="bar-fill qi" :style="{ width: qiPct + '%' }"></div></div>
        <span class="bar-value">{{ formatNum(char.qi) }}/{{ formatNum(char.max_qi) }}</span>
      </div>
      <div class="bar-row" :title="`修为: ${char.exp} / ${(char.level + 1) * 100}`">
        <span class="bar-label">✨</span>
        <div class="bar"><div class="bar-fill exp" :style="{ width: expPct + '%' }"></div></div>
        <span class="bar-value">{{ formatNum(char.exp) }}/{{ formatNum((char.level + 1) * 100) }}</span>
      </div>
      <div class="bar-row" :title="`疲劳: ${char.fatigue || 0} / ${char.max_fatigue || 80}`">
        <span class="bar-label">💤</span>
        <div class="bar"><div class="bar-fill" :style="{ width: fatPct + '%', background: fatigueColor }"></div></div>
        <span class="bar-value">{{ formatNum(char.fatigue || 0) }}/{{ formatNum(char.max_fatigue || 80) }}</span>
      </div>
    </div>

    <!-- 右:战斗数值(紧凑列式) + 8 属性弹出 -->
    <div class="combat-stats">
      <div class="cs-grid">
        <div class="cs" :title="`攻击: ${char.atk}`">
          <span class="cs-label">攻</span>
          <span class="cs-val">{{ formatNum(char.atk) }}</span>
        </div>
        <div class="cs" :title="`防御: ${char.def_}`">
          <span class="cs-label">防</span>
          <span class="cs-val">{{ formatNum(char.def_) }}</span>
        </div>
        <div class="cs" :title="`速度: ${char.spd}`">
          <span class="cs-label">速</span>
          <span class="cs-val">{{ formatNum(char.spd) }}</span>
        </div>
        <div class="cs" :title="`暴击率: ${Math.round((char.crit_rate || 0) * 100)}%`">
          <span class="cs-label">暴</span>
          <span class="cs-val">{{ Math.round((char.crit_rate || 0) * 100) }}%</span>
        </div>
      </div>
      <button class="attrs-btn" @click="showAttrs = !showAttrs" title="查看 8 项资质">
        🌀
      </button>
    </div>

    <!-- 8 属性面板(浮在状态条上方)-->
    <Transition name="attrs-popup">
      <div v-if="showAttrs && char.attrs" class="attrs-popup">
        <div class="ap-title">⚯ 角色资质 · 八大属性</div>
        <div class="ap-grid">
          <div v-for="k in ATTR_KEYS" :key="k" class="attr-cell">
            <div class="ac-icon">{{ ATTR_META[k].icon }}</div>
            <div class="ac-info">
              <div class="ac-row">
                <span class="ac-name">{{ ATTR_META[k].name }}</span>
                <span class="ac-value">{{ char.attrs[k] || 0 }}</span>
              </div>
              <div class="ac-desc">{{ ATTR_META[k].desc }}</div>
              <div class="ac-bar"><div class="ac-fill" :style="{ width: Math.min(100, (char.attrs[k]||0)*5) + '%' }"></div></div>
            </div>
          </div>
        </div>
        <div v-if="char.blessings?.length" class="ap-blessings">
          <div class="ap-bless-title">📿 拜入机缘</div>
          <span v-for="(b, i) in char.blessings" :key="i" class="bless-chip">
            {{ b.attr_icon }} {{ b.note }} +{{ b.delta }}
          </span>
        </div>
        <button class="ap-close" @click="showAttrs = false">关闭</button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.status-bar {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  z-index: 50;
  display: grid;
  grid-template-columns: 200px minmax(0, 1fr) auto;
  gap: 20px;
  align-items: center;
  padding: 8px calc(24px + var(--safe-right)) calc(8px + var(--safe-bottom)) calc(24px + var(--safe-left));
  background:
    linear-gradient(180deg,
      rgba(8,5,2,0.75) 0%,
      rgba(8,5,2,0.95) 60%,
      rgba(8,5,2,0.98) 100%);
  border-top: 1.5px solid;
  border-image: linear-gradient(90deg,
    transparent, rgba(212,162,76,0.6), rgba(212,162,76,0.9),
    rgba(212,162,76,0.6), transparent) 1;
  backdrop-filter: blur(10px);
  font-family: 'STKaiti', 'KaiTi', serif;
  box-shadow: 0 -8px 24px rgba(0,0,0,0.6);
}
.status-bar.compact { padding: 6px 14px; grid-template-columns: 180px minmax(0, 1fr) auto; gap: 14px; }

/* 左:身份 */
.ident { display: flex; gap: 10px; align-items: center; }
.avatar {
  width: 44px; height: 44px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(212,162,76,0.3), rgba(20,15,8,0.8));
  border: 1.5px solid #D4A24C;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px;
  box-shadow: 0 0 12px rgba(212,162,76,0.4);
}
.ident-text { display: flex; flex-direction: column; gap: 1px; }
.ident-name { font-size: 14px; color: #FFE0A3; letter-spacing: 1px; font-weight: 600; }
.ident-sect { font-size: 10px; color: #888; letter-spacing: 1px; }

/* 中:4 条 bars — 2 列布局,自适应 */
.bars {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 18px;
  min-width: 0;   /* 关键:让 1fr 真正可缩 */
}
.bar-row {
  display: grid;
  grid-template-columns: 22px minmax(60px, 1fr) auto;
  gap: 8px;
  align-items: center;
  font-size: 10px;
  min-width: 0;
}
.bar-label {
  color: #aaa;
  letter-spacing: 1px;
  font-size: 12px;
  text-align: center;
}
.bar {
  height: 8px;
  background: rgba(0,0,0,0.6);
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,0.04);
  min-width: 0;
}
.bar-fill { height: 100%; transition: width 0.5s ease; border-radius: 3px; }
.bar-fill.hp  { background: linear-gradient(90deg, #C03F3F, #FF6B6B); }
.bar-fill.qi  { background: linear-gradient(90deg, #3A6B6E, #7FC7E8); }
.bar-fill.exp { background: linear-gradient(90deg, #B58A3E, #FFE0A3); }
.bar-value {
  color: #ccc;
  font-family: 'SF Mono', monospace;
  font-size: 10px;
  text-align: right;
  white-space: nowrap;     /* ★ 强制不换行 */
  letter-spacing: -0.2px;  /* 紧凑数字间距 */
  min-width: 0;
}

/* 右:战斗数值 + 属性按钮(紧凑) */
.combat-stats {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}
.cs-grid {
  display: grid;
  grid-template-columns: repeat(4, auto);
  gap: 4px;
}
.cs {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  padding: 3px 8px;
  border-radius: 4px;
  min-width: 38px;
}
.cs-label { font-size: 9px; color: #888; letter-spacing: 1px; }
.cs-val {
  font-size: 11px;
  color: #FFE0A3;
  font-weight: 600;
  font-family: 'SF Mono', monospace;
  letter-spacing: -0.3px;
  white-space: nowrap;
  margin-top: 1px;
}
.attrs-btn {
  background: linear-gradient(135deg, rgba(212,162,76,0.22), rgba(212,162,76,0.06));
  border: 1px solid rgba(212,162,76,0.45);
  color: #FFE0A3;
  width: 36px; height: 36px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 18px;
  font-family: inherit;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  transition: all 0.18s;
}
.attrs-btn:hover {
  background: linear-gradient(135deg, rgba(212,162,76,0.35), rgba(212,162,76,0.1));
  border-color: #FFE0A3;
  box-shadow: 0 0 12px rgba(212,162,76,0.4);
}

/* === 8 属性弹出面板 === */
.attrs-popup {
  position: absolute;
  bottom: 100%;
  right: 24px;
  width: 380px;
  margin-bottom: 8px;
  background:
    radial-gradient(ellipse at top, rgba(212,162,76,0.15), transparent 60%),
    linear-gradient(180deg, rgba(20,15,8,0.97), rgba(8,5,2,0.99));
  border: 1px solid rgba(212,162,76,0.5);
  border-radius: 12px;
  padding: 14px;
  box-shadow:
    0 12px 36px rgba(0, 0, 0, 0.7),
    0 0 24px rgba(212,162,76,0.2);
}
.ap-title {
  text-align: center;
  font-size: 14px;
  color: #FFE0A3;
  letter-spacing: 6px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(212,162,76,0.3);
}
.ap-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.attr-cell {
  display: flex; gap: 8px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(212,162,76,0.15);
  border-radius: 6px;
  padding: 6px 8px;
}
.ac-icon { font-size: 22px; flex-shrink: 0; }
.ac-info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.ac-row { display: flex; justify-content: space-between; align-items: baseline; }
.ac-name { font-size: 13px; color: #FFE0A3; font-weight: 600; letter-spacing: 1px; }
.ac-value { font-size: 16px; color: #fff; font-weight: 700; font-family: 'SF Mono', monospace; }
.ac-desc { font-size: 9px; color: #888; line-height: 1.3; }
.ac-bar { height: 3px; background: rgba(0,0,0,0.4); border-radius: 1.5px; overflow: hidden; margin-top: 2px; }
.ac-fill { height: 100%; background: linear-gradient(90deg, #D4A24C, #FFE0A3); }

.ap-blessings {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed rgba(212,162,76,0.25);
}
.ap-bless-title { font-size: 11px; color: #D4A24C; letter-spacing: 2px; margin-bottom: 6px; }
.bless-chip {
  display: inline-block;
  background: rgba(212,162,76,0.12);
  border: 1px solid rgba(212,162,76,0.3);
  color: #FFE0A3;
  padding: 2px 8px;
  margin: 2px 4px 2px 0;
  border-radius: 4px;
  font-size: 10px;
  letter-spacing: 0.5px;
}

.ap-close {
  display: block; width: 100%;
  margin-top: 10px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  color: #aaa;
  padding: 5px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  letter-spacing: 2px;
}
.ap-close:hover { color: #fff; }

.attrs-popup-enter-active, .attrs-popup-leave-active { transition: all 0.25s; }
.attrs-popup-enter-from, .attrs-popup-leave-to { opacity: 0; transform: translateY(10px); }

@media (max-width: 900px) {
  .status-bar {
    bottom: calc(var(--mobile-bottom-nav-h) + var(--safe-bottom));
    grid-template-columns: 1fr;
    gap: 6px;
    padding: 6px calc(12px + var(--safe-right)) 6px calc(12px + var(--safe-left));
  }
  .bars { grid-template-columns: 1fr; }
  .combat-stats { justify-content: flex-start; }
  .attrs-popup { width: calc(100vw - 24px); right: 12px; }
}

@media (orientation: landscape) and (max-height: 520px) {
  .status-bar {
    left: calc(68px + var(--safe-left));
    bottom: 0;
    grid-template-columns: 180px minmax(0, 1fr) auto;
    padding-bottom: calc(6px + var(--safe-bottom));
  }
  .bars {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
