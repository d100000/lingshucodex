# 灵枢笔录 · 战斗模块系统化代码复审

> **范围**：`backend/app/battle.py`（BattleEngine）· `backend/app/main.py`（HTTP + WS）· `backend/app/store.py`（持久化）· `frontend/src/views/Battle.vue`（前端 UI）· `frontend/src/components/GiftDialog.vue`
> **方法**：每个调用链路按"输入 → 状态 → 输出 → 持久化"四点验证
> **结论**：发现 5 类系统性缺陷，共 23 项确认漏洞

---

## 一、整体架构索引（先建立心智模型）

```
                 ┌─ HTTP /api/battle/start  ──────┐
[ 玩家客户端 ]  ─┼─ WS  /ws/battle/{id}            ├─►  BattleEngine 实例
                 ├─ HTTP /api/battle/give-gift    │      │
                 ├─ HTTP /api/inventory/use       │      │ self.state (内存，独立轨道)
                 └─ HTTP /api/battle/{id}/preview ┘      │ self.history
                                                          │ self.events_queue (单队列)
                                                          │
                              ┌── narration_task ◄────────┤
                              ├── chapter_task   ◄────────┤
                              ├── _refill_pool   ◄────────┤
                              └── warmup_pool    ◄────────┤
                                                          ▼
                                                 SQLite (characters JSON blob)
                                                 _battles dict (内存，进程级)
```

**两条核心断层：**

1. `BattleEngine.state["player_hp/qi"]` ↔ `character["hp/qi"]` 是两套独立数据，从未在战斗内同步。
2. `engine` 接受 4 路并发输入（WS 收消息、`/give-gift`、`/use-item`、`/card-preview`），但内部**没有任何锁**。

这两个断层是后面 80% 漏洞的根因。

---

## 二、模块 A：状态机 / 出招层（`battle.py:216 cast()`）

### 2.1 状态机自身的脆弱性

```
status: player_turn ──cast─► processing ──结算─► enemy_turn ──结算─► player_turn
                                  │                 │
                                  └─ ended ──end── (终态)
```

### 2.2 缺陷清单

| ID | 位置 | 缺陷描述 |
|----|------|---------|
| **A-1** | `main.py:1329` + `battle.py:218` | `cast()` 仅判 `is_finished()`，**不要求 `status == "player_turn"`**；recv_loop 用 `create_task` 不串行化。脚本/连点/多端可绕过节奏 |
| **A-2** | `battle.py:216-425` | `cast()` 全程 12 处 `await`，每一处都让出事件循环；无 `asyncio.Lock` |
| **A-3** | `battle.py:240-241` | `destiny_used = True / destiny_charged = False` 在结算前置位；中间任意 `_push` 抛异常都会让玩家本场失去天命 |
| **A-4** | `battle.py:256` | `status = "processing"` 后没有 try/finally 保护，结算任意环节抛异常 → status 永久卡 processing，玩家死锁 |
| **A-5** | `battle.py:715-724` | `_apply_outcome()` 在 `miss` 分支也走 else，把 `focus_next` buff 一并清空 |
| **A-6** | `battle.py:715-724` | heal/buff 卡不进 else 分支，buff 永不消耗——开 buff 然后回血/再开 buff = 永久叠加 |
| **A-7** | `battle.py:687-688` | `hit_rate = card.hit_rate - evasion`，敌人高敏捷时可为负，`random()>负数` 永真 → 100% miss |

---

## 三、模块 B：持久化层（state ↔ character ↔ SQLite）

> 这是整个战斗系统**最严重**的结构性缺陷。三轨数据互不同步，且 SQLite 表是 JSON blob，无法做字段级原子更新。

### 3.1 数据流真相图

```
战斗中:
   cast/敌人攻击  ───►  engine.state.player_hp  (变化)
   /api/inventory/use ─►  character.hp           (变化)  ← 互不通信
   /api/battle/give-gift ─►  character.exp/factions  (变化)

战斗结束:
   victory  ─►  _grant_rewards 写 exp/qi/level → character  (state.player_hp 不写)
   defeat   ─►  _apply_defeat_penalty 强制 hp=1            (与 state 不一致)
   fled     ─►  什么都不写                                  (满血回家)

最终 SQLite:
   characters.data = json.dumps(character)  整段覆盖
```

### 3.2 缺陷清单

| ID | 位置 | 缺陷描述 |
|----|------|---------|
| **B-1** | `Battle.vue:644-660` + `main.py:1142-1149` | 战斗中嗑丹只改 `character.hp` 与前端本地 `state.value.player.hp`，**`engine.state.player_hp` 完全不知道**。下一回合敌人攻击仍按战斗内旧值算伤害 |
| **B-2** | `battle.py:659-664` | `flee()` 不写 hp/qi 回 character → 撤退 = 免费回血 |
| **B-3** | `battle.py:296-347` | victory 分支只写 exp/qi/level/attrs，**state.player_hp 永不持久化**；玩家"血量永远定格在战前" |
| **B-4** | `battle.py:378-394` | defeat 分支先 push state（player_hp=0），再写 hp=1 入库——前端显示 0 但库里是 1，回主城刷新后不一致 |
| **B-5** | `store.py:100-106` | `save_character` 是 `INSERT OR REPLACE` 整段 JSON。打坐+战斗+赠礼+使用道具任意两个并发时 **后写覆盖先写**，经验/灵气/友好度/保底 pity 全可能丢失 |
| **B-6** | `main.py:1374` | WS 任意一端断开就 `delete_battle()` 把 engine 从 `_battles` 删除，但战斗中产生的 hp 损耗/灵气消耗在内存里没落库——直接断网 = 损失消失 |
| **B-7** | `Battle.vue:712-718` | 前端在 `returnToMap/backToHome` 把 `state.player.hp → character.hp`，但**只更新本地 ref**，没有 PUT 任何接口持久化。刷新页面后又取 SQLite 旧值 |
| **B-8** | `battle.py:73-74` | `record_encounter` 在 `BattleEngine.__init__` 阶段就执行；engine 创建出来但 WS 没连上、用户立刻关闭就**已经记图鉴**——新手"开战又关闭"会污染图鉴 |

### 3.3 系统性结论

> 战斗模块本质是 **"内存模拟器"**，结束时手动对 character 做"差量回写"。差量回写的字段不全、且没事务 → **存档与战斗实际过程长期不一致**。
>
> 这不是单点 bug，而是一开始就没有把 character 当 single source of truth。要么改成 `BattleEngine` 直接读写 character（每回合 save），要么严格收敛差量字段并加事务。

---

## 四、模块 C：WebSocket 传输层（`main.py:1280`）

### 4.1 收发协程的设计假设

```python
recv_loop:  while not finished: receive → create_task(cast)   # 不等待
send_loop:  async for ev in engine.events(): send_json(ev)
asyncio.wait([recv, send], FIRST_COMPLETED) → 任一完成 → cancel 另一个 → delete_battle
```

### 4.2 缺陷清单

| ID | 位置 | 缺陷描述 |
|----|------|---------|
| **C-1** | `main.py:1280` | 没有 "一个 battle 只能挂一个 WS" 的限制。多端打开同战斗 → 单 events_queue 被多 socket 抢消费，谁都收不全 |
| **C-2** | `main.py:1182-1219` | `/api/battle/start` 不查 active 战斗。多标签页能并行打两场 → exp/掉落/降级 pity 互相覆盖 |
| **C-3** | `main.py:1374` | recv_loop 异常退出 → finally 直接 `delete_battle` → 另一端的 send_loop 还没消费完事件就被强制 cancel；玩家什么都没收到 |
| **C-4** | `main.py:1310-1340` | recv_loop 没有空闲超时；玩家半夜挂着不点，engine 永远占内存（连同 narration_pool / chapter_task） |
| **C-5** | `main.py:1311 cast 分支` | `create_task(engine.cast(...))` 既不持引用也不收集异常；cast 内 unhandled exception 会被 asyncio 吞掉，玩家看不到任何错误 |
| **C-6** | `main.py:1322-1323` | `ping` 处理直接 `ws.send_json` 而不是走 events_queue；与 send_loop 并发写同一 socket，绕开了队列设计的统一性 |

### 4.3 链路级隐患

> 由于战斗状态完全在内存 + 一连接一周期，任何**网络抖动**都会导致：（1）engine 被 delete，（2）下一个 WS 连接拿到 404，（3）玩家被迫从 explore 重开。和移动端真实网络场景严重不匹配。
>
> 标准做法是：WS 断开**只标记 detached**，engine 保留 N 秒；新 WS 用同一 battle_id 重连可继续。

---

## 五、模块 D：辅助 HTTP 接口

### 5.1 缺陷清单

| ID | 位置 | 缺陷描述 |
|----|------|---------|
| **D-1** | `main.py:1189` + `attributes.py:196` | `is_first_battle = len(char.get("battle_history",[]))==0`。`battle_history` 在 attributes.py 初始化为 `[]` 后**全代码再无 append**。所有玩家每次开战都被判首战，强制重定向 `fox_01`。这是当前最严重的流程漏洞 |
| **D-2** | `main.py:560,573` | `give_gift` 信任客户端传 `gift_count_so_far`，恒传 0 即可绕过 3 次上限 |
| **D-3** | `main.py:563-642` | `give_gift` 不检查 `engine.is_finished()`；战斗已结束仍可继续赠礼刷经验、刷友好度 |
| **D-4** | `main.py:638-642` | 强行结束的 result 设 `"victory_gift"`，但前端 `Battle.vue:1139` 只识别 `"victory" / "defeat"`；玩家看到的会是默认的"逃离战斗"视觉，奖励面板缺失 |
| **D-5** | `main.py:608` | `remove_item` 在 `accepted` 判定后扣，但**前面没事务**：扣物品+发奖励+save_character+push events 是 4 步；任一步抛异常都会留下中间态（典型：物品扣了但战斗没结束） |
| **D-6** | `main.py:1262` | card-preview 公式 `c.hit_rate + char.evasion * 0.5` 与战斗内 `card.hit_rate - enemy.evasion` 完全不同，玩家看到的命中预览是骗人的 |
| **D-7** | `main.py:1241-1274` | card-preview 直接读 `engine.state` 不加锁；与 cast 并发时拿到中间值（player_atk 已变 / qi 已扣） |
| **D-8** | `main.py:1142-1158 use_item` | 道具效果 `breakthrough_bonus / unlock_card` 写入 character 但**战斗内没有任何消费这些字段的逻辑**——使用了等于丢了 |

---

## 六、模块 E：异步背景任务层

### 6.1 任务图谱

| 任务 | 创建点 | 取消点 | 引用 |
|------|--------|--------|------|
| `current_narration_task` | `battle.py:435` | 下一回合 / skip | ✅ self 上 |
| `chapter_task` | `battle.py:346,393` | **从不取消** | ✅ self 上 |
| `_refill_pool` | `battle.py:467` | **从不取消** | ❌ 无引用 |
| `warmup_pool` | `main.py:1308` | **从不取消** | ❌ 无引用 |

### 6.2 缺陷清单

| ID | 位置 | 缺陷描述 |
|----|------|---------|
| **E-1** | `battle.py:659-664` | `flee()` 不取消 narration / chapter / pool，后台仍消耗 LLM token |
| **E-2** | `battle.py:346` | `chapter_task` 从不被 await/cancel；WS 关闭后仍在跑（最长 60s 流式） |
| **E-3** | `battle.py:613-628 _refill_pool` | fire-and-forget 无引用，engine GC 时 task 仍存活，**asyncio 警告 "Task was destroyed while pending"** |
| **E-4** | `llm_client.prefetch_pool_narrations` | 池子统一用"普攻"模板，消费时不分卡牌 ID → 玩家用沧澜九式仍看到普攻文字（沉浸感破裂） |
| **E-5** | `battle.py:432-433` | `current_narration_task.cancel()` 是非阻塞信号；新 task 立刻启动；两个 task 短暂并发 push delta，前端可能拼出"上回合尾巴+新回合开头" |
| **E-6** | `battle.py:568-586 fallback` | fallback 模板 `self.state["player"]["name"]` 读不到（state 是扁平结构），所有兜底永远是"执笔者 / 妖兽" |

---

## 七、模块 F：前端配合（Battle.vue 同步逻辑）

| ID | 位置 | 缺陷描述 |
|----|------|---------|
| **F-1** | `Battle.vue:1132` | result 仅识别 `victory/defeat`；`fled / victory_gift` 走默认"逃离"分支，赠礼成功 + 战败 +flee 三种结局视觉相同 |
| **F-2** | `Battle.vue:644-660 useItem` | 前端"模拟同步" `state.value.player.hp = data.character.hp` 只是**视觉糖**，不影响后端；玩家以为吃了药，实际下回合敌人按旧 HP 打 |
| **F-3** | `Battle.vue:701-720` | `returnToMap` 只改本地 `character.value`，没有调任何 PUT 接口。下次 `/api/character` 请求会刷回数据库值 |
| **F-4** | `Battle.vue:677-679` | flee 兜底"1.5s 没收到 end 就强制返回"；服务端撤退处理慢就会导致玩家走了但 engine 还在跑、章节还在写 token |
| **F-5** | `Battle.vue 客户端 castQueue` | 客户端 castQueue 上限 3——这是当前**唯一**的连点防御。脚本绕过即破，A-1 就成立 |

---

## 八、漏洞优先级总表

| 等级 | 数量 | 编号 | 必须先修原因 |
|------|------|------|------------|
| **P0** | 6 | A-1, A-2, B-1, B-2, B-3, D-1 | 直接破坏战斗公平/资源经济或核心流程 |
| **P1** | 11 | A-3, A-4, A-5, A-6, B-4, B-5, B-6, C-1, C-2, D-2, D-3 | 影响存档一致性、并发安全、付费转化点 |
| **P2** | 8 | A-7, B-7, B-8, C-3, C-4, D-4, D-5, D-7 | 边界条件 / 用户感知 |
| **P3** | 余下 | C-5, C-6, D-6, D-8, E-*, F-* | 体验优化与 token 浪费 |

---

## 九、结构性修复骨架（优先级排序）

> 不是逐 bug 打补丁，而是把**根因层**改对。

### 修复路径 1：`battle_history` 持久化（D-1，工作量极小，收益极大）

战斗 `_grant_rewards` / `_apply_defeat_penalty` / `flee` 三处统一调用：

```
record_battle_end(user_id, enemy_id, result, rounds, drops)
  → 在 character 里 append 一条到 battle_history（保留最近 50 条）
  → save_character
```

首战判定改为读 SQLite 实际记录。

### 修复路径 2：BattleEngine 状态写回的"差量字段契约"（B-1/B-2/B-3/B-7）

定义 `engine.commit_to_character()`：

```
character.hp  = state.player_hp
character.qi  = state.player_qi
character.exp += rewards.exp
character.last_battle_at = now
save_character
```

- `flee()`、`victory`、`defeat` 三处终态一律调用 commit。
- 战斗中道具使用改成 `engine.use_item(item_id)`，内部直接写 state 并 push event。

### 修复路径 3：cast 串行化 + 状态校验（A-1/A-2/A-3/A-4）

```
self._lock = asyncio.Lock()
async def cast(...):
    async with self._lock:
        if status != "player_turn": push error; return
        try:
            self.status = "processing"
            ...结算 + 推 events...
        finally:
            if not is_finished: self.status = "player_turn"
```

destiny 状态置位移到 try 内、紧贴结算成功后。

### 修复路径 4：服务端权威赠礼计数（D-2/D-3）

GiveGiftRequest 删除 `gift_count_so_far`；engine 上加 `self.gift_count`，`give-gift` 接口：

```
if engine.is_finished(): 400
if engine.gift_count >= 3: 400
... 计算并 increment ...
```

### 修复路径 5：单玩家 active battle 互斥（C-2）

`_battles` 加索引 `_active_battle_by_user: dict[user_id, battle_id]`。
`/api/battle/start` 先查：

- 已有未结束战斗 → 返回 409 + 旧 battle_id（前端可选"恢复 / 放弃"）
- 或自动 `flee()` 旧战，再开新战。

### 修复路径 6：背景任务统一注册 + cleanup（E-1/E-2/E-3）

```
self._bg_tasks: set[asyncio.Task] = set()
def _spawn(self, coro):
    t = asyncio.create_task(coro)
    self._bg_tasks.add(t); t.add_done_callback(self._bg_tasks.discard)
async def cleanup(self):
    for t in self._bg_tasks: t.cancel()
    await asyncio.gather(*self._bg_tasks, return_exceptions=True)
```

WS finally 调用 `await engine.cleanup()`。

### 修复路径 7：character 写入加 SQLite 事务级别保护（B-5）

短期：在 `store.py` 用 `threading.Lock` 包 `save_character` 全过程（read-modify-write）。
长期：把高频字段（hp, qi, exp, level, factions, drop_pity）拆出 JSON blob 进独立列，用 `UPDATE ... SET hp=hp+?` 等增量 SQL，避免 read-modify-write 竞态。

---

## 十、最关键的 1 句话总结

> 当前战斗模块**没有把 `character` 当作权威状态**，也**没有把回合当作互斥临界区**。这两条结构性缺陷催生了表面上看似无关的 23 个 bug——从首战误判、撤退满血、丹药无效，到多端并发覆盖存档。
>
> 任何不动这两条根因的"逐 bug 修补"，都会在下一次需求迭代时再次重现等价的漏洞。

最小可上线修复包：路径 1 + 2 + 3 + 4 四组（约 5–6 个文件改动），其余可在下一迭代回收。
