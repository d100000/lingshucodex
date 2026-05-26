import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, adminApi } from '../api/client.js'

export const useAuthStore = defineStore('auth', () => {
  // 从 localStorage 初始化(刷新页面保持登录)
  const token = ref(localStorage.getItem('auth_token') || '')
  const user  = ref(JSON.parse(localStorage.getItem('auth_user') || 'null'))

  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const isAdmin    = computed(() => !!user.value?.is_admin)

  function _persist() {
    if (token.value) localStorage.setItem('auth_token', token.value)
    else             localStorage.removeItem('auth_token')
    if (user.value)  localStorage.setItem('auth_user', JSON.stringify(user.value))
    else             localStorage.removeItem('auth_user')
  }

  async function login(username, password) {
    const { data } = await authApi.login(username, password)
    token.value = data.token
    user.value  = data.user
    _persist()
    return data.user
  }

  async function register(username, password) {
    const { data } = await authApi.register(username, password)
    token.value = data.token
    user.value  = data.user
    _persist()
    return data.user
  }

  async function adminLogin(username, password) {
    const { data } = await adminApi.login(username, password)
    token.value = data.token
    user.value = data.user
    _persist()
    return data.user
  }

  async function adminBootstrap(username, password) {
    const { data } = await adminApi.bootstrap(username, password)
    token.value = data.token
    user.value = data.user
    _persist()
    return data.user
  }

  async function refresh() {
    if (!token.value) return null
    try {
      const { data } = await authApi.me()
      user.value = data
      _persist()
      return data
    } catch (_e) {
      logout()
      return null
    }
  }

  function logout() {
    token.value = ''
    user.value  = null
    _persist()
  }

  return { token, user, isLoggedIn, isAdmin, login, register, adminLogin, adminBootstrap, refresh, logout }
})
