<!--
  Login.vue — 登录 / 注册 (同页 tab 切换)
-->
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useAuthStore } from '../stores/auth.js'
import Logo from '../components/Logo.vue'
import SectBackground from '../components/SectBackground.vue'

const router = useRouter()
const route = useRoute()
const msg = useMessage()
const auth = useAuthStore()

const tab = ref('login')   // 'login' | 'register'
const username = ref('')
const password = ref('')
const passwordConfirm = ref('')
const submitting = ref(false)

const tip = ref('')

onMounted(() => {
  // 如果已登录,直接跳目标
  if (auth.isLoggedIn) {
    router.replace(route.query.redirect || '/home')
  }
})

async function submit() {
  if (submitting.value) return
  if (!username.value.trim()) { tip.value = '请输入道号(用户名)'; return }
  if (password.value.length < 4) { tip.value = '密码至少 4 位'; return }
  if (tab.value === 'register' && password.value !== passwordConfirm.value) {
    tip.value = '两次密码不一致'
    return
  }
  tip.value = ''
  submitting.value = true
  try {
    if (tab.value === 'login') {
      const u = await auth.login(username.value.trim(), password.value)
      msg.success(`欢迎归来,${u.username}!`)
    } else {
      const u = await auth.register(username.value.trim(), password.value)
      msg.success(`道号 ${u.username} 已开,踏入修行!`)
    }
    const dest = route.query.redirect || '/home'
    router.replace(dest)
  } catch (e) {
    tip.value = e?.message || '操作失败'
    msg.error(tip.value)
  } finally {
    submitting.value = false
  }
}

function switchTab(t) {
  tab.value = t
  tip.value = ''
}
</script>

<template>
  <div class="login-page">
    <SectBackground sect-id="canglan" overlay="dark" :opacity="0.5" />

    <div class="login-card">
      <div class="beta-badge" aria-label="Beta 内测版本">BETA · 内测</div>
      <div class="brand">
        <Logo :size="48" :show-text="true" :text-size="22" />
        <div class="brand-sub">执笔者,记录天地修行</div>
      </div>

      <div class="tab-bar">
        <button :class="['tab', { active: tab === 'login' }]" @click="switchTab('login')">登录</button>
        <button :class="['tab', { active: tab === 'register' }]" @click="switchTab('register')">注册</button>
      </div>

      <form class="form" @submit.prevent="submit">
        <div class="field">
          <label>道号</label>
          <input v-model="username" type="text" maxlength="32" autocomplete="username"
                 placeholder="2-32 字符" />
        </div>
        <div class="field">
          <label>玄令(密码)</label>
          <input v-model="password" type="password" minlength="4"
                 :autocomplete="tab === 'login' ? 'current-password' : 'new-password'"
                 placeholder="至少 4 位" />
        </div>
        <div class="field" v-if="tab === 'register'">
          <label>再次玄令</label>
          <input v-model="passwordConfirm" type="password" autocomplete="new-password" />
        </div>

        <div class="tip" v-if="tip">⚠ {{ tip }}</div>

        <button class="submit-btn" type="submit" :disabled="submitting">
          {{ submitting ? '…' : (tab === 'login' ? '⇲ 入门' : '★ 开宗') }}
        </button>
      </form>

      <div class="foot-hint">
        <span v-if="tab === 'login'">还未拜师 ? <a @click="switchTab('register')">注册新道号</a></span>
        <span v-else>已有道号 ? <a @click="switchTab('login')">回主登录</a></span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  display: flex; align-items: center; justify-content: center;
  padding: 40px 20px;
}
.login-card {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 380px;
  padding: 32px 28px 24px;
  background: linear-gradient(180deg, rgba(15, 27, 46, 0.92), rgba(8, 12, 24, 0.96));
  border: 1px solid rgba(212, 162, 76, 0.32);
  border-radius: 14px;
  backdrop-filter: blur(10px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6);
}
.beta-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  padding: 0 9px;
  border: 1px solid rgba(212, 162, 76, 0.42);
  border-radius: 999px;
  background: rgba(212, 162, 76, 0.12);
  color: #FFE0A3;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 1px;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  box-shadow: 0 0 16px rgba(212, 162, 76, 0.12);
}
.brand {
  text-align: center;
  margin-bottom: 22px;
}
.brand-sub {
  color: #888;
  font-size: 12px;
  font-family: 'STKaiti', serif;
  letter-spacing: 4px;
  margin-top: 6px;
}
.tab-bar {
  display: flex;
  border-bottom: 1px solid rgba(212, 162, 76, 0.18);
  margin-bottom: 22px;
}
.tab {
  flex: 1;
  background: transparent;
  border: none;
  color: #888;
  padding: 10px 0;
  font-size: 14px;
  letter-spacing: 4px;
  font-family: 'STKaiti', serif;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}
.tab.active {
  color: #FFE0A3;
  border-bottom-color: #D4A24C;
}
.form .field {
  margin-bottom: 14px;
}
.form label {
  display: block;
  font-size: 12px;
  color: #C9A876;
  font-family: 'STKaiti', serif;
  letter-spacing: 2px;
  margin-bottom: 6px;
}
.form input {
  width: 100%;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(212, 162, 76, 0.25);
  color: #FFE0A3;
  padding: 9px 12px;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.18s, box-shadow 0.18s;
  box-sizing: border-box;
}
.form input:focus {
  border-color: rgba(212, 162, 76, 0.6);
  box-shadow: 0 0 0 2px rgba(212, 162, 76, 0.12);
}
.tip {
  color: #FF8888;
  font-size: 12px;
  margin: 8px 0 6px;
  letter-spacing: 1px;
}
.submit-btn {
  width: 100%;
  margin-top: 8px;
  background: linear-gradient(135deg, #D4A24C, #B58A3E);
  border: none;
  color: #0F1B2E;
  padding: 11px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: bold;
  letter-spacing: 6px;
  cursor: pointer;
  font-family: 'STKaiti', serif;
  transition: transform 0.18s, box-shadow 0.18s;
}
.submit-btn:hover:not([disabled]) {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(212, 162, 76, 0.4);
}
.submit-btn[disabled] {
  opacity: 0.4;
  cursor: wait;
}
.foot-hint {
  text-align: center;
  margin-top: 18px;
  font-size: 12px;
  color: #888;
  font-family: 'STKaiti', serif;
}
.foot-hint a {
  color: #D4A24C;
  cursor: pointer;
  margin-left: 4px;
  border-bottom: 1px dotted rgba(212, 162, 76, 0.5);
}
.foot-hint a:hover { color: #FFE0A3; }
@media (max-width: 420px) {
  .login-page {
    padding: 24px 14px;
  }
  .login-card {
    padding: 34px 18px 22px;
  }
  .beta-badge {
    top: 10px;
    right: 10px;
    height: 22px;
    padding: 0 8px;
    font-size: 9px;
  }
}
</style>
