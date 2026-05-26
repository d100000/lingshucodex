# 灵枢笔录 · 战斗模块 Bug 修复实施指南

> 面向对象:后续负责修复代码的 AI / 工程师  
> 创建日期:2026-05-25  
> 项目路径:`/Users/bobdong/项目/LingshuCodex`  
> 关联审计文档:`docs/BATTLE_MODULE_AUDIT_REPORT.md`  
> 目标:把战斗系统从“前端节奏约束 + 多处局部写库”修成“服务端规则可信 + 状态统一提交 + 可回归验证”的结构。

---

## 0. 你要先理解的核心问题

当前战斗系统的最大问题不是某一张卡牌伤害太高,而是这三件事:

1. **战斗内存状态和角色存档不同步**
   - 战斗真实数值在 `BattleEngine.state`。
   - 角色长期存档在 SQLite 的 `character` JSON。
   - HP、Qi、奖励、战斗历史、掉落保底被多个函数分散写入。

2. **服务端没有守住回合制规则**
   - WebSocket 收到 `cast` 后直接 `asyncio.create_task(engine.cast(card_id))`。
   - `cast()` 没有 `asyncio.Lock`。
   - `cast()` 不检查 `state["status"] == "player_turn"`。
   - 前端可以限制正常点击,但脚本/多标签页/连发 WS 可以绕过。

3. **结束结算不是幂等的**
   - 胜利、战败、撤退、赠礼胜利路径分散。
   - 奖励、掉落、日课、历史可能重复写或互相覆盖。
   - `battle_history` 已部分写入,但不是统一提交的一部分。

你的修复方向必须围绕:

```text
行动串行化 -> 回合状态校验 -> 统一战斗提交 -> 幂等保护 -> 后台任务清理
```

---

## 1. 关键文件地图

优先读这些文件:

| 文件 | 必看区域 | 为什么 |
|---|---|---|
| `backend/app/battle.py` | `BattleEngine.__init__`, `cast`, `flee`, `_grant_rewards`, `_apply_defeat_penalty`, `_record_battle_to_character`, `_roll_drops`, `_generate_chapter` | 战斗状态机和主要漏洞都在这里 |
| `backend/app/main.py` | `/api/battle/start`, `/api/battle/give-gift`, `/api/inventory/use/{item_id}`, `/ws/battle/{battle_id}` | API/WS 入口与赠礼/道具问题在这里 |
| `backend/app/store.py` | `_battles`, `save_character`, `add_item/remove_item`, bestiary/daily 方法 | 内存战斗与 SQLite 写入 |
| `frontend/src/views/Battle.vue` | `castCard`, `useItem`, `skipNarration`, `returnToMap`, `backToHome`, WS `handleEvent` | 前端与服务端状态契约 |
| `frontend/src/api/client.js` | `battleApi`, `inventoryApi`, `giftApi` | 需要新增或调整接口 |

辅助参考:

| 文件 | 用途 |
|---|---|
| `backend/app/cards.py` | 卡牌类型、灵丹卡、费用 |
| `backend/app/monster_skills.py` | 怪物技能效果尚未落地 |
| `backend/app/llm_client.py` | 叙事池/章节生成 |
| `docs/BATTLE_MODULE_AUDIT_REPORT.md` | 完整漏洞背景 |

---

## 2. 修复总策略

不要先大改 UI,也不要先调数值。先修服务端规则。

推荐分 5 个阶段:

```text
Phase 1  服务端行动锁 + 回合校验
Phase 2  统一 battle commit,同步 HP/Qi/奖励/历史
Phase 3  战斗内道具与赠礼服务端化
Phase 4  生命周期清理与多连接/多战斗限制
Phase 5  数值与叙事一致性修复
```

每个 Phase 都应该能独立提交、独立验证。

---

## 3. Phase 1:服务端行动锁与回合校验

### 3.1 要修的问题

覆盖:

- P0-5:WebSocket cast 并发执行。
- P0-6:cast 不校验玩家回合。
- P1-12:奖励/掉落/日课不是幂等操作的前置风险。

### 3.2 修改文件

- `backend/app/battle.py`
- `backend/app/main.py`

### 3.3 实施要求

在 `BattleEngine.__init__` 增加:

```python
self._action_lock = asyncio.Lock()
self._committed = False
```

如果你更喜欢放在 `self.state`,也可以:

```python
"committed": False
```

但建议 `_committed` 用实例属性,避免被 snapshot 暴露给前端。

将 `cast()` 主体包进锁:

```python
async def cast(self, card_id: str):
    async with self._action_lock:
        await self._cast_locked(card_id)
```

或者直接在 `cast()` 内:

```python
async with self._action_lock:
    ...
```

在锁内第一时间检查:

```python
if self.is_finished():
    await self._push({"type": "error", "data": {"message": "战斗已结束"}})
    return

if self.state["status"] != "player_turn":
    await self._push({"type": "error", "data": {"message": "尚未轮到你出手"}})
    return
```

注意:这个检查必须在卡牌校验、天命置位、扣灵气之前。

### 3.4 WebSocket 是否还用 create_task

短期可以保留:

```python
asyncio.create_task(engine.cast(card_id))
```

因为 `engine.cast()` 内部已经有锁。  
更稳妥的方式是把 task 保存到集合,但 Phase 1 不强制。

不要在 `recv_loop` 里直接 `await engine.cast(card_id)`,否则某些较长结算可能阻塞 ping/flee/skip。

### 3.5 验收

写一个最小测试脚本或临时手测:

```python
await asyncio.gather(
    engine.cast("basic_strike"),
    engine.cast("basic_strike"),
    engine.cast("basic_strike"),
)
```

期望:

- 最多只有一个 cast 进入真实结算。
- 其余请求收到“尚未轮到你出手”或等第一个结束后根据状态被拒绝。
- `round` 不会异常连跳。
- `player_qi` 不会被多次异常扣除。

---

## 4. Phase 2:统一战斗结果提交

### 4.1 要修的问题

覆盖:

- P0-1:撤退不提交 HP/Qi。
- P0-2:胜利不提交战斗后 HP。
- P0-3:战败推送状态与存档不一致。
- P0-7:战斗历史只部分写入,不是完整提交。
- P0-10:灵气消耗没有可靠持久化。
- P1-13:角色 JSON 多次分散保存导致覆盖。

### 4.2 修改文件

- `backend/app/battle.py`
- 可能少量影响 `frontend/src/views/Battle.vue`

### 4.3 目标结构

把这些分散函数:

```text
_grant_rewards()
_apply_defeat_penalty()
_record_battle_to_character()
_roll_drops() 内部 save_character(drop_pity)
```

逐步收敛成一个统一提交函数:

```python
def _commit_battle_result(self, result: str, rewards: dict | None = None, drops: list | None = None) -> dict:
    ...
```

这个函数必须:

1. 幂等。
2. 一次读取角色。
3. 一次保存角色。
4. 同步 HP/Qi。
5. 应用奖励或惩罚。
6. 写 battle_history。
7. 更新 drop_pity。
8. 返回给前端需要展示的最终数据。

### 4.4 建议实现草图

```python
def _commit_battle_result(self, result: str, rewards: dict | None = None, drops: list | None = None) -> dict:
    if self._committed:
        return {"already_committed": True}
    self._committed = True

    char = get_character(self.user_id)
    if not char:
        return {}

    rewards = rewards or {}
    drops = drops or []

    # 1. 先同步战斗内存态
    final_hp = self.state.get("player_hp", char.get("hp", 1))
    final_qi = self.state.get("player_qi", char.get("qi", 0))

    if result == "defeat":
        final_hp = 1
        char["exp"] = max(0, char.get("exp", 0) - 5)
    elif result == "fled":
        final_hp = max(1, final_hp)

    char["hp"] = max(0, min(char.get("max_hp", final_hp), final_hp))
    char["qi"] = max(0, min(char.get("max_qi", final_qi), final_qi))

    # 2. 胜利奖励:注意 qi 要从战斗剩余 qi 上加,不是从旧存档 qi 上加
    if result == "victory":
        exp_mult = char.get("exp_mult", 1.0)
        final_exp = int(rewards.get("exp", 0) * exp_mult)
        char["exp"] = char.get("exp", 0) + final_exp
        char["qi"] = min(char.get("max_qi", 0), char["qi"] + rewards.get("qi", 0))
        # 升级逻辑可以复用旧 _grant_rewards 的 while,但不要在里面 save_character

    # 3. drop_pity 更新也在这里做
    # 如果 drops 中存在 rarity>=3,drop_pity=0;否则 +1

    # 4. 历史
    history = char.get("battle_history", [])
    history.append({
        "battle_id": self.battle_id,
        "enemy_id": self.state.get("enemy_id"),
        "enemy_name": self.state.get("enemy_name"),
        "result": result,
        "rounds": self.state.get("round", 0),
        "timestamp": time.time(),
        "rewards": {
            "exp": rewards.get("exp", 0),
            "qi": rewards.get("qi", 0),
            "drops": [d.get("id") for d in drops if isinstance(d, dict)],
        },
    })
    char["battle_history"] = history[-50:]

    save_character(self.user_id, char)
    return {"character": char}
```

### 4.5 重要注意

不要保留这种顺序:

```python
_roll_drops() -> save_character(drop_pity)
_grant_rewards() -> save_character(exp/qi)
_record_battle_to_character() -> save_character(history)
```

这会继续造成 JSON 覆盖。

可以把 `_grant_rewards()` 改为只修改传入的 `char`,不保存:

```python
def _apply_rewards_to_char(self, char: dict, rewards: dict) -> Optional[dict]:
    ...
```

把 `_apply_defeat_penalty()` 改为:

```python
def _apply_defeat_penalty_to_char(self, char: dict):
    ...
```

### 4.6 胜利分支正确顺序

建议:

```python
if self.state["enemy_hp"] <= 0:
    self.state["status"] = "ended"
    self.state["result"] = "victory"

    drops, drop_meta = self._roll_drops_no_commit()
    reward_data = {"exp": ..., "qi": ..., "drops": drops}
    commit_data = self._commit_battle_result("victory", reward_data, drops)

    await self._push({"type": "state", "data": self.snapshot()})
    await self._push({"type": "end", "data": {"result": "victory", "rewards": reward_data, "commit": commit_data}})
```

注意:如果升级会满血满灵气,需要同步回 `self.state["player_hp"] / ["player_qi"]`,再推 state。

### 4.7 战败分支正确顺序

建议:

```python
if self.state["player_hp"] <= 0:
    self.state["status"] = "ended"
    self.state["result"] = "defeat"
    self.state["player_hp"] = 1
    commit_data = self._commit_battle_result("defeat")
    await self._push({"type": "state", "data": self.snapshot()})
    await self._push({"type": "end", "data": {"result": "defeat", "penalty": {"hp": 1, "exp": -5}}})
```

### 4.8 撤退分支正确顺序

建议:

```python
async def flee(self):
    async with self._action_lock:
        if self.is_finished():
            return
        self.state["status"] = "ended"
        self.state["result"] = "fled"
        self.state["player_hp"] = max(1, self.state["player_hp"])
        self._commit_battle_result("fled")
        await self._push({"type": "state", "data": self.snapshot()})
        await self._push({"type": "end", "data": {"result": "fled"}})
```

### 4.9 验收

必须验证:

1. 胜利后 HP 是战斗结束 HP,不是战前 HP。
2. 胜利后 Qi = 战斗剩余 Qi + 奖励 Qi。
3. 撤退后 HP/Qi 不回到战前。
4. 战败后前端 state 和 `/api/character/me` 都是 HP 1。
5. 普通胜利、战败、撤退都只写一条 battle_history。
6. 重复触发 end 不重复发奖励。

---

## 5. Phase 3:战斗内道具与赠礼服务端化

### 5.1 战斗内道具

#### 要修的问题

覆盖:

- P0-4:战斗中吃药写角色,不写 BattleEngine。
- P2-14:通用背包使用接口并发重复生效。

#### 修改文件

- `backend/app/battle.py`
- `backend/app/main.py`
- `backend/app/store.py`
- `frontend/src/views/Battle.vue`
- `frontend/src/api/client.js`

#### 推荐方案

新增 WebSocket action:

```json
{ "action": "use_item", "payload": { "item_id": "item_lingdan_basic" } }
```

`main.py` 的 `recv_loop` 增加:

```python
elif action == "use_item":
    item_id = msg.get("payload", {}).get("item_id")
    asyncio.create_task(engine.use_item(item_id))
```

`BattleEngine` 新增:

```python
async def use_item(self, item_id: str):
    async with self._action_lock:
        if self.is_finished():
            ...
        if self.state["status"] != "player_turn":
            ...
        # 原子扣背包
        # 应用到 self.state
        # 推 item_used + state
```

#### 关键点

战斗中使用道具必须改 `self.state`,不能只改 character。

例如:

```python
self.state["player_hp"] = min(self.state["player_max_hp"], self.state["player_hp"] + heal)
self.state["player_qi"] = min(self.state["player_max_qi"], self.state["player_qi"] + qi_add)
```

#### 通用背包接口也要修

`/api/inventory/use/{item_id}` 中不要先加属性再扣物品。应改为:

```python
if not remove_item("demo_player", item_id, 1):
    raise HTTPException(400, "物品不足")
# 扣成功后再应用效果
```

更好是给 `remove_item()` 改成 SQL 条件更新,保证原子。

### 5.2 赠礼

#### 要修的问题

覆盖:

- P0-9:赠礼次数信任前端。
- P1-1:赠礼 result 契约不一致。
- P1-2:已结束战斗仍可赠礼。

#### 修改文件

- `backend/app/main.py`
- `backend/app/battle.py`
- `frontend/src/components/GiftDialog.vue`
- `frontend/src/api/client.js`

#### 推荐方案

短期保留 REST `/api/battle/give-gift`,但后端不再读取 `gift_count_so_far`。

`BattleEngine.__init__` 增加:

```python
self.gift_count = 0
```

或:

```python
self.state["gift_count"] = 0
```

`give_gift()` 中:

```python
if engine.is_finished():
    raise HTTPException(400, "战斗已结束")

if engine.state.get("gift_count", 0) >= 3:
    raise HTTPException(400, "本场战斗已赠礼 3 次")

engine.state["gift_count"] += 1
```

接受概率里的 penalty 改用服务端次数:

```python
penalty = (engine.state["gift_count"] - 1) * 0.18
```

赠礼成功 result 建议统一:

```python
engine.state["result"] = "victory"
await engine._push({"type": "end", "data": {
    "result": "victory",
    "finish_reason": "gift",
    ...
}})
```

然后前端根据 `finish_reason === "gift"` 显示“安抚成功”,但 result 仍是 victory。

赠礼成功也必须走 `_commit_battle_result("victory", rewards)` 或专门的 `"pacified"` 结果,不要只改 char exp。

### 5.3 验收

1. 手写请求传 `gift_count_so_far=0`,第 4 次仍被拒绝。
2. 赠礼成功后 UI 显示胜利/安抚成功,不是逃离。
3. 赠礼成功写入 battle_history。
4. 已结束 battle 再赠礼返回错误。
5. 战斗中吃药后后端下一次敌人攻击基于新 HP。

---

## 6. Phase 4:生命周期清理与多连接限制

### 6.1 要修的问题

覆盖:

- P0-8:同一玩家可同时开启多场战斗。
- P1-3:同一 battle 可被多个 WS 抢事件。
- P1-7:叙事 task 取消后不等旧 task 收尾。
- P1-8:chapter/refill task 缺少统一清理。
- P2-15:跳过章节不能取消 chapter_task。

### 6.2 修改文件

- `backend/app/store.py`
- `backend/app/main.py`
- `backend/app/battle.py`
- `frontend/src/views/Battle.vue`

### 6.3 限制同一玩家 active battle

在 `store.py` 增加:

```python
_active_battle_by_user: dict[str, str] = {}
```

或先简单在 `start_battle()` 里扫描 `_battles`。

推荐函数:

```python
def get_active_battle_for_user(user_id: str): ...
def set_active_battle_for_user(user_id: str, battle_id: str): ...
def clear_active_battle_for_user(user_id: str, battle_id: str): ...
```

MVP 策略:

- 如果已有未结束 battle,返回已有 battle。
- 或创建新 battle 前清理旧 battle。

不要让同一玩家同时有多场可结算战斗。

### 6.4 限制同一 battle 单 WS 连接

`BattleEngine.__init__`:

```python
self.ws_attached = False
```

WS 连接时:

```python
if engine.ws_attached:
    await ws.send_json({"type": "error", "data": {"message": "战斗已在其他窗口打开"}})
    await ws.close()
    return
engine.ws_attached = True
```

finally:

```python
engine.ws_attached = False
```

如果需要支持重连,要设计 owner token 和短 grace period。MVP 可先单连接。

### 6.5 后台任务清理

`BattleEngine.__init__`:

```python
self._bg_tasks: set[asyncio.Task] = set()
```

新增:

```python
def _track_task(self, task: asyncio.Task):
    self._bg_tasks.add(task)
    task.add_done_callback(self._bg_tasks.discard)
    return task

async def cleanup(self):
    tasks = list(self._bg_tasks)
    if self.current_narration_task and not self.current_narration_task.done():
        self.current_narration_task.cancel()
    if self.chapter_task and not self.chapter_task.done():
        self.chapter_task.cancel()
    for t in tasks:
        if not t.done():
            t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
```

所有 `asyncio.create_task(...)` 改成:

```python
self._track_task(asyncio.create_task(...))
```

包括:

- `current_narration_task`
- `chapter_task`
- `_refill_pool()`
- `warmup_pool()` 如果从 WS 启动,可以由 main 侧跟踪或 engine 提供 `start_warmup_pool()`

### 6.6 skip 行为

当前 `skip_narration()` 只取消 `current_narration_task`。建议:

```python
def skip_narration(self, include_chapter: bool = False):
    ...
    if include_chapter and self.chapter_task and not self.chapter_task.done():
        self.chapter_task.cancel()
```

WS action 可拆:

```text
skip_narration
skip_chapter
```

前端在 `chapterGenerating` 时发 `skip_chapter`。

### 6.7 验收

1. 同一 battle 打开两个标签页,第二个被拒绝或明确接管。
2. 同一玩家不能同时结算两场战斗。
3. 离开战斗页后 chapter_task 不继续消耗 token。
4. 点击跳过章节后后端停止章节生成。
5. 连续 20 场战斗后后台 task 数量不持续增长。

---

## 7. Phase 5:数值与叙事一致性

### 7.1 命中率 clamp

修改:

```python
hit_rate = card.hit_rate - evasion
```

为:

```python
hit_rate = max(0.05, min(0.98, card.hit_rate - evasion))
```

敌方命中同理。

### 7.2 卡牌预览复用真实公式

`/api/battle/{battle_id}/card-preview` 当前命中率公式是错的。  
建议抽公共函数:

```python
def estimate_player_card(engine, card):
    ...
```

预览和实际结算至少使用相同:

```text
player_atk
enemy_def
enemy_evasion
crit_rate
crit_dmg
focus_next
```

### 7.3 预生成叙事池绑定卡牌

当前通用池可能让治疗/高级招式拿到普攻叙事。短期修法:

```python
if card.id == "basic_strike" and my_outcome["type"] == "hit" and self.narration_pool:
    ...
```

不要让 heal/buff/ult 使用普通池。

### 7.4 灵丹卡策略

`cards.py` 里的 `lingdan` 是 0 成本回血卡。选择一个策略:

| 策略 | 修改 |
|---|---|
| 消耗灵气 | `qi_cost` 改为合理数值 |
| 消耗背包物品 | 战斗内道具系统接管 |
| 每场限次 | `state["heal_card_used"]` |

不要让它继续无成本无限回血。

### 7.5 怪物技能 effect 落地

第一批可不做。但若要做,先实现 4 个:

```text
poison/bleed/burn -> DOT
qi_drain -> 扣灵气
stun/bind -> 下回合概率无法行动
defend/reflect -> 减伤/反伤
```

---

## 8. 测试与验证

### 8.1 建议新增测试文件

如果项目还没有测试目录,可新增:

```text
backend/tests/test_battle_engine.py
backend/tests/test_battle_api.py
```

如果不想引入 pytest,至少写临时脚本:

```text
scripts/check_battle_fixes.py
```

但正式修复建议用 pytest。

### 8.2 必测用例

#### 状态同步

1. 胜利后 HP 持久化为战斗结束 HP。
2. 胜利后 Qi = 战斗剩余 Qi + 奖励 Qi。
3. 撤退后 HP/Qi 不回到战前。
4. 战败后 UI 和 `/api/character/me` 都是 HP 1。
5. 升级满血满灵气时,`engine.state` 和 character 都同步。

#### 并发

1. 100ms 内连发 10 个 cast,只结算 1 个或严格串行拒绝。
2. enemy_turn/processing 时 cast 不改变状态。
3. victory 后 cast 返回错误。
4. 重复 end 不重复发奖励。
5. 多标签页同 battle 不抢事件。

#### 赠礼

1. 第 4 次赠礼被服务端拒绝,即使请求传 0。
2. 赠礼成功后 result 是统一枚举。
3. 赠礼成功写 battle_history。
4. 已结束 battle 不能赠礼。

#### 道具

1. 战斗中吃药修改 `engine.state`。
2. 最后一颗药并发使用不会多次生效。
3. 背包扣除失败时不应用角色效果。

#### 生命周期

1. 离开战斗页后 task 被清理。
2. 跳过章节能取消 `chapter_task`。
3. 连续多场战斗不出现 task 泄漏。

---

## 9. 不要踩的坑

### 9.1 不要只修前端

前端按钮禁用、队列、防抖都不能当安全边界。所有规则必须后端验证。

### 9.2 不要继续分散 save_character

同一场战斗结束只应有一个角色提交点。多个函数分别 save 会继续覆盖字段。

### 9.3 不要让奖励基于旧 character.qi

胜利奖励必须基于战斗剩余 Qi:

```text
final_qi = battle_state_qi + reward_qi
```

不是:

```text
final_qi = old_character_qi + reward_qi
```

### 9.4 不要让赠礼继续信任前端次数

次数必须服务端记录。

### 9.5 不要在锁内等待 LLM

行动锁只保护数值结算和状态提交。LLM 叙事仍应 fire-and-forget,不要放在 action lock 内长时间 await。

### 9.6 不要用 battle_history 判断所有教学状态

新增独立 flag:

```python
char["flags"]["battle_tutorial_done"] = True
```

历史是展示数据,不是流程控制唯一来源。

---

## 10. 建议提交顺序

### Commit 1:服务端行动锁

内容:

- `BattleEngine._action_lock`
- `cast()` 状态校验
- `flee()` 持锁

验证:

- 并发 cast 脚本。

### Commit 2:统一提交

内容:

- `_commit_battle_result`
- `_grant_rewards` 改为 apply-to-char
- `_record_battle_to_character` 合并进 commit
- HP/Qi 持久化

验证:

- 胜利/失败/撤退状态同步。

### Commit 3:赠礼修复

内容:

- 服务端 gift_count
- ended 检查
- result 统一
- 赠礼成功走 commit

验证:

- 第 4 次赠礼拒绝。
- 赠礼胜利显示正确。

### Commit 4:战斗内道具

内容:

- WS `use_item`
- `BattleEngine.use_item`
- 前端 Battle.vue 改走 WS 或 battle API
- 通用 inventory use 原子扣物品

验证:

- 战斗中吃药真实生效。

### Commit 5:生命周期清理

内容:

- active battle 限制
- WS 单连接限制
- cleanup tasks
- skip chapter

验证:

- 多标签页/离开页面/跳过章节。

### Commit 6:数值和体验一致性

内容:

- hit_rate clamp
- card-preview 公式
- narration pool 限定 basic_strike
- 灵丹卡成本策略

验证:

- 预览与实际接近。
- 治疗/高级招式叙事不再错配。

---

## 11. 最小验收标准

修复完成后,至少必须满足:

```text
1. 服务端拒绝非 player_turn 的 cast。
2. 并发 cast 不会造成多次结算。
3. 胜利、战败、撤退都会正确持久化 HP/Qi。
4. 胜利奖励基于战斗剩余 Qi 计算。
5. 同一场战斗奖励只发一次。
6. 赠礼次数无法由前端绕过。
7. 战斗中吃药会修改 BattleEngine.state。
8. 战斗结束后 battle_history 正确且不重复。
9. 离开战斗后 LLM 后台任务不会继续泄漏。
10. 前端返回地图后刷新角色,不会显示一套、数据库另一套。
```

如果只修了 UI,或者只让“正常点击路径看起来没问题”,不算通过。

---

## 12. 给修复 AI 的最终指令

请按 Phase 1 到 Phase 5 顺序修复。每个阶段都要:

1. 先读相关文件。
2. 保持改动范围小。
3. 不重构无关 UI。
4. 不改变现有世界观文案,除非是错误提示或 result 枚举需要。
5. 每完成一阶段,运行最小验证。
6. 如果发现当前代码和本文档描述不一致,以当前代码为准,并在修复说明中写出差异。

最高优先级是:

```text
BattleEngine action lock
cast player_turn 校验
统一 _commit_battle_result
战斗内 use_item
服务端 gift_count
```

先把这五个修完,再处理数值、叙事、章节和体验问题。
