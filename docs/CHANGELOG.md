# 灵枢笔录 · 版本变更日志

> 给 AI 接手项目快速了解每个版本做了什么。最新在顶部。

---

## v5.3 · 沉浸式选派 + 全局门派主题 (2026-05-24)

### ✨ 大改造

#### 1. SectChoose 沉浸式选派(类游戏选角色)
- 中央 480×480 大舞台,展示每派独家动效
- 左右切换:`←/→` 键 / 箭头按钮 / 底部 dock
- Enter 直接确认
- 切换时金色 flash 速线
- 文字区入场动画(根据方向左/右 slide)

#### 2. 5 派独家中央动效
| 门派 | 中央动效 |
|---|---|
| 🗡️ 沧澜剑派 | 巨大毛笔 + 3 把剑气环绕公转 + 3 团水墨晕染脉冲 |
| ⚙️ 天机阁 | 八卦盘 + 3 个齿轮反向旋转 + 双层符文虚线圆 |
| 🧠 玄机宗 | 大脑 + 3 层紫色波纹扩散 + 5 个浮动数字 `7 2 π ∞ √` |
| 📜 青冥派 | 卷轴 + 6 个古字"道仁易天学思"浮动 + 翠玉光晕 |
| 🌙 月隐宫 | 月亮 + 30 颗闪烁星 + 3 个月相沿轨道公转 |

#### 3. 全局门派主题系统 `frontend/src/config/sectTheme.js`
- 5 派统一配置:`primary/accent/glow/secondary/contrast` 配色
- 战斗专属:`fx_cast_color`、`fx_crit_color`、`fx_aura`、`fx_screen_tint`
- 招式风格关键词
- `getSectCssVars(sectId)` 返回 CSS variables,直接 `:style` 用

#### 4. 各页面应用主题色
- **Home.vue**:顶部光晕 + 头像 aura + 入口卡片金色变色随门派
- **Battle.vue**:战斗页背景渐变染色 + 头像 portrait-breath 呼吸光晕
- **SectChoose.vue**:中央舞台背景渐变 + 各派配色随切换变化

### 🔧 新文件

| 文件 | 行数 | 内容 |
|---|---|---|
| `frontend/src/config/sectTheme.js` | ~120 | 5 派统一主题配置 |

### 📁 修改文件

- `frontend/src/views/SectChoose.vue` 完全重写(从纯列表 → 沉浸式选角)
- `frontend/src/views/Battle.vue` 应用 sectCssVars + portrait-breath
- `frontend/src/views/Home.vue` 应用 sectCssVars + 主入口染色

---

## v5.2 · 欢迎页 + 仙侠流动背景 (2026-05-24)

### ✨ 新增

- **WelcomePage.vue**:游戏首次进入的欢迎页
  - 黑色幕布 → 墨色晕染 → 主内容入场(2.5s 时序)
  - 鎏金大标题 + 流光"入道"按钮
  - 一句话描述
- **WuxiaBackground.vue**:7 层叠加的仙侠流动背景
  - 渐变底色 + 远山 + 3 层云雾 + 灵气粒子 + 飘落花瓣 + 修真符文 + 顶部柔光
  - 3 档强度(light/normal/rich)
- 应用到 Welcome / Onboarding / SectChoose / KeyVerify 4 个页面
- **FREE_RESOURCES.md**:免费修仙资源清单(国内外 30+ 资源站)

### 🔧 路由变更

- `/` 从 `redirect: /onboarding` 改为 → `WelcomePage.vue`

---

## v5.1 · 战斗系统全面升级 (2026-05-24)

### ✨ 大改造:对战系统
- **三栏 Tab 布局**:招式 / 物品 / 天命 / 撤退
- **48 个怪物招式**(12 族 × 4 等级)
  - 每族:basic / mid / high / ult 4 招
  - 等级越高解锁越多 + 触发 ult 几率越高
- **天命降临系统**(P0 新功能)
  - 每回合 5% 几率触发
  - 触发后整场战斗可释放 **宗派独家神技 1 次**
  - 沧澜:沧澜剑域·一笔诛仙(5x ATK / 必中 / 必暴击)
  - 天机:万象天衍·推演无敌(5x ATK / 必中 / 必暴击)
  - 触发时全屏特效 + 自动切到天命栏
- **战报卡**:每回合下方插入一张数值汇总卡
  - 玩家招式 vs 敌人招式 各推一张
  - 暴击金色 / 普通红色 / 失手灰色 / 天命金光
- **关键字高亮**:LLM 叙事中的 `**xxx**` 自动转高亮
  - 招式名/状态:金色描边
  - 数字伤害:红色 mono 字体
  - 暴击/天命:金色 + pulse 动画
- **卷轴式 UI**:叙事区双竹简边框 + 上下铜环
- **LLM prompt 升级**:要求输出 `**xxx**` 重点标记 + 天命特殊文风

### 🐛 BUG 修复
- 第一回合后无法继续:battle.py 末尾没 yield state,前端 status 卡死
  - 修复:加 `state` + `turn_ready` 双事件

### 🔧 后端
- 新文件 `monster_skills.py` — 48 招式定义,按族分类
- 新文件 `behaviors.py` — 12 族行为准则(部分已完成,前端未集成)
- `battle.py` 大改:
  - `process_action` 加天命分支
  - `_compute_enemy_action(skill)` 接受招式参数
  - `_compute_destiny_outcome` 新方法
  - `_build_enemy_narration(outcome, skill)` 用招式名 + `**xxx**` 标记
  - snapshot 加 `destiny_charged/used/skill` 字段
  - 推 `destiny_trigger` 和 `damage_summary` 事件
- `sects.py` 加 `DESTINY_SKILLS` 表 + `get_destiny_skill()`
- `llm_client.py` 的 BASE_SYSTEM_PROMPT 加入 `**xxx**` 重点标记规则

### 🎨 前端
- `Battle.vue` 大改:
  - 三 Tab:招式 / 丹药 / 天命(条件解锁)
  - 战报卡 `battleLog` 数组,TransitionGroup 入场
  - `highlightNarration()` 解析 `**xxx**` 转 span
  - 天命遮罩 + 3 同心圆扩散动画
  - 天命卡片旋转环 + shine 流光
  - 头像系统(18 个境界 × 门派,见 v5.0)

---

## v5.0 · 战斗页大重构 (2026-05-23)

- 战斗页全部重写
- 主角等级头像系统(9 境界 × 2 派 = 18 个独特头像 + 称号)
- 招式 4 级分色(basic 蓝 / normal 绿 / special 橙 / ult 金)
- 施法前摇 + 释放粒子(立刻响应,LLM 在后台跑)
- 战斗开场动画 + 结算 pop 动画

## v4.1 · 灵脉配置(随时换 key)

- `POST /api/character/me/byok` 后端校验
- 主城 ⚙️ 灵脉配置 modal
- bobdong.cn 推荐广告卡

## v4.0 · 修仙世界大充实

- 113 怪物 / 12 族 / 9 等级
- 21 Boss / 18 真实公司宗派 / 4 故事线
- 55 物品(材料/丹药/法宝/灵宝/心法)
- 修真名录(Bosses.vue)
- 仿真地图(怪物移动 + 碰撞自动开战)

## v3.0 · Onboarding 入门流程

- 填 key → probe → 显示门派可用性 → 选派 → 验证 → 创角
- 飞升期(Lv.151-200)

## v2.0 · 5 大门派 + LLM 厂商映射

- 5 派对应 5 厂商:沧澜(Anthropic)/天机(OpenAI)/玄机(DeepSeek)/青冥(智谱)/月隐(Kimi)
- 各派独立 LLM 叙事风格
- 选派即锁定(不可直接换)

## v1.0 · MVP

- 选派 → 验证 → 创角 → 战斗循环
- WebSocket 战斗 + LLM 叙事
- 沧澜剑派(Anthropic)+ 天机阁(OpenAI)可用
