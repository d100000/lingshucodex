# 灵枢笔录 · 全面 Review + 开发路线图

> 最后更新: 2026-05-24

---

## 一、系统 Review 总览

### 1.1 已完成模块清单

| 系统 | 后端 | 前端 | 状态 |
|------|------|------|------|
| BYOK 探测 + 验证 | `health_check.py` probe + stream_verify | `Onboarding.vue` + `KeyVerify.vue` | ✅ 完整 |
| 5 门派配置(9 境界) | `sects.py` 含飞升期 | `SectChoose.vue` 沉浸式 | ✅ 完整 |
| 8 属性系统 | `attributes.py` derive_stats + random_bless | `Home.vue` 八角雷达 + `StatusBar.vue` | ✅ 完整 |
| 战斗引擎 v2 | `battle.py` events_queue + fire-and-forget LLM | `Battle.vue` 双协程 WS | ✅ 完整 |
| 三档 LLM 分级 | `llm_client.py` pick_narration_model | Battle AI HUD | ✅ 完整 |
| 预生成叙事池 | warmup_pool + refill | 0 延迟首击 | ✅ 完整 |
| 战后章节(Opus) | stream_chapter_narration | chapter 面板 | ✅ 完整 |
| 天命降临(5%) | destiny_charged + destiny skill | 金光动画 + tab | ✅ 完整 |
| 12 族怪物(108只) | `enemies.py` + 12 clan | `ExploreMap.vue` 漫游 | ✅ 完整 |
| 48 怪物招式 | `monster_skills.py` 4 tier/族 | damage_summary 展示 | ✅ 完整 |
| 22 Boss + 故事线 | `bosses.py` + 4 storylines | `Bosses.vue` 列表 | ✅ 完整 |
| 物品系统(丹药/法宝/材料) | `items.py` + store 背包 | `Inventory.vue` + `Items.vue` | ✅ 完整 |
| 12 类随机事件引擎 | `events.py` 加权选择 + LLM prompt | `FortuneEvent.vue` 弹窗 | ✅ 完整 |
| 赠礼安抚系统 | give_gift API + 概率公式 | `GiftDialog.vue` | ✅ 完整 |
| 打坐回血 | meditate API + 30s CD | `MeditateButton.vue` | ✅ 完整 |
| 图片生成插件 | `image_gen.py` gpt-image-2 | 通过 API 调用 | ✅ 完整 |
| 怪物章节 LLM 生成 | generate_enemy_chapter API + cache | 前端尚未对接 | ⚠️ 缺前端 UI |
| 拜入仪式动画 | choose-sect API | `Initiation.vue` 5 阶段 | ✅ 完整 |
| 友好度系统 | factions dict + spawn 加权 | Home 五色条 | ✅ 完整 |

### 1.2 本次修复的 Bug (6 个)

| # | 严重度 | 文件 | 问题 | 修复 |
|---|--------|------|------|------|
| 1 | **P0** | `attributes.py` L193 | `refresh_derived` 用循环残留变量 `v` 作 hp/qi 默认值,导致旧角色迁移时 hp 变成 float | 改为 `char["max_hp"]` / `char["max_qi"]` |
| 2 | **P0** | `battle.py` _grant_rewards | 升级只设 `realm_name` 不设 `realm`,前端头像系统读 `realm` 永远是 "qi";手动 +20hp/+3atk 与属性系统脱节 | 改为通过 attrs +2 随机点 + `refresh_derived`;同步设 `realm` 英文 key |
| 3 | **P1** | `battle.py` events() | speed 模式下 `end` 事件后等 60s chapter_grace 超时才关 WS(章节永远不会来) | speed 模式或无 chapter_task 时 grace=0.5s |
| 4 | **P1** | `main.py` use_item | qi 计算 `min(max_qi_or_current+add, current+add)` 逻辑错误,永远加满 | 改为标准 `min(max_qi, current + add)` |
| 5 | **P2** | `main.py` give_gift | 友好度 ±5/-1 永远作用到玩家自己门派(应该根据怪物族群映射到对应派) | 新增 CLAN_TO_SECT 12 族→5 派映射 |
| 6 | **P2** | `battle.py` REALM_DISPLAY | 缺少 "feisheng" 键,飞升期玩家的 realm 不会被正确显示 | 补上 `"feisheng": "飞升期"` |

### 1.3 潜在风险点(非 Bug,需关注)

| 风险 | 说明 | 建议 |
|------|------|------|
| 内存存储 | `store.py` 全 dict,进程重启数据全丢 | Phase 2 换 SQLite/Redis |
| 升级曲线过陡 | Lv.100 需 10100 exp/级,高阶几乎无法升级 | 改为 `100 + level * 20` 或 sqrt 曲线 |
| LLM 并发竞态 | `cast()` create_task 后,队列内事件顺序依赖 Python GIL | 当前 single-player 无问题;多人时需加锁 |
| 奇遇 JSON 解析 | LLM 可能返回非 JSON(概率 ~5%) | 已有 try/catch 兜底;可加 retry 1 次 |
| 前端无离线缓存 | 角色数据全靠 API,刷新即失 | 考虑 localStorage 缓存 character 快照 |

---

## 二、8 属性系统 Review

### 2.1 属性 → 派生 公式

```
atk       = 20 + STR * 2.5
max_qi    = 600 + QI * 30
max_hp    = 80 + VIT * 8
spd       = 75 + AGI * 1.5
evasion   = 0.03 + AGI * 0.004
crit_rate = 0.05 + WIS * 0.008
crit_dmg  = 1.5 + WIS * 0.02
def_      = 8 + END * 1.2
max_fatigue = 80 + END
luck      = 0.5 + FATE * 0.01
exp_mult  = 1.0 + INS * 0.02
```

### 2.2 平衡评估

- **STR 过强**: 每点 STR = +2.5 ATK,而战斗伤害 = ATK * power * (100/(100+def))。一个 STR=50 的角色 ATK=145,远超初始 22。
- **INS (悟性) 效用不足**: `exp_mult = 1.0 + INS * 0.02`,即 INS=50 只有 2x 经验。高等级时 10000+ exp/级,2x 仍然很慢。
- **FATE 收益太低**: `luck = 0.5 + FATE * 0.01`,FATE=50 → luck=1.0。但 luck 目前仅影响事件类型权重(+20% treasure 之类),不直接影响掉落率。
- **建议**: 让 FATE 直接乘到 `rarity_probs`,INS 加速升级曲线本身(而非乘到 exp)。

---

## 三、战斗逻辑 Review

### 3.1 伤害公式

```
damage = ATK * card.power * (100 / (100 + enemy_DEF)) * crit_mult * random(0.9~1.1)
```

- 减伤公式 `100/(100+DEF)`:DEF=100 → 50% 减伤;DEF=200 → 33% 减伤。曲线合理。
- 暴击倍率 `crit_dmg` 初始 1.7,满 WIS=50 时 2.5。偏高(对比主流 ARPG 暴击通常 1.5-2.0)。
- **天命招式**: power=5.0 * crit_dmg * 1.5 = 实际 12.75x ATK。加上 ATK 自身可能 100+,一击可达 5000+ 伤害。对比高级 Boss HP ~10000,可能秒杀。

### 3.2 战斗节奏

1. 玩家出牌 → 数值即结算(< 5ms)
2. LLM 叙事异步流(Haiku 1-3s / Sonnet 3-8s / Opus 8-15s)
3. 预生成池命中 → 0 延迟
4. 玩家可在 LLM 跑时继续出牌(队列 max=3)
5. 跳过按钮取消当前叙事

**问题**: 如果玩家全速点击(利用队列),3 回合内可能结束战斗,LLM 叙事完全来不及展示。
**建议**: 队列消费时加最小间隔 500ms,给玩家时间看数值反馈。

### 3.3 怪物 AI

当前: 从 4 级招式池中按等级解锁随机选 1 个。无策略。
**建议**: 加入简单 FSM:
- HP > 50% → 偏好攻击(mid/high 招)
- HP < 30% → 有概率自愈(若该族有 heal 效果)
- 玩家暴击后 → 下回合用 ult(愤怒触发)

---

## 四、地图奇遇系统 Review

### 4.1 触发机制

- 60-90s 随机定时器(前端 `scheduleFortune`)
- 后端 55s 冷却(防重复)
- 战斗中 / 弹窗中暂停
- 12 类事件加权选择,根据 context 动态调整

### 4.2 已知问题

1. **fortune_log 无上限刷新**: 已 clamp 到 20 条 ✅
2. **LLM 返回非 JSON**: 有 try/catch,返回 `{skipped: true}` ✅
3. **效果 clamp 范围**: hp±30, qi±200, exp±50, fatigue±15 — 合理 ✅
4. **掉落物验证**: 只接受 `_ITEMS_MAP` 中存在的 item_id ✅
5. **force_battle 验证**: 只接受 `_ENEMIES_MAP` 中存在的 enemy_id ✅

**改进建议**:
- 添加事件去重(最近 3 次不重复同 type)
- 高 FATE 属性应提升 `good_chance` 总体概率(当前只影响 treasure/hermit/item_drop 权重)

---

## 五、全流程走查

```
[首次访问]
  / (WelcomePage) → /onboarding
    ↓ 填 key + 探灵脉
  /onboarding → /sect-choose?avail=canglan,tianji
    ↓ 选可用派
  /key-verify/:sectId?base_url=...&api_key=...
    ↓ SSE 逐模型验证
  /initiation/:sectId?base_url=...&api_key=...&name=...
    ↓ 拜入仪式 5 阶段动画
  /home (主城)

[游戏循环]
  /home → /explore (修行地图)
    ↓ 漫游看怪 / 60s 奇遇 / 打坐回血
  /explore → 双击怪物 → /battle/:id
    ↓ 出招 / LLM 叙事 / 赠礼 / 天命
  /battle → 战斗结束 → 10s 倒计时 → /explore
    ↓ 战败: hp=1, exp-5
    ↓ 胜利: exp+, qi+, 掉落, 可能升级

[辅助]
  /home → /inventory (背包)
  /home → /bosses (修真名录)
  /home → /items (物品图鉴)
  /home → ByokSettings (换 key)
```

**流程缺口**:
- ❌ 没有"死亡/复活"页面(战败直接 10s 回地图)
- ❌ 没有"升级恭喜"全屏动画(只有 toast + level_up 事件)
- ❌ 没有"退出确认"(刷新即丢进度,内存存储)
- ❌ 怪物章节 UI 未对接(API 已就绪)

---

## 六、完整开发路线图

### Phase 1 — 稳定 MVP (1-2 周)

| 优先级 | 任务 | 预估 |
|--------|------|------|
| P0 | 持久化存储(SQLite + JSON 序列化) | 4h |
| P0 | 升级曲线重平衡(改 exp 公式 + 属性点分配 UI) | 2h |
| P0 | 前端 localStorage 角色快照(防刷新丢失) | 1h |
| P1 | 升级全屏动画(境界突破仪式) | 3h |
| P1 | 战败复活页面(可选:原地复活 / 回主城 / 用丹药) | 2h |
| P1 | 怪物章节 UI 对接(Bosses 页 + 战后弹出) | 3h |
| P2 | 队列消费最小间隔 500ms | 0.5h |
| P2 | 事件去重(最近 3 次不重复) | 0.5h |

### Phase 2 — 深度内容 (3-4 周)

| 任务 | LLM 用法 | 预估 |
|------|----------|------|
| NPC 对话系统(怪物可交谈) | Haiku 流式对话,记忆 5 轮 | 8h |
| 怪物独特技能扩展(48→113) | 无 LLM,纯数值 | 4h |
| 技能树 + 心法系统 | 无 LLM,属性加成 | 6h |
| 日任务 / 周任务系统 | 无 LLM | 4h |
| NPC 商店(墟市) | Haiku 生成商品描述 | 4h |
| 多存档系统(3 个槽位) | SQLite 支撑 | 3h |
| 师徒系统(NPC 师父 LLM 对话) | Sonnet 对话,给修行建议 | 6h |
| 时间系统(日夜 + 月相影响) | 无 LLM | 3h |

### Phase 3 — 差异化体验 (5-8 周)

| 任务 | LLM 创新点 | 预估 |
|------|-----------|------|
| **AI 副本生成器** | Opus 生成完整 5 层副本(怪物/地形/Boss/奖励),玩家可"许愿"主题 | 12h |
| **修真日记** | 每日 Sonnet 自动写 200 字修真日记(根据当天行为) | 4h |
| **LLM 裁判系统** | 战斗争议时 Opus 裁定(如:闪避后能否反击) | 6h |
| **个性化叙事记忆** | LLM 记住玩家历史,叙事引用前事("上次你在此败给了三尾灵狐") | 8h |
| **AI 画师(怪物立绘)** | gpt-image-2 按怪物 lore 生成独特立绘(首次遭遇时触发) | 6h |
| **宗门对决(PvP)** | 两个玩家的 LLM 互写叙事,交叉验证 | 16h |
| **境界突破试炼** | Opus 生成 3 选 1 叙事分支,选错扣血选对突破 | 8h |
| **AI Dungeon Master** | 玩家输入自由文本,LLM 解析为游戏动作(开放式交互) | 12h |

### Phase 4 — 社交 + 商业化 (8-12 周)

| 任务 | 说明 |
|------|------|
| 排行榜(境界 / 战力 / 日记字数) | 轻社交 |
| 宗门大殿(多人聊天 + LLM NPC 主持) | 社交核心 |
| 限时秘境(24h 有效,Opus 生成剧情) | 活动系统 |
| API Key 用量统计 + 月度报表 | BYOK 核心体验 |
| 免费试玩层(前 10 级不需 key,用服务端池) | 拉新 |
| 付费内容:独家 Boss 皮肤 / 叙事风格包 | 变现 |
| PWA + 移动适配 | 触及更多用户 |
| 国际化(英文/日文叙事模板) | 扩圈 |

---

## 七、修仙游戏市场与 LLM 融合研究

### 7.1 修仙游戏市场现状 (2024-2026)

**头部产品格局:**
- **MMO/ARPG**: 《诛仙》(热度500万)、《倩女幽魂》(700万)、《仙剑奇侠传》(600万)占头部;2025年《诛仙世界》《问剑长生》《遮天世界》加剧竞争
- **放置/挂机**: 《一念逍遥》(2000万+用户,体/法/剑/鬼/儒五修)是标杆,但2024流水下滑;同质化严重
- **文字/模拟**: Steam《挂机修仙》、itch.io Xianxia Simulator、Cultivation Quest(2024.12)
- **海外**: 国产修仙游戏欧美流水过千万,题材有跨文化吸引力
- **风口**: 黑神话悟空破90亿;10家上市公司计划上线20款国风新游

**核心用户**: 程序员/上班族,追求"每天10分钟"不肝不氪;赛道玩法创新是突破关键。

### 7.2 LLM 在游戏中的应用现状

| 产品/技术 | 做法 | 效果 |
|-----------|------|------|
| AI Dungeon | 文本冒险,纯LLM驱动叙事 | 高即兴性,连贯性不足 |
| Inworld AI | NPC中间件:人格/知识库/情感+多轮记忆 | 头部方案,延迟2-5s |
| BYOK.gg | 游戏AI SDK:多LLM路由+玩家自管钱包 | 验证BYOK模式可行 |
| 网易+清华 | NPC人格化:自感知游戏状态+动态生成行为 | 工业级落地 |
| 2025行业数据 | 96%工作室已将AI工具纳入工作流 | AI已不是选配 |

### 7.3 当前已实现(灵枢笔录独有)

1. **门派=模型梯度**: 游戏进度=解锁更强模型,修仙隐喻完美契合
2. **BYOK 架构**: 玩家"自带法力",开发者零token成本
3. **三档叙事分级**: 普通=Haiku(快)/暴击=Sonnet(美)/天命=Opus(震撼)
4. **实时流式叙事**: WebSocket 逐字推送,打字机效果
5. **预生成池**: 用廉价模型提前备好,首击0延迟
6. **12类奇遇引擎**: LLM填充无限事件内容,分类约束防失控
7. **战后章节**: 500字Opus长文回顾,可收藏

### 7.4 未被覆盖的市场空白

| 方向 | 竞品现状 | 灵枢笔录可做 |
|------|----------|------------|
| **境界=模型能力可感知** | 无游戏将模型质量差异作为核心机制 | 低境界叙事简陋,高境界华丽——用户"摸到"模型差异 |
| **修炼=Prompt Engineering** | 无 | 功法(system prompt)、心法(参数)、灵根(模型选择)=AI素养即游戏技能 |
| AI生成副本 | 无 | 输入主题→Opus生成5层完整副本 |
| 个性化叙事记忆 | AI Dungeon有但不做数值 | 战斗叙事引用玩家历史 |
| LLM裁判 | 无 | 争议判定由AI解释 |
| 修真日记自动生成 | 无 | 每日复盘,可分享到社交 |
| AI画师按需生成 | 不集成到游戏循环 | 首遇怪物→即时gpt-image-2生成立绘 |
| 境界突破试炼 | 交互小说不做数值 | 叙事分支选择影响属性成长 |
| 多模型对抗(PvP) | 无 | 两派LLM互写攻防叙事,评判模型裁定 |

### 7.5 核心竞争力总结

> **灵枢笔录 = 修仙RPG × LLM流式叙事 × BYOK自带法力**
>
> **目标用户**: AI开发者/API重度用户/修仙文化爱好者(精准交集:程序员既是放置修仙核心玩家也是Key持有者)
>
> **核心体验**: "用你自己的API Key修仙,境界越高模型越强,每一战都是独一无二的叙事"
>
> **vs竞品**: vs一念逍遥(AI驱动无限内容) / vs AI Dungeon(有完整数值+修仙观) / vs传统MMO(零运营成本BYOK)

---

## 八、技术债清单

| 债务 | 影响 | 优先修 |
|------|------|--------|
| 内存存储 (store.py) | 重启丢数据 | Phase 1 |
| 单玩家 hardcode "demo_player" | 无法多用户 | Phase 2 |
| 无测试覆盖 | 回归风险高 | Phase 1 起 |
| LLM 调用无成本追踪 | 无法统计 token 消耗 | Phase 2 |
| CSS 未提取 design token | 各页风格微偏 | Phase 2 |
| 无 service worker / PWA | 离线不可用 | Phase 4 |
| battle engine 非线程安全 | 多人时竞态 | Phase 4 |
| 图片全走 public/ 无 CDN | 加载慢 | Phase 3 |
