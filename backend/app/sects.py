"""5 大门派完整配置:门派 → 模型梯度 + 风格 + 数值

实际部署环境(bobdong.cn)可用模型:
- Claude 系列:claude-haiku-4-5, claude-sonnet-4-6, claude-opus-4-7
- GPT 系列:gpt-5.4-mini, gpt-5.4, gpt-5.4-openai-compact, gpt-5.5

MVP 阶段开放 2 派(沧澜=Claude / 天机=GPT),其余 3 派(玄机/青冥/月隐)
界面置灰,提示"该派灵脉尚未开通"。
"""

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class TierConfig:
    name: str          # 境界中文名
    level_min: int     # 解锁等级下限
    level_max: int     # 解锁等级上限
    model: str         # 该境界对应模型
    max_tokens: int    # 叙事长度
    atk_multiplier: float  # 数值加成

@dataclass
class SectConfig:
    id: str
    name: str
    provider_display: str
    description: str
    style_short: str
    tagline: str
    initial_difficulty: int   # 1-5
    endgame_difficulty: int
    cost_tier: str
    available: bool           # MVP 是否开放
    initial_stats: dict
    buffs: list[dict]
    tiers: list[TierConfig]
    narration_style: str      # LLM system prompt 风格附加
    keywords: list[str]
    color_primary: str
    color_accent: str
    # ★ provider 关键词:模型 ID 含任一关键词即视为该派可用
    # 用于 probe 模糊匹配 + 运行时 fallback 找具体模型
    provider_keywords: list[str] = field(default_factory=list)

# ============================================================
# 沧澜剑派 / Anthropic
# ============================================================
CANGLAN = SectConfig(
    id="canglan",
    name="沧澜剑派",
    provider_display="Anthropic · 克劳神宗",
    description="沧澜者,沧海无澜,深不见底也。讲究'深思而后动,一击必中要害'。",
    style_short="精准深远,长叙事",
    tagline="每一击都凝聚了千年思虑",
    initial_difficulty=3,
    endgame_difficulty=5,
    cost_tier="中等-高",
    available=True,
    initial_stats={
        "hp": 100, "max_hp": 100,
        "atk": 22, "def_": 12, "spd": 90,
        "crit_rate": 0.18, "crit_dmg": 1.7, "evasion": 0.05,
        "qi": 800, "max_qi": 800,
    },
    buffs=[
        {"name": "剑意如墨", "desc": "连击伤害递增 +5%/层,上限 +50%"},
        {"name": "深思熟虑", "desc": "每回合 10% 触发洞察"},
        {"name": "墨韵悠长", "desc": "灵气上限 +20%"},
    ],
    tiers=[
        # 9 境界,3 个模型级别(haiku-4-5 / sonnet-4-6 / opus-4-7,opus-4-7 提前覆盖化神 & 合体)
        # ★ v3.1:移除 opus-4-6(网关稳定性差),化神/合体直接升 opus-4-7
        TierConfig("炼气", 1, 10,   "claude-haiku-4-5-20251001", 200, 1.0),
        TierConfig("筑基", 11, 25,  "claude-haiku-4-5-20251001", 220, 1.15),
        TierConfig("金丹", 26, 45,  "claude-sonnet-4-6",         250, 1.35),
        TierConfig("元婴", 46, 65,  "claude-sonnet-4-6",         280, 1.55),
        TierConfig("化神", 66, 85,  "claude-opus-4-7",           300, 1.80),
        TierConfig("合体", 86, 105, "claude-opus-4-7",           320, 2.10),
        TierConfig("大乘", 106, 125,"claude-opus-4-7",           350, 2.50),
        TierConfig("渡劫", 126, 150,"claude-opus-4-7",           400, 3.00),
        TierConfig("飞升", 151, 200,"claude-opus-4-7",           450, 3.50),  # ★ v3.0 新增最终境
    ],
    narration_style=(
        "你的叙事风格:深沉文学化,长句多,逻辑严密。"
        "喜用'剑意'、'墨韵'、'沧澜'、'九霄'、'洞察'、'沉吟'等词。"
        "战斗前往往有 1-2 句'剑意凝聚 / 内心运算'的描写。"
        "暴击时强调'凝聚千年修为'的深远感,而非爆炸冲击感。"
        "节奏沉稳,避免短促急迫的句子。"
    ),
    keywords=["墨色", "沧澜", "九霄", "深远", "洞察", "沉吟", "剑意如墨"],
    color_primary="#0F1B2E",
    color_accent="#D4A24C",
    provider_keywords=["claude", "anthropic"],
)

# 天命降临:沧澜独家神技
CANGLAN_DESTINY = {
    "id": "destiny_canglan",
    "name": "沧澜剑域 · 一笔诛仙",
    "tier": "destiny",
    "power": 5.0,
    "hit_rate": 1.0,
    "force_crit": True,
    "description": "天道为之颤栗,一笔挥就便有诛仙之势",
    "icon": "🗡️",
    "color": "#FFE0A3",
}

# ============================================================
# 天机阁 / OpenAI
# ============================================================
TIANJI = SectConfig(
    id="tianji",
    name="天机阁",
    provider_display="OpenAI · 山姆道君",
    description="天机阁主'山姆道君',讲究'诸法皆通,万象归一,机关算尽'。",
    style_short="全能多变,机关算尽",
    tagline="万法归一,千变万化",
    initial_difficulty=2,
    endgame_difficulty=4,
    cost_tier="中等",
    available=True,
    initial_stats={
        "hp": 110, "max_hp": 110,
        "atk": 25, "def_": 10, "spd": 100,
        "crit_rate": 0.15, "crit_dmg": 1.6, "evasion": 0.08,
        "qi": 700, "max_qi": 700,
    },
    buffs=[
        {"name": "万法归一", "desc": "手牌容量 +2"},
        {"name": "机关算尽", "desc": "对未知敌人首次攻击 +20%"},
        {"name": "诸法皆通", "desc": "可同时学习多种心法"},
    ],
    tiers=[
        # 9 境界,3 个模型级别(gpt-5.3-codex / gpt-5.4 / gpt-5.5,gpt-5.5 占顶端 5 境)
        TierConfig("炼气", 1, 10,   "gpt-5.3-codex", 200, 1.0),
        TierConfig("筑基", 11, 25,  "gpt-5.3-codex", 220, 1.15),
        TierConfig("金丹", 26, 45,  "gpt-5.4",       250, 1.35),
        TierConfig("元婴", 46, 65,  "gpt-5.4",       280, 1.55),
        TierConfig("化神", 66, 85,  "gpt-5.5",       300, 1.80),
        TierConfig("合体", 86, 105, "gpt-5.5",       320, 2.10),
        TierConfig("大乘", 106, 125,"gpt-5.5",       350, 2.50),
        TierConfig("渡劫", 126, 150,"gpt-5.5",       400, 3.00),
        TierConfig("飞升", 151, 200,"gpt-5.5",       450, 3.50),  # ★ v3.0 新增最终境
    ],
    narration_style=(
        "你的叙事风格:广博多变,各种比喻和典故信手拈来。"
        "喜用'机关'、'万象'、'诸法'、'运筹'、'千变'、'齿轮'等词。"
        "战斗描写富有视觉冲击力,常带数字 / 几何 / 机械元素。"
        "暴击时强调'万法归元'的全能感。"
        "节奏轻快明亮。"
    ),
    keywords=["机关", "万象", "诸法", "运筹", "千变", "齿轮", "玄机"],
    color_primary="#1B1A2E",
    color_accent="#FFB454",
    provider_keywords=["gpt", "openai", "o1-", "o3-", "o4-"],
)

# 天命降临:天机独家神技
TIANJI_DESTINY = {
    "id": "destiny_tianji",
    "name": "万象天衍 · 推演无敌",
    "tier": "destiny",
    "power": 5.0,
    "hit_rate": 1.0,
    "force_crit": True,
    "description": "千机齐转,万象归一,推演已尽世间变数",
    "icon": "⚙️",
    "color": "#FFE0A3",
}

# ============================================================
# 以下 3 派 MVP 不开放,但保留入口提示
# ============================================================
XUANJI = SectConfig(
    id="xuanji", name="玄机宗", provider_display="深度求索 · 幻方真人",
    description="玄机宗,潜居终南山。讲究'深思而后行,一击必透,性价比为王'。",
    style_short="暴击推理,极致性价比", tagline="一念之间,推演千局",
    initial_difficulty=1, endgame_difficulty=4, cost_tier="极低",
    available=True,
    initial_stats={
        "hp": 105, "max_hp": 105,
        "atk": 23, "def_": 11, "spd": 105,
        "crit_rate": 0.22, "crit_dmg": 1.8, "evasion": 0.07,
        "qi": 850, "max_qi": 850,
    },
    buffs=[
        {"name": "幻方推演", "desc": "暴击伤害 +15%"},
        {"name": "性价比之神", "desc": "灵气消耗 -10%"},
        {"name": "深思一击", "desc": "首回合 +20% 暴击"},
    ],
    tiers=[
        # DeepSeek 模型梯度:flash (轻量推理) / pro (重型推理)
        TierConfig("炼气", 1, 10,    "deepseek-v4-flash", 180, 1.0),
        TierConfig("筑基", 11, 25,   "deepseek-v4-flash", 200, 1.15),
        TierConfig("金丹", 26, 45,   "deepseek-v4-flash", 230, 1.35),
        TierConfig("元婴", 46, 65,   "deepseek-v4-pro",   260, 1.60),
        TierConfig("化神", 66, 85,   "deepseek-v4-pro",   290, 1.85),
        TierConfig("合体", 86, 105,  "deepseek-v4-pro",   320, 2.15),
        TierConfig("大乘", 106, 125, "deepseek-v4-pro",   350, 2.50),
        TierConfig("渡劫", 126, 150, "deepseek-v4-pro",   400, 3.00),
        TierConfig("飞升", 151, 200, "deepseek-v4-pro",   450, 3.50),
    ],
    narration_style=(
        "你的叙事风格:简洁犀利,直击要害。"
        "喜用'幻方'、'推演'、'破局'、'一击'、'极简'等词。"
        "战斗描写讲究'瞬息千变,以一驭百'。"
        "暴击时强调'深思之后一击致命'的精确感。"
    ),
    keywords=["幻方", "推演", "破局", "极简", "深思"],
    color_primary="#1E1B2E", color_accent="#9B59B6",
    provider_keywords=["deepseek"],
)
QINGMING = SectConfig(
    id="qingming", name="青冥派", provider_display="智谱 · 智冥仙翁",
    description="青冥派源出'智冥仙翁',讲究'博学根基,稳扎稳打,千年学问'。",
    style_short="中文根基,稳健", tagline="博学广闻,根基深厚",
    initial_difficulty=1, endgame_difficulty=3, cost_tier="免费起步",
    available=True,
    initial_stats={
        "hp": 120, "max_hp": 120,
        "atk": 20, "def_": 18, "spd": 85,
        "crit_rate": 0.12, "crit_dmg": 1.5, "evasion": 0.10,
        "qi": 750, "max_qi": 750,
    },
    buffs=[
        {"name": "博学根基", "desc": "防御 +15%"},
        {"name": "千古经文", "desc": "受到伤害每次 -3"},
        {"name": "稳扎稳打", "desc": "HP 上限 +20%"},
    ],
    tiers=[
        # 智谱 GLM 系列:全境界使用 glm 模型(用户上游通常只一档)
        TierConfig("炼气", 1, 10,    "glm-4.6", 180, 1.0),
        TierConfig("筑基", 11, 25,   "glm-4.6", 200, 1.15),
        TierConfig("金丹", 26, 45,   "glm-4.6", 230, 1.35),
        TierConfig("元婴", 46, 65,   "glm-4.6", 260, 1.55),
        TierConfig("化神", 66, 85,   "glm-4-plus", 290, 1.80),
        TierConfig("合体", 86, 105,  "glm-4-plus", 320, 2.10),
        TierConfig("大乘", 106, 125, "glm-4-plus", 350, 2.40),
        TierConfig("渡劫", 126, 150, "glm-4-plus", 400, 2.85),
        TierConfig("飞升", 151, 200, "glm-4-plus", 450, 3.30),
    ],
    narration_style=(
        "你的叙事风格:文白相间,博学典雅。"
        "喜用'青冥'、'博学'、'经文'、'稳扎'、'根基'等词。"
        "战斗描写讲究'千古传承,一招制胜'。"
        "暴击时强调'博学之力'的厚重感。"
    ),
    keywords=["青冥", "博学", "经文", "根基", "千古"],
    color_primary="#1A2E20", color_accent="#52B788",
    provider_keywords=["glm", "chatglm", "zhipu"],
)
YUEYIN = SectConfig(
    id="yueyin", name="月隐宫", provider_display="月之暗面 · 月隐天尊",
    description="月隐宫,夜阑山深处。讲究'千古不忘,潜伏待发,记忆万年'。",
    style_short="超长记忆,谋略翻盘", tagline="千年回忆,一击成名",
    initial_difficulty=4, endgame_difficulty=5, cost_tier="中等-高",
    available=True,
    initial_stats={
        "hp": 95, "max_hp": 95,
        "atk": 26, "def_": 9, "spd": 115,
        "crit_rate": 0.20, "crit_dmg": 1.9, "evasion": 0.12,
        "qi": 900, "max_qi": 900,
    },
    buffs=[
        {"name": "千年回忆", "desc": "受到致命一击时,5% 复活"},
        {"name": "夜阑追击", "desc": "速度 +10%,先手出招"},
        {"name": "月隐之姿", "desc": "闪避率 +5%"},
    ],
    tiers=[
        # Moonshot Kimi 系列:超长上下文 + 反推
        TierConfig("炼气", 1, 10,    "kimi-k2-thinking", 180, 1.0),
        TierConfig("筑基", 11, 25,   "kimi-k2-thinking", 200, 1.15),
        TierConfig("金丹", 26, 45,   "kimi-k2-thinking", 230, 1.35),
        TierConfig("元婴", 46, 65,   "kimi-k2-thinking", 260, 1.60),
        TierConfig("化神", 66, 85,   "moonshot-v1-128k", 290, 1.85),
        TierConfig("合体", 86, 105,  "moonshot-v1-128k", 320, 2.15),
        TierConfig("大乘", 106, 125, "moonshot-v1-128k", 350, 2.50),
        TierConfig("渡劫", 126, 150, "moonshot-v1-128k", 400, 3.00),
        TierConfig("飞升", 151, 200, "moonshot-v1-128k", 450, 3.50),
    ],
    narration_style=(
        "你的叙事风格:幽暗诡谲,谋略深沉。"
        "喜用'月隐'、'夜阑'、'记忆'、'千年'、'潜伏'等词。"
        "战斗描写讲究'夜行如风,一击成名'。"
        "暴击时强调'千年蛰伏,一击翻盘'的反转感。"
    ),
    keywords=["月隐", "夜阑", "记忆", "千年", "潜伏"],
    color_primary="#1F1A2E", color_accent="#B59CFF",
    provider_keywords=["kimi", "moonshot"],
)

ALL_SECTS = {
    "canglan": CANGLAN,
    "tianji": TIANJI,
    "xuanji": XUANJI,
    "qingming": QINGMING,
    "yueyin": YUEYIN,
}

# 天命招式映射
DESTINY_SKILLS = {
    "canglan": CANGLAN_DESTINY,
    "tianji":  TIANJI_DESTINY,
}

def get_destiny_skill(sect_id: str):
    """返回天命招式 dict 或 None"""
    return DESTINY_SKILLS.get(sect_id)

# 各派对应厂商提示(用于 UI 显示"应填什么 key")
SECT_TO_PROVIDER_HINT = {
    "canglan":  {"provider": "anthropic", "key_format": "sk-ant-... 或网关 sk-...",
                 "default_base_url": "https://bobdong.cn/v1",
                 "official_base_url": "https://api.anthropic.com"},
    "tianji":   {"provider": "openai",   "key_format": "sk-... (OpenAI)",
                 "default_base_url": "https://bobdong.cn/v1",
                 "official_base_url": "https://api.openai.com/v1"},
    "xuanji":   {"provider": "deepseek", "key_format": "sk-... (DeepSeek)",
                 "default_base_url": "https://bobdong.cn/v1",
                 "official_base_url": "https://api.deepseek.com"},
    "qingming": {"provider": "zhipu",    "key_format": "智谱长串",
                 "default_base_url": "https://bobdong.cn/v1",
                 "official_base_url": "https://open.bigmodel.cn/api/paas/v4"},
    "yueyin":   {"provider": "moonshot", "key_format": "sk-... (Moonshot)",
                 "default_base_url": "https://bobdong.cn/v1",
                 "official_base_url": "https://api.moonshot.cn/v1"},
}

def get_sect(sect_id: str) -> Optional[SectConfig]:
    return ALL_SECTS.get(sect_id)

def get_tier_for_level(sect_id: str, level: int) -> Optional[TierConfig]:
    """根据等级返回该派对应境界配置"""
    sect = get_sect(sect_id)
    if not sect or not sect.tiers:
        return None
    for t in sect.tiers:
        if t.level_min <= level <= t.level_max:
            return t
    return sect.tiers[-1]  # 超过最高级用最高


def resolve_model_for_sect(sect_id: str, configured_model: str, available_models: list) -> str:
    """运行时模型选择 — 如果 tier 里写的 model 用户没有,fallback 到同 provider 的模型。

    available_models: 用户 key 里实际可用的模型 ID 列表(从 list_available_models 拉的)。
    """
    if not available_models:
        return configured_model  # 没拉到列表,退到默认
    if configured_model in available_models:
        return configured_model  # 精确命中
    sect = get_sect(sect_id)
    if not sect or not sect.provider_keywords:
        return configured_model
    keywords = [kw.lower() for kw in sect.provider_keywords]
    for m in available_models:
        ml = m.lower()
        if any(kw in ml for kw in keywords):
            return m  # 取第一个同 provider 的模型
    return configured_model  # 同 provider 也没有,只能用默认(会失败,但保持原行为)

def sect_to_dict(sect: SectConfig) -> dict:
    hint = SECT_TO_PROVIDER_HINT.get(sect.id, {})
    return {
        "id": sect.id,
        "name": sect.name,
        "provider_display": sect.provider_display,
        "description": sect.description,
        "style_short": sect.style_short,
        "tagline": sect.tagline,
        "initial_difficulty": sect.initial_difficulty,
        "endgame_difficulty": sect.endgame_difficulty,
        "cost_tier": sect.cost_tier,
        "available": sect.available,
        "initial_stats": sect.initial_stats,
        "buffs": sect.buffs,
        "tiers": [
            {"name": t.name, "level_min": t.level_min, "level_max": t.level_max,
             "model": t.model, "max_tokens": t.max_tokens,
             "atk_multiplier": t.atk_multiplier}
            for t in sect.tiers
        ],
        "color_primary": sect.color_primary,
        "color_accent": sect.color_accent,
        "flag_url": f"/images/sects/flags/{sect.id}.png",
        "byok_hint": hint,
    }
