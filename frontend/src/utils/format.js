/**
 * 数值格式化 — 仙侠数值膨胀后的友好显示
 *
 * formatNum(12345)    → "1.2万"
 * formatNum(1234567)  → "123.5万"
 * formatNum(123456789) → "1.2亿"
 * formatNum(999)       → "999"
 */
export function formatNum(n) {
  if (n == null) return '0'
  const v = Math.abs(n)
  const sign = n < 0 ? '-' : ''
  if (v >= 1e8) return sign + (v / 1e8).toFixed(1).replace(/\.0$/, '') + '亿'
  if (v >= 1e4) return sign + (v / 1e4).toFixed(1).replace(/\.0$/, '') + '万'
  return sign + Math.round(v).toString()
}

/**
 * 精确版 — 条形文字用(保留完整数字 + 千分位)
 * formatFull(12345) → "12,345"
 */
export function formatFull(n) {
  if (n == null) return '0'
  return Math.round(n).toLocaleString('zh-CN')
}
