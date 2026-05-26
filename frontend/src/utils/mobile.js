export const MOBILE_RESUME_EVENT = 'lingshu:resume'
export const MOBILE_FEEDBACK_EVENT = 'lingshu:feedback'

export function syncViewportVars() {
  if (typeof window === 'undefined') return
  const vv = window.visualViewport
  const h = vv?.height || window.innerHeight
  const w = vv?.width || window.innerWidth
  const root = document.documentElement
  root.style.setProperty('--visual-vh', `${h}px`)
  root.style.setProperty('--visual-vw', `${w}px`)
  root.style.setProperty('--app-orientation', w > h ? 'landscape' : 'portrait')
}

export function installViewportSync() {
  if (typeof window === 'undefined') return () => {}
  syncViewportVars()
  const opts = { passive: true }
  window.visualViewport?.addEventListener('resize', syncViewportVars, opts)
  window.visualViewport?.addEventListener('scroll', syncViewportVars, opts)
  window.addEventListener('resize', syncViewportVars, opts)
  window.addEventListener('orientationchange', syncViewportVars, opts)
  return () => {
    window.visualViewport?.removeEventListener('resize', syncViewportVars)
    window.visualViewport?.removeEventListener('scroll', syncViewportVars)
    window.removeEventListener('resize', syncViewportVars)
    window.removeEventListener('orientationchange', syncViewportVars)
  }
}

export function dispatchResume(reason = 'manual') {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(MOBILE_RESUME_EVENT, {
    detail: { reason, at: Date.now() },
  }))
}

export function openFeedback(payload = {}) {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(MOBILE_FEEDBACK_EVENT, { detail: payload }))
}

export function logTelemetry(type, payload = {}) {
  if (typeof window === 'undefined') return
  try {
    const key = 'lingshu_telemetry_buffer'
    const list = JSON.parse(localStorage.getItem(key) || '[]')
    list.push({
      type,
      payload,
      route: window.location.hash || window.location.pathname,
      at: new Date().toISOString(),
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
        orientation: window.innerWidth > window.innerHeight ? 'landscape' : 'portrait',
      },
    })
    localStorage.setItem(key, JSON.stringify(list.slice(-80)))
  } catch (_) {}
}

export function readTelemetry() {
  if (typeof window === 'undefined') return []
  try {
    return JSON.parse(localStorage.getItem('lingshu_telemetry_buffer') || '[]')
  } catch (_) {
    return []
  }
}

export function vibrate(pattern = 30) {
  if (typeof navigator === 'undefined') return
  try {
    if (navigator.vibrate) navigator.vibrate(pattern)
  } catch (_) {}
}
