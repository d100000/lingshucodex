import { createRouter, createWebHashHistory } from 'vue-router'
import { characterApi, battleApi } from './api/client.js'
import { useGameStore } from './stores/game.js'
import { useAuthStore } from './stores/auth.js'

const routes = [
  {
    path: '/',
    component: () => import('./views/WelcomePage.vue'),
    meta: { title: '灵枢笔录 · Lingshu Codex', publicAccess: true, hideMobileTabBar: true, showQueueBar: false, hideFeedback: true },
  },

  // ★ Phase C: 登录页(无需 auth)
  {
    path: '/login',
    component: () => import('./views/Login.vue'),
    meta: { title: '登录 · 灵枢笔录', publicAccess: true, hideMobileTabBar: true, showQueueBar: false, hideFeedback: true },
  },

  {
    path: '/onboarding',
    component: () => import('./views/Onboarding.vue'),
    meta: { title: '入门 · 灵枢笔录', requireAuth: true, hideMobileTabBar: true, showQueueBar: false, guardLeave: true },
  },

  {
    path: '/sect-choose',
    component: () => import('./views/SectChoose.vue'),
    meta: { title: '选派 · 灵枢笔录', hideMobileTabBar: true, showQueueBar: false, guardLeave: true },
  },

  {
    path: '/key-verify/:sectId',
    component: () => import('./views/KeyVerify.vue'),
    meta: { title: '灵脉验证 · 灵枢笔录', hideMobileTabBar: true, showQueueBar: false, guardLeave: true },
  },

  {
    path: '/initiation/:sectId',
    component: () => import('./views/Initiation.vue'),
    meta: { title: '拜入师门 · 灵枢笔录', hideMobileTabBar: true, showQueueBar: false, guardLeave: true },
  },

  {
    path: '/home',
    component: () => import('./views/Home.vue'),
    meta: { title: '修行 · 灵枢笔录', requireCharacter: true, mobileTab: 'home' },
  },

  {
    path: '/explore',
    component: () => import('./views/ExploreMap.vue'),
    meta: { title: '修行地图 · 灵枢笔录', requireCharacter: true, mobileTab: 'explore', showMapStatusBar: true },
  },

  {
    path: '/inventory',
    component: () => import('./views/Inventory.vue'),
    meta: { title: '背包 · 灵枢笔录', requireCharacter: true, mobileTab: 'inventory' },
  },

  {
    path: '/items',
    component: () => import('./views/Items.vue'),
    meta: { title: '修行物品 · 灵枢笔录', requireCharacter: true, mobileTab: 'more' },
  },

  {
    path: '/bosses',
    component: () => import('./views/Bosses.vue'),
    meta: { title: '修真名录 · 灵枢笔录', requireCharacter: true, mobileTab: 'more' },
  },

  {
    path: '/bestiary',
    component: () => import('./views/Bestiary.vue'),
    meta: { title: '山海经图鉴 · 灵枢笔录', requireCharacter: true, mobileTab: 'more' },
  },

  {
    path: '/craft',
    component: () => import('./views/Craft.vue'),
    meta: { title: '炼丹炼器 · 灵枢笔录', requireCharacter: true, mobileTab: 'more' },
  },

  {
    path: '/skills',
    component: () => import('./views/Skills.vue'),
    meta: { title: '修行心法 · 灵枢笔录', requireCharacter: true, mobileTab: 'more' },
  },

  {
    path: '/journal',
    component: () => import('./views/Journal.vue'),
    meta: { title: '修行录 · 灵枢笔录', requireCharacter: true, mobileTab: 'more' },
  },

  {
    path: '/novel',
    component: () => import('./views/NovelBook.vue'),
    meta: { title: '本命书 · 灵枢笔录', requireCharacter: true, mobileTab: 'novel' },
  },

  {
    path: '/novel/chapter/:id',
    component: () => import('./views/NovelChapter.vue'),
    meta: { title: '本命书章节 · 灵枢笔录', requireCharacter: true, mobileTab: 'novel', hideMobileTabBar: true },
  },

  {
    path: '/more',
    component: () => import('./views/More.vue'),
    meta: { title: '更多 · 灵枢笔录', requireCharacter: true, mobileTab: 'more' },
  },

  {
    path: '/admin',
    redirect: '/admin-console',
  },

  {
    path: '/admin-console/login',
    component: () => import('./views/AdminLogin.vue'),
    meta: { title: '管理后台入口 · 灵枢笔录', publicAccess: true, hideMobileTabBar: true, showQueueBar: false, hideFeedback: true },
  },

  {
    path: '/admin-console',
    component: () => import('./views/AdminConsole.vue'),
    meta: { title: '用户管理后台 · 灵枢笔录', requireAuth: true, requireAdmin: true, hideMobileTabBar: true, showQueueBar: false, hideFeedback: true },
  },

  {
    path: '/battle/:id',
    component: () => import('./views/Battle.vue'),
    meta: { title: '战斗 · 灵枢笔录', requireCharacter: true, requireBattle: true, mobileImmersive: true, hideMobileTabBar: true, guardLeave: true },
  },

  {
    path: '/404',
    component: () => import('./views/NotFound.vue'),
    meta: { title: '404 · 灵枢笔录', hideMobileTabBar: true, showQueueBar: false },
  },

  // catch-all 任何未匹配路径
  {
    path: '/:pathMatch(.*)*',
    redirect: to => ({
      path: '/404',
      query: { from: to.fullPath, reason: '路径不存在' },
    }),
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// 全局前置守卫:统一处理"需要登录 / 需要角色 / 需要战斗"的访问校验
router.beforeEach(async (to, from, next) => {
  // 设置 title
  if (to.meta.title) document.title = to.meta.title

  const game = useGameStore()
  const auth = useAuthStore()
  const isAdminRoute = to.path.startsWith('/admin-console') || to.path === '/admin'

  // === 0. 鉴权:除 publicAccess 页面外都必须登录 ===
  const PUBLIC_PATHS = ['/login']
  const isPublic = to.meta.publicAccess || PUBLIC_PATHS.includes(to.path) || to.path === '/'
  if (!isPublic && !auth.isLoggedIn) {
    return next({ path: isAdminRoute ? '/admin-console/login' : '/login', query: { redirect: to.fullPath } })
  }
  // 已登录访问 /login → 直接跳 home
  if (auth.isLoggedIn && to.path === '/login') {
    return next('/home')
  }
  if (auth.isLoggedIn && auth.isAdmin && to.path === '/admin-console/login') {
    return next('/admin-console')
  }

  if (to.meta.requireAdmin && !auth.isAdmin) {
    return next(isAdminRoute
      ? { path: '/admin-console/login', query: { redirect: to.fullPath, error: 'admin_required' } }
      : { path: '/home', query: { error: 'admin_required', msg: '需要管理员权限' } })
  }

  // === 1. 需要角色的页面(/home, /battle/*) ===
  if (to.meta.requireCharacter) {
    if (!game.character) {
      try {
        const { data } = await characterApi.me()
        game.setCharacter(data)
      } catch (e) {
        // 没角色 → 跳入门页(从这开始填 key + 选派)
        return next({
          path: '/onboarding',
          query: { reason: '请先填写 API Key 并选择门派' },
        })
      }
    }
  }

  // === 2. 需要战斗的页面(/battle/:id) ===
  if (to.meta.requireBattle) {
    const battleId = to.params.id
    if (!battleId || typeof battleId !== 'string' || battleId.length < 4) {
      return next({
        path: '/home',
        query: { error: 'battle_invalid_id', msg: '战斗编号格式不正确' },
      })
    }
    try {
      await battleApi.get(battleId)
    } catch (e) {
      // 战斗不存在 / 已结束 → 跳主城,带错误提示
      const msg = e.code === 'BATTLE_NOT_FOUND'
        ? '该战斗不存在或已结束'
        : (e.message || '无法进入此战斗')
      return next({
        path: '/home',
        query: { error: 'battle_not_found', msg },
      })
    }
  }

  next()
})

// 路由后置:失败时容错
router.onError((err) => {
  console.error('[router error]', err)
  // 动态 import 失败(网络/chunk 丢失)→ 强制刷新一次
  if (/Loading chunk \w+ failed|Failed to fetch dynamically imported/i.test(err.message)) {
    setTimeout(() => location.reload(), 800)
  }
})

export default router
