<!--
  GiftDialog.vue — 战斗中赠礼对话框

  从玩家背包选物品送给当前敌人,接受率取决于:
    - 物品稀有度 + 友好度 + INS 悟性 + 已送次数 + tanh
-->
<script setup>
import { ref, computed, watch } from 'vue'
import { useMessage } from 'naive-ui'
import { inventoryApi, giftApi, characterApi } from '../api/client.js'
import ItemIcon from './ItemIcon.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  battleId: { type: String, required: true },
  enemyName: { type: String, default: '敌方' },
  giftCount: { type: Number, default: 0 },  // 本场已送几次
})
const emit = defineEmits(['close', 'accepted', 'rejected'])
const msg = useMessage()

const inventory = ref([])
const sending = ref(false)
const lastResult = ref(null)  // { accepted, message, accept_prob }

const remaining = computed(() => Math.max(0, 3 - props.giftCount))

watch(() => props.visible, async (v) => {
  if (v) {
    lastResult.value = null
    try {
      const { data } = await inventoryApi.list()
      // 优先材料和丹药(易得)
      inventory.value = (data.items || []).filter(it =>
        ['material', 'consumable', 'equipment'].includes(it.type)
      ).sort((a, b) => b.rarity - a.rarity)
    } catch (e) {
      msg.error('背包加载失败: ' + e.message)
    }
  }
})

const RARITY_COLOR = {
  1: '#B0B0B0', 2: '#2EBB6B', 3: '#4A90E2',
  4: '#8B5CF6', 5: '#F59E0B', 6: '#EF4444',
}

async function sendGift(item) {
  if (sending.value || remaining.value === 0) return
  sending.value = true
  lastResult.value = null
  try {
    const { data } = await giftApi.give(props.battleId, item.id, props.giftCount)
    lastResult.value = data
    if (data.accepted) {
      msg.success(`🎉 ${props.enemyName} 收下了礼物 — 人情章已入墨炉`)
      // 1.5s 后通知父组件战斗已被礼物结束
      setTimeout(() => emit('accepted', data), 1500)
    } else {
      msg.warning(`💢 ${props.enemyName} 拒绝了!`)
      emit('rejected', data)
      // 刷新背包(物品扣了 1)
      const inv = await inventoryApi.list()
      inventory.value = (inv.data.items || []).filter(it =>
        ['material', 'consumable', 'equipment'].includes(it.type)
      ).sort((a, b) => b.rarity - a.rarity)
    }
  } catch (e) {
    msg.error('赠礼失败: ' + e.message)
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <Transition name="gift-fade">
    <div v-if="visible" class="gift-overlay" @click.self="emit('close')">
      <div class="gift-card">
        <button class="gift-close" @click="emit('close')">×</button>

        <div class="gift-header">
          <img src="/images/ui/gift-box.png" class="gift-icon"
               @error="(e)=>{e.target.style.display='none'}" />
          <div>
            <h2>赠礼安抚</h2>
            <p>试图让 <strong>{{ enemyName }}</strong> 收下礼物离去</p>
            <p class="rem">本场剩余次数 <span class="rem-n">{{ remaining }}/3</span></p>
          </div>
        </div>

        <!-- 上次结果反馈 -->
        <Transition name="result-pop">
          <div v-if="lastResult" class="last-result" :class="{ accepted: lastResult.accepted }">
            {{ lastResult.accepted
                ? `✓ 接受了!人情章已入墨炉`
                : `✗ ${lastResult.message}` }}
            <span class="prob">(接受率 {{ Math.round((lastResult.accept_prob || 0) * 100) }}%)</span>
          </div>
        </Transition>

        <!-- 物品网格 -->
        <div v-if="remaining === 0" class="no-more">
          🥲 本场已用完 3 次机会,无法继续赠礼
        </div>
        <div v-else-if="inventory.length === 0" class="empty-inv">
          🎒 背包没有可赠之物
        </div>
        <div v-else class="item-grid">
          <button v-for="item in inventory" :key="item.id"
                  class="gift-item"
                  :disabled="sending"
                  :style="{ borderColor: RARITY_COLOR[item.rarity] + '88' }"
                  @click="sendGift(item)">
            <ItemIcon class="gi-icon" :item="item" :size="42" />
            <div class="gi-name" :style="{ color: RARITY_COLOR[item.rarity] }">
              {{ item.name }}
            </div>
            <div class="gi-rarity">{{ item.rarity_name }}</div>
            <div class="gi-count">×{{ item.count }}</div>
          </button>
        </div>

        <div class="gift-tip">
          💡 接受率 ≈ 物品稀有度 × 0.12 + 友好度 / 200 + 悟性 × 0.02 − 已送次数 × 0.18
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.gift-overlay {
  position: fixed; inset: 0;
  z-index: 250;
  display: flex; align-items: center; justify-content: center;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
}
.gift-card {
  position: relative;
  width: 90%; max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
  background: linear-gradient(180deg, rgba(40, 28, 12, 0.96), rgba(20, 12, 4, 0.98));
  border: 1px solid rgba(212, 162, 76, 0.5);
  border-radius: 14px;
  padding: 24px;
  color: #f0e0c0;
  font-family: 'STKaiti', 'KaiTi', serif;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8);
  animation: gift-pop 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}
@keyframes gift-pop {
  from { transform: scale(0.85) translateY(20px); opacity: 0; }
  to   { transform: scale(1) translateY(0); opacity: 1; }
}
.gift-close {
  position: absolute; top: 12px; right: 16px;
  background: none; border: none;
  color: #888; font-size: 24px;
  cursor: pointer;
}
.gift-close:hover { color: #FFE0A3; }

.gift-header {
  display: flex; gap: 16px; align-items: center;
  margin-bottom: 18px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(212, 162, 76, 0.25);
}
.gift-icon {
  width: 64px; height: 64px;
  border-radius: 8px;
  filter: drop-shadow(0 0 12px rgba(212, 162, 76, 0.5));
}
.gift-header h2 {
  margin: 0;
  color: #FFE0A3;
  font-size: 22px;
  letter-spacing: 4px;
}
.gift-header p { margin: 4px 0; font-size: 13px; color: #ccc; }
.gift-header strong { color: #FFB454; }
.rem { color: #aaa; }
.rem-n { color: #FFE0A3; font-weight: 700; font-family: 'SF Mono', monospace; }

.last-result {
  margin: 8px 0 16px;
  padding: 10px 14px;
  border-radius: 6px;
  background: rgba(192, 63, 63, 0.15);
  border: 1px solid rgba(192, 63, 63, 0.4);
  color: #FFCCCC;
  font-size: 13px;
  letter-spacing: 1px;
}
.last-result.accepted {
  background: rgba(82, 183, 136, 0.18);
  border-color: rgba(82, 183, 136, 0.5);
  color: #95D5B2;
}
.last-result .prob { font-size: 11px; color: #888; margin-left: 8px; }

.result-pop-enter-active { transition: all 0.3s; }
.result-pop-enter-from { opacity: 0; transform: scale(0.85); }

.no-more, .empty-inv {
  text-align: center; padding: 32px;
  color: #888; font-size: 14px;
  letter-spacing: 2px;
}

.item-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 10px;
}
.gift-item {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid;
  border-radius: 8px;
  padding: 10px 8px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex; flex-direction: column; gap: 3px;
  text-align: center;
  color: inherit;
  font-family: inherit;
}
.gift-item:hover:not(:disabled) {
  transform: translateY(-3px);
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.5);
}
.gift-item:disabled { opacity: 0.5; cursor: not-allowed; }
.gi-icon { margin: 0 auto; }
.gi-name { font-size: 12px; font-weight: 600; letter-spacing: 1px; }
.gi-rarity { font-size: 10px; color: #888; }
.gi-count { font-size: 11px; color: #FFE0A3; font-family: 'SF Mono', monospace; }

.gift-tip {
  margin-top: 18px;
  padding: 8px 12px;
  background: rgba(127, 199, 232, 0.06);
  border-left: 2px solid #7FC7E8;
  font-size: 11px;
  color: #aaa;
  border-radius: 4px;
  line-height: 1.6;
  letter-spacing: 0.5px;
  font-family: system-ui, monospace;
}

.gift-fade-enter-active, .gift-fade-leave-active { transition: opacity 0.3s; }
.gift-fade-enter-from, .gift-fade-leave-to { opacity: 0; }
</style>
