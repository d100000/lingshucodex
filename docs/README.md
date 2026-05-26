# 灵枢笔录 · 文档导航

> 这里是 AI / 新接手者的入口。**直接读 ARCHITECTURE.md 通常就够了**。

---

## 📚 文档清单

| 文件 | 给谁看 | 一句话 |
|---|---|---|
| **[ARCHITECTURE.md](./ARCHITECTURE.md)** ⭐ | **AI / 开发者** | 项目骨架、文件作用、API 表、维护模板 |
| [CHANGELOG.md](./CHANGELOG.md) | 任何人 | 每个版本做了什么 |
| [GAME_OVERVIEW.md](./GAME_OVERVIEW.md) | 用户/运营 | 产品概览,5 派、113 怪、21 Boss |
| [GETTING_STARTED.md](./GETTING_STARTED.md) | 新玩家 | 从 0 到第一场战斗 |
| [PLAYER_GUIDE.md](./PLAYER_GUIDE.md) | 老玩家 | 攻略、Boss 解析、隐藏内容 |
| [TOKEN_CULTIVATION_PRODUCT_PLAN.md](./TOKEN_CULTIVATION_PRODUCT_PLAN.md) | 策划/开发 | 燃灵队列、小说化修行、token 转修为改造方案 |

---

## 🎯 5 秒接手指南(AI 必读)

**项目根**:`/Users/bobdong/项目/LingshuCodex/`

**技术栈**:
- 后端 Python 3.11 + FastAPI + httpx + WebSocket(`backend/app/`)
- 前端 Vue 3 + Vite + Naive UI(`frontend/src/`)
- LLM 网关:`https://bobdong.cn/v1`(OpenAI 协议兼容)

**启动**:
```bash
cd /Users/bobdong/项目/LingshuCodex && ./start.sh
# 后端 8020 · 前端 5173
```

**清理进程**:
```bash
lsof -ti:8020 | xargs -r kill -9
lsof -ti:5173 | xargs -r kill -9
```

**最近版本**:v5.1(2026-05-24)— 战斗系统升级 + 天命降临 + 战报卡

---

## 📁 核心代码定位(grep 友好)

```bash
# 后端
backend/app/main.py             FastAPI 入口,30+ 端点
backend/app/sects.py            5 大门派 + 天命招式
backend/app/enemies.py          113 怪物 12 族
backend/app/bosses.py           21 Boss 18 公司宗派
backend/app/cards.py            8 玩家卡牌
backend/app/items.py            55 物品(材料/丹药/法宝/灵宝/心法)
backend/app/monster_skills.py   48 怪物招式
backend/app/behaviors.py        12 族行为准则(后端写好,前端未集成)
backend/app/battle.py           BattleEngine 战斗引擎
backend/app/llm_client.py       LLM 调用 + 重试 + fallback
backend/app/health_check.py     probe + verify-key SSE
backend/app/store.py            内存存储(单玩家 MVP)

# 前端
frontend/src/router.js                 11 路由 + 守卫
frontend/src/api/client.js             8 个 *Api 命名空间
frontend/src/components/Logo.vue       SVG logo
frontend/src/components/ByokSettings.vue 灵脉配置 modal
frontend/src/views/Onboarding.vue      入门页(填 key + probe)
frontend/src/views/KeyVerify.vue       流式精细验证
frontend/src/views/Home.vue            修行主城(4 入口卡片)
frontend/src/views/ExploreMap.vue      仿真地图(怪物移动)
frontend/src/views/Battle.vue          战斗页 ★ 核心(三栏 + 天命)
frontend/src/views/Inventory.vue       背包
frontend/src/views/Items.vue           物品全集
frontend/src/views/Bosses.vue          修真名录(4 故事线)
frontend/src/views/NotFound.vue        404
```

---

## 🔥 v5.1 战斗系统亮点(本轮重点)

1. **48 个怪物招式** — 12 族 × 4 等级,每只怪物按等级动态选招式
2. **天命降临** — 每回合 5% 几率触发,整场可释放宗派独家神技 1 次
   - 沧澜:沧澜剑域·一笔诛仙
   - 天机:万象天衍·推演无敌
   - 必中必暴击 5x ATK
3. **三栏 Tab** — 招式 / 丹药 / 天命 / 撤退,天命栏默认 locked
4. **战报卡** — 每回合右侧推一张数值汇总卡
5. **关键字高亮** — LLM 叙事中的 `**xxx**` 自动转金色 / 红色 / 暴击金光
6. **卷轴 UI** — 叙事区双竹简边框 + 铜环

---

## 🐛 常见问题快速定位

| 症状 | 看哪 |
|---|---|
| 启动报错 | `/tmp/lingshu_backend.log` / `/tmp/lingshu_frontend.log` |
| 战斗第一回合后无法继续 | 已修复 v5.1(`battle.py` 末尾 yield state + turn_ready) |
| LLM 不出 `**xxx**` 重点 | `llm_client.py` BASE_SYSTEM_PROMPT 已加规则,但 LLM 不保证遵守 |
| 天命不触发 | 概率 5%/回合,改 `battle.py` 末尾 `random.random() < 0.05` |
| WS 连不上 | F12 看 Network → WS,确认 `/ws/battle/{id}` |
| 路由跳错 | `frontend/src/router.js` 守卫 + `frontend/src/api/client.js` 错误码 |

---

## 🛣️ TODO(下个版本可做)

- 怪物行为分化(`behaviors.py` 已写好,前端未集成 — 6 种移动模式)
- 怪物之间相遇时 LLM 对话(`behaviors.py` 有 fallback,API 未写)
- 开通玄机/青冥/月隐 3 派(需 bobdong.cn 支持 DeepSeek/GLM/Kimi)
- 真实持久化(SQLite + Alembic)
- 多用户(JWT 鉴权)
- BYOK 加密(目前内存明文)

---

**最后更新**:2026-05-24
**当前版本**:v5.1
