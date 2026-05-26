"""怪物行为准则 — 每族独立的移动模式 / 食物链 / 聊天人格

设计:
- 6 种移动模式覆盖 12 族,前端按模式分化
- 食物链:hunter/prey/peer 三类关系决定相遇时的态度
- 聊天人格:给 LLM 的 system prompt 风格附加
"""

from dataclasses import dataclass, field
from typing import Optional

# ---------- 移动模式枚举 ----------
PATTERN_WANDER     = "wander"      # 随机游走(默认)
PATTERN_PATROL_H   = "patrol_h"    # 主要横向巡逻(飞鸟)
PATTERN_ORBIT      = "orbit"       # 围绕初始点画圆(龙、仙器)
PATTERN_STATIONARY = "stationary"  # 几乎不动(草木、神兽)
PATTERN_TELEPORT   = "teleport"    # 不规则瞬移(鬼、异域)
PATTERN_HUNT       = "hunt"        # 主动追逐食物链下方(猛兽)


@dataclass
class ClanBehavior:
    pattern: str             # 移动模式
    base_speed: float        # 基础速度 0.0-1.0
    move_range: float        # 活动半径(%)
    wobble_chance: float     # 转向概率
    aggression: int          # 0-10,影响相遇时的态度
    fear_player: bool        # 看到玩家是否退避
    # 食物链(族名字符串)
    chase_prey: list[str] = field(default_factory=list)
    flee_from: list[str] = field(default_factory=list)
    # 相遇时的随机 emoji 表情
    interaction_emojis: list[str] = field(default_factory=list)
    # 聊天人格(给 LLM 用作 system prompt 附加)
    chat_personality: str = ""
    # 颜色调(用于 UI 高亮)
    aura_color: str = "#888"


CLAN_BEHAVIORS: dict[str, ClanBehavior] = {
    "山林狐妖族": ClanBehavior(
        pattern=PATTERN_WANDER, base_speed=0.6, move_range=35,
        wobble_chance=0.04, aggression=4, fear_player=False,
        chase_prey=["灵雀飞鸟族", "草木精怪族"],
        flee_from=["猛兽族", "龙族", "神兽族"],
        interaction_emojis=["😏", "✨", "🦊", "💭", "🎭"],
        chat_personality="顽皮狡黠,说话喜欢半真半假。会用'哼'/'嗤'开头嘲讽对方,但也好奇心重。",
        aura_color="#E89B5F",
    ),
    "灵雀飞鸟族": ClanBehavior(
        pattern=PATTERN_PATROL_H, base_speed=1.2, move_range=55,
        wobble_chance=0.005, aggression=2, fear_player=True,
        chase_prey=["蛇蟒族"],   # 鸟吃蛇蛋
        flee_from=["猛兽族", "蛇蟒族", "鬼族"],
        interaction_emojis=["🎶", "☁️", "🐦", "✨"],
        chat_personality="啁啾欢快,语句短促,常带'唧'/'啾'拟声。乐天派,但见到天敌瞬间惊慌。",
        aura_color="#7FC7E8",
    ),
    "蛇蟒族": ClanBehavior(
        pattern=PATTERN_WANDER, base_speed=0.35, move_range=20,
        wobble_chance=0.005, aggression=6, fear_player=False,
        chase_prey=["灵雀飞鸟族", "山林狐妖族"],
        flee_from=["神兽族", "龙族"],
        interaction_emojis=["🐍", "💧", "👁️", "🌫️"],
        chat_personality="缓慢冷漠,说话拖长音如吐信。每句都带威胁感:'嘶...你想做什么...'",
        aura_color="#52B788",
    ),
    "猛兽族": ClanBehavior(
        pattern=PATTERN_HUNT, base_speed=0.85, move_range=50,
        wobble_chance=0.03, aggression=8, fear_player=False,
        chase_prey=["山林狐妖族", "灵雀飞鸟族", "草木精怪族"],
        flee_from=["神兽族", "上古凶兽族"],
        interaction_emojis=["🔥", "💢", "🐺", "🦷"],
        chat_personality="凶猛直接,说话像低吼。短句多,带'咆'/'呃'拟声。挑衅时极嚣张。",
        aura_color="#C03F3F",
    ),
    "草木精怪族": ClanBehavior(
        pattern=PATTERN_STATIONARY, base_speed=0.1, move_range=4,
        wobble_chance=0.0, aggression=1, fear_player=False,
        chase_prey=[],
        flee_from=["猛兽族"],
        interaction_emojis=["🌿", "💚", "🌸", "☁️"],
        chat_personality="宁静古老,语句缓慢有哲思。常引用古诗。看尽千年风霜。",
        aura_color="#95D5B2",
    ),
    "鬼族": ClanBehavior(
        pattern=PATTERN_TELEPORT, base_speed=0.3, move_range=45,
        wobble_chance=0.12, aggression=7, fear_player=False,
        chase_prey=["山林狐妖族", "灵雀飞鸟族", "草木精怪族"],
        flee_from=["神兽族", "仙器之灵族"],
        interaction_emojis=["💀", "😱", "👻", "🌫️", "⚰️"],
        chat_personality="幽冷哀怨,常带怨气与回忆。开口必提'当年'/'我死时'。冷笑频繁。",
        aura_color="#9B59B6",
    ),
    "龙族": ClanBehavior(
        pattern=PATTERN_ORBIT, base_speed=0.5, move_range=40,
        wobble_chance=0.001, aggression=5, fear_player=False,
        chase_prey=[],
        flee_from=["盘古残魂"],  # 几乎不怕任何东西
        interaction_emojis=["⚡", "✨", "🐉", "👑"],
        chat_personality="高傲威严,自称'本王'/'吾'。句句铿锵,引经据典。看不起凡品但偶尔慈悲。",
        aura_color="#3498DB",
    ),
    "神兽族": ClanBehavior(
        pattern=PATTERN_STATIONARY, base_speed=0.06, move_range=10,
        wobble_chance=0.0, aggression=3, fear_player=False,
        chase_prey=[],
        flee_from=[],
        interaction_emojis=["🌟", "✨", "🐲", "☯️"],
        chat_personality="庄严仁慈,如菩萨临世。语调平和但威压自显。常以'施主'/'尔等'称呼。",
        aura_color="#FFE0A3",
    ),
    "上古凶兽族": ClanBehavior(
        pattern=PATTERN_WANDER, base_speed=0.7, move_range=55,
        wobble_chance=0.015, aggression=9, fear_player=False,
        chase_prey=["山林狐妖族", "灵雀飞鸟族", "猛兽族", "魔修族"],
        flee_from=[],
        interaction_emojis=["🔥", "💢", "👹", "⚡"],
        chat_personality="残暴远古,声如雷霆。说话不顾文法,纯粹的恐吓与挑衅。",
        aura_color="#B59CFF",
    ),
    "魔修族": ClanBehavior(
        pattern=PATTERN_WANDER, base_speed=0.7, move_range=40,
        wobble_chance=0.04, aggression=7, fear_player=True,  # 怕被发现
        chase_prey=["草木精怪族", "山林狐妖族"],
        flee_from=["神兽族", "仙器之灵族"],
        interaction_emojis=["🥷", "🩸", "😈", "🗡️", "👁️"],
        chat_personality="邪魅诡异,声音压低如耳语。说话含毒,常以'兄弟'/'朋友'反讽。",
        aura_color="#8B0000",
    ),
    "仙器之灵族": ClanBehavior(
        pattern=PATTERN_ORBIT, base_speed=0.35, move_range=22,
        wobble_chance=0.005, aggression=4, fear_player=False,
        chase_prey=[],
        flee_from=[],
        interaction_emojis=["✨", "💫", "🗡️", "🪞"],
        chat_personality="器灵之声,有金石回响感。常忆主人往事。说话简短但有典雅韵味。",
        aura_color="#FFD700",
    ),
    "异域生灵族": ClanBehavior(
        pattern=PATTERN_TELEPORT, base_speed=0.55, move_range=70,
        wobble_chance=0.04, aggression=6, fear_player=False,
        chase_prey=[],
        flee_from=[],
        interaction_emojis=["🌌", "👁️", "❓", "🌀"],
        chat_personality="费解陌生,语法古怪。说的话似乎不属于本界,常带逻辑断裂感。",
        aura_color="#7B68EE",
    ),
}


def get_behavior(clan: str) -> ClanBehavior:
    """根据族名取行为配置,未配置返回默认 wander"""
    return CLAN_BEHAVIORS.get(clan, CLAN_BEHAVIORS["山林狐妖族"])


def behavior_to_dict(b: ClanBehavior) -> dict:
    return {
        "pattern": b.pattern,
        "base_speed": b.base_speed,
        "move_range": b.move_range,
        "wobble_chance": b.wobble_chance,
        "aggression": b.aggression,
        "fear_player": b.fear_player,
        "chase_prey": b.chase_prey,
        "flee_from": b.flee_from,
        "interaction_emojis": b.interaction_emojis,
        "aura_color": b.aura_color,
    }


# ============================================================
# 相遇互动类型(给前端决定显示什么气泡)
# ============================================================
def get_interaction_type(clan_a: str, clan_b: str) -> str:
    """返回 a 看到 b 时的反应:
       'hunt'  — a 想吃 b
       'flee'  — a 怕 b
       'peer'  — 同族,友好
       'mutual_threat' — 相互敌对
       'neutral' — 中立路过
    """
    if clan_a == clan_b:
        return "peer"
    ba, bb = get_behavior(clan_a), get_behavior(clan_b)
    if clan_b in ba.chase_prey and clan_a in bb.chase_prey:
        return "mutual_threat"
    if clan_b in ba.chase_prey:
        return "hunt"
    if clan_b in ba.flee_from:
        return "flee"
    return "neutral"


# ============================================================
# 怪物对话生成的 fallback 模板
# ============================================================
FALLBACK_DIALOGS = {
    "peer": [
        ["{a_name}: 师兄安好。","{b_name}: 嗯,你也是。"],
        ["{a_name}: 千年了,你还在?","{b_name}: 是啊,还在等。"],
        ["{a_name}: 看那执笔者来了。","{b_name}: 嗯,他还嫩。"],
    ],
    "hunt": [
        ["{a_name}: 嗤,你逃不掉的。","{b_name}: 别...别过来!"],
        ["{a_name}: 我闻到了血气...","{b_name}: 这次的猎物太脏了..."],
    ],
    "flee": [
        ["{a_name}: 别...我什么都没看见!","{b_name}: 嗯?谁在那里?"],
        ["{a_name}: (闭气屏息中)","{b_name}: 嗅...有股气息..."],
    ],
    "mutual_threat": [
        ["{a_name}: 是你!","{b_name}: 来啊,我等这一刻很久了!"],
        ["{a_name}: 千年血仇,今日了结!","{b_name}: 哼,正合我意!"],
    ],
    "neutral": [
        ["{a_name}: ...","{b_name}: ..."],
        ["{a_name}: 又见面了。","{b_name}: 嗯。"],
        ["{a_name}: 道路漫漫,珍重。","{b_name}: 各自修行罢。"],
    ],
}


def fallback_dialog(clan_a: str, name_a: str, clan_b: str, name_b: str) -> list[str]:
    """LLM 失败时的兜底对话"""
    import random
    interaction = get_interaction_type(clan_a, clan_b)
    template = random.choice(FALLBACK_DIALOGS.get(interaction, FALLBACK_DIALOGS["neutral"]))
    return [line.format(a_name=name_a, b_name=name_b) for line in template]
