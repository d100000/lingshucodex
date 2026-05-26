<script setup>
import { useRouter, useRoute } from 'vue-router'
import Logo from '../components/Logo.vue'

const router = useRouter()
const route = useRoute()

// 路由跳来时可以带 reason / from query 告诉用户为什么到这
const reason = route.query.reason || ''
const from = route.query.from || ''

function goHome() {
  router.replace('/')
}
</script>

<template>
  <div class="nf-page">
    <div class="nf-card">
      <Logo :size="84" :show-text="false" />

      <div class="code">404</div>
      <h1>此地非修仙之所</h1>
      <p class="sub">你访问的灵域并不存在,或已飞升渡劫。</p>

      <div v-if="reason || from" class="meta">
        <div v-if="from"><span class="k">原路径:</span> <code>{{ from }}</code></div>
        <div v-if="reason"><span class="k">原因:</span> {{ reason }}</div>
      </div>

      <button class="btn" @click="goHome">回到主城</button>
    </div>
  </div>
</template>

<style scoped>
.nf-page {
  min-height: 100vh;
  background: radial-gradient(ellipse at center, #1a1a2e 0%, #0a0a14 80%);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.nf-card {
  max-width: 480px; width: 100%;
  text-align: center;
  background: rgba(22,22,42,0.5);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(212,162,76,0.2);
  border-radius: 16px;
  padding: 50px 40px;
}
.code {
  font-size: 96px;
  font-weight: 200;
  letter-spacing: 12px;
  background: linear-gradient(135deg, #D4A24C 0%, #FFE0A3 50%, #D4A24C 100%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 24px 0 8px;
  font-family: 'SF Mono', Menlo, monospace;
}
h1 {
  font-size: 22px; margin: 0 0 12px;
  color: #D4A24C; letter-spacing: 4px;
  font-family: 'STKaiti','KaiTi',serif;
  font-weight: 500;
}
.sub {
  color: #aaa; font-size: 14px;
  margin: 0 0 24px; line-height: 1.7;
}
.meta {
  background: rgba(0,0,0,0.3);
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 13px;
  color: #888;
  margin: 16px 0 24px;
  text-align: left;
}
.meta .k { color: #aaa; margin-right: 6px; }
.meta code {
  color: #7FC7E8;
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 12px;
}
.btn {
  background: linear-gradient(135deg, #D4A24C, #B58A3E);
  border: none; color: #1a1a2e;
  padding: 12px 36px; border-radius: 8px;
  font-size: 14px; font-weight: 600;
  cursor: pointer;
  letter-spacing: 2px;
}
.btn:hover {
  box-shadow: 0 6px 24px rgba(212,162,76,0.4);
}
</style>
