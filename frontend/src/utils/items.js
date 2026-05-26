/**
 * 全局物品字典 — 单源数据,懒加载缓存
 *
 * 用途:任何地方需要把后端给的 item_id (英文) 显示成中文 + icon,
 * 调用 getItemDisplay(id) 即可,自动 fallback 到原始 id。
 *
 * 用法:
 *   import { ensureItemMap, getItemDisplay, prettifyItem } from '@/utils/items.js'
 *   await ensureItemMap()                        // App 启动时调一次
 *   const { name, icon, icon_url } = getItemDisplay('item_qi_dust')
 *   prettifyItem('item_qi_dust')                 // → '⚪ 灵气尘' (字符串形式)
 *
 * 如果直接从后端拿到 {drop_name, drop_icon} 等已展平字段,优先用那个;
 * 这个 util 只是 fallback 场景。
 */
import { itemApi } from '../api/client.js'

const _cache = new Map()  // id → { name, icon, rarity }
let _loading = null       // Promise(去重并发拉)
let _loaded = false

export async function ensureItemMap() {
  if (_loaded) return _cache
  if (_loading) return _loading
  _loading = (async () => {
    try {
      const { data } = await itemApi.list()
      const arr = Array.isArray(data) ? data : (data?.items || [])
      for (const it of arr) {
        if (it && it.id) {
          _cache.set(it.id, {
            name: it.name || it.id,
            icon: it.icon || '🎁',
            icon_url: it.icon_url || `/images/items/${it.id}.png`,
            rarity: it.rarity || 1,
            rarity_name: it.rarity_name || '',
          })
        }
      }
      _loaded = true
    } catch (e) {
      console.warn('[items.js] 加载物品字典失败,后续依赖 fallback:', e?.message || e)
    } finally {
      _loading = null
    }
    return _cache
  })()
  return _loading
}

export function getItemDisplay(id) {
  if (!id) return { name: '', icon: '', rarity: 0 }
  const hit = _cache.get(id)
  if (hit) return hit
  // fallback:从 id 推断
  return {
    name: id,           // 没拿到字典 → 显示原始 id
    icon: '🎁',
    icon_url: `/images/items/${id}.png`,
    rarity: 1,
  }
}

export function prettifyItem(id) {
  if (!id) return ''
  const { name, icon } = getItemDisplay(id)
  return `${icon} ${name}`
}

export function itemName(id) {
  return getItemDisplay(id).name
}

export function itemIcon(id) {
  return getItemDisplay(id).icon
}

export function itemIconUrl(id) {
  return getItemDisplay(id).icon_url
}
