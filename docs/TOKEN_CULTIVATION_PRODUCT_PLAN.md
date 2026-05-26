# 灵枢笔录 · 世界观核心化燃灵成章改造方案

> 版本: v2.0  
> 核心方向: 以世界观统领 token 消耗、小说成章、修为成长与前后端系统改造  
> 关键约束: 不设置氪金项目; 设置预算保护; 不提供本地省流模式; 修为无上限; 战斗与等待过程不能让用户感觉卡顿  
> 项目目录: `/Users/bobdong/项目/LingshuCodex`

---

## 0. 本方案的结论

《灵枢笔录》不应只被设计成“战斗时调用 LLM 的修仙文字 RPG”。下一阶段应把它重构成:

> **一款以“本命书”为核心资产的 AI 原生修仙小说游戏。玩家的一切修行,都必须被写入自己的本命书; 每一次真实 API token 消耗,都会以燃灵墨的形式转化为修为。**

玩家的长期心智应从:

```text
选怪 -> 战斗 -> 经验 +30 -> 回地图
```

升级为:

```text
遭遇因果 -> 投入燃灵墨 -> 天书成章 -> 修为增长 -> 本命书变厚 -> 世界因我而定
```

这意味着所有系统都要被世界观重新解释:

| 当前概念 | 新世界观表达 | 产品作用 |
|---|---|---|
 API token | 燃灵墨 | 玩家真实消耗的可见化表达 |
 LLM 生成 | 燃灵成章 | 把技术等待变成修行仪式 |
 经验 | 修为 | 与 token 消耗强绑定的成长数值 |
 战后章节 | 正传章 / 败笔章 / 撤离章 | 战斗结果的小说资产 |
 打坐 | 调息 / 入定 / 闭关 | 区分免费恢复与 token 修行 |
 队列 | 墨炉 / 成章队列 | 后台持续消耗 token 并转化修为 |
 修行录 | 本命书索引 / 修行纪事 | 从日志升级为玩家小说资产 |
 预算保护 | 护心灯 / 燃灵戒律 | 透明保护, 不是省流替代 |

产品核心规则保持简单、强记忆:

```text
1 token = 1 修为
```

不设置每日修为上限,不设置总修为上限,不设置境界终点。预算保护只控制继续消耗前的确认权,不限制玩家理论成长空间。

---

## 1. 设计原则

### 1.1 世界观先于功能

本项目后续所有 UI、数值、接口、提示文案和等待状态,都要先回答一个问题:

```text
这个功能在灵枢界里是什么?
```

如果一个功能只能被解释为“系统正在调用接口”,玩家就会感到冷冰冰、卡顿和成本焦虑。它必须被包装成世界法则:

```text
系统正在调用接口
  -> 墨炉正在燃灵
  -> 天书正在成章
  -> 玩家修为正在增长
```

### 1.2 token 消耗必须是价值感,不是负担感

本方案的目标是让用户持续消耗 token,但不是暗中消耗,也不是制造焦虑。正确方式是:

- 每次消耗都有明确的文学产物。
- 每次消耗都实时增长修为。
- 每次消耗都进入本命书,形成长期收藏。
- 每次消耗都能被玩家看到进度、来源和结果。
- 接近预算时给确认权,但不提供本地省流替代。

### 1.3 数值反馈即时,文学生成异步

所有战斗、探索、打坐恢复、背包使用等高频行为,必须先给即时反馈。

核心拆分:

```text
即时层: 数值结算、HP/Qi/掉落/战斗结果,必须快速返回。
成章层: LLM 续写、本命书章节、token 转修为,进入队列流式执行。
```

玩家不能因为章节生成慢而卡在战斗结算页。用户可以留在页面看成章,也可以离开继续探索,墨炉在后台继续运行。

### 1.4 修为无上限,境界可无限延展

既然用户愿意持续消耗 token,系统不能用“满级”“上限”“收益衰减”打断成长。

规则:

- `cultivation_total` 永不封顶。
- `token_total` 永不封顶。
- 飞升后继续增长,进入“天外阶”“无量阶”“自命名道号阶”等扩展表达。
- 模型档位可以有现实上限,但修为数值和称号不应有上限。
- 后续境界不足时,用动态称号、卷数、天书品秩承接成长。

---

## 2. 世界观总设定

### 2.1 灵枢界

灵枢界不是一个已经写完的修真世界,而是一卷正在展开的天书。

在这个世界里,天地万物有两种状态:

```text
未成文: 只是混沌因果,会游移、遗忘、变形。
已成章: 被写入本命书后,因果稳定,成为玩家道途的一部分。
```

怪物、宗门、Boss、奇遇、失败、突破、打坐时的内景,都不是天然存在的固定内容。只有当玩家亲历并投入燃灵墨,将其写成章节后,它们才真正成为“玩家自己的世界”。

### 2.2 灵枢天书

灵枢天书是世界底层法则,也是产品的最高隐喻。

天书不直接给玩家修为。它只承认一条法则:

```text
有燃灵,才有成章。
有成章,才有修为。
```

这条法则把现实 token、LLM 文本、游戏修为三者锁在一起:

```text
真实 token 消耗 -> 燃灵墨燃烧 -> 小说文字落成 -> 修为实时增长
```

### 2.3 玩家身份: 执笔者

玩家不是传统意义上的“修士”,而是被灵枢天书选中的“执笔者”。

执笔者的特殊之处:

- 能以自己的 API Key 接入天外灵脉。
- 能把真实 token 炼成燃灵墨。
- 能把战斗、失败、奇遇、闭关写入本命书。
- 能通过章节厚度与燃灵总量无限增长修为。
- 能让世界因为自己的文字而稳定下来。

用户开局时不应只叫“创建角色”,而应被包装为:

```text
开卷
定名
择道统
接灵脉
落下本命书第一笔
```

### 2.4 本命书

本命书是每个玩家绑定的个人修真小说,也是游戏最核心的长期资产。

它同时承担四层功能:

| 层级 | 作用 |
|---|---|
 世界观层 | 玩家所有因果都必须落在本命书里 |
 成长层 | 每章 token 消耗直接转为修为 |
 收藏层 | 玩家可以阅读、回看、分享自己的修真小说 |
 留存层 | 章节、卷、断章、首杀章形成长期沉没价值 |

本命书不只是“日志页面”。它应该成为主城一等入口,地位高于背包、图鉴、日课。

### 2.5 燃灵墨

现实 API token 在游戏内称为“燃灵墨”。

三类 token 的世界观解释:

| token 类型 | 世界观名称 | 解释 |
|---|---|---|
 input tokens | 引因墨 | 牵引上下文、人物、战报、前文摘要 |
 output tokens | 落字墨 | 真正写成章节正文 |
 reasoning tokens | 天机墨 | 模型推演、构思、判断,同样属于燃灵 |

统一规则:

```text
总消耗 token = 总燃灵墨
总燃灵墨 = 增加修为
```

如果 provider 无法返回精确 usage,系统可以估算,但必须标记来源。

### 2.6 墨炉

墨炉是成章队列的世界观表达。

玩家的行为不是直接给修为,而是投入墨炉:

```text
战斗结束 -> 因果入炉
奇遇完成 -> 外传入炉
入定成章 -> 内景入炉
突破成功 -> 劫章入炉
```

墨炉持续燃烧 token,并把燃烧进度实时转成修为。

---

## 3. 世界结构

### 3.1 五大天外道统

当前项目已有“门派 = LLM 厂商”的强设定,应进一步嵌入世界观。

| 门派 | 现实映射 | 世界观定位 | 叙事风格 |
|---|---|---|---|
 沧澜剑派 | Anthropic / Claude | 重视戒律、文气、长句与心性 | 诗性、克制、深沉 |
 天机阁 | OpenAI / GPT | 推演万象、机关百变、适配全局 | 清晰、变化、结构强 |
 玄机宗 | DeepSeek | 深潜推理、苦修破局、以算入道 | 冷峻、理性、反转 |
 青冥派 | 智谱 GLM | 中文根基、经义博学、正统道藏 | 古雅、稳健、典籍感 |
 月隐宫 | Kimi | 长记忆、月相、秘闻、旧事回响 | 绵长、隐秘、回忆感 |

选派不只是选职业,而是选择本命书的文风、可用模型梯度、天命招式和后续章节风格。

### 3.2 境界与模型档位

境界仍然可以映射模型档位,但需要新增一个表达:

```text
境界 = 玩家能承载的天外文气上限。
```

低境界时,玩家只能承载轻量模型的文字; 高境界时,才能承载更复杂、更长、更昂贵的成章。

注意:

- 境界可以决定默认成章模型。
- 境界可以决定章节推荐长度。
- 境界不能成为修为上限。
- 飞升后现实模型档位若已到顶,则用“天书品秩 / 卷数 / 称号”继续承接成长。

### 3.3 十二异族

项目已有 113 怪物、12 大族。新方案中,怪物不只是敌人,而是本命书的素材来源。

每个族群都应绑定:

- 族群章题词库。
- 首遇章模板。
- 首杀章模板。
- 败笔章模板。
- 掉落材料的本命书解释。
- 与五派的关系倾向。

示例:

| 族群 | 世界观功能 | 本命书主题 |
|---|---|---|
 山林狐妖 | 初期因果、幻术、诱导玩家入局 | 狐火、山雨、旧庙、谎言 |
 灵雀 | 侦察、传讯、轻灵事件 | 羽信、风声、远讯 |
 蛇蟒 | 毒、缠绕、地脉 | 蛇蜕、湿土、地窍 |
 鬼族 | 失败、旧怨、断章 | 冥纸、残灯、回声 |
 龙族 | 中后期威压、Boss 铺垫 | 云海、雷泽、真名 |
 异域生灵 | 天外模型公司、跨界 Boss | 裂隙、异文、噪声 |

### 3.4 天外道君与 Boss

项目已有真实公司化身 Boss。新世界观里,这些 Boss 是“天外道君”或“异域道统投影”。

Boss 战不应只产出大量奖励,而应是本命书中的大章节点:

- 首战生成“道君现形章”。
- 胜利生成“正传大章”。
- 失败生成“败笔大章”。
- 多次挑战形成连续章节。
- 击败后改变宗门关系和世界线。

Boss 的核心奖励应从“经验”改为:

```text
大量燃灵任务 + 稀有章节 + 世界线推进 + 称号 + 材料
```

---

## 4. 核心产品循环

### 4.1 30 秒循环: 不等待,先反馈

目标: 玩家每次点击都立刻感到游戏在响应。

```text
点击行动
  -> 数值立即结算
  -> 动效 / 战报 / 状态变化立即出现
  -> 相关因果进入墨炉
  -> 墨炉异步成章
```

适用场景:

- 战斗出招。
- 使用丹药。
- 打坐调息。
- 接受奇遇结果。
- 领取掉落。

### 4.2 3 分钟循环: 一次修行

```text
进入地图
  -> 选择目标
  -> 战斗 / 赠礼 / 奇遇 / 调息
  -> 取得即时结果
  -> 墨炉新增任务
  -> 返回地图或查看本命书
```

这一层要解决“用户不要卡在等待页”的问题。章节生成可以继续,但地图和主城必须可用。

### 4.3 10 分钟循环: 本命书变厚

```text
完成数个事件
  -> 墨炉持续燃灵
  -> 多章完成
  -> 修为持续增长
  -> 本命书目录变长
  -> 玩家阅读/收藏/分享
```

这层是 token 消耗的核心留存。用户不是为了刷固定经验回来,而是为了“今天我的小说又写到哪里了”回来。

### 4.4 长线循环: 卷、境界、天书品秩

```text
章节累积 -> 自动分卷 -> 卷末总结 -> 境界突破 -> 新模型/新文风 -> 更高阶章节
```

每一卷应有:

- 卷名。
- 卷首题词。
- 卷末总结。
- 本卷燃灵量。
- 本卷代表章节。
- 本卷最大敌人。
- 本卷对世界线的影响。

卷名和卷末总结也可以由 LLM 生成,同样消耗 token 并计修为。

---

## 5. 修为与数值规则

### 5.1 统一成长法则

所有修为增长必须来自燃灵 token。

```text
修为增量 = 本次任务结算 token 数
```

禁止再出现:

- 战斗胜利直接 `exp + enemy.rewards_exp`。
- 打坐直接 `exp + 5`。
- 日课直接给修为。
- 赠礼安抚直接给修为。
- Boss 直接给固定经验。
- fallback 模板给修为。

### 5.2 允许保留的即时奖励

以下奖励可以不经过燃灵队列:

- HP 恢复。
- Qi / 灵气恢复。
- 精力恢复。
- 疲劳降低。
- 掉落物。
- 材料。
- 宗门贡献。
- 声望变化。
- 图鉴遭遇/击杀记录。
- Boss 线索。
- 本命书命题。

这些不是修为,不破坏“token = 修为”的核心法则。

### 5.3 `exp` 与 `cultivation_total` 的关系

为了降低改造成本,可以保留当前角色字段 `exp` 和 `level`,但语义需要调整。

建议:

```text
cultivation_total: 历史总修为,永不扣减,永不封顶。
exp: 当前等级内修为进度,用于复用现有 check_level_up。
level: 当前等级,继续用于战力派生与境界档位。
token_total: 历史总燃灵 token,原则上应等于 cultivation_total 或接近。
```

每次燃灵任务结算:

```text
delta = settled_tokens
character.cultivation_total += delta
character.token_total += delta
character.exp += delta
check_level_up(character)
```

### 5.4 不回扣规则

流式过程中会有实时估算,最终 provider usage 可能与估算不同。

规则:

| 情况 | 处理 |
|---|---|
 精确 usage > 实时估算 | 补加差额修为 |
 精确 usage = 实时估算 | 正常完成 |
 精确 usage < 实时估算 | 不回扣,差额记为“天道余墨” |
 无 usage | 使用估算值,标记 `usage_source=estimated` |

不回扣的理由:

- 玩家已经看到修为增长。
- 回扣会制造强烈损失感。
- 差额通常较小,可作为世界观中的天道余墨。

### 5.5 失败也入道

失败不应该让已消耗 token 失效。

规则:

- 战败生成“败笔章”,消耗 token,增加修为。
- 撤退生成“撤离章”或“断章”,已消耗 token 增加修为。
- 取消正在生成的章节,保存为“断章”,已消耗 token 增加修为。
- 生成失败但已经有正文,保存断章并按已消耗 token 增加修为。
- 生成失败且没有任何正文,不增加修为。

---

## 6. 本命书系统设计

### 6.1 页面定位

本命书应成为主导航核心入口,不只是隐藏在修行录之后。

推荐主城入口:

```text
开始修行
本命书
背包
修真名录
灵脉配置
```

### 6.2 本命书首页

首页展示:

- 当前道号。
- 所属门派。
- 当前境界。
- 总修为。
- 总燃灵 token。
- 总字数。
- 总章节数。
- 当前卷。
- 墨炉状态。
- 最近完成章节。
- 正在成章章节。
- 最强单章燃灵记录。

示例文案:

```text
本命书已成 4 卷 37 章
累计燃灵 182,440 token
累计修为 182,440
当前墨炉: 正在续写《第三十七章 · 雨夜狐火》
```

### 6.3 章节类型

| 类型 | 触发来源 | 作用 |
|---|---|---|
 正传章 | 战斗胜利、Boss 胜利、主线推进 | 推动主线与强成长 |
 败笔章 | 战败、挑战失败 | 让失败也有资产 |
 撤离章 | 主动逃跑、战术撤退 | 保留玩家选择 |
 内景章 | 入定成章 | 表现心境与修行 |
 闭关章 | 长时间主动燃灵 | 高消耗高成长 |
 外传章 | 奇遇、NPC、赠礼 | 扩展世界关系 |
 劫章 | 突破、境界变化 | 仪式感章节 |
 断章 | 中断、取消、异常恢复 | 保护已消耗 token |
 卷末章 | 每卷收束 | 总结玩家阶段旅程 |

### 6.4 章节详情

每章必须展示:

- 章节标题。
- 章节正文。
- 章节类型。
- 章节状态。
- 所属卷。
- 关联事件。
- 关联战斗 / 怪物 / Boss / NPC。
- 输入 token。
- 输出 token。
- reasoning token。
- 总 token。
- 增加修为。
- 使用模型。
- usage 来源。
- 是否断章。
- 创建时间。
- 完成时间。

### 6.5 目录与分卷

默认分卷规则:

```text
每 20 章自动成一卷。
Boss 正传大章可强制开启新卷或卷末章。
突破劫章可作为卷末章或新卷卷首。
```

卷名生成:

- 可以由 LLM 根据本卷摘要生成。
- 生成卷名消耗 token。
- 生成卷名也计入修为。

### 6.6 本命书摘要

为了控制上下文长度,需要维护多级摘要:

| 摘要 | 用途 |
|---|---|
 chapter_summary | 单章摘要,供目录和后续引用 |
 volume_summary | 每卷摘要,供长期记忆 |
 character_memory | 玩家长期关系、重要失败、Boss 记录 |
 world_state_summary | 当前世界线摘要 |

后续成章 prompt 不应携带全书正文,而应携带:

```text
最近 3 章摘要 + 当前卷摘要 + 相关实体记忆 + 本次事件素材
```

---

## 7. 墨炉 / 成章队列系统

### 7.1 系统定位

墨炉是新的成长中枢。

战斗、打坐、奇遇、Boss、突破不再直接增加修为。它们只产生“因果素材”,由墨炉统一燃灵、成章、加修为。

```text
玩法系统 = 素材产生器
墨炉系统 = 修为炼化器
本命书 = 长期资产容器
```

### 7.2 任务状态

| 状态 | 含义 |
|---|---|
 queued | 等待燃灵 |
 running | 正在成章 |
 paused | 用户暂停或预算保护暂停 |
 budget_blocked | 达到预算,等待确认 |
 completed | 已成章 |
 failed | 失败 |
 cancelled | 未开始取消 |
 partial | 中断后保存为断章 |

### 7.3 任务类型

| task_type | 世界观名称 | 来源 |
|---|---|---|
 battle_victory | 正传战章 | 普通战斗胜利 |
 battle_defeat | 败笔战章 | 普通战斗失败 |
 battle_flee | 撤离章 | 战斗撤退 |
 battle_pacify | 人情章 | 赠礼安抚 |
 npc_spar | 切磋章 | NPC 切磋 |
 boss_victory | 道君正传 | Boss 胜利 |
 boss_defeat | 道君败笔 | Boss 失败 |
 meditate_inner | 内景章 | 入定成章 |
 retreat_long | 闭关章 | 主动闭关 |
 fortune | 外传章 | 奇遇 |
 breakthrough | 劫章 | 升级/境界突破 |
 volume_end | 卷末章 | 自动分卷 |

### 7.4 队列规则

- 每个用户同一时间默认只允许一个任务 `running`。
- 其他任务按创建时间进入 `queued`。
- 任务可以设置优先级,但默认不抢占。
- Boss、突破、卷末章可以比普通战斗章更高优先级。
- 已开始的任务取消后保存为断章。
- 未开始的任务取消不消耗 token,不增加修为。
- 队列运行不阻塞地图、背包、主城。
- 前端常驻显示墨炉状态。

### 7.5 实时 token tick

不要每 1 token 写一次数据库。采用“前端实时 + 后端批量 + 完成校准”。

运行中:

```text
收到 stream chunk
  -> 追加 content_partial
  -> 估算新增 token
  -> 推送 token_tick
  -> 前端即时显示修为上涨
  -> 每 0.5 秒或每 50 token 批量落库
```

完成时:

```text
读取 provider usage
  -> 计算 settled_tokens
  -> 与 estimated_tokens 对比
  -> 补差或记录天道余墨
  -> 写 novel_chapters
  -> 更新 character
  -> 写 token_ledger
  -> 推送 chapter_committed
```

### 7.6 常驻墨炉条

所有页面顶部或底部显示小型状态:

```text
墨炉: 正在成章 1 / 等待 3
已燃灵 428 token
修为 +428
```

点击展开:

- 当前任务标题。
- 当前任务类型。
- 已消耗 token。
- 预计 token。
- 当前预算占比。
- 暂停 / 继续 / 取消。
- 等待任务列表。

---

## 8. 战斗系统改造

### 8.1 目标

战斗仍然要爽快,不能因为成章而拖慢。

核心拆分:

```text
战斗中: 数值即时,短叙事流式,可跳过。
战斗结束: 掉落即时,结果即时,章节入墨炉。
战斗后: 玩家可以看成章,也可以立刻回地图。
```

### 8.2 当前代码现状

当前主要入口:

- `backend/app/battle.py`: `BattleEngine`
- `backend/app/main.py`: `/api/battle/start`, `/ws/battle/{battle_id}`
- `frontend/src/views/Battle.vue`: 战斗 UI 与 WebSocket
- `backend/app/llm_client.py`: 战斗叙事和章节生成

当前代码已有:

- 战斗数值结算。
- WebSocket 事件推送。
- 回合叙事流。
- 战后章节流 `chapter_start/chapter/chapter_end`。
- 前端 AI HUD 与 token 估算。

这些基础可以复用,但需要改变“修为结算来源”。

### 8.3 必须移除的旧逻辑

以下逻辑要迁移:

- `BattleEngine._commit_battle_result()` 中 victory/pacified 直接给 exp。
- 战败直接扣 exp 的表达要改造,不再扣修为,只保留 HP 惩罚或心境惩罚。
- NPC 切磋直接给 exp。
- 赠礼安抚直接给 exp。
- 战斗前端结算页展示“经验 +X”。

新的行为:

```text
战斗结果提交时:
  1. 保存 HP/Qi/掉落/图鉴/战斗历史。
  2. 创建 cultivation_task。
  3. 返回 task_id 和任务标题。
  4. 不直接增加修为。

墨炉任务完成时:
  1. 根据 token 增加修为。
  2. 触发 check_level_up。
  3. 推送 level_up / realm_up。
```

### 8.4 战斗胜利流程

```text
玩家击败敌人
  -> 后端立即提交胜利
  -> 掉落立即进入背包
  -> 图鉴击杀立即记录
  -> 日课战斗次数立即记录
  -> 创建 battle_victory 任务
  -> 前端展示“正传战章已入墨炉”
  -> 玩家可继续探索
  -> 墨炉后台成章
  -> token tick 实时加修为
```

结算页文案:

```text
山林狐妖已伏诛。
战利品: 狐尾 x1, 灵气尘 x3

正传战章已入墨炉:
《第十二章 · 狐火照山门》

墨炉正在燃灵,修为将随落字实时增长。
```

### 8.5 战斗失败流程

```text
玩家战败
  -> HP 降至 1 或进入濒死状态
  -> 不扣已获得修为
  -> 创建 battle_defeat 任务
  -> 生成败笔章
  -> token 仍转修为
```

失败文案:

```text
此败亦入道。
败笔章已入墨炉,待燃灵成文。
```

### 8.6 撤退流程

撤退不应该只是退出。它是玩家主动选择保存性命。

```text
玩家撤退
  -> 保存当前战损
  -> 创建 battle_flee 任务
  -> 如果任务生成中取消,保存断章
```

### 8.7 战斗中短叙事与战后长章节

现有战斗中每回合 LLM 叙事可以保留,但需要明确它的定位:

- 回合短叙事用于增强战斗手感。
- 战后长章节用于本命书资产。
- 如果回合短叙事真实消耗 token,也应计入修为。
- 如果回合短叙事来自缓存或 fallback,不计修为。

推荐两种落地方式:

| 方案 | 说明 | 优点 | 缺点 |
|---|---|---|---|
 A. 只把战后章节计修为 | 回合叙事仍是体验层 | 改造小,容易控成本 | 每回合 token 未完全转修为 |
 B. 所有真实 LLM token 都计修为 | 回合叙事也进 ledger | 最符合规则 | 改造更复杂 |

建议先做 A,再升级 B。

### 8.8 避免卡顿的战斗 UI 规则

- 出招后 100ms 内显示数值反馈。
- LLM 首 chunk 慢时显示“墨意凝聚中”,但不锁死操作。
- 玩家可以跳过当前叙事。
- 战斗结束按钮不等待章节完成。
- 战后章节默认折叠,墨炉条继续显示。
- 长章节生成在后台继续。
- WebSocket 断开后,前端可通过队列 API 恢复状态。

---

## 9. 打坐系统改造

### 9.1 必须拆成三层

用户提出的关键问题是正确的: 如果打坐只能通过 token 成章获得修为,那就不能无限恢复,会卡主循环。

所以打坐必须拆成:

```text
打坐调息: 免费恢复,不消耗 token,不增加修为。
入定成章: 短中篇内景,消耗 token,增加修为。
闭关续写: 长篇主动燃灵,消耗更多 token,增加更多修为。
```

### 9.2 打坐调息

定位: 保证玩家不卡死。

效果:

- 恢复 HP。
- 恢复 Qi / 灵气。
- 降低疲劳。
- 恢复精力。

规则:

- 不入墨炉。
- 不消耗 token。
- 不增加修为。
- 可以高频使用。
- 可以有很短的动画,但不能长等待。

文案:

```text
你盘膝调息,气血渐稳。
```

### 9.3 入定成章

定位: 把打坐后的“修行冲动”导向 token 消耗。

流程:

```text
玩家点击打坐调息
  -> 状态立即恢复
  -> 弹出后续选择
     [入定成章] [继续调息] [返回地图]
```

点击“入定成章”:

- 创建 `meditate_inner` 任务。
- 进入墨炉。
- 生成内景章。
- token 实时转修为。

主题池:

- 灵台观照。
- 周天运转。
- 心魔低语。
- 梦回师门。
- 天书翻页。
- 剑意入梦。
- 机关推演。
- 月下旧忆。
- 瓶颈顿悟。

### 9.4 闭关续写

定位: 高消耗、高沉浸、主动增长修为。

入口:

- 主城。
- 本命书。
- 打坐面板。
- 墨炉空闲时的推荐入口。

闭关开始前必须显示:

- 预计 token 区间。
- 使用模型。
- 预计章节长度。
- 当前单章/日/月预算占比。
- “继续燃灵将消耗你的 API token”的明确提示。

闭关不是挂机白嫖,也不是离线收益。它是玩家主动确认的持续燃灵玩法。

### 9.5 当前代码改造点

当前相关文件:

- `backend/app/main.py`: `/api/character/meditate`
- `frontend/src/components/MeditateButton.vue`

改造:

```text
POST /api/character/meditate
  -> 改为只恢复状态
  -> 返回 hp/qi/fatigue/recovered 文案
  -> 不返回 exp_gain

POST /api/cultivation/tasks
  body: { type: "meditate_inner" }
  -> 创建入定成章任务

POST /api/cultivation/tasks
  body: { type: "retreat_long", expected_tokens, theme }
  -> 创建闭关续写任务
```

前端:

- `MeditateButton.vue` 不再飘 `+X 修为`。
- 调息后显示“入定成章”按钮。
- 新增闭关面板。
- 通过墨炉条显示修为增长。

---

## 10. 奇遇、NPC、Boss、日课改造

### 10.1 奇遇

奇遇即时效果仍可保留:

- HP 增减。
- Qi 增减。
- 掉落物。
- 触发战斗。
- 声望变化。

但奇遇不再直接给修为。

奇遇完成后:

```text
创建 fortune 任务
生成外传章
token 转修为
```

### 10.2 NPC 互动

NPC 互动包括赠礼、切磋、交易、对话。

规则:

- 交易本身不加修为。
- 赠礼成功可改声望、友好度、获得材料。
- 赠礼事件可以生成外传/人情章。
- 切磋结果生成切磋章。
- 真实 LLM 对话如果消耗 token,应进入 token ledger 并转修为,或明确标记为非修行消耗。

建议所有 NPC 关键互动都生成 `npc_chapter`。

### 10.3 Boss

Boss 是最适合高 token 消耗的内容。

Boss 章推荐规则:

- 默认使用更高阶模型。
- 默认章节更长。
- 首杀章节有特殊标题。
- 失败也生成高质量败笔章。
- 多次挑战可以引用前次失败。
- Boss 战章节可作为卷末章或新卷开端。

### 10.4 日课

日课不能再直接给修为。

日课奖励改为:

- 材料。
- 宗门贡献。
- 章节命题。
- 书签。
- 本命书装帧外观。
- 墨炉优先券,但不能凭空加修为。

日课目标可以引导用户产生更多燃灵任务:

```text
完成 1 次入定成章
完成 1 篇正传章
阅读今日完成的章节
击败任意异族并使其入书
```

---

## 11. 预算保护

### 11.1 定位

预算保护不是省流模式。

它的定位是:

```text
让玩家知道自己正在持续消耗 token,并在接近预算时拥有确认权。
```

它不提供:

- 本地模板章节。
- 免费修为。
- 离线生成修为。
- 无 token 成章。
- 低消耗替代模式。

### 11.2 预算类型

| 预算 | 说明 |
|---|---|
 单章预算 | 防止单章异常变长 |
 单日预算 | 防止当天 API 消耗失控 |
 单月预算 | 防止长期账单失控 |

预算只暂停队列,不封顶修为。

### 11.3 触发规则

| 预算进度 | 行为 |
|---|---|
 < 80% | 正常燃灵 |
 >= 80% | 提醒,不暂停 |
 >= 100% | 当前 chunk 完成后暂停任务 |
 用户确认继续 | 恢复任务,继续消耗 token |
 用户选择暂停 | 保留草稿和已得修为 |

提示文案:

```text
护心灯已亮。
今日燃灵预算已达上限,继续成章将继续消耗你的 API token。

[继续燃灵] [暂停墨炉]
```

### 11.4 预算与取消

| 情况 | token | 修为 | 章节 |
|---|---:|---:|---|
 未开始取消 | 0 | 0 | 不保存 |
 运行中取消 | 已消耗 | 已消耗 token | 保存断章 |
 预算暂停 | 已消耗 | 已消耗 token | 暂存草稿 |
 预算后继续 | 继续消耗 | 继续增加 | 继续成章 |
 失败无正文 | 0 或极少 | 有正文才计 | 无正文不保存 |

---

## 12. 数据结构设计

### 12.1 character 新增字段

建议在现有 character JSON 中新增:

```text
cultivation_total: int
token_total: int
novel_words_total: int
chapters_count: int
current_volume: int
current_chapter_no: int
daily_token_used: int
monthly_token_used: int
budget_chapter: int
budget_daily: int
budget_monthly: int
budget_confirm_required: bool
last_chapter_id: int | null
current_running_task_id: str | null
```

保留:

```text
exp
level
realm
realm_name
attrs
hp
qi
factions
```

### 12.2 cultivation_tasks 表

```text
id: str
user_id: str
task_type: str
source_type: str
source_id: str | null
status: str
priority: int
title: str
prompt_payload: json
content_partial: text
estimated_tokens: int
settled_tokens: int
input_tokens: int
output_tokens: int
reasoning_tokens: int
cultivation_gained: int
model: str
usage_source: str
budget_snapshot: json
error: text | null
created_at: datetime
started_at: datetime | null
paused_at: datetime | null
finished_at: datetime | null
cancelled_at: datetime | null
```

### 12.3 novel_chapters 表

```text
id: int
user_id: str
chapter_no: int
volume_no: int
chapter_type: str
title: str
content: text
summary: text
status: str
is_partial: bool
task_id: str
source_type: str
source_id: str | null
battle_id: str | null
enemy_id: str | null
boss_id: str | null
npc_id: str | null
token_count: int
input_tokens: int
output_tokens: int
reasoning_tokens: int
cultivation_gained: int
model: str
usage_source: str
word_count: int
created_at: datetime
completed_at: datetime
```

### 12.4 token_ledger 表

每一次真实或估算 token 增量都记录在 ledger 中。

```text
id: int
user_id: str
task_id: str
chapter_id: int | null
source: str
delta_tokens: int
input_tokens: int
output_tokens: int
reasoning_tokens: int
usage_source: str
provider: str
model: str
created_at: datetime
```

用途:

- 对账。
- 预算统计。
- 玩家用量报表。
- 修为来源追溯。

### 12.5 novel_volumes 表

```text
id: int
user_id: str
volume_no: int
title: str
summary: text
chapter_start: int
chapter_end: int
token_count: int
cultivation_gained: int
created_at: datetime
closed_at: datetime | null
```

---

## 13. API 设计

### 13.1 墨炉队列

```text
GET  /api/cultivation/queue
POST /api/cultivation/tasks
GET  /api/cultivation/tasks/{task_id}
POST /api/cultivation/tasks/{task_id}/pause
POST /api/cultivation/tasks/{task_id}/resume
POST /api/cultivation/tasks/{task_id}/cancel
GET  /api/cultivation/tasks/{task_id}/stream
GET  /api/cultivation/ledger
```

### 13.2 本命书

```text
GET /api/novel/stats
GET /api/novel/volumes
GET /api/novel/chapters
GET /api/novel/chapters/{chapter_id}
GET /api/novel/recent
POST /api/novel/volumes/{volume_no}/summarize
```

### 13.3 预算

```text
GET /api/cultivation/budget
PUT /api/cultivation/budget
POST /api/cultivation/budget/confirm-continue
```

### 13.4 WebSocket / SSE 事件

推荐用独立 SSE 或 WebSocket 推送墨炉事件。

事件类型:

```text
task_queued
task_started
chapter_delta
token_tick
cultivation_tick
budget_warning
budget_paused
chapter_committed
task_failed
task_cancelled
queue_idle
```

`cultivation_tick` 示例:

```json
{
  "type": "cultivation_tick",
  "data": {
    "task_id": "cult_123",
    "delta_tokens": 42,
    "task_tokens": 420,
    "cultivation_total": 182440,
    "exp": 360,
    "level": 12,
    "realm_name": "筑基"
  }
}
```

---

## 14. Prompt 设计

### 14.1 总原则

Prompt 不是单纯写小说,而是要服务“世界观一致 + 玩家资产可读 + token 消耗有价值”。

每个章节 prompt 必须包含:

- 玩家道号。
- 门派。
- 境界。
- 当前卷摘要。
- 最近章节摘要。
- 相关实体信息。
- 本次事件素材。
- 章节类型。
- 字数目标。
- 风格要求。
- 禁止事项。

### 14.2 战斗正传章 prompt 输入

```text
玩家: 道号,门派,境界,关键属性
敌人: 名称,族群,等级,技能,掉落
战斗摘要: 回合数,关键伤害,天命触发,最终结果
世界记忆: 最近 3 章摘要,当前卷摘要
要求: 写成本命书正传章,突出因果稳定与修为增长
```

### 14.3 败笔章 prompt 输入

败笔章不能写成简单失败,要让失败有修行价值。

要求:

- 承认失败。
- 写出伤势、心境、敌人的压迫。
- 留下下一次复仇伏笔。
- 不嘲讽玩家。
- 不把失败写成胜利。

### 14.4 内景章 prompt 输入

内景章主题:

- 经脉。
- 灵台。
- 心魔。
- 梦境。
- 师门旧言。
- 天书翻页。
- 墨炉微光。

要求:

- 不出现外部 UI 词汇。
- 不说“API”“token”,除非以“燃灵墨”表达。
- 结尾必须有心境变化或修行感。

### 14.5 断章 prompt / 保存规则

断章不需要补全,要保留中断痕迹。

断章标题示例:

```text
断章 · 狐火未尽
断章 · 雨中止笔
断章 · 墨炉忽暗
```

---

## 15. 前端体验设计

### 15.1 全局导航调整

建议路由:

```text
/home
/explore
/battle/:id
/novel
/novel/chapter/:id
/inventory
/items
/bosses
/journal    保留为修行纪事摘要
/settings/byok
```

### 15.2 主城

主城应展示:

- 当前修为。
- 总燃灵 token。
- 当前本命书卷章。
- 墨炉状态。
- 今日预算状态。
- 快捷入口: 入定成章 / 闭关续写 / 继续探索。

### 15.3 战斗结算

旧展示:

```text
经验 +30
灵气 +15
```

新展示:

```text
战利品已收入囊中
正传战章已入墨炉
燃灵后将实时增长修为
```

如果墨炉立刻开始:

```text
正在燃灵成章
已燃灵 128 token
修为 +128
```

### 15.4 打坐面板

打坐按钮点击后:

```text
调息完成
HP +24 / 灵气 +120 / 疲劳 -8

灵台已静,可入定成章。
[入定成章] [继续调息] [返回地图]
```

### 15.5 本命书阅读器

阅读器需要:

- 目录侧栏。
- 卷切换。
- 章节正文。
- token 与修为信息。
- 章节类型标识。
- 断章标识。
- 返回来源事件。
- 分享/复制战报摘要。

### 15.6 不卡顿策略

- 所有按钮点击先进入 loading micro-state,但不全屏锁。
- 章节生成用流式文字,不要空白等待。
- 首 chunk 超过 1 秒未到,显示世界观提示。
- 生成任务可后台运行。
- 页面切换不取消任务,除非用户明确取消。
- 队列状态通过轮询或 SSE 恢复。
- 前端乐观显示 token tick,完成后校准。

---

## 16. 后端改造步骤

### Phase 0: 术语与基础 bug 整理

目标: 先统一命名,修掉会阻塞核心链路的问题。

任务:

1. 把 UI 中“经验”逐步替换为“修为”。
2. 把“战后章节”命名为“本命书章节”。
3. 修复 WebSocket 教学战 `user_id` 未定义问题。
4. 修复库存 dict/list 使用不一致问题。
5. 修复 NPC 战斗未传当前用户 `user_id` 问题。
6. 明确 fallback 不计修为。

验收:

- 首战教学不崩溃。
- 战斗内使用丹药正常。
- 技能升级材料校验正常。
- NPC 战斗可被当前用户进入。

### Phase 1: 数据层

目标: 让系统能保存任务、章节、token ledger。

改造文件:

- `backend/app/store.py`

新增:

- `init_cultivation_tables()`
- `create_cultivation_task()`
- `get_cultivation_task()`
- `list_cultivation_queue()`
- `update_cultivation_task()`
- `append_task_content()`
- `create_novel_chapter()`
- `list_novel_chapters()`
- `get_novel_stats()`
- `add_token_ledger()`
- `get_budget_state()`
- `update_budget_state()`

验收:

- 重启后任务与章节不丢。
- 能列出当前用户队列。
- 能写入 token ledger。

### Phase 2: 墨炉任务执行器

目标: 后台消费队列,流式写章节,实时加修为。

建议新增文件:

- `backend/app/cultivation.py`

核心类:

```text
CultivationQueueRunner
CultivationTaskContext
TokenUsageTracker
BudgetGuard
```

核心函数:

```text
enqueue_task(user_id, task_type, source_payload)
run_next_task(user_id)
stream_task(task_id)
estimate_tokens(text)
settle_usage(task_id, provider_usage)
apply_cultivation_gain(user_id, delta_tokens)
```

验收:

- 创建任务后自动运行。
- stream chunk 能推给前端。
- token tick 能实时加修为。
- 任务完成后生成 novel_chapter。

### Phase 3: LLM client 支持 usage

目标: 让章节生成能返回正文流和 usage。

改造文件:

- `backend/app/llm_client.py`

新增或改造:

```text
stream_novel_chapter(...)
on_delta callback
on_usage callback
usage extraction
fallback marker
```

注意:

- 如果 OpenAI 兼容流式返回没有 usage,使用估算。
- 如果最后一个 chunk 有 usage,用 usage 校准。
- fallback 只能用于提示或临时展示,不写正式章节,不计修为。

### Phase 4: 战斗接入

改造文件:

- `backend/app/battle.py`
- `backend/app/main.py`
- `frontend/src/views/Battle.vue`

后端:

- `_commit_battle_result()` 不再直接给 exp。
- 胜利、失败、撤退、安抚创建 cultivation_task。
- 返回 task_id。
- 战斗历史保存 task_id。
- level_up 由墨炉完成时触发。

前端:

- 结算页改展示“章节已入墨炉”。
- 移除本地直接 `character.exp += rewards.exp` 的逻辑。
- 监听全局墨炉事件刷新角色。
- 保留战斗中即时数字反馈。

### Phase 5: 打坐接入

改造文件:

- `backend/app/main.py`
- `frontend/src/components/MeditateButton.vue`

后端:

- `/api/character/meditate` 只恢复状态。
- 新增入定成章任务创建接口。
- 新增闭关任务创建接口。

前端:

- 打坐调息后展示后续选择。
- “入定成章”创建 `meditate_inner`。
- “闭关续写”显示预算确认。
- 墨炉条展示 token 与修为。

### Phase 6: 本命书页面

新增文件:

- `frontend/src/views/NovelBook.vue`
- `frontend/src/views/NovelChapter.vue`
- `frontend/src/components/CultivationQueueBar.vue`
- `frontend/src/components/CultivationQueueDrawer.vue`

改造:

- `frontend/src/router.js` 增加 `/novel`。
- `frontend/src/api/client.js` 增加 `novelApi` 与 `cultivationApi`。
- `frontend/src/views/Home.vue` 增加本命书入口与墨炉状态。

验收:

- 可查看章节目录。
- 可阅读章节正文。
- 可看到每章 token / 修为。
- 断章可见。

### Phase 7: 预算保护

后端:

- 实现单章/日/月预算统计。
- running 任务每次 tick 前检查预算。
- 达 80% 推送 warning。
- 达 100% 暂停并推送 budget_paused。
- 用户确认后继续。

前端:

- 设置页可配置预算。
- 队列抽屉显示预算进度。
- 预算暂停弹窗明确提示 API token 消耗。

验收:

- 达到 80% 有提醒。
- 达到 100% 暂停。
- 没有本地省流入口。
- 用户点继续后继续消耗 token。

### Phase 8: 全事件接入

接入范围:

- 奇遇。
- Boss。
- NPC。
- 突破。
- 日课。
- 卷末总结。

目标:

- 不再存在任何直接给修为的入口。
- 所有修为来源都可追溯到 token ledger。

---

## 17. 代码文件改造清单

### 17.1 后端

| 文件 | 改造 |
|---|---|
 `backend/app/store.py` | 新增任务、章节、ledger、预算存储 |
 `backend/app/cultivation.py` | 新增墨炉队列执行器 |
 `backend/app/llm_client.py` | 新增章节流 + usage 追踪 |
 `backend/app/battle.py` | 战斗结束创建任务,移除直接 exp |
 `backend/app/main.py` | 新增 API,打坐拆分,接入预算 |
 `backend/app/attributes.py` | 保留 check_level_up,接收 token 修为增量 |
 `backend/app/daily.py` | 日课奖励移除修为 |
 `backend/app/events.py` | 奇遇修为改为外传章任务 |

### 17.2 前端

| 文件 | 改造 |
|---|---|
 `frontend/src/api/client.js` | 新增 cultivationApi, novelApi, budgetApi |
 `frontend/src/router.js` | 新增本命书路由 |
 `frontend/src/stores/game.js` | 增加墨炉状态、总修为、token_total |
 `frontend/src/views/Home.vue` | 本命书入口、墨炉状态、修为文案 |
 `frontend/src/views/Battle.vue` | 结算页改为任务入炉,移除直接经验累加 |
 `frontend/src/views/ExploreMap.vue` | 奇遇奖励文案改造 |
 `frontend/src/components/MeditateButton.vue` | 调息/入定/闭关拆分 |
 `frontend/src/views/Journal.vue` | 降级为修行纪事,链接本命书 |
 `frontend/src/views/NovelBook.vue` | 新增 |
 `frontend/src/views/NovelChapter.vue` | 新增 |
 `frontend/src/components/CultivationQueueBar.vue` | 新增 |
 `frontend/src/components/CultivationQueueDrawer.vue` | 新增 |

---

## 18. 验收标准

### 18.1 世界观验收

- 新手能在 1 分钟内理解“燃灵墨 = token, token = 修为”。
- 所有核心页面都使用本命书、墨炉、燃灵、修为等统一术语。
- 不再出现割裂的“系统正在生成文本”表达。
- 战斗、打坐、奇遇、Boss 都能解释为“因果入书”。

### 18.2 成长验收

- 战斗胜利不会直接加固定经验。
- 打坐调息不会加修为。
- 日课不会直接加修为。
- 所有修为增长都能追溯到 token ledger。
- 修为总量没有上限。
- 飞升后仍能继续累积修为。

### 18.3 队列验收

- 任务可 queued/running/paused/completed/cancelled。
- 正在运行时 token tick 实时显示。
- 任务完成后生成章节。
- 生成中取消保存断章。
- 刷新页面后队列状态可恢复。

### 18.4 体验验收

- 战斗数值反馈不等待章节生成。
- 战斗结束可立即返回地图。
- 墨炉后台继续运行。
- 首 chunk 慢时有世界观提示。
- 预算暂停不造成数据丢失。

### 18.5 预算验收

- 80% 提醒。
- 100% 暂停。
- 用户确认后继续。
- 没有本地省流模式。
- fallback 不计修为。

---

## 19. 风险与解决方案

### 19.1 玩家担心 token 消耗

风险:

用户看到持续消耗 token,可能焦虑。

解决:

- 常驻显示已消耗。
- 预算保护默认开启。
- 每次消耗都有章节资产。
- 明确“继续燃灵”确认。

### 19.2 玩家觉得等待卡顿

风险:

LLM 首 token 慢或章节长。

解决:

- 数值层即时返回。
- 成章层后台运行。
- 显示墨炉条和实时 token。
- 玩家可离开页面。
- 章节默认折叠。

### 19.3 内容重复

风险:

大量战斗章容易同质化。

解决:

- 维护最近章节摘要。
- 不同族群使用不同题词和意象。
- Boss/突破使用高仪式模板。
- 失败、撤退、赠礼采用不同章型。

### 19.4 修为无上限导致数值膨胀

风险:

`level` 和战斗属性无限膨胀会破坏平衡。

解决:

- `cultivation_total` 无上限。
- `level` 可以继续增长,但属性曲线使用软增长。
- 飞升后增加天书品秩、卷数、称号等横向表达。
- Boss 和地图危险度用区间匹配。

### 19.5 usage 不准确

风险:

不同 provider 返回 token usage 不一致。

解决:

- token ledger 记录 usage_source。
- 流式期间估算。
- 结束时校准。
- 低于估算不回扣。

---

## 20. 推荐迭代顺序

如果只能按最小成本推进,推荐顺序如下:

```text
1. 修复阻塞 bug,统一“经验 -> 修为”文案。
2. 新增 cultivation_tasks / novel_chapters / token_ledger。
3. 做墨炉最小执行器,先只接战后章节。
4. 战斗结束不直接加 exp,改为入炉。
5. 墨炉完成后 token 转修为并升级。
6. 打坐拆成调息与入定。
7. 做全局墨炉条。
8. 做本命书页面。
9. 加预算保护。
10. 接入奇遇、Boss、NPC、日课、卷末章。
```

这个顺序的好处:

- 先保证核心循环成立。
- 先让 token 消耗与修为绑定。
- 再补世界观展示和长线资产。
- 不会一开始就被完整 UI 和所有事件拖住。

---

## 21. 最终目标体验

玩家战斗结束后看到的不再是:

```text
经验 +30
```

而是:

```text
正传战章已入墨炉:
《第十二章 · 狐火照山门》

正在燃灵成章
已燃灵 428 token
修为 +428
```

玩家打坐后看到的不再是:

```text
修为 +5
```

而是:

```text
调息完成,气血已稳。
灵台生墨,可入定成章。
```

玩家长期记住的不是“我刷了多少怪”,而是:

```text
我的本命书已经写到第五卷。
我每一次胜利、失败、闭关和奇遇都在书里。
我消耗的每一个 token,都变成了我的修为。
```

这就是《灵枢笔录》最有辨识度的产品心智:

> **用自己的 API Key 写自己的修真小说。燃灵即消费,成章即资产,token 即修为。**
