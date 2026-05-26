import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useGameStore = defineStore('game', () => {
  const character = ref(null)
  const sects = ref([])

  function setCharacter(c) { character.value = c }
  function setSects(s) { sects.value = s }
  function clear() { character.value = null }

  /** 轻量更新 — 只 patch 部分字段(不走 /me 接口) */
  function patchCharacter(partial) {
    if (!character.value) return
    Object.assign(character.value, partial)
  }

  return {
    character, sects,
    setCharacter, setSects, clear, patchCharacter,
  }
})
