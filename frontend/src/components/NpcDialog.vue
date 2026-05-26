<!--
  NpcDialog.vue — NPC 互动对话框
  显示 NPC 立绘 + 意图 + 4 个互动按钮(根据 intent 智能高亮主动作)
-->
<script setup>
import { ref, computed } from 'vue'
import { useMessage } from 'naive-ui'
import { npcApi } from '../api/client.js'
import RoundPortrait from './RoundPortrait.vue'
import ItemIcon from './ItemIcon.vue'
import { npcPortraitRef, npcPreview } from '../utils/characterPreview.js'

const props = defineProps({
  npc: { type: Object, default: null },
  visible: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'battle-start', 'refresh'])
const msg = useMessage()

const loading = ref(false)
const resultData = ref(null)   // 行动结果(narrative + 状态)
const tradeItems = ref(null)   // 商店物品

const intentText = {
  pass: '路过', spar: '切磋', hostile: '敌意', trade: '行商', teach: '传道',
}
const intentDesc = {
  pass: '寒暄一下,交个朋友',
  spar: '切磋武艺,胜负不伤性命',
  hostile: '生死搏杀,赢者通吃',
  trade: '看看他带了什么货',
  teach: '请教对方派系绝学(需要通用秘籍)',
}

async function doAction(intent) {
  if (loading.value || !props.npc) return
  loading.value = true
  try {
    const { data } = await npcApi.engage(props.npc.id, intent, props.npc)
    if (data.fatigue) emit('refresh')
    if (data.result === 'battle_start') {
      emit('battle-start', data.battle_id)
      emit('close')
    } else if (data.result === 'trade_offer') {
      tradeItems.value = data.items
      resultData.value = { narrative: data.narrative, kind: 'trade' }
    } else {
      resultData.value = { ...data, kind: data.result }
    }
  } catch (e) {
    msg.error(e.message)
  } finally {
    loading.value = false
  }
}

async function buyItem(item) {
  loading.value = true
  try {
    const { data } = await npcApi.tradeBuy(props.npc.id, item.id, 1)
    msg.success(`已购入 ${item.name}`)
    if (data.fatigue) emit('refresh')
  } catch (e) {
    msg.error(e.message)
  } finally {
    loading.value = false
  }
}

function close() {
  resultData.value = null
  tradeItems.value = null
  emit('close')
}

const portraitRef = computed(() => npcPortraitRef(props.npc || {}, 'circle'))
const portraitId = computed(() => portraitRef.value.id)
const portraitKind = computed(() => portraitRef.value.kind)
</script>

<template>
  <Transition name="fade">
    <div v-if="visible && npc" class="npc-overlay" @click.self="close">
      <div class="npc-card">
        <button class="close" @click="close">✕</button>

        <!-- Header: 立绘 + 名字 + 意图 -->
        <div class="head">
          <RoundPortrait :kind="portraitKind" :id="portraitId" :size="120"
                         shape="circle" :name="npc.name"
                         :level="npc.level"
                         :preview="npcPreview(npc)" />
          <div class="info">
            <div class="name">{{ npc.name }}</div>
            <div class="title">{{ npc.title }}</div>
            <div class="intent">
              {{ npc.intent_icon || '👤' }} {{ npc.intent_label || intentText[npc.intent] }} · Lv {{ npc.level }}
            </div>
          </div>
        </div>

        <div class="desc">{{ npc.description }}</div>

        <!-- 行动按钮(只在没有 result 时显示)-->
        <div v-if="!resultData" class="actions">
          <button class="act" :class="{ primary: npc.intent === 'pass' }"
                  @click="doAction('pass')" :disabled="loading">
            🚶 寒暄路过
            <span class="hint">{{ intentDesc.pass }}</span>
          </button>
          <button class="act" :class="{ primary: npc.intent === 'spar' }"
                  @click="doAction('spar')" :disabled="loading">
            🤝 切磋武艺
            <span class="hint">{{ intentDesc.spar }}</span>
          </button>
          <button class="act danger" :class="{ primary: npc.intent === 'hostile' }"
                  @click="doAction('hostile')" :disabled="loading">
            ⚔ 拔剑相向
            <span class="hint">{{ intentDesc.hostile }}</span>
          </button>
          <button class="act" :class="{ primary: npc.intent === 'trade' }"
                  v-if="npc.intent === 'trade'"
                  @click="doAction('trade')" :disabled="loading">
            🛒 看看货
            <span class="hint">{{ intentDesc.trade }}</span>
          </button>
          <button class="act" :class="{ primary: npc.intent === 'teach' }"
                  v-if="npc.intent === 'teach'"
                  @click="doAction('teach')" :disabled="loading">
            📖 求道讨教
            <span class="hint">{{ intentDesc.teach }}</span>
          </button>
        </div>

        <!-- 结果显示 -->
        <div v-if="resultData" class="result">
          <p class="narrative">{{ resultData.narrative }}</p>

          <!-- 商店物品 -->
          <div v-if="tradeItems" class="trade-list">
            <div v-for="it in tradeItems" :key="it.id" class="trade-item">
              <ItemIcon class="ti-icon" :item="it" :size="36" />
              <div class="ti-info">
                <div class="ti-name">{{ it.name }}</div>
                <div class="ti-desc">{{ it.description }}</div>
              </div>
              <button class="ti-buy" @click="buyItem(it)" :disabled="loading">
                💧 {{ it.price_qi }}
              </button>
            </div>
          </div>

          <!-- 传授成功 -->
          <div v-if="resultData.skill" class="taught-skill">
            <div class="ts-title">习得新招</div>
            <div class="ts-body">
              {{ resultData.skill.icon }} <strong>{{ resultData.skill.name }}</strong>
              <div class="ts-desc">{{ resultData.skill.description }}</div>
            </div>
          </div>

          <button class="ok-btn" @click="close">告辞</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.npc-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.78);
  display: flex; align-items: center; justify-content: center;
  z-index: 300; padding: 20px;
  backdrop-filter: blur(4px);
}
.npc-card {
  position: relative;
  width: 100%; max-width: 480px;
  max-height: 90vh; overflow-y: auto;
  background: linear-gradient(180deg, rgba(20,30,52,0.97), rgba(8,12,24,0.99));
  border: 1px solid rgba(212,162,76,0.55); border-radius: 14px;
  padding: 24px;
  box-shadow: 0 12px 48px rgba(0,0,0,0.7), 0 0 24px rgba(212,162,76,0.2);
}
.close {
  position: absolute; top: 8px; right: 12px;
  background: transparent; color: #888;
  border: none; font-size: 22px; cursor: pointer;
}
.close:hover { color: #fff; }

.head { display: flex; gap: 16px; margin-bottom: 12px; }
.info { flex: 1; }
.name { font-size: 22px; color: #FFE0A3; letter-spacing: 3px; font-family: 'STKaiti', serif; }
.title { font-size: 12px; color: #aaa; letter-spacing: 2px; margin: 4px 0; }
.intent { font-size: 13px; color: #D4A24C; letter-spacing: 1px; font-family: 'STKaiti', serif; }

.desc {
  margin: 12px 0 18px;
  padding: 10px 12px;
  background: rgba(255,255,255,0.03);
  border-left: 3px solid rgba(212,162,76,0.5);
  font-size: 13px; color: #ccc; line-height: 1.7;
  font-family: 'STKaiti', serif;
}

.actions { display: grid; gap: 8px; }
.act {
  display: flex; flex-direction: column; align-items: flex-start;
  background: rgba(255,255,255,0.04); color: #FFE0A3;
  border: 1px solid rgba(212,162,76,0.3);
  padding: 10px 14px; border-radius: 6px;
  cursor: pointer;
  font-family: 'STKaiti', serif; letter-spacing: 2px; font-size: 14px;
  transition: all 0.18s;
}
.act:hover { background: rgba(212,162,76,0.16); border-color: #D4A24C; transform: translateX(3px); }
.act.primary {
  background: linear-gradient(135deg, rgba(212,162,76,0.3), rgba(212,162,76,0.1));
  border-color: #D4A24C;
  box-shadow: 0 0 12px rgba(212,162,76,0.25);
}
.act.danger { color: #FF8888; border-color: rgba(192,63,63,0.45); }
.act.danger:hover { background: rgba(192,63,63,0.15); border-color: #C03F3F; }
.act .hint { font-size: 10px; color: #888; letter-spacing: 1px; margin-top: 3px; }
.act:disabled { opacity: 0.5; cursor: not-allowed; }

.result { margin-top: 6px; }
.narrative {
  font-size: 14px; color: #FFE0A3; line-height: 1.8;
  padding: 14px; background: rgba(212,162,76,0.08);
  border: 1px dashed rgba(212,162,76,0.3); border-radius: 8px;
  font-family: 'STKaiti', serif;
}

.trade-list { display: flex; flex-direction: column; gap: 6px; margin-top: 14px; }
.trade-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.05); border-radius: 6px;
}
.ti-icon { flex-shrink: 0; }
.ti-info { flex: 1; }
.ti-name { color: #FFE0A3; font-size: 13px; font-family: 'STKaiti', serif; }
.ti-desc { color: #888; font-size: 11px; margin-top: 2px; }
.ti-buy {
  background: rgba(127,199,232,0.18); color: #7FC7E8;
  border: 1px solid rgba(127,199,232,0.4);
  padding: 6px 12px; border-radius: 4px;
  cursor: pointer; font-family: 'SF Mono', monospace; font-size: 13px;
}
.ti-buy:hover { background: rgba(127,199,232,0.3); }
.ti-buy:disabled { opacity: 0.5; cursor: not-allowed; }

.taught-skill {
  margin-top: 14px; padding: 12px;
  background: linear-gradient(135deg, rgba(255,215,0,0.1), rgba(212,162,76,0.05));
  border: 1px solid rgba(255,215,0,0.4); border-radius: 8px;
}
.ts-title { color: #FFD700; font-size: 12px; letter-spacing: 3px; margin-bottom: 6px; font-family: 'STKaiti', serif; }
.ts-body { color: #FFE0A3; font-size: 14px; font-family: 'STKaiti', serif; }
.ts-desc { color: #aaa; font-size: 11px; margin-top: 4px; }

.ok-btn {
  margin-top: 14px; width: 100%;
  background: linear-gradient(135deg, #D4A24C, #B58A3E);
  color: #0F1B2E; border: none;
  padding: 10px; border-radius: 6px; cursor: pointer;
  font-family: 'STKaiti', serif; letter-spacing: 4px; font-size: 14px;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
