"""物品大全 — 丹药 / 法宝 / 材料 / 心法

类型说明:
- material(材料):怪物掉落,可合成或卖出
- consumable(丹药/消耗品):使用立即恢复或加 buff
- equipment(法宝):可装备,提供永久属性
- skill_book(心法):一次性使用,提升角色属性 / 解锁招式
- treasure(灵宝):稀有掉落,可镶嵌/合成更强法宝
"""

from dataclasses import dataclass

@dataclass
class Item:
    id: str
    name: str
    type: str         # material / consumable / equipment / skill_book / treasure
    rarity: int       # 1-6:白 / 绿 / 蓝 / 紫 / 橙 / 红
    icon: str         # emoji
    description: str
    lore: str
    # 使用效果(仅 consumable / skill_book)
    use_effect: dict = None
    # 装备属性(仅 equipment)
    equip_stats: dict = None
    # 价值
    value_qi: int = 0


# rarity 字串
RARITY_NAMES = {1: "凡品", 2: "灵品", 3: "宝品", 4: "玄品", 5: "仙品", 6: "神品"}
ITEM_ICON_BASE = "/images/items"


ITEMS = {}

def _add(item: Item):
    ITEMS[item.id] = item


# ============ 材料(怪物掉落)============
_add(Item("item_qi_dust", "灵气尘", "material", 1, "✨",
          "微弱的灵气结晶,可炼制低级丹药", "万物含灵,皆有此尘。", value_qi=2))
_add(Item("item_fur_white", "白兽皮", "material", 1, "🟫",
          "山林兽类的毛皮", "可用于编织凡品法袍。", value_qi=10))
_add(Item("item_fur_red", "赤狐尾", "material", 2, "🦊",
          "妖狐的尾羽,带有微量灵气", "三尾以上狐妖才会掉落,十分珍贵。", value_qi=50))
_add(Item("item_fur_gold", "金毛皮", "material", 3, "🦁",
          "九尾老祖座下精怪的皮", "稀有的灵兽皮料,可制上品法袍。", value_qi=200))
_add(Item("item_feather_white", "白羽", "material", 1, "🪶",
          "灵雀的普通羽毛", "微弱的风元素附着其上。", value_qi=8))
_add(Item("item_feather_rainbow", "七彩翎", "material", 2, "🌈",
          "彩翎雀的羽毛", "在阳光下变幻七色,可炼幻术法宝。", value_qi=60))
_add(Item("item_feather_phoenix", "凤翎", "material", 4, "🔥",
          "凤凰之裔脱落的羽毛", "焚而不毁,可炼制顶级火属性法宝。", value_qi=800))
_add(Item("item_serpent_skin", "蛇蜕", "material", 1, "🐍",
          "蛇蟒蜕下的皮", "可用于配置毒药或炼制柔韧法甲。", value_qi=12))
_add(Item("item_serpent_scale_white", "白蟒鳞", "material", 3, "🐍",
          "千年白蟒的鳞片", "传说中曾被白娘子留下一片。", value_qi=350))
_add(Item("item_poison_sac", "毒囊", "material", 2, "🧪",
          "毒蛇的毒腺", "提取后可制蛊药或毒剑。", value_qi=80))
_add(Item("item_beast_fur", "猛兽皮", "material", 2, "🐅",
          "虎豹狼等猛兽之皮", "比凡兽皮更厚实,适合战甲。", value_qi=40))
_add(Item("item_swift_claw", "迅捷之爪", "material", 3, "🪝",
          "山豹/鹰隼锋爪", "可镶嵌于法宝以增加速度。", value_qi=150))
_add(Item("item_eagle_eye", "鹰眼晶", "material", 3, "👁️",
          "鹰王体内凝结的目力之晶", "镶嵌后大幅提升暴击。", value_qi=180))
_add(Item("item_thunder_core", "雷击核", "material", 3, "⚡",
          "雷击鹰体内的雷元素核", "可炼制雷系法宝。", value_qi=200))
_add(Item("item_herb_basic", "凡品草药", "material", 1, "🌿",
          "山间常见灵草", "炼制基础丹药的原料。", value_qi=5))
_add(Item("item_herb_mid", "灵品草药", "material", 2, "🌱",
          "已成精怪的草药", "比凡品功效十倍。", value_qi=50))
_add(Item("item_herb_high", "千年灵药", "material", 4, "🍀",
          "千年以上的稀世灵药", "可延寿百年,可炼仙品丹药。", value_qi=1000))
_add(Item("item_ghost_essence", "阴煞", "material", 2, "👻",
          "鬼族凝结的阴气", "可制鬼修法宝,凡修需小心驾驭。", value_qi=70))
_add(Item("item_dragon_scale", "龙鳞", "material", 4, "🐉",
          "龙族脱落的鳞片", "坚不可摧,顶级护甲材料。", value_qi=2000))
_add(Item("item_dragon_essence", "龙髓", "material", 5, "💧",
          "龙族体内的元髓", "极其稀有,可炼仙品法宝。", value_qi=8000))
_add(Item("item_phoenix_feather", "凤凰真翎", "material", 5, "🔥",
          "正神朱雀脱落的羽", "千年才出一根,炼制焚天法宝。", value_qi=10000))
_add(Item("item_xuanwu_shell", "玄武甲片", "material", 5, "🛡️",
          "玄武正神的龟甲", "无坚不摧,顶级护甲材料。", value_qi=9000))
_add(Item("item_baihu_claw", "白虎尖牙", "material", 5, "🦷",
          "白虎正神的尖牙", "可斩开任何护甲。", value_qi=9500))
_add(Item("item_qinglong_horn", "青龙之角", "material", 5, "🦌",
          "青龙正神的角", "蕴含东方木气,生机无限。", value_qi=10500))
_add(Item("item_ancient_horn", "凶兽之角", "material", 4, "👹",
          "上古凶兽的犄角", "蕴含远古之力。", value_qi=2500))
_add(Item("item_demon_blood", "魔血", "material", 3, "🩸",
          "魔修身上凝聚的污血", "邪修最爱的炼宝材料。", value_qi=400))
_add(Item("item_alien_essence", "异界精华", "material", 5, "🌌",
          "异域生灵的本源", "其规律不属于本界,极难驾驭。", value_qi=12000))
_add(Item("item_starlight", "星辉粉", "material", 6, "⭐",
          "上古星辰陨落后的粉末", "传说中的炼器至宝。", value_qi=30000))
_add(Item("item_charm_doll", "媚术符纸", "material", 2, "📜",
          "妖修使用的迷魂符", "贴身佩戴有惑心之效,凡修慎用。", value_qi=120))
_add(Item("item_yaodan", "妖丹", "material", 3, "🟡",
          "妖修体内的内丹", "凝聚一身修为之精华,炼丹最佳原料。", value_qi=500))


# ============ 丹药(consumable)============
_add(Item("item_focus_pill", "凝神丹", "consumable", 1, "💊",
          "凝聚心神的基础丹药", "战斗中服下可清明心神,炼气期专属。",
          use_effect={"qi_percent": 12, "qi_min": 100}, value_qi=30))
_add(Item("item_lingdan_basic", "灵元丹", "consumable", 2, "💊",
          "恢复灵气的丹药", "服下立刻恢复 200 点灵气。",
          use_effect={"qi_percent": 25, "qi_min": 250}, value_qi=100))
_add(Item("item_lingdan_mid", "回元丹", "consumable", 3, "💊",
          "恢复 HP 与 灵气", "战斗中救命之物。",
          use_effect={"hp_percent": 30, "qi_percent": 25, "qi_min": 300}, value_qi=350))
_add(Item("item_pill_breakthrough", "破境丹", "consumable", 4, "🟠",
          "助修士突破境界", "服下后渡劫成功率 +30%。",
          use_effect={"breakthrough_bonus": 0.3}, value_qi=2000))
_add(Item("item_pill_immortal", "九转金丹", "consumable", 5, "🟡",
          "传说中的太上老君九转金丹", "服下可立刻提升一个境界(限制条件多)。",
          use_effect={"breakthrough_bonus": 1.0}, value_qi=15000))


# ============ 法宝(equipment)============
_add(Item("item_storm_blade", "风暴之刃", "equipment", 4, "🌪️",
          "风暴宗米斯特拉的传家剑", "持有时攻击 +120,速度 +20。",
          equip_stats={"atk": 120, "spd": 20}, value_qi=5000))
_add(Item("item_void_blade", "虚无之刃", "equipment", 5, "🌌",
          "玄道魔主的剑,能撕裂空间", "持有时攻击 +250,暴击 +15%。",
          equip_stats={"atk": 250, "crit_rate": 0.15}, value_qi=25000))
_add(Item("item_baichuan_sword", "百川剑", "equipment", 4, "🌊",
          "百川海主所铸,可吸纳百派之长", "持有时攻击 +130,灵气 +200。",
          equip_stats={"atk": 130, "qi_max": 200}, value_qi=6500))
_add(Item("item_step_ladder", "阶星阶梯", "equipment", 4, "🪜",
          "阶星阁的传承法宝", "每场战斗每回合 +5% ATK(累计)。",
          equip_stats={"atk_per_round": 0.05}, value_qi=5500))
_add(Item("item_lpu_chip", "极速天枢核", "equipment", 4, "⚡",
          "极速门铸造的核心法宝", "持有时速度 +50,攻速 +30%。",
          equip_stats={"spd": 50, "atk_speed": 0.3}, value_qi=7000))
_add(Item("item_mask_thousand", "千面之面", "equipment", 4, "🎭",
          "千面殿之主的本命面具", "每次战斗可化为敌人形态一次。",
          equip_stats={"clone_enemy": 1}, value_qi=6000))
_add(Item("item_brush_of_dream", "梦笔", "equipment", 4, "🖌️",
          "持心门稳心圣女的法宝", "持有时使敌人 evasion -10%。",
          equip_stats={"enemy_evasion": -0.1}, value_qi=5800))
_add(Item("item_trace_compass", "索踪罗盘", "equipment", 3, "🧭",
          "迷踪派的法宝", "战斗前可查看敌人 1 项属性。",
          equip_stats={"inspect": 1}, value_qi=2200))
_add(Item("item_empathy_jade", "共情玉", "equipment", 3, "💚",
          "转折宫的本命法宝", "受击时 30% 几率反治疗 20%。",
          equip_stats={"counter_heal": 0.3}, value_qi=2500))
_add(Item("item_open_secret_scroll", "开源秘卷", "treasure", 4, "📜",
          "拥抱观至宝", "持有时可使用任何门派的卡牌(实验性)。",
          equip_stats={"cross_sect_cards": 1}, value_qi=8000))
_add(Item("item_dragon_essence_pearl", "龙髓珠", "equipment", 5, "🟢",
          "炼自龙髓的珠子", "持有时灵气恢复速度 +50%。",
          equip_stats={"qi_regen": 0.5}, value_qi=18000))


# ============ 心法(skill_book)============
_add(Item("item_canglan_book", "沧澜剑诀·初", "skill_book", 2, "📕",
          "沧澜剑派入门心法", "学习后解锁'剑诀·初'招式。",
          use_effect={"unlock_card": "canglan_init"}, value_qi=300))
_add(Item("item_canglan_book2", "沧澜九式残卷", "skill_book", 4, "📕",
          "沧澜九式的残篇", "学习后解锁'沧澜九式'招式。",
          use_effect={"unlock_card": "canglan_nine"}, value_qi=4000))
_add(Item("item_tianji_book", "天机机关诀", "skill_book", 2, "📘",
          "天机阁机关入门", "学习后解锁'机关连发'。",
          use_effect={"unlock_card": "tianji_gear"}, value_qi=300))


# ============ 灵宝(treasure 稀有)============
_add(Item("item_void_essence", "虚空之核", "treasure", 6, "🌑",
          "界外神祇的本源", "最终 Boss 掉落,可重铸天道。", value_qi=100000))
_add(Item("item_gear_core", "万象齿轮", "treasure", 5, "⚙️",
          "天机阁山主独有", "镶嵌后所有攻击触发连击。", value_qi=22000))
_add(Item("item_replicate_key", "衍化钥匙", "treasure", 4, "🗝️",
          "衍化盟的标志", "可复制本场战斗中敌人 1 项属性。", value_qi=6000))
_add(Item("item_ship_sail", "同舟之帆", "treasure", 4, "⛵",
          "同舟会的法宝", "组队时全队属性 +10%。", value_qi=5500))
_add(Item("item_sensing_eye", "千眼之珠", "treasure", 4, "👁️",
          "商汤殿的至宝", "永久看见所有敌人属性。", value_qi=7500))
_add(Item("item_micro_essence", "微观之精", "treasure", 4, "🔬",
          "微极派的炼制成果", "持有时小怪伤害翻倍。", value_qi=5000))


# ════════════════════════════════════════════════════════════
# ★ 补全:炼丹/法宝配方的产物物品(原 recipes.py 引用了但未注册)
# ════════════════════════════════════════════════════════════
# ── 丹药 ──
_add(Item("item_antidote", "解毒丸", "consumable", 1, "💊",
          "化解蛇蟒余毒的小药丸", "服下立即清除中毒状态,恢复 80 HP。",
          use_effect={"clear_poison": True, "hp": 80}, value_qi=40))
_add(Item("item_iron_pill", "铁骨丹", "consumable", 2, "💊",
          "猛兽皮淬炼的护体丹", "战前服下,该场战斗防御 +15%。",
          use_effect={"def_buff_pct": 0.15, "duration_battles": 1}, value_qi=150))
_add(Item("item_crit_pill", "灵犀丹", "consumable", 2, "💊",
          "灵雀羽与凝神丹合炼", "战前服下,该场战斗暴击率 +10%。",
          use_effect={"crit_buff": 0.10, "duration_battles": 1}, value_qi=180))
_add(Item("item_speed_pill", "疾风散", "consumable", 3, "💨",
          "灵雀疾爪炼成的速度药", "战前服下,该场战斗速度 +20%。",
          use_effect={"spd_buff_pct": 0.20, "duration_battles": 1}, value_qi=300))
_add(Item("item_lingdan_high", "上品回春丹", "consumable", 4, "💊",
          "高阶丹药,瞬间回满气血", "服下立即恢复 100% HP。",
          use_effect={"hp_percent": 100}, value_qi=1200))

# ── 法宝(equipment) ──
_add(Item("item_fox_charm", "狐尾护符", "equipment", 2, "🦊",
          "九尾狐妖之尾骨为引,佐以媚术符纸炼成", "佩戴时闪避率 +5%。",
          equip_stats={"evasion": 0.05}, value_qi=400))
_add(Item("item_eagle_goggles", "鹰眼护目镜", "equipment", 3, "🦅",
          "金喙隼瞳孔炼制,可洞察战机", "佩戴时暴击率 +8%。",
          equip_stats={"crit_rate": 0.08}, value_qi=800))
_add(Item("item_serpent_armor", "蛇鳞甲", "equipment", 3, "🐍",
          "白蟒精脱下的整片鳞甲", "佩戴时防御 +12%、HP +50。",
          equip_stats={"def_pct": 0.12, "hp": 50}, value_qi=1500))
_add(Item("item_dragon_staff", "龙骨杖", "equipment", 4, "🐲",
          "应龙骨炼成,杖端凝结上古角", "佩戴时法术伤害 +15%、灵气 +200。",
          equip_stats={"magic_dmg_pct": 0.15, "qi_max": 200}, value_qi=4000))
_add(Item("item_phoenix_fan", "凤凰羽扇", "equipment", 5, "🦚",
          "凤凰涅槃残羽 × 龙髓 × 星辉粉合炼,扇风可焚劫云", "佩戴时全属性 +10%。",
          equip_stats={"all_stats_pct": 0.10}, value_qi=12000))


# ════════════════════════════════════════════════════════════
# ★ Round 1: 招式心得 — 用于升级技能 (Lv1→2 / 2→3 / 3→4 / 4→5)
# ════════════════════════════════════════════════════════════
_add(Item("item_skill_essence_basic", "招式心得·初", "material", 2, "📖",
          "初阶招式领悟之精华", "升级 Lv1 → Lv2 招式需要 1 个。", value_qi=80))
_add(Item("item_skill_essence_mid", "招式心得·中", "material", 3, "📘",
          "中阶招式领悟之精华", "升级 Lv2 → Lv3 招式需要 2 个。", value_qi=300))
_add(Item("item_skill_essence_high", "招式心得·高", "material", 4, "📗",
          "高阶招式领悟之精华", "升级 Lv3 → Lv4 招式需要 3 个。", value_qi=1000))
_add(Item("item_skill_essence_supreme", "招式心得·绝", "material", 5, "📕",
          "绝阶招式领悟之精华", "升级 Lv4 → Lv5 招式需要 5 个。", value_qi=4000))
_add(Item("item_skill_codex_universal", "通用秘籍", "material", 4, "📜",
          "可跨派学习招式的秘籍", "向 NPC 求教时消耗,学到一招跨派招式。", value_qi=2000))


def get_item(item_id: str):
    return ITEMS.get(item_id)


def item_icon_url(item_id: str) -> str:
    return f"{ITEM_ICON_BASE}/{item_id}.png"


def item_to_dict(item: Item) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "type": item.type,
        "rarity": item.rarity,
        "rarity_name": RARITY_NAMES.get(item.rarity, "?"),
        "icon": item.icon,
        "icon_url": item_icon_url(item.id),
        "description": item.description,
        "lore": item.lore,
        "use_effect": item.use_effect,
        "equip_stats": item.equip_stats,
        "value_qi": item.value_qi,
    }


def list_all_items():
    return list(ITEMS.values())
