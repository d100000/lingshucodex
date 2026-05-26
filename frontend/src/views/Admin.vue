<script setup>
import { onMounted, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { siteApi } from '../api/client.js'
import BackButton from '../components/BackButton.vue'

const msg = useMessage()

const loading = ref(true)
const saving = ref(false)
const showBobdongAds = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await siteApi.config()
    showBobdongAds.value = !!data?.show_bobdong_ads
  } catch (e) {
    msg.error('读取站点配置失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const { data } = await siteApi.updateConfig({
      show_bobdong_ads: showBobdongAds.value,
    })
    showBobdongAds.value = !!data?.show_bobdong_ads
    msg.success('站点配置已保存')
  } catch (e) {
    msg.error('保存失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="admin-page">
    <header class="admin-head">
      <BackButton label="返回更多" inline to="/more" />
      <div>
        <p>ADMIN</p>
        <h1>管理后台</h1>
      </div>
    </header>

    <section class="panel">
      <div class="panel-title">
        <div>
          <span>站点展示</span>
          <h2>广告开关</h2>
        </div>
        <strong :class="{ on: showBobdongAds }">{{ showBobdongAds ? '显示中' : '已隐藏' }}</strong>
      </div>

      <label class="switch-row" :class="{ disabled: loading || saving }">
        <input v-model="showBobdongAds" type="checkbox" :disabled="loading || saving" />
        <span class="switch">
          <i></i>
        </span>
        <span class="copy">
          <strong>BobDong.cn 推广入口</strong>
          <small>控制入门页推荐卡、灵脉配置推荐条和快速入口。</small>
        </span>
      </label>

      <button class="save-btn" :disabled="loading || saving" @click="save">
        {{ saving ? '保存中...' : '保存设置' }}
      </button>
    </section>
  </main>
</template>

<style scoped>
.admin-page {
  min-height: var(--app-svh);
  padding: calc(24px + var(--safe-top)) max(18px, calc((100vw - 900px) / 2)) calc(92px + var(--safe-bottom));
  background:
    radial-gradient(circle at 20% 0%, rgba(127,199,232,0.12), transparent 30%),
    #0B0B14;
  color: #F3E4C3;
}

.admin-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.admin-head p {
  margin: 0 0 4px;
  color: #7FC7E8;
  font-size: 12px;
  letter-spacing: 2px;
  text-align: right;
}

.admin-head h1 {
  margin: 0;
  color: #FFE0A3;
  font-family: STKaiti, "KaiTi", serif;
  font-size: 30px;
  letter-spacing: 4px;
}

.panel {
  border: 1px solid rgba(212,162,76,0.28);
  background: rgba(15,15,28,0.88);
  padding: 18px;
  border-radius: 8px;
  box-shadow: 0 18px 40px rgba(0,0,0,0.28);
}

.panel-title {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(255,255,255,0.07);
}

.panel-title span {
  display: block;
  color: #9CA8BB;
  font-size: 12px;
  margin-bottom: 4px;
}

.panel-title h2 {
  margin: 0;
  color: #FFE0A3;
  font-size: 20px;
}

.panel-title strong {
  color: #9CA8BB;
  border: 1px solid rgba(156,168,187,0.35);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
}

.panel-title strong.on {
  color: #52B788;
  border-color: rgba(82,183,136,0.45);
}

.switch-row {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 14px;
  align-items: center;
  padding: 18px 0;
  cursor: pointer;
}

.switch-row.disabled {
  opacity: 0.58;
  cursor: wait;
}

.switch-row input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.switch {
  width: 54px;
  height: 30px;
  border-radius: 999px;
  background: rgba(156,168,187,0.22);
  border: 1px solid rgba(156,168,187,0.28);
  padding: 3px;
  transition: background 0.18s, border-color 0.18s;
}

.switch i {
  display: block;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #9CA8BB;
  transition: transform 0.18s, background 0.18s;
}

.switch-row input:checked + .switch {
  background: rgba(82,183,136,0.22);
  border-color: rgba(82,183,136,0.48);
}

.switch-row input:checked + .switch i {
  transform: translateX(24px);
  background: #52B788;
}

.copy strong {
  display: block;
  color: #F3E4C3;
  margin-bottom: 4px;
}

.copy small {
  color: #9CA8BB;
  font-size: 12px;
  line-height: 1.7;
}

.save-btn {
  width: 100%;
  min-height: 42px;
  border: 1px solid rgba(212,162,76,0.5);
  background: linear-gradient(135deg, #D4A24C, #B58A3E);
  color: #101522;
  border-radius: 6px;
  font-weight: 800;
  letter-spacing: 3px;
  cursor: pointer;
}

.save-btn:disabled {
  opacity: 0.5;
  cursor: wait;
}

@media (max-width: 600px) {
  .admin-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .admin-head p,
  .admin-head h1 {
    text-align: left;
  }
}
</style>
