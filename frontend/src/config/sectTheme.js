/**
 * 灵枢笔录 · 五大门派统一主题配置
 *
 * 在每个页面 import 后,根据 character.sect / route 取对应主题。
 * 包含:
 *   - 配色(primary / accent / glow / background)
 *   - emoji / 中央图标
 *   - motto / 中文描述
 *   - 动效 keyframe 名(各页面用)
 *   - 战斗专属:屏幕震动颜色、暴击色、施法粒子、招式名前缀
 */

export const SECT_THEME = {
  canglan: {
    id: 'canglan',
    name: '沧澜剑派',
    short: '沧澜',
    emoji: '🗡️',
    flag: '/images/sects/flags/canglan.png',
    motto: '深思而后动 · 一击必中要害',
    /* 配色 */
    primary: '#0F1B2E',       // 主色:深墨蓝
    accent: '#D4A24C',         // 主点缀:鎏金
    glow: '#FFE0A3',           // 高光:浅金
    secondary: '#7FC7E8',      // 辅助:水墨蓝
    contrast: '#8B5A2B',       // 对比:暗木
    /* 战斗特效 */
    fx_cast_color: '#FFE0A3',           // 施法粒子色
    fx_crit_color: '#FFD700',           // 暴击文字色
    fx_hit_color: '#FFAA66',            // 普通命中色
    fx_aura: 'rgba(212,162,76,0.5)',    // 头像光圈
    fx_screen_tint: 'rgba(40,30,20,0.5)', // 屏幕滤镜
    /* 招式风格关键词 */
    skill_keywords: ['剑意', '墨痕', '九霄', '深远', '沧澜'],
    /* 中央动效 key(供 SectChoose / 战斗背景用)*/
    central_anim: 'fx-canglan',
    /* 字体偏好 */
    title_font: "'STKaiti','KaiTi','Source Han Serif SC',serif",
    /* 渐变背景 */
    bg_gradient: 'linear-gradient(180deg, #0a1024 0%, #1a1e3a 50%, #0a1024 100%)',
    /* 战斗页头像边框光晕 */
    avatar_glow: '0 0 32px rgba(212,162,76,0.5), inset 0 0 16px rgba(255,224,163,0.2)',
  },

  tianji: {
    id: 'tianji',
    name: '天机阁',
    short: '天机',
    emoji: '⚙️',
    flag: '/images/sects/flags/tianji.png',
    motto: '诸法皆通 · 万象归一',
    primary: '#1B1A2E',
    accent: '#FFB454',          // 橘金
    glow: '#FFDEA3',
    secondary: '#9B59B6',
    contrast: '#FF7F50',
    fx_cast_color: '#FFDEA3',
    fx_crit_color: '#FFA500',
    fx_hit_color: '#FFB454',
    fx_aura: 'rgba(255,180,84,0.5)',
    fx_screen_tint: 'rgba(50,40,20,0.5)',
    skill_keywords: ['机关', '万象', '齿轮', '诸法', '运筹'],
    central_anim: 'fx-tianji',
    title_font: "'STKaiti','KaiTi','Source Han Serif SC',serif",
    bg_gradient: 'linear-gradient(180deg, #1a0a1a 0%, #3a2a1a 50%, #1a0a1a 100%)',
    avatar_glow: '0 0 32px rgba(255,180,84,0.5), inset 0 0 16px rgba(255,222,163,0.2)',
  },

  xuanji: {
    id: 'xuanji',
    name: '玄机宗',
    short: '玄机',
    emoji: '🧠',
    flag: '/images/sects/flags/xuanji.png',
    motto: '推演天机 · 一击必透',
    primary: '#1E1B2E',
    accent: '#9B59B6',          // 深紫
    glow: '#C8A6DD',
    secondary: '#7B68EE',
    contrast: '#FF1493',
    fx_cast_color: '#C8A6DD',
    fx_crit_color: '#FF00FF',
    fx_hit_color: '#9B59B6',
    fx_aura: 'rgba(155,89,182,0.5)',
    fx_screen_tint: 'rgba(40,20,50,0.5)',
    skill_keywords: ['推演', '深思', '布局', '终南', '幻方'],
    central_anim: 'fx-xuanji',
    title_font: "'STKaiti','KaiTi','Source Han Serif SC',serif",
    bg_gradient: 'linear-gradient(180deg, #0a0a24 0%, #2a1e3a 50%, #0a0a24 100%)',
    avatar_glow: '0 0 32px rgba(155,89,182,0.5), inset 0 0 16px rgba(200,166,221,0.2)',
  },

  qingming: {
    id: 'qingming',
    name: '青冥派',
    short: '青冥',
    emoji: '📜',
    flag: '/images/sects/flags/qingming.png',
    motto: '博学根基 · 中文为本',
    primary: '#1A2E20',
    accent: '#52B788',          // 翠玉
    glow: '#95D5B2',
    secondary: '#3A6B6E',
    contrast: '#D4A24C',
    fx_cast_color: '#95D5B2',
    fx_crit_color: '#52B788',
    fx_hit_color: '#52B788',
    fx_aura: 'rgba(82,183,136,0.5)',
    fx_screen_tint: 'rgba(20,40,30,0.5)',
    skill_keywords: ['典籍', '诗韵', '学海', '根基', '青冥'],
    central_anim: 'fx-qingming',
    title_font: "'STKaiti','KaiTi','Source Han Serif SC',serif",
    bg_gradient: 'linear-gradient(180deg, #0a1a14 0%, #1a3a2a 50%, #0a1a14 100%)',
    avatar_glow: '0 0 32px rgba(82,183,136,0.5), inset 0 0 16px rgba(149,213,178,0.2)',
  },

  yueyin: {
    id: 'yueyin',
    name: '月隐宫',
    short: '月隐',
    emoji: '🌙',
    flag: '/images/sects/flags/yueyin.png',
    motto: '千古不忘 · 月隐千年',
    primary: '#1F1A2E',
    accent: '#B59CFF',          // 银紫
    glow: '#D9CCFF',
    secondary: '#4A4E69',
    contrast: '#FFD700',
    fx_cast_color: '#D9CCFF',
    fx_crit_color: '#E6E6FA',
    fx_hit_color: '#B59CFF',
    fx_aura: 'rgba(181,156,255,0.5)',
    fx_screen_tint: 'rgba(30,20,50,0.5)',
    skill_keywords: ['月华', '记忆', '千年', '暗影', '夜阑'],
    central_anim: 'fx-yueyin',
    title_font: "'STKaiti','KaiTi','Source Han Serif SC',serif",
    bg_gradient: 'linear-gradient(180deg, #0a0a1f 0%, #1f1a3a 50%, #0a0a1f 100%)',
    avatar_glow: '0 0 32px rgba(181,156,255,0.5), inset 0 0 16px rgba(217,204,255,0.2)',
  },
}

/** 默认主题(未选派或异常时) */
export const DEFAULT_THEME = SECT_THEME.canglan

/** 取门派主题 */
export function getSectTheme(sectId) {
  return SECT_THEME[sectId] || DEFAULT_THEME
}

/** 取门派背景图(战斗页头像左/右色调用) */
export function getSectAuraGradient(sectId) {
  const t = getSectTheme(sectId)
  return `radial-gradient(ellipse at 25% 50%, ${t.accent}22, transparent 40%),
          radial-gradient(ellipse at 75% 50%, ${t.contrast}22, transparent 40%)`
}

/** 给战斗页 / 主城用的 CSS variables 集合 */
export function getSectCssVars(sectId) {
  const t = getSectTheme(sectId)
  return {
    '--sect-primary': t.primary,
    '--sect-accent': t.accent,
    '--sect-glow': t.glow,
    '--sect-secondary': t.secondary,
    '--sect-contrast': t.contrast,
    '--sect-aura': t.fx_aura,
    '--sect-cast': t.fx_cast_color,
    '--sect-crit': t.fx_crit_color,
    '--sect-hit': t.fx_hit_color,
  }
}
