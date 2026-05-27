# 灵枢笔录 · 架构文档(AI 友好版)

> **本文档面向 AI agent**:接手项目时只读这一份,即可掌握全部模块定位。
> **关键约定**:
> - 所有路径都给绝对路径,可直接 Read
> - 所有 API endpoint 都列了完整 method + path + 请求/响应字段
> - 所有数据结构都标了字段类型 + 出处文件
> - 出现 BUG 时,本文末"常见维护任务"章节给了定位 + 修复模板

---

## 目录

1. [项目身份](#1-项目身份)
2. [快速启动 / 验证健康](#2-快速启动--验证健康)
3. [目录结构总览(每个文件一句话)](#3-目录结构总览)
4. [数据流图](#4-数据流图)
5. [后端模块详解](#5-后端模块详解)
6. [前端模块详解](#6-前端模块详解)
7. [API 接口全表](#7-api-接口全表)
8. [核心数据模型](#8-核心数据模型)
9. [配置与环境变量](#9-配置与环境变量)
10. [关键约定与模式](#10-关键约定与模式)
11. [常见维护任务(模板)](#11-常见维护任务)
12. [已知问题与 TODO](#12-已知问题与-todo)
13. [关键文件清单(grep 友好)](#13-关键文件清单)

---

## 1. 项目身份

| 项目名 | 灵枢笔录(Lingshu Codex)|
|---|---|
| 类型 | Web 版 Token 修仙文字 RPG |
| 核心机制 | 5 大门派 ↔ 5 家 LLM 厂商,选派即锁定 Key,战斗 LLM 实时生成叙事 |
| 后端 | Python 3.11 + FastAPI 0.115 + httpx + WebSocket + 内存存储 |
| 前端 | Vue 3.5 + Vite 5.4 + Naive UI 2.41 + Pinia + WebSocket |
| LLM 网关 | 默认 https://bobdong.cn/v1 (OpenAI 协议兼容,支持 Claude + GPT) |
| 项目根目录 | `/Users/bobdong/项目/LingshuCodex/` |
| 设计文档 | `/Users/bobdong/项目/FireworkRouter/docs/game-plan/` (规划阶段) |
| 状态 | v4.1 MVP 可运行 |

### 1.1 用户故事 / 核心循环

```
1. 打开首页 → 自动跳 /onboarding
2. 填 base_url + api_key + 道号 → 后端 /api/byok/probe 探测 → 显示 5 派可用性
3. 选可用门派 → /key-verify/:sectId 流式逐个测试该派模型 → 全过创角
4. 主城 /home → 选「开始修行 / 背包 / 修行物品 / 修真名录 / ⚙️ 灵脉配置 / 转世重修」
5. 修行 /explore → 12 怪物随机移动 → 悬停看信息 → 点击战斗
6. 战斗 /battle/:id → WebSocket 推流,LLM 实时生成 150-250 字仙侠叙事 + 数字飞屏 + 屏幕震动
7. 胜利 → 掉落物品到背包 → 返回主城
```

---

## 2. 快速启动 / 验证健康

```bash
# === 启动后端 ===
cd /Users/bobdong/项目/LingshuCodex/backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8020 --reload

# === 启动前端 ===
cd /Users/bobdong/项目/LingshuCodex/frontend
npm run dev
# → http://127.0.0.1:5173/

# === 或一键 ===
cd /Users/bobdong/项目/LingshuCodex
./start.sh
```

### 2.1 5 秒健康检查

```bash
# 后端
curl http://127.0.0.1:8020/health
# 期望:{"status":"ok"}

# 前端
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:5173/
# 期望:HTTP 200

# 数据加载
curl -s http://127.0.0.1:8020/api/enemies/count
# 期望:{"data":{"total":113,"by_clan":{...},"clans_total":12}}

# Boss 数据
curl -s http://127.0.0.1:8020/api/boss/list | python3 -c "import sys,json;print(len(json.load(sys.stdin)['data']))"
# 期望:21
```

### 2.2 进程清理

```bash
# 端口被占用时
lsof -ti:8020 | xargs -r kill -9
lsof -ti:5173 | xargs -r kill -9
pkill -f "uvicorn app.main"
pkill -f "vite"
```

---

## 3. 目录结构总览

```
/Users/bobdong/项目/LingshuCodex/
├── README.md                    旧 v0.1 README,部分内容已过时,以本文为准
├── start.sh                     一键启动脚本(自动建 venv + npm install + 双服务)
├── .gitignore                   忽略 .env / node_modules / .venv
│
├── docs/                        【本目录】游戏文档
│   ├── ARCHITECTURE.md          ★ 给 AI 看,本文件
│   ├── GAME_OVERVIEW.md         给用户看的产品介绍
│   ├── GETTING_STARTED.md       新玩家入门
│   └── PLAYER_GUIDE.md          玩家攻略
│
├── backend/                     【FastAPI 后端】
│   ├── .env                     生产配置(已含测试 key,git ignored)
│   ├── .env.example             配置模板
│   ├── requirements.txt         python 依赖(fastapi/httpx/python-dotenv)
│   └── app/
│       ├── __init__.py          版本声明
│       ├── main.py              ★ FastAPI 入口 + 30+ REST + 1 WS 端点
│       ├── sects.py             5 大门派配置(沧澜/天机/玄机/青冥/月隐)
│       ├── enemies.py           113 怪物 / 12 族(同族有羁绊故事)
│       ├── bosses.py            21 Boss + 18 公司宗派 + 4 故事线
│       ├── cards.py             8 战斗卡牌(4 通用 + 各派 2 张)
│       ├── items.py             55 物品(材料/丹药/法宝/心法/灵宝)
│       ├── battle.py            ★ BattleEngine 战斗引擎(数值+LLM)
│       ├── llm_client.py        ★ LLM 调用 + 重试 + fallback
│       ├── health_check.py      ★ probe(快验证)+ verify(流式逐模型测试)
│       └── store.py             内存存储(单玩家 demo_player)
│
└── frontend/                    【Vue 3 前端】
    ├── package.json             npm 依赖
    ├── vite.config.js           Vite + 代理 /api → 8020
    ├── index.html               入口 HTML + favicon
    ├── public/
    │   └── favicon.svg          国风金色"笔"字徽章
    └── src/
        ├── main.js              Vue 入口
        ├── App.vue              根组件(Naive UI 主题配置)
        ├── router.js            ★ 路由 + 守卫(requireCharacter/requireBattle)
        ├── api/
        │   └── client.js        ★ axios 封装 + 统一错误归一
        ├── stores/
        │   └── game.js          Pinia 全局状态(character/sects)
        ├── components/
        │   ├── Logo.vue         游戏 LOGO(可复用)
        │   └── ByokSettings.vue ★ 灵脉配置 modal(随时换 key)
        └── views/
            ├── Onboarding.vue   ★ 入门页(填 key + 探测 5 派)
            ├── SectChoose.vue   旧选派页(保留兼容,默认走 onboarding)
            ├── KeyVerify.vue    ★ 流式精细验证页
            ├── Home.vue         ★ 修行主城(4 入口卡片)
            ├── ExploreMap.vue   ★ 仿真地图(怪物移动 + 悬停信息)
            ├── Inventory.vue    背包(战利品 + 使用丹药)
            ├── Items.vue        物品全集(只读浏览)
            ├── Bosses.vue       修真名录(21 Boss + 故事线)
            ├── Battle.vue       ★ 战斗页(WebSocket + 卡牌 + 屏幕反馈)
            └── NotFound.vue     404 页
```

★ = 改动率高 / 核心文件,改之前必看

---

## 4. 数据流图

### 4.1 入门 + 选派 + 创角(只发生一次)

```
浏览器                后端                                 LLM 网关 (bobdong.cn)
   │                    │                                       │
   ├─① GET /api/sect/list ─▶                                    │
   │                    │ (返回 5 派配置 + 各派 8-9 境界 model)   │
   ◀────────────────────┤                                       │
   │                    │                                       │
   ├─② POST /api/byok/probe(base_url, api_key)─▶                │
   │                    ├─ GET {base_url}/models ──────────────▶│
   │                    │                                       │
   │                    │ (拿到模型 id 列表)◀──────────────────┤
   │                    │ (按各派 tier.model 算可选性)            │
   ◀────────────────────┤                                       │
   │  (前端显示 5 派可选/不可选)                                │
   │                    │                                       │
   ├─③ 选派 → 跳 /key-verify/:sectId ──────────────────────────  │
   │                    │                                       │
   ├─④ POST /api/sect/verify-key (SSE 流) ────▶                 │
   │                    │ 对该派 N 个去重 model 逐个              │
   │                    │ POST {base_url}/chat/completions ──▶  │
   │                    │   (失败重试 0.5s/1.5s,最多 3 次)      │
   │                    │ ◀──────────── (200 OK)───────────────│
   │  data: {event:"result", model, ok:true} ◀──┤              │
   │  ...                                                       │
   │                    │                                       │
   ├─⑤ POST /api/character/choose-sect ─▶                       │
   │                    │ (保存 character {sect, base_url, api_key, ...} 到内存)
   ◀────────────────────┤                                       │
   │                    │                                       │
   ◀────────────────────  路由跳 /home                          │
```

### 4.2 战斗循环(每场战斗多次发生)

```
浏览器                后端                                 LLM 网关
   │                    │                                       │
   ├─① POST /api/battle/start(enemy_id)─▶                        │
   │                    │ BattleEngine 创建,放 store._battles  │
   ◀────── battle_id ───┤                                       │
   │                    │                                       │
   ├─② WebSocket /ws/battle/:id ─▶                              │
   ◀──── {type:"state",...} ───┤                                │
   │                    │                                       │
   ├─③ {action:"cast", card_id} ──▶                             │
   │                    │ ① 数值层 _compute_outcome (确定性)    │
   │                    │   立即推 damage/effect 事件 ──────▶   │
   ◀── {type:"damage"...} ─┤                                    │
   ◀── {type:"effect"...} ─┤  (前端开始震屏 + 数字飞屏)         │
   │                    │                                       │
   │                    │ ② LLM 叙事层(可缓存)                │
   │                    │   build_user_prompt → stream_battle_narration │
   │                    │   POST /chat/completions (stream=true) ─▶│
   │                    │   ◀────── SSE chunks ──────────────│
   ◀── {type:"narration",delta:"你..."} ──┤                     │
   ◀── {type:"narration",delta:"沉吟"} ──┤  (前端打字机)         │
   │  ...                                                       │
   │                    │                                       │
   ◀── {type:"state",...} ──┤                                  │
   │                    │ (HP <= 0 时)                          │
   │                    │ _roll_drops 概率掉物品到 store        │
   ◀── {type:"end",rewards:{exp,qi,drops:[...]}} ───┤           │
```

---

## 5. 后端模块详解

> 路径前缀全部省略 `/Users/bobdong/项目/LingshuCodex/backend/app/`

### 5.1 `main.py` — FastAPI 入口

**职责**:HTTP/WebSocket 端点 + 路由分发,本身**不做业务**,业务在各 service。

**关键导入**:
```python
from .sects import ALL_SECTS, get_sect, sect_to_dict, SECT_TO_PROVIDER_HINT
from .enemies import ENEMIES, get_enemy, ALL_CLANS, count_enemies
from .cards import get_cards_for_sect, get_card
from .battle import BattleEngine
from .bosses import BOSSES, BOSS_SECTS, STORYLINES
from .items import ITEMS, get_item
from .health_check import stream_verify_sect_models, probe_byok
from .store import get_character, save_character, ...
```

**Pydantic 模型**(全在文件顶部):
- `ChooseSectRequest`:创角(sect_id, character_name, base_url, api_key)
- `VerifyKeyRequest`:逐模型验证(sect_id, base_url, api_key)
- `ProbeRequest`:快速探测(base_url, api_key)
- `UpdateByokRequest`:游戏中换 key(base_url, api_key, verified)
- `StartBattleRequest`:开战(enemy_id)

**端点分组**:见 [§ 7 API 接口全表](#7-api-接口全表)

### 5.2 `sects.py` — 5 大门派配置

**数据结构**:
```python
@dataclass
class TierConfig:        # 境界 = 模型映射
    name: str            # "炼气"/"筑基"/.../"飞升"(9 个境界)
    level_min: int
    level_max: int
    model: str           # 如 "claude-haiku-4-5-20251001"
    max_tokens: int      # LLM 叙事预算
    atk_multiplier: float # 战斗数值加成

@dataclass
class SectConfig:
    id: str              # canglan / tianji / xuanji / qingming / yueyin
    name: str            # "沧澜剑派"
    provider_display: str # "Anthropic · 克劳神宗"
    initial_stats: dict   # {hp,atk,def_,spd,crit_rate,...}
    buffs: list[dict]    # 门派被动 [{"name","desc"}]
    tiers: list[TierConfig]  # 9 个境界配置
    narration_style: str  # 给 LLM 的 system prompt 风格附加
    available: bool       # MVP 阶段只有 canglan/tianji=True
```

**关键常量**:
- `ALL_SECTS`(dict id→SectConfig)
- `SECT_TO_PROVIDER_HINT`(dict id→{provider, key_format, default_base_url, official_base_url})
- `CANGLAN`, `TIANJI`, `XUANJI`, `QINGMING`, `YUEYIN`(5 个门派单例)

**关键函数**:
- `get_sect(sect_id)`:取门派配置
- `get_tier_for_level(sect_id, level)`:根据等级返回当前境界配置(注意 level 超过最高 tier 时返回最后一个)
- `sect_to_dict(sect)`:转 JSON 友好(给前端用)

**怎么改门派模型映射?** 改 `tiers` 列表,如:
```python
TierConfig("飞升", 151, 200, "claude-opus-4-7", 450, 3.50)
```

### 5.3 `enemies.py` — 113 怪物 12 族

**12 个族常量**(命名规范 `CLAN_XXX`):
```python
CLAN_FOX        # 山林狐妖族(终南九尾血脉)
CLAN_BIRD       # 灵雀飞鸟族(朱雀旁支)
CLAN_SERPENT    # 蛇蟒族(玄武水族)
CLAN_BEAST      # 猛兽族(白虎旁支)
CLAN_HERB       # 草木精怪族(神农百草)
CLAN_GHOST      # 鬼族(阴曹逃囚)
CLAN_DRAGON     # 龙族(四海龙王后裔)
CLAN_DIVINE     # 神兽族(四圣神兽)
CLAN_ANCIENT    # 上古凶兽族
CLAN_DEMON      # 魔修族
CLAN_ARTIFACT   # 仙器之灵族
CLAN_ALIEN      # 异域生灵族
```

每族 **9 个等级阶段**,共 108 怪 + 5 个 legacy 别名(wild_fox 等)= 113 ENEMIES。

**数据结构**:
```python
@dataclass
class Enemy:
    id: str              # 如 "fox_01"
    name: str            # "山林小狐"
    clan: str            # "山林狐妖族"
    tier: str            # low / mid / high / myth / boss
    level: int           # 推荐挑战等级 3~200
    hp/atk/def_/spd/evasion: ...
    rewards_exp/rewards_qi: ...
    image_emoji: str
    description: str     # 卡片简介
    lore: str            # 完整背景故事(含族内羁绊)
    drops: list          # 掉落表 item_id
```

**关键函数**:
- `get_enemy(enemy_id)`:取单只
- `list_enemies_for_level(level, span=8)`:返回该等级 ±span 范围内的怪物(用于地图 spawn / Home 推荐)
- `enemy_to_dict(e)`
- `count_enemies()` → (total, {clan_name: count})

**如何添加新怪物?** 在对应族列表中加 `Enemy(...)`,需保证:
1. `id` 全局唯一
2. `clan` 必须在 12 族字符串中
3. drops 引用的 `item_id` 必须存在于 `items.py`

### 5.4 `bosses.py` — 21 Boss + 18 公司宗派 + 4 故事线

**关键常量**:
- `BOSS_SECTS`(dict)— 18 个 Boss 宗派,对应真实公司
  - 故事线 A:`deepmind_pavilion`, `cohere_harmony`, `ai21_babel`(西方三皇)
  - 故事线 B:`mistral_storm`, `together_sail`, `replicate_evolve`, `huggingface_temple`, `stability_garden`(开源觉醒)
  - 故事线 C:`baichuan_sea`, `yi_peak`, `step_star`, `minimax_micro`, `sensetime_hall`(东方崛起)
  - 故事线 D:`inflection_turn`, `character_mask`, `perplexity_trail`, `groq_speed`, `xai_void`(异端崛起)
- `BOSSES`(dict)— 21 个 Boss
- `STORYLINES`(dict A/B/C/D)— 4 条故事线 + 3 幕结构

**数据结构**:
```python
@dataclass
class BossSect:
    id, name, company, founded
    real_background: str   # 真实公司背景
    sect_story: str        # 仙侠演绎
    storyline: str         # A/B/C/D
    base_color: str

@dataclass
class Boss:
    id, name, title, sect_id, level
    hp/atk/def_/spd/evasion/crit_rate
    rewards_exp/rewards_qi
    image_emoji, lore
    bonds: list[str]              # 与其他 Boss id 的羁绊
    bond_descriptions: list[str]  # 羁绊描述(同 index)
    drops: list
    signature_skill: str          # 标志性招式
```

**如何添加新 Boss?**
1. 在 `BOSS_SECTS` 加宗派(或复用现有)
2. `_add(Boss(...))` 加 Boss
3. 在 `STORYLINES[X]["key_bosses"]` 或 `["side_bosses"]` 加 id
4. 在其他相关 Boss 的 `bonds` 中加 id + bond_description(双向羁绊)

### 5.5 `cards.py` — 战斗卡牌

8 张卡:4 通用(灵气一击 / 凝神咒 / 寒冰诀 / 灵丹)+ 沧澜 2(剑诀·初 / 沧澜九式)+ 天机 2(机关连发 / 万象归元)。

**关键数据**:
- `qi_cost`:消耗灵气
- `power`:ATK 倍率
- `hit_rate`:基础命中
- `type`:attack / buff / heal
- `sect_requirement`:any / canglan / tianji

**如何加卡?** 加 `Card(...)` 实例到 CARDS dict,前端会自动从 `/api/battle/cards` 拿到。

### 5.6 `items.py` — 55 物品

5 类:material(30)/ consumable(5)/ equipment(10)/ skill_book(3)/ treasure(7)。

```python
@dataclass
class Item:
    id, name, type, rarity (1-6), icon
    description, lore
    use_effect: dict   # consumable 才有,如 {"qi":200} / {"hp_percent":30}
    equip_stats: dict  # equipment 才有
    value_qi: int      # 价值(卖出 / 兑换)
```

**rarity → 名称**:
```python
RARITY_NAMES = {1:"凡品", 2:"灵品", 3:"宝品", 4:"玄品", 5:"仙品", 6:"神品"}
```

### 5.7 `battle.py` — 战斗引擎(核心)

**类** `BattleEngine`:

| 方法 | 用途 |
|---|---|
| `__init__(character, enemy_id)` | 加载角色+敌人,初始化 state dict |
| `snapshot()` | 返回简化状态(发给前端) |
| `is_finished()` | 战斗是否结束 |
| `process_action(card_id)` → async generator | **核心**:玩家出牌 → 数值判定 → 推 damage/effect 立即事件 → 调 LLM 流式叙事 → 推 narration 事件 → 敌人回合 → 状态更新 |
| `_compute_outcome(card)` | 数值判定:命中/伤害/暴击 |
| `_apply_outcome(outcome, card)` | 应用结果到 state |
| `_compute_enemy_action()` | 敌人 AI(简单固定攻击) |
| `_apply_enemy_outcome(outcome)` | 应用敌人伤害 |
| `_request_narration(card, action_result)` | **未使用**,留作未来重构 |
| `_build_system_prompt()` / `_build_user_prompt(card, action_result)` | 构造 LLM 输入 |
| `_get_fallback_narration(outcome_type)` | LLM 失败时的兜底文本 |
| `_roll_drops()` | 战斗胜利掉物品 |
| `_build_enemy_narration(outcome)` | 敌人攻击的简化叙事(不走 LLM) |

**state dict 重要字段**:
```python
{
    "battle_id": str,
    "round": int,
    "status": "player_turn|processing|enemy_turn|ended",
    "result": None|"victory"|"defeat"|"fled",
    "buffs": {"focus_next": bool},
    # 玩家
    "sect_id", "sect_name", "realm", "realm_name",
    "model",                 # 当前境界对应的 LLM model
    "narration_max_tokens",
    "atk_mult",
    "player_hp", "player_max_hp",
    "player_atk", "player_def", "player_spd",
    "player_crit", "player_crit_dmg", "player_evasion",
    "player_qi", "player_max_qi",
    # 敌人
    "enemy_id", "enemy_name", "enemy_emoji",
    "enemy_hp", "enemy_max_hp",
    "enemy_atk", "enemy_def", "enemy_spd", "enemy_evasion",
    "enemy_rewards_exp", "enemy_rewards_qi",
}
```

**事件类型**(yield 给 WebSocket):
- `action_resolved` — 玩家动作判定完成
- `damage` — 数值伤害事件
- `effect` — 屏幕特效(screen_shake / flash)
- `narration` — LLM 流式叙事 chunk
- `narration_end` — 一段叙事结束
- `state` — 状态快照
- `enemy_action` — 敌人行动判定
- `end` — 战斗结束(victory/defeat,带 rewards)
- `error` — 战斗内错误

### 5.8 `llm_client.py` — LLM 调用核心

**导出函数**:`stream_battle_narration(sect_narration_style, model, max_tokens, user_prompt, api_key, base_url)` → async generator

**重试策略**(env 可调):
- `LLM_MAX_RETRIES=3` 默认 3 次
- `LLM_RETRY_BASE_DELAY=1.0` 指数退避起点
- `LLM_RETRY_MAX_DELAY=8.0` 单次等待上限

**错误分类**:
- `LLMRetryableError`:5xx / 429 / 网络错误 / 超时 → 重试
- `LLMFatalError`:400/401/403/404/422 → 立即放弃,走 fallback
- `LLMRetryableError`:已经 yield 内容时不再重试(避免文本重复)
- 全失败 → `_fallback_narration(user_prompt)` 从 `FALLBACK_NARRATIONS` 随机抽兜底

**Fallback 模板**:在 `FALLBACK_NARRATIONS` dict,按 outcome_type 分组(crit/hit/miss/heal/buff)。

**关键约定**:
- 函数参数 `api_key` 优先于环境变量 LLM_API_KEY,实现 BYOK
- `_env(name, default)`:运行时读环境变量(支持热更新)
- `BASE_SYSTEM_PROMPT`:通用 system prompt,门派风格附加在后

### 5.9 `health_check.py` — 探测 + 验证

**两个核心函数**:

#### `list_available_models(base_url, api_key)` → `(model_ids, error_msg)`
- 调 `GET {base_url}/models`
- 失败时 model_ids = []
- 用于 Onboarding 快速探测

#### `probe_byok(base_url, api_key)` → dict
- 调 `list_available_models`
- 按 `ALL_SECTS` 算每派可选性
- 返回:
```python
{
  ok: bool,
  models: list[str],
  total_models: int,
  sects: [{id, name, required, have, missing, can_choose, ...}],
  available_sect_ids: list[str],
  error: str
}
```

#### `stream_verify_sect_models(sect_id, base_url, api_key)` → async generator
- 对该派所有(去重)模型逐个测试
- 单模型失败可重试 2 次(0.5s/1.5s)
- yield 事件:start / testing / retrying / result / done
- 用于 KeyVerify 页面 / ByokSettings modal

### 5.10 `store.py` — 内存存储

**MVP 单玩家模式**,所有 user_id 都是 `"demo_player"`。

```python
_characters: dict[str, dict]    # user_id → character dict
_battles: dict[str, BattleEngine]
_inventories: dict[str, dict[str, int]]  # user_id → {item_id: count}
_equipped: dict[str, dict[str, str]]     # user_id → {slot: item_id}
```

**函数**:`get_character / save_character / delete_character`,`get_battle / save_battle / delete_battle`,`get_inventory / add_item / remove_item / get_equipped / equip_item / unequip_item`。

**重启即清空** — 这是 MVP 限制,生产需换 Postgres + Redis。

---

## 6. 前端模块详解

> 路径前缀省略 `/Users/bobdong/项目/LingshuCodex/frontend/src/`

### 6.1 `main.js` + `App.vue`

- `main.js`:挂载 Vue + Pinia + Naive UI + router
- `App.vue`:配 Naive UI 暗色主题 + 鎏金主色

### 6.2 `router.js` — 路由配置

**路由表**:

| path | component | meta |
|---|---|---|
| `/` | (redirect → /onboarding) | — |
| `/onboarding` | Onboarding.vue | title |
| `/sect-choose` | SectChoose.vue(旧)| title |
| `/key-verify/:sectId` | KeyVerify.vue | title |
| `/home` | Home.vue | title + **requireCharacter** |
| `/explore` | ExploreMap.vue | requireCharacter |
| `/inventory` | Inventory.vue | requireCharacter |
| `/items` | Items.vue | requireCharacter |
| `/bosses` | Bosses.vue | requireCharacter |
| `/battle/:id` | Battle.vue | requireCharacter + **requireBattle** |
| `/404` | NotFound.vue | — |
| `/:pathMatch(.*)*` | (redirect /404) | catch-all |

**前置守卫** `router.beforeEach(to, from, next)`:
1. 设置 title
2. `to.meta.requireCharacter` → 调 `characterApi.me()`,失败跳 `/onboarding`
3. `to.meta.requireBattle` → 调 `battleApi.get(battleId)`,失败跳 `/home` 带 query.error

**onError**:chunk 加载失败 800ms 后 `location.reload()` 自愈

### 6.3 `api/client.js` — axios 封装

**导出**:
```javascript
client                // 原始 axios instance
sectApi {list, get}
byokApi {probe}
characterApi {me, chooseSect, reset, updateByok}
battleApi {listEnemies, listCards, start, get}
exploreApi {spawn, enemiesCount}
bossApi {list, get, listSects, storylines}
itemApi {list, get}
inventoryApi {list, use, grant}
```

**统一错误归一**(拦截器):
- 网络错误 → `{code:"NETWORK_ERROR", status, message}`
- 超时 → `{code:"TIMEOUT"}`
- 5xx → `{code:"SERVER_ERROR"}`
- 401 → `{code:"AUTH_REQUIRED"}`
- 404 → `{code:"NOT_FOUND"}` 或后端给的 `code`(如 `BATTLE_NOT_FOUND`)

**reject 的 Error 对象**会带 `.code / .status / .detail` 属性。

### 6.4 `stores/game.js` — Pinia 状态

```javascript
character: ref(null)   // 当前角色对象
sects: ref([])         // 5 派列表(缓存)
setCharacter(c) / setSects(s) / clear()
```

### 6.5 `components/Logo.vue` — 游戏 LOGO

可复用 SVG 组件,props:`size`、`showText`、`textSize`、`layout`(horizontal/vertical)。

中央"笔"字 + 鎏金圆边 + 八方装饰 + 四角墨点。

### 6.6 `components/ByokSettings.vue` — 灵脉配置 modal

**核心组件**,可在主城任意时刻打开修改 base_url + api_key。

**Props**:`show`(bool), `character`(object)
**Emits**:`close`, `updated(data)`

**内部流程**:
1. 用户改 base_url / api_key → 自动清掉 `verified` 标记
2. 点 ① 验证可用性 → fetch `/api/sect/verify-key` SSE 流
3. 全过 → `verified=true`,② 保存按钮解锁
4. 点 ② 保存 → `characterApi.updateByok(base_url, api_key, true)`
5. 后端再次 probe 二次校验

**关键 watch**:
```javascript
watch([baseUrl, apiKey], () => {
  verified.value = false  // 输入变了就失效
})
```

### 6.7 Views

#### `Onboarding.vue` — 入门页(★ 默认入口)
- Step 1:bobdong.cn 推荐广告卡 → 表单(base_url 5 个预设按钮 + api_key + 道号)
- Step 2:调 `byokApi.probe()` → 展示 5 派 ✓/✗
- 点可用门派 → `router.push('/key-verify/' + id + '?base_url=...&api_key=...&name=...')`

#### `SectChoose.vue` — 旧选派页(保留)
- 不走 probe,直接列 5 派,点选派 → KeyVerify
- 默认入口已迁移到 Onboarding,这条路径仅向后兼容

#### `KeyVerify.vue` — 流式精细验证
- 接受 `route.query.base_url / api_key / name` 预填
- 调 `/api/sect/verify-key` SSE 流式
- 全过 → 调 `characterApi.chooseSect()` 创角 → /home
- 顶部"已带入 Key"绿色提示条(fromOnboarding 时)

#### `Home.vue` — 修行主城
- Logo + 角色面板(HP/灵气/经验/5 属性)
- 4 个入口卡片:开始修行(大入口)/ 背包 / 修行物品 / 修真名录
- 右上:**⚙️ 灵脉配置**(打开 ByokSettings modal) + 转世重修

#### `ExploreMap.vue` — 仿真地图
- 玩家居中(基于门派 emoji)
- 12 个怪物在地图上自由移动(`setInterval 100ms` 重算坐标 + 边界反弹)
- 鼠标悬停 → 右下信息面板(名/lore/属性/奖励)
- 点击怪物 → `battleApi.start()` → /battle/:id

#### `Inventory.vue` — 背包
- 5 类筛选(全部/材料/丹药/法宝/心法/灵宝)
- 丹药可点"使用"调 `inventoryApi.use()`
- 显示物品 lore 卡片化

#### `Items.vue` — 修行物品全集
- 只读浏览(配合搜索 + 类型筛选)
- 物品按 rarity 降序排列
- 显示 use_effect / equip_stats 细节

#### `Bosses.vue` — 修真名录
- 顶部 4 故事线 Tab(A/B/C/D)
- 切换故事线时展示 summary + 三幕
- Boss 卡片网格,点击展开右侧详情
- 详情含:Boss 故事 + 宗派背景(真实公司+仙侠演绎) + 羁绊网状跳转 + 战斗信息

#### `Battle.vue` — 战斗页(★ 核心)
- WebSocket /ws/battle/:id
- 立绘左+敌人右 + 中间叙事框 + 底部 6 卡牌
- WS 事件处理:state / damage / effect / narration / end / error
- 屏幕反馈:screenShake / flashColor / damageFx / playerShake / enemyShake
- 战斗结束 → result-overlay 弹窗显示奖励
- 离场逻辑:`leavingForResult` 标志区分正常结算 vs 异常断

#### `NotFound.vue` — 404 页
国风版"此地非修仙之所" + Logo + 跳主城按钮。

---

## 7. API 接口全表

> 全部前缀 `http://127.0.0.1:8020`
> 全部 JSON 请求/响应,错误格式 `{"detail": "..."}` 或 `{"detail":{"code","message","..."}}`

### 7.1 健康 / 元信息

| Method | Path | 说明 |
|---|---|---|
| GET | `/health` | `{"status":"ok"}` |
| GET | `/api/enemies/count` | 怪物总数 + 12 族分布 |

### 7.2 门派

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/sect/list` | 5 派完整配置(含 byok_hint) |
| GET | `/api/sect/{sect_id}` | 单派详情 |
| POST | `/api/sect/verify-key` | **SSE 流**,逐个测该派模型 |

`/api/sect/verify-key` 请求:`{sect_id, base_url, api_key}`
响应 SSE 事件:`start / testing / retrying / result / done / error`

### 7.3 BYOK 探测 + 修改

| Method | Path | 说明 |
|---|---|---|
| POST | `/api/byok/probe` | 探测 key 可用模型 + 各派可选性(快) |
| POST | `/api/character/me/byok` | **二次校验后**更新当前角色 byok |

`/api/byok/probe` 请求:`{base_url, api_key}`
响应:`{data: {ok, models, total_models, sects:[...], available_sect_ids}}`

`/api/character/me/byok` 请求:`{base_url, api_key, verified:bool}`
- `verified=false` → 400 `NOT_VERIFIED`
- 后端再 probe,失败 → 400 `BYOK_PROBE_FAILED`
- 门派错配 → 400 `SECT_NOT_AVAILABLE`
- 成功 → `{data:{updated:true, old/new_api_key_masked, new_base_url, ...}}`

### 7.4 角色

| Method | Path | 说明 |
|---|---|---|
| POST | `/api/character/choose-sect` | 创角(需带 base_url + api_key) |
| GET | `/api/character/me` | 取当前角色(api_key 不返回,只返 api_key_masked) |
| DELETE | `/api/character/me` | 重置角色(测试用) |

`choose-sect` 请求:`{sect_id, character_name, base_url, api_key}`

### 7.5 战斗

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/battle/enemies` | 适合当前等级的敌人 |
| GET | `/api/battle/cards` | 当前角色可用卡牌 |
| POST | `/api/battle/start` | 开始一场战斗 → battle_id |
| GET | `/api/battle/{battle_id}` | 检查战斗是否存在(路由守卫调用) |
| WS | `/ws/battle/{battle_id}` | **WebSocket 战斗主入口** |

WS 客户端 → 服务端:
```javascript
{action:"cast",  payload:{card_id}}
{action:"flee",  payload:{}}
{action:"ping",  payload:{...}}
```

WS 服务端 → 客户端事件类型见 § 5.7。

### 7.6 探索 / 地图

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/explore/spawn?count=N` | 生成 N 只怪 + 随机坐标 + 移动速度 |

### 7.7 Boss / 故事线

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/boss/list` | 21 个 Boss |
| GET | `/api/boss/{boss_id}` | 单 Boss 详情 |
| GET | `/api/boss-sects/list` | 18 个 Boss 宗派(真实公司) |
| GET | `/api/storylines` | 4 条故事线 |

### 7.8 物品 / 背包

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/items/list` | 55 物品列表 |
| GET | `/api/items/{item_id}` | 单物品详情 |
| GET | `/api/inventory` | 玩家背包 |
| POST | `/api/inventory/use/{item_id}` | 使用消耗品(应用 use_effect) |
| POST | `/api/inventory/grant/{item_id}?count=N` | 管理员调试用:给自己的测试账号发物品 |

---

## 8. 核心数据模型

### 8.1 Character(玩家档,内存对象)

```python
{
  "user_id": "demo_player",   # MVP 固定
  "name": str,
  "sect": str,                # canglan / tianji
  "sect_name": str,
  "level": int,               # 1-200
  "exp": int,
  "realm": str,               # qi/foundation/golden/yuanying/huashen/hetishi/dacheng/dujie/feisheng
  "realm_name": str,
  # BYOK(api_key 永不返前端,只返 api_key_masked)
  "base_url": str,
  "api_key": str,
  # 战斗属性
  "hp", "max_hp", "atk", "def_", "spd",
  "crit_rate", "crit_dmg", "evasion",
  "qi", "max_qi",
}
```

### 8.2 BattleState(内存,见 § 5.7)

### 8.3 InventoryItem

```python
{
  "id": str,
  "name", "type", "rarity", "rarity_name", "icon",
  "description", "lore",
  "use_effect": dict | None,
  "equip_stats": dict | None,
  "value_qi": int,
  "count": int,    # 背包返回时才有
}
```

---

## 9. 配置与环境变量

### 9.1 `backend/.env`

```bash
LLM_BASE_URL=https://bobdong.cn/v1
LLM_API_KEY=<your-llm-api-key>   # 仅用于 fallback(BYOK 用户用自己的)
HOST=127.0.0.1
PORT=8020
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DEFAULT_SECT=canglan
LLM_TIMEOUT=60
LLM_MAX_RETRIES=3
LLM_RETRY_BASE_DELAY=1.0
LLM_RETRY_MAX_DELAY=8.0
```

### 9.2 `frontend/vite.config.js`

```javascript
proxy: {
  '/api': { target: 'http://127.0.0.1:8020' },
  '/ws':  { target: 'ws://127.0.0.1:8020', ws:true },
}
```

---

## 10. 关键约定与模式

### 10.1 命名规范

| 对象 | 命名规范 | 示例 |
|---|---|---|
| 门派 id | 小写汉拼 | `canglan` / `tianji` / `xuanji` |
| 怪物 id | `{clan_short}_{NN}` | `fox_01` / `dragon_05` |
| Boss id | `boss_{name}` | `boss_canglan_supreme` |
| Boss 宗派 id | 公司英文小写 | `mistral_storm` / `xai_void` |
| 物品 id | `item_{category}_{name}` | `item_fur_red` / `item_pill_breakthrough` |
| 卡牌 id | snake_case | `sword_basic` / `canglan_init` |

### 10.2 错误码约定

后端 HTTPException detail 优先 dict 形式:
```python
raise HTTPException(404, {
  "code": "BATTLE_NOT_FOUND",
  "message": "战斗不存在或已结束",
  "battle_id": battle_id,
})
```

前端 axios 拦截器把 detail 自动映射到 `error.code / .message`,UI 层只 check `e.code`。

### 10.3 安全约定

- **api_key 永不返前端**,只返 `api_key_masked: "****XXXX"`
- 修改 byok 时**前后双重校验**:前端流式 verify-key 全过 + 后端 probe 二次校验
- 战斗 LLM 调用使用 character 自己的 api_key(BYOK),不读全局 env

### 10.4 状态管理约定

- 内存存储,**重启即清**(MVP)
- 单玩家 `user_id = "demo_player"` 硬编码
- 战斗状态在 BattleEngine 实例内,通过 `store._battles[battle_id]` 引用

### 10.5 LLM 调用约定

- 优先 BYOK key,无则 fallback env
- 重试只在"未 yield 内容"时进行
- 失败必定 fallback 模板,游戏不中断
- 流式优先(stream=True),max_tokens 由当前境界配置

---

## 11. 常见维护任务

### 11.1 添加新怪物

```python
# backend/app/enemies.py
# 找到对应族(如 CLAN_FOX),加新 Enemy:
CLAN_FOX.append(
    Enemy("fox_10", "九尾老祖", "山林狐妖族", "myth", 100,
          50000, 800, 250, 140, 0.30, 20000, 10000, "🦊",
          "传说中的狐族至尊",
          "终南山主宰,八尾妖王的母亲...",
          ["item_fur_gold", "item_yaodan", "item_pill_immortal"])
)
```

注意:**重启后端**才能生效。

### 11.2 添加新 Boss + 公司宗派

```python
# backend/app/bosses.py
# 1. 加宗派(BOSS_SECTS)
BOSS_SECTS["new_sect_id"] = BossSect(
    id="new_sect_id", name="新宗派",
    company="Real Company", founded="20XX · 城市",
    real_background="公司真实背景...",
    sect_story="仙侠演绎...",
    storyline="A",  # 或 B/C/D
    base_color="#XXXXXX",
)

# 2. 加 Boss
_add(Boss(
    id="boss_new", name="...", title="...",
    sect_id="new_sect_id",
    level=80, hp=20000, atk=500, ...
    lore="...",
    bonds=["boss_xxx"],
    bond_descriptions=["..."],
    drops=["item_xxx"],
    signature_skill="...",
))

# 3. 更新故事线(STORYLINES["A"]["side_bosses"].append("boss_new"))
```

### 11.3 添加新物品

```python
# backend/app/items.py
_add(Item("item_new_name", "新物品", "consumable", 3, "💊",
          "描述", "故事",
          use_effect={"hp_percent": 50},
          value_qi=500))
```

### 11.4 添加新门派(开通 xuanji/qingming/yueyin)

```python
# backend/app/sects.py
# 把 XUANJI/QINGMING/YUEYIN 的 available 改为 True
# 填好 tiers / initial_stats / buffs / narration_style / keywords
# 务必确保 tier.model 在目标厂商的实际 API 中存在
```

### 11.5 添加新卡牌

```python
# backend/app/cards.py
CARDS["new_card"] = Card(
    id="new_card", name="...",
    sect_requirement="any",  # 或 canglan/tianji
    type="attack", qi_cost=20, power=1.5, hit_rate=0.9,
    description="...", icon="⚡",
)
```

### 11.6 调整战斗数值

- 战斗 ATK 倍率 / 暴击伤害:`backend/app/sects.py` 的 `initial_stats` 或 `TierConfig.atk_multiplier`
- 怪物属性:`backend/app/enemies.py`
- 卡牌威力:`backend/app/cards.py`
- 公式细节:`backend/app/battle.py` 的 `_compute_outcome` / `_compute_enemy_action`

### 11.7 修改 LLM 叙事风格

- 通用 system prompt:`backend/app/llm_client.py` 的 `BASE_SYSTEM_PROMPT`
- 门派特色 prompt:`backend/app/sects.py` 的 `narration_style` 字段
- Fallback 文本:`backend/app/llm_client.py` 的 `FALLBACK_NARRATIONS`

### 11.8 修改前端路由 / 添加新页面

```javascript
// frontend/src/router.js
{
  path: '/new-page',
  component: () => import('./views/NewPage.vue'),
  meta: { title: '新页面 · 灵枢笔录', requireCharacter: true },
}
```

并在 `Home.vue` 加入口卡片。

### 11.9 调试 BUG

| 症状 | 看哪 |
|---|---|
| 启动报错 | `/tmp/lingshu_backend.log` / `/tmp/lingshu_frontend.log` |
| 后端模块加载失败 | `python -c "from app.main import app"` |
| API 404 | `grep -n "@app.get\|@app.post" backend/app/main.py` |
| WS 异常 | 浏览器 F12 Network → WS,看 frames |
| 数值计算错 | `backend/app/battle.py` 的 `_compute_outcome` |
| LLM 不响应 | 看 `[LLM Retry]` 或 `[LLM Fallback]` 日志 |
| 路由跳转错 | `frontend/src/router.js` 守卫 + `frontend/src/api/client.js` 错误码 |

---

## 12. 已知问题与 TODO

### 12.1 已知限制

- **单玩家模式**:user_id 硬编码 demo_player,重启清空
- **没有持久化**:数据库 / Redis 未接入
- **3 派未开放**:玄机/青冥/月隐当前 `available=False`(因 bobdong.cn 仅有 Claude+GPT)
- **没有真实抽卡**:卡牌系统只是 8 张固定卡,无 SSR 抽卡
- **战斗没有连击 / 不能逃跑暂停**:简化版

### 12.2 TODO(优先级)

1. **持久化**:SQLite 起步,user 表 + character + inventory + battle_log
2. **多用户**:JWT 鉴权,user_id 真实化
3. **BYOK 加密**:目前 api_key 明文存内存,生产需 AES-256
4. **开通玄机/青冥/月隐 3 派**:需 bobdong.cn 增加 DeepSeek/GLM/Kimi 接入
5. **抽卡系统**:绑定 SSR 笔魂 → 改 LLM system prompt 风格
6. **更多卡牌 + 装备**:目前每派只有 2 张专属卡
7. **AI 美术**:目前用 emoji 占位,接入 SiliconFlow Flux 出立绘
8. **真实 BattleEngine 持久化**:战斗中刷新会断,目前直接跳主城

---

## 13. 关键文件清单(grep 友好)

```
# 后端
backend/app/main.py                    1 个 FastAPI app,30+ 端点
backend/app/sects.py                   5 个 SectConfig,2 个 available=True
backend/app/enemies.py                 113 个 Enemy,12 个族常量 CLAN_XXX
backend/app/bosses.py                  21 个 Boss,18 个 BossSect,4 条故事线 STORYLINES
backend/app/cards.py                   8 个 Card
backend/app/items.py                   55 个 Item,5 类
backend/app/battle.py                  1 个 BattleEngine 类
backend/app/llm_client.py              stream_battle_narration() 是主入口
backend/app/health_check.py            probe_byok() + stream_verify_sect_models()
backend/app/store.py                   4 个 dict 内存,函数式访问

# 前端
frontend/src/router.js                 11 个路由 + 2 守卫规则
frontend/src/api/client.js             8 个 *Api 命名空间
frontend/src/components/Logo.vue       1 个 SVG logo 组件
frontend/src/components/ByokSettings.vue 1 个 modal 组件
frontend/src/views/*.vue               10 个页面组件
```

### 13.1 快速 grep 索引

```bash
# 找 API 端点
grep -n "^@app\." backend/app/main.py

# 找所有 5 个门派
grep -n "^[A-Z_]\+\s*=\s*SectConfig" backend/app/sects.py

# 找所有怪物族
grep -n "^CLAN_\w\+" backend/app/enemies.py

# 找所有 Boss
grep -n "^_add(Boss" backend/app/bosses.py

# 找所有物品
grep -n "^_add(Item" backend/app/items.py

# 找前端 Vue 路由
grep -n "path:" frontend/src/router.js

# 找前端 API 调用
grep -n "Api\." frontend/src/views/*.vue
```

---

## 14. 文档维护

| 文档 | 何时更新 |
|---|---|
| `ARCHITECTURE.md`(本文)| 每次加新模块 / 新 API / 新数据结构 |
| `GAME_OVERVIEW.md` | 产品定位变化时 |
| `GETTING_STARTED.md` | 入门流程变化时 |
| `PLAYER_GUIDE.md` | 添加新内容时 |

---

**版本**:v5.1 (2026-05-24)
**作者**:bobdong
**项目**:灵枢笔录(Lingshu Codex)
**联系**:本架构文档面向 AI,如有疑问直接 Read + grep 项目源码

---

## 15. v5.1 战斗系统升级(2026-05-24)

> **本节专门记录 v5.1 的新模块**,与上面的整体架构对照阅读。

### 15.1 新增文件

| 文件 | 行数 | 职责 |
|---|---|---|
| `backend/app/monster_skills.py` | ~180 | 12 族 × 4 招 = 48 怪物招式定义 |
| `backend/app/behaviors.py` | ~200 | 12 族行为准则 + 食物链(后端已写,前端未用) |
| `frontend/src/components/Logo.vue` | (已存在)| 通用 logo |
| `docs/CHANGELOG.md` | — | 版本变更日志 |

### 15.2 关键模块变更

#### `monster_skills.py`(新)

```python
@dataclass
class Skill:
    id, name, tier        # basic / mid / high / ult
    power, hit_rate, crit_bonus
    effect, description

SKILL_TABLE: dict[clan_name, list[Skill]]  # 12 族,每族 4 招

# 主入口
pick_skill_for_enemy(clan: str, level: int) -> Skill
    # 等级分段权重:
    # L<=30:  basic 70%, mid 30%
    # L<=70:  basic 40%, mid 40%, high 20%
    # L<=100: basic 20%, mid 30%, high 35%, ult 15%
    # L>100:  mid 20%, high 40%, ult 40%
```

#### `sects.py` 新增

```python
CANGLAN_DESTINY = {  # 沧澜独家天命
    "id": "destiny_canglan",
    "name": "沧澜剑域 · 一笔诛仙",
    "power": 5.0, "hit_rate": 1.0, "force_crit": True, ...
}
TIANJI_DESTINY = {  # 天机独家天命
    "id": "destiny_tianji",
    "name": "万象天衍 · 推演无敌",
    "power": 5.0, ...
}
DESTINY_SKILLS = {"canglan": ..., "tianji": ...}
get_destiny_skill(sect_id) -> dict | None
```

#### `battle.py` 改动

新 state 字段:
- `destiny_charged: bool` — 天命就绪未用
- `destiny_used: bool` — 整场已用 1 次
- `enemy_clan/enemy_level` — 用于招式选择

新方法:
- `_compute_destiny_outcome(card)` — 天命必中必暴击 5x ATK
- `_compute_enemy_action(skill)` — 接受 Skill 参数

`process_action` 新分支:
- card_id 以 `destiny_` 开头 → 走天命分支
- 末尾 5% 概率 trigger 天命降临

新事件:
- `destiny_trigger` — 天命降临通知
- `damage_summary` — 每回合战报卡

#### `llm_client.py` 改动

`BASE_SYSTEM_PROMPT` 新增段落:
```
【★ 重点标记格式】
请用 Markdown 风格的 ** 双星号 ** 包裹下列关键内容:
- 招式名(如 **沧澜九式**)
- 伤害数字(如 **147 点伤害**)
- 暴击 / 关键判定(**暴击**、**致命一击**)
每段叙事至少包含 2-4 个 ** 标记。

【天命招式特殊处理】
当判定结果是 "destiny" / "天命降世" 时,叙事风格要极致夸张
- 至少 3 处 ** 重点标记
- 字数可放宽到 200-280
```

#### `Battle.vue` 改动

新 ref:
- `destinyCharged`, `destinySkill`, `showDestinyAnim` — 天命状态
- `battleLog` — 战报卡数组(保留 6 条)
- `activeTab` 选项加 `destiny`

新方法:
- `highlightNarration(text)` — 用 regex 把 `**xxx**` 转 `<em class="hi[...]">`
  - 数字 → hi-num(红色 mono)
  - 暴击/天命关键词 → hi-crit(金色 pulse)
  - 其他 → hi(金色 highlight)

新事件处理:
- `destiny_trigger` → 显示全屏遮罩 + 切到天命栏
- `damage_summary` → 推一张战报卡

新 UI 组件:
- **卷轴叙事**:左右双竹简边框 + 上下铜环
- **战报卡**:右侧 280px 栏,TransitionGroup 入场
- **天命栏**:locked / ready 两种状态
- **天命遮罩**:3 个同心圆扩散 + 大字 zoom pop

### 15.3 WebSocket 新事件清单(v5.1)

| 事件 | 触发 | data 字段 |
|---|---|---|
| `destiny_trigger` | 天命降临 5% 概率 | skill, round, message |
| `damage_summary` | 每次出招后(玩家 + 敌人各一次)| round, attacker, skill_name, skill_icon, skill_tier, outcome_type, outcome_label, damage, is_crit, heal, qi_cost, is_destiny |
| `turn_ready` | 回合切回玩家 | round |
| `state`(扩展) | 加 destiny_charged/used/skill | 同前 |

### 15.4 数据流(v5.1 战斗循环)

```
玩家点卡牌(可能是 destiny_*)
    ↓ WS send action:"cast", card_id
后端 process_action:
    1. 检测 is_destiny = card_id.startswith("destiny_")
    2. 若是 destiny:
       - 校验 destiny_charged && !destiny_used
       - 构造伪 card 对象(必中必暴击 5x)
       - mark destiny_used
    3. 数值判定 → 立即 yield damage/effect
    4. 调 LLM 流式叙事(带 **xxx** 标记)
    5. yield narration_end
    6. yield damage_summary(玩家战报卡)
    7. 检查胜负
    8. 敌人回合:pick_skill_for_enemy → _compute_enemy_action(skill)
    9. yield damage/effect/narration
    10. yield damage_summary(敌人战报卡)
    11. 玩家回合恢复:
        - 5% 几率 yield destiny_trigger(若未触发未用过)
        - yield state(BUG 修复)
        - yield turn_ready
```

### 15.5 维护手册(添加内容)

#### 添加新招式

```python
# backend/app/monster_skills.py
SKILL_TABLE["山林狐妖族"].append(
    Skill("fox_extra", "新招", "high", 1.7, 0.82, 0.10,
          effect="confuse", description="...")
)
```

#### 添加新门派的天命招式

```python
# backend/app/sects.py
XUANJI_DESTINY = {
    "id": "destiny_xuanji",
    "name": "...",
    "power": 5.0, "hit_rate": 1.0, "force_crit": True,
    "description": "...", "icon": "🧠", "color": "#9B59B6",
}
DESTINY_SKILLS["xuanji"] = XUANJI_DESTINY
```

#### 调整天命触发概率

```python
# backend/app/battle.py 的 process_action 末尾
if random.random() < 0.05:  # ← 改这个,0.01 = 1%, 0.10 = 10%
    self.state["destiny_charged"] = True
    ...
```

### 15.6 已知 v5.1 限制

- 天命招式只为沧澜 / 天机定义,其他 3 派暂未开通(需要先开通门派)
- 战报卡最多保留 6 条,长战斗早期记录会丢失
- 关键字高亮是前端 regex,LLM 偶尔不按 ** 格式输出时无高亮
- 怪物招式名固定,LLM 叙事中提到的招式名可能与战报卡的招式名不一致(LLM 自由发挥)
