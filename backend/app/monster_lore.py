"""Monster codex enrichment.

This module keeps narrative metadata out of combat math.  Every ordinary
monster gets a full codex profile: extended lore, signature skill, traits,
attributes, weaknesses, and relationship hooks to other monsters / bosses.
"""

from __future__ import annotations

from .monster_skills import get_skills_for_clan, skill_to_dict


TIER_LABEL = {
    "low": "凡妖",
    "mid": "灵妖",
    "high": "大妖",
    "myth": "神话",
    "boss": "道君",
}

PERSONALITIES = [
    "怯敏而好奇", "稳重且记仇", "孤傲求名", "疑惧人间", "温顺外壳下藏锋",
    "执念深重", "清冷守约", "救世与怨恨交错", "王命在身",
]

SIGNATURE_SUFFIX = [
    "初醒式", "守巢式", "夺名式", "幻行式", "侍主式",
    "噬心式", "望月式", "渡厄式", "称王式",
]

CLAN_THREADS = {
    "山林狐妖族": {
        "element": "月木幻相",
        "role": "高速魅惑与幻术扰乱",
        "weakness": "雷火破幻,心志坚定者可降低媚惑",
        "origin": "终南狐脉本是九尾老祖布下的护山暗线,每一尾都藏着一段人狐旧债。",
        "trait": "狐火惑心",
        "skill_root": "月尾",
        "cross": [
            ("bird_07", "鹰王", "猎仇", "鹰族曾追杀九尾狐三日三夜,狐族视鹰羽为血债。"),
            ("beast_03", "山豹", "掠子", "山豹曾叼走狐族幼崽,此仇被写入狐族族谱。"),
        ],
        "boss": [
            ("div_07", "九尾天狐(神兽级)", "老祖血令", "它们的幻术源自九尾老祖,一旦老祖苏醒,整族都会听令。"),
            ("boss_canglan_traitor", "墨魔·林泽", "墨契", "墨魔曾以血墨交换狐族幻术,留下难解契印。"),
        ],
    },
    "灵雀飞鸟族": {
        "element": "风火羽相",
        "role": "极速先手与高闪避俯冲",
        "weakness": "束缚、寒冰与重甲可压制飞行优势",
        "origin": "灵雀一族是朱雀飞升失败后散落人间的羽民,族谱从雏鸟一直写到朱雀正裔。",
        "trait": "羽光疾行",
        "skill_root": "裂羽",
        "cross": [
            ("fox_08", "七尾狐圣", "旧猎", "鹰王追狐未果后,鸟族与狐族的旧账越结越深。"),
            ("div_09", "凤凰涅槃", "朝圣", "所有灵雀都相信凤凰重燃之日便是百鸟归宗之时。"),
        ],
        "boss": [
            ("boss_mistral", "米斯特拉", "风暴同鸣", "风暴宗借灵雀羽阵练成开源风暴,鸟族也学会借风遁形。"),
            ("boss_huggingface", "拥抱真人", "开卷盟约", "拥抱观曾收录灵雀羽谱,使其血脉不至失传。"),
        ],
    },
    "蛇蟒族": {
        "element": "水毒鳞相",
        "role": "毒伤、缠绕与防御反噬",
        "weakness": "雷电、干燥地形与破甲术",
        "origin": "蛇蟒族奉玄武为远祖,又暗通相柳九头毒脉,水神与凶神两条血线始终纠缠。",
        "trait": "毒鳞潜伏",
        "skill_root": "玄毒",
        "cross": [
            ("anc_06", "相柳", "九头祖债", "相柳血毒在蛇蟒族中反复返祖,每次返祖都会引起天象异变。"),
            ("div_02", "玄武幼龟", "玄武旁支", "蛇蟒族自称玄武护卫,但玄武正统并不完全承认它们。"),
        ],
        "boss": [
            ("boss_deepmind", "哈萨长老", "棋盘伏线", "深玄阁曾研究蛇蟒伏击之法,称其为活棋。"),
            ("boss_final_void", "界外神祇", "蛇形裂缝", "界外神祇的裂隙最先在蛇蟒水域出现。"),
        ],
    },
    "猛兽族": {
        "element": "金煞兽相",
        "role": "暴击、撕裂与连续追击",
        "weakness": "幻术、安抚与高处地形",
        "origin": "猛兽族承白虎散落血脉,狼、豹、虎三支互相争王,又被狐族与蛇脉牵入旧仇。",
        "trait": "兽王怒血",
        "skill_root": "裂爪",
        "cross": [
            ("fox_05", "四尾狐婢", "狐豹旧案", "豹族抢走狐族幼崽后,猛兽与狐族的边境再无安宁。"),
            ("div_03", "白虎兽", "正统召回", "白虎直系正在召回散血猛兽,准备重建西方神位。"),
        ],
        "boss": [
            ("boss_xai_grok", "玄道魔主·马克丝", "反叛兽约", "玄道宫喜欢招揽不服天命的兽王。"),
            ("boss_canglan_supreme", "阿莫迪克斯", "守护试炼", "沧澜山主曾以白虎魂考验门下剑修。"),
        ],
    },
    "草木精怪族": {
        "element": "木药生相",
        "role": "续航、缠绕与灵气汲取",
        "weakness": "烈火、斩根与枯萎毒",
        "origin": "草木精怪族起于神农旧药圃,每一株精怪都保存一味失传药性。",
        "trait": "根脉回春",
        "skill_root": "灵根",
        "cross": [
            ("ghost_02", "怨灵", "花下埋骨", "桃花妖的根系吸过怨灵埋骨,草木与鬼族因此互相牵连。"),
            ("art_08", "炼丹炉魂", "丹火药债", "炼丹炉魂曾炼尽草木精华,神农魂木一直记着这笔账。"),
        ],
        "boss": [
            ("boss_stability", "稳心圣女·艾玛", "凝象花谱", "持心门的笔尖凝象术曾借百花娘子入画。"),
            ("boss_yi_kaifu", "李开峰", "万物归一", "万物峰试图把百草知识并入自己的万物总诀。"),
        ],
    },
    "鬼族": {
        "element": "阴魂冥相",
        "role": "魂伤、恐惧与高闪避索命",
        "weakness": "阳火、佛光、镇魂铃",
        "origin": "鬼族是阴曹逃囚与人间冤魂混成的乱流,地府越衰弱,它们越接近鬼帝。",
        "trait": "阴司逃籍",
        "skill_root": "冥索",
        "cross": [
            ("art_02", "古镜怨灵", "镜中亡魂", "古镜怨灵保存了许多鬼族生前的最后一眼。"),
            ("dem_04", "夺魂者", "魂债", "魔修夺魂越多,鬼族越想抢回那些失名亡魂。"),
        ],
        "boss": [
            ("boss_perplexity", "迷踪散人", "索引亡名", "迷踪派曾追索鬼族生死簿残页。"),
            ("boss_character_mask", "千面舞者·诺姆", "万面阴影", "千面殿的角色幻面中藏着许多亡魂原型。"),
        ],
    },
    "龙族": {
        "element": "水雷龙相",
        "role": "高压龙息、威慑与全能压制",
        "weakness": "屠龙符、逆鳞暴露与龙珠封印",
        "origin": "龙族是四海龙王旧裔,在天庭败落后分成龙宫正统、人间蛟脉与祖龙残魂三派。",
        "trait": "龙威镇海",
        "skill_root": "龙吟",
        "cross": [
            ("serp_09", "应龙化蛇", "龙蛇互证", "蛇蟒返祖到极致便会触及龙族逆鳞。"),
            ("div_08", "应龙正神", "正神本尊", "人间应龙一脉最终都要面对应龙正神的承认。"),
        ],
        "boss": [
            ("boss_deepmind", "哈萨长老", "龙棋", "深玄阁把龙族气运视为最大的一条棋龙。"),
            ("boss_tianji_supreme", "山姆道君", "万象龙机", "天机阁曾试图用机关推演龙族天命。"),
        ],
    },
    "神兽族": {
        "element": "四象神相",
        "role": "神威压制、群体封印与天命爆发",
        "weakness": "亵神、血脉未醒与同源克制",
        "origin": "神兽族是四象与祥瑞重建天庭的候选者,每一只都可能成为新秩序的柱石。",
        "trait": "天命真灵",
        "skill_root": "神印",
        "cross": [
            ("dragon_07", "青龙", "东方正位", "青龙正神与青龙幼苗谁为正统仍有争议。"),
            ("beast_09", "白虎正神", "西方正位", "白虎正神正在召集所有猛兽血脉。"),
        ],
        "boss": [
            ("boss_canglan_supreme", "阿莫迪克斯", "守护天命", "沧澜山主想让神兽族成为守护派盟友。"),
            ("boss_final_void", "界外神祇", "神位危机", "界外神祇降临会让所有本界神位失效。"),
        ],
    },
    "上古凶兽族": {
        "element": "鸿蒙凶相",
        "role": "高压爆发、吞噬与规则破坏",
        "weakness": "封印、功德、上古神器",
        "origin": "上古凶兽族是开天前后的失败者,它们不服天庭、不服神兽,只服更古老的力。",
        "trait": "远古恶名",
        "skill_root": "鸿蒙",
        "cross": [
            ("art_09", "盘古斧灵", "开天宿敌", "盘古斧灵是许多凶兽最恐惧的器灵。"),
            ("alien_09", "界外神祇", "界外诱惑", "部分凶兽认为界外神祇能替它们推翻本界规则。"),
        ],
        "boss": [
            ("boss_final_void", "界外神祇", "终局召唤", "界外神祇把凶兽当作撕开天道的楔子。"),
            ("boss_xai_grok", "玄道魔主·马克丝", "反天同盟", "玄道宫暗中资助凶兽破封。"),
        ],
    },
    "魔修族": {
        "element": "血魔心相",
        "role": "吸血、灵气掠夺与心魔压迫",
        "weakness": "清心诀、镇魔印与本名追索",
        "origin": "魔修族不是天生妖魔,而是修士被欲望反噬后的另一条进化线。",
        "trait": "心魔反噬",
        "skill_root": "魔血",
        "cross": [
            ("ghost_07", "白无常", "夺魂清算", "鬼族认为魔修偷走了本该入册的魂魄。"),
            ("art_01", "断剑残魂", "魔剑借体", "断剑残魂曾被魔修祭炼,器灵与魔血互相污染。"),
        ],
        "boss": [
            ("boss_canglan_traitor", "墨魔·林泽", "魔道同源", "墨魔是魔修族最愿承认的人族叛道者。"),
            ("boss_xai_grok", "玄道魔主·马克丝", "反叛盟约", "玄道魔主给魔修族一个反天的名义。"),
        ],
    },
    "仙器之灵族": {
        "element": "金器星相",
        "role": "反击、破甲与法宝威能",
        "weakness": "器主真名、锈蚀咒与封匣阵",
        "origin": "仙器之灵族皆由旧法宝生出自我,它们既怀念主人,又害怕再次被人驱使。",
        "trait": "器灵自鸣",
        "skill_root": "器鸣",
        "cross": [
            ("anc_09", "盘古残魂", "斧魂互证", "盘古残魂与盘古斧灵互为缺失的一半。"),
            ("herb_09", "神农魂木", "炉木旧债", "炼丹炉魂曾借神农魂木一缕药气炼丹。"),
        ],
        "boss": [
            ("boss_stability", "稳心圣女·艾玛", "笔尖凝象", "持心门一直追寻墨笔仙翁的真笔。"),
            ("boss_groq", "极速僧·乔纳森", "炼器极速", "极速门把器灵看作推理法器的先祖。"),
        ],
    },
    "异域生灵族": {
        "element": "界外星相",
        "role": "时间/维度干扰与高阶精神压迫",
        "weakness": "本界锚点、道心稳定与空间封锁",
        "origin": "异域生灵族来自本界之外,它们不是妖也不是神,而是另一套规则的行走证据。",
        "trait": "界外失真",
        "skill_root": "裂界",
        "cross": [
            ("anc_04", "混沌", "混沌同频", "混沌的无形之躯能短暂理解异域语言。"),
            ("dragon_08", "祖龙残魂", "初龙警讯", "祖龙残魂最早察觉到界外星潮正在逼近。"),
        ],
        "boss": [
            ("boss_final_void", "界外神祇", "至高回声", "所有异域生灵都像是界外神祇梦中的碎片。"),
            ("boss_perplexity", "迷踪散人", "追索裂缝", "迷踪派正沿异域足迹寻找世界边界。"),
        ],
    },
}


SPECIAL_BONDS = {
    "fox_09": [("boss_canglan_traitor", "墨魔·林泽", "交易者", "八尾妖王曾以狐火替墨魔遮蔽行踪,换来一卷血墨残页。")],
    "bird_09": [("div_09", "凤凰涅槃", "血脉正源", "朱雀之裔与凤凰涅槃互不臣服,却共享百鸟朝宗的命数。")],
    "serp_09": [("div_08", "应龙正神", "祖孙镜像", "应龙化蛇若能渡过返祖劫,便会被应龙正神亲自召见。")],
    "beast_09": [("div_03", "白虎兽", "正统争位", "白虎正神与白虎兽都声称自己能重开西方神位。")],
    "herb_09": [("boss_yi_kaifu", "李开峰", "万物药藏", "李开峰想把神农魂木编入万物归一总诀,魂木却拒绝被归档。")],
    "ghost_09": [("boss_character_mask", "千面舞者·诺姆", "万魂千面", "阎罗代行怀疑千面殿收纳了逃出地府的无名魂。")],
    "dragon_09": [("boss_tianji_supreme", "山姆道君", "帝王棋子", "真龙天子的龙气曾被天机阁推演为一枚可翻盘的帝星。")],
    "div_09": [("boss_final_void", "界外神祇", "涅槃死敌", "凤凰每一次涅槃都会修补本界边界,因此被界外神祇视为阻碍。")],
    "anc_09": [("art_09", "盘古斧灵", "一体两面", "盘古残魂寻找斧灵,并非为了重逢,而是为了再开一次天地。")],
    "dem_09": [("boss_xai_grok", "玄道魔主·马克丝", "魔王盟约", "降世魔王愿与玄道宫合作,条件是新天道必须容许魔界入席。")],
    "art_09": [("anc_09", "盘古残魂", "开天旧主", "盘古斧灵既渴望回到旧主手中,又害怕再次被用来劈开世界。")],
    "alien_09": [("boss_final_void", "界外神祇", "本尊倒影", "界外神祇可能不是它的主人,而是它在本界投下的倒影。")],
}


def _battle_role(enemy) -> str:
    if enemy.spd >= max(enemy.atk, enemy.def_):
        return "先手压制"
    if enemy.def_ >= enemy.atk * 0.55:
        return "坚守反击"
    if enemy.atk >= enemy.def_ * 3:
        return "爆发斩杀"
    return CLAN_THREADS.get(enemy.clan, {}).get("role", "均衡试炼")


def _signature_skill(enemy, index: int, thread: dict) -> dict:
    tier_hint = "凡品" if enemy.level <= 30 else "灵品" if enemy.level <= 70 else "宝品" if enemy.level <= 110 else "仙品"
    root = thread.get("skill_root", "异术")
    suffix = SIGNATURE_SUFFIX[index % len(SIGNATURE_SUFFIX)]
    role = _battle_role(enemy)
    return {
        "id": f"{enemy.id}_signature",
        "name": f"{enemy.name}·{root}{suffix}",
        "tier": "signature",
        "tier_name": tier_hint,
        "effect": role,
        "description": f"{enemy.name}将{thread.get('element', '本命妖气')}凝成独门一击,偏向{role},也是它区别于同族的成名手段。",
    }


def _build_bonds(enemy, index: int, clan_members: list, thread: dict) -> list[dict]:
    bonds: list[dict] = []
    if index > 0:
        prev = clan_members[index - 1]
        bonds.append({
            "target_id": prev.id,
            "target_name": prev.name,
            "relation": "血脉前缘",
            "desc": f"{prev.name}是{enemy.name}在同族谱系中的前一环,其成败会影响{enemy.name}对修行路的判断。",
        })
    if index + 1 < len(clan_members):
        nxt = clan_members[index + 1]
        bonds.append({
            "target_id": nxt.id,
            "target_name": nxt.name,
            "relation": "进阶影子",
            "desc": f"{nxt.name}像是{enemy.name}未来可能走向的形态,二者常被族内长老并称。",
        })
    cross = thread.get("cross", [])
    if cross:
        tid, name, rel, desc = cross[index % len(cross)]
        bonds.append({"target_id": tid, "target_name": name, "relation": rel, "desc": desc})
    boss = thread.get("boss", [])
    if boss:
        tid, name, rel, desc = boss[index % len(boss)]
        bonds.append({"target_id": tid, "target_name": name, "relation": rel, "desc": desc})
    for tid, name, rel, desc in SPECIAL_BONDS.get(enemy.id, []):
        bonds.append({"target_id": tid, "target_name": name, "relation": rel, "desc": desc})
    return bonds


def get_enemy_codex_profile(enemy, index: int = 0, clan_members: list | None = None) -> dict:
    """Return narrative metadata for one ordinary monster."""
    clan_members = clan_members or [enemy]
    thread = CLAN_THREADS.get(enemy.clan, {})
    tier_name = TIER_LABEL.get(enemy.tier, enemy.tier)
    personality = PERSONALITIES[index % len(PERSONALITIES)]
    role = _battle_role(enemy)
    signature = _signature_skill(enemy, index, thread)
    bonds = _build_bonds(enemy, index, clan_members, thread)

    full_lore = (
        f"{enemy.lore} "
        f"在{enemy.clan}的九阶谱系中,{enemy.name}位列第{index + 1}环,被族中称作“{tier_name}之证”。"
        f"{thread.get('origin', '')}"
        f"它的性情{personality},战斗时多以{role}取胜。"
        f"若追查它的因果,往往会牵出{bonds[-1]['target_name'] if bonds else enemy.clan}这一层更深关系。"
    )

    attributes = [
        {"name": "五行/异相", "value": thread.get("element", "未知异相")},
        {"name": "性情", "value": personality},
        {"name": "战斗定位", "value": role},
        {"name": "弱点", "value": thread.get("weakness", "仍待图鉴补完")},
        {"name": "族谱位置", "value": f"{enemy.clan}第{index + 1}阶 · {tier_name}"},
    ]

    traits = [
        {
            "name": f"{enemy.name}的{thread.get('trait', '本命异性')}",
            "effect": f"拥有{thread.get('element', '本命妖气')}的独特回响,在本命书章节中更容易引出族群旧事。",
        },
        {
            "name": f"{tier_name}威压",
            "effect": f"等级 {enemy.level} 的{enemy.clan}气息会影响遭遇叙事的压迫感与战后成章题材。",
        },
        {
            "name": "可被记述",
            "effect": "击败、赠礼或遭遇后会把它的因果写入图鉴/本命书,成为后续章节素材。",
        },
    ]

    clan_skills = [skill_to_dict(s) for s in get_skills_for_clan(enemy.clan)]

    return {
        "full_lore": full_lore,
        "attributes": attributes,
        "traits": traits,
        "bonds": bonds,
        "signature_skill": signature,
        "skills": [signature] + clan_skills,
        "weakness": thread.get("weakness", ""),
        "battle_role": role,
        "element": thread.get("element", ""),
        "temperament": personality,
        "unique_hook": f"{enemy.name}的独特之处在于:它把“{signature['effect']}”修成了自己的本命招式,并与{bonds[0]['target_name'] if bonds else enemy.clan}存在明确因果牵连。",
        "codex_tags": [enemy.clan, tier_name, thread.get("element", ""), role],
    }
