<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { adminApi } from '../api/client.js'
import { useAuthStore } from '../stores/auth.js'

const router = useRouter()
const route = useRoute()
const msg = useMessage()
const auth = useAuthStore()

const loading = ref(true)
const submitting = ref(false)
const needsSetup = ref(false)
const username = ref('')
const password = ref('')
const passwordConfirm = ref('')
const errorText = ref('')

async function loadStatus() {
  loading.value = true
  errorText.value = ''
  try {
    const { data } = await adminApi.bootstrapStatus()
    needsSetup.value = !!data?.needs_setup
  } catch (e) {
    errorText.value = e.message || '无法读取管理后台状态'
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (submitting.value) return
  const name = username.value.trim()
  if (name.length < 2 || name.length > 32) {
    errorText.value = '账号名长度需 2-32'
    return
  }
  if (password.value.length < 8) {
    errorText.value = '管理后台密码至少 8 位'
    return
  }
  if (needsSetup.value && password.value !== passwordConfirm.value) {
    errorText.value = '两次密码不一致'
    return
  }
  submitting.value = true
  errorText.value = ''
  try {
    if (needsSetup.value) {
      await auth.adminBootstrap(name, password.value)
      msg.success('管理后台已初始化')
    } else {
      await auth.adminLogin(name, password.value)
      msg.success('已进入管理后台')
    }
    router.replace(route.query.redirect || '/admin-console')
  } catch (e) {
    errorText.value = e.message || '登录失败'
  } finally {
    submitting.value = false
  }
}

onMounted(loadStatus)
</script>

<template>
  <main class="admin-login">
    <section class="entry-card">
      <div class="eyebrow">LINGSHU CODEX ADMIN</div>
      <h1>{{ needsSetup ? '初始化管理后台' : '管理后台登录' }}</h1>
      <p class="subcopy">
        {{ needsSetup ? '首次进入需要配置管理员账号和密码，凭据将写入服务器数据库。' : '请输入已配置的管理员账号进入控制台。' }}
      </p>

      <div v-if="loading" class="state">读取后台状态中...</div>
      <form v-else class="form" @submit.prevent="submit">
        <label>
          <span>账号名</span>
          <input v-model="username" autocomplete="username" maxlength="32" />
        </label>
        <label>
          <span>密码</span>
          <input
            v-model="password"
            type="password"
            :autocomplete="needsSetup ? 'new-password' : 'current-password'"
          />
        </label>
        <label v-if="needsSetup">
          <span>确认密码</span>
          <input v-model="passwordConfirm" type="password" autocomplete="new-password" />
        </label>
        <p v-if="errorText" class="error">{{ errorText }}</p>
        <button :disabled="submitting">
          {{ submitting ? '处理中...' : (needsSetup ? '创建管理员并进入' : '进入控制台') }}
        </button>
      </form>
    </section>
  </main>
</template>

<style scoped>
.admin-login {
  min-height: var(--app-svh);
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    linear-gradient(135deg, rgba(9, 14, 24, 0.94), rgba(12, 10, 18, 0.98)),
    #080A12;
  color: #F3E4C3;
}

.entry-card {
  width: min(420px, 100%);
  border: 1px solid rgba(212, 162, 76, 0.28);
  border-radius: 8px;
  background: rgba(13, 18, 30, 0.96);
  padding: 26px;
  box-shadow: 0 22px 70px rgba(0, 0, 0, 0.42);
}

.eyebrow {
  color: #7FC7E8;
  font-size: 12px;
  letter-spacing: 2px;
  margin-bottom: 10px;
}

h1 {
  margin: 0;
  color: #FFE0A3;
  font-size: 28px;
}

.subcopy {
  margin: 10px 0 22px;
  color: #9CA8BB;
  line-height: 1.7;
}

.state {
  padding: 18px;
  color: #9CA8BB;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.04);
}

.form {
  display: grid;
  gap: 14px;
}

label {
  display: grid;
  gap: 7px;
  color: #C9A876;
  font-size: 13px;
}

input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(212, 162, 76, 0.28);
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.28);
  color: #F3E4C3;
  min-height: 40px;
  padding: 0 12px;
  font: inherit;
}

input:focus {
  outline: none;
  border-color: rgba(127, 199, 232, 0.65);
  box-shadow: 0 0 0 2px rgba(127, 199, 232, 0.12);
}

.error {
  margin: 0;
  color: #FF8888;
  font-size: 13px;
}

button {
  min-height: 42px;
  border: 1px solid rgba(212, 162, 76, 0.5);
  border-radius: 6px;
  background: linear-gradient(135deg, #D4A24C, #B58A3E);
  color: #101522;
  font-weight: 800;
  cursor: pointer;
}

button:disabled {
  opacity: 0.55;
  cursor: wait;
}
</style>
