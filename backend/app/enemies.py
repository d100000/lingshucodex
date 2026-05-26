"""怪物大全 — 108 普通怪 + 22 Boss

设计思路:
- 12 族 × 9 等级阶段 = 108 普通怪物,同族有血缘羁绊
- 每族对应一个境界范围,等级越高怪物越凶
- 怪物有完整背景故事,族间存在食物链 / 师承 / 前世今生

Boss 单独在 bosses.py 中定义。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from .combat_balance import balanced_enemy_stats
from .monster_lore import get_enemy_codex_profile
from .drop_rules import SKILL_DROP_ITEM_IDS, skill_drop_item_for_enemy

@dataclass
class Enemy:
    id: str
    name: str
    clan: str          # 族群
    tier: str          # low / mid / high / myth / boss
    level: int         # 推荐挑战等级
    hp: int
    atk: int
    def_: int
    spd: int
    evasion: float
    rewards_exp: int
    rewards_qi: int
    image_emoji: str
    description: str   # 简短卡片介绍
    lore: str          # 完整背景故事
    drops: list = field(default_factory=list)  # 掉落表项 id
    image_url: str = ""  # 怪物绘画头像 URL(有则前端显示图片,无则 fallback 到 emoji)


# ========================================================================
# 族 1 · 山林狐妖族(炼气期)
# 设定:终南山一支千年狐家族,九尾老祖隐居,后代渐入凡尘
# ========================================================================
CLAN_FOX = [
    Enemy("fox_01", "山林小狐", "山林狐妖族", "low", 3,
          80, 12, 4, 90, 0.10, 30, 15, "🦊",
          "初通灵性的小狐狸,贪玩好奇。",
          "出生于终南后山,母亲早逝。常潜入村庄偷食,被农人厌恶又无奈。",
          ["item_fur_white", "item_qi_dust"]),
    Enemy("fox_02", "石板狐", "山林狐妖族", "low", 6,
          130, 16, 6, 95, 0.12, 50, 25, "🦊",
          "经常在石板上晒太阳的成年狐妖。",
          "山林小狐的同窝兄弟,性格稳重。曾被一位道士点化,识得部分人言。",
          ["item_fur_white", "item_focus_pill"]),
    Enemy("fox_03", "双尾赤狐", "山林狐妖族", "low", 10,
          200, 22, 8, 100, 0.13, 80, 40, "🦊",
          "妖力凝聚出第二条尾巴的赤色狐妖。",
          "终南狐族百年才出一只双尾。它认为自己注定要继承祖业,孤傲不群。",
          ["item_fur_red", "item_focus_pill"]),
    Enemy("fox_04", "三尾灵狐", "山林狐妖族", "mid", 16,
          400, 32, 12, 105, 0.15, 160, 80, "🦊",
          "已成形的三尾灵狐,会简单幻术。",
          "曾化作人形混入凡间集市,差点被发现而险些丧命。从此对人间又惧又恨。",
          ["item_fur_red", "item_lingdan_basic"]),
    Enemy("fox_05", "四尾狐婢", "山林狐妖族", "mid", 22,
          700, 50, 18, 110, 0.16, 280, 140, "🦊",
          "九尾老祖座下侍婢,姿色绝丽。",
          "本是凡间女子,被九尾老祖救下后甘愿献身侍奉百年,渐渐化为狐形。",
          ["item_fur_red", "item_lingdan_basic", "item_charm_doll"]),
    Enemy("fox_06", "五尾媚妖", "山林狐妖族", "mid", 30,
          1300, 75, 26, 115, 0.18, 500, 260, "🦊",
          "擅以媚术控人心智的妖修。",
          "为了报复对它始乱终弃的书生,凝五尾入魔。书生终身被她梦魇缠身。",
          ["item_fur_red", "item_charm_doll", "item_yaodan"]),
    Enemy("fox_07", "六尾天狐", "山林狐妖族", "high", 42,
          3000, 120, 40, 120, 0.20, 1200, 600, "🦊",
          "六尾接通灵脉,通晓阴阳。",
          "九尾老祖的亲传弟子,性格清冷。常在月圆之夜独坐山巅,似在等待什么。",
          ["item_fur_gold", "item_yaodan", "item_lingdan_mid"]),
    Enemy("fox_08", "七尾狐圣", "山林狐妖族", "high", 60,
          7500, 200, 65, 125, 0.22, 3000, 1500, "🦊",
          "已悟得圣道的七尾,法力非凡。",
          "曾化形济世三百年,救苦救难。然功成之日,却被人类背叛险些化为皮草。",
          ["item_fur_gold", "item_yaodan", "item_pill_breakthrough"]),
    Enemy("fox_09", "八尾妖王", "山林狐妖族", "myth", 80,
          18000, 350, 100, 130, 0.24, 8000, 4000, "🦊",
          "距九尾仅一步之遥的妖王。",
          "九尾老祖的长女,继任已定。准备最后一次渡劫飞升,届时狐族将易主。",
          ["item_fur_gold", "item_yaodan", "item_dragon_scale"]),
]

# ========================================================================
# 族 2 · 灵雀飞鸟族(炼气-筑基)
# 设定:朱雀血脉旁支,曾辅佐凤凰飞升,失败后陨落人间
# ========================================================================
CLAN_BIRD = [
    Enemy("bird_01", "小灵雀", "灵雀飞鸟族", "low", 4,
          70, 14, 3, 130, 0.20, 35, 18, "🐦",
          "羽翼有花纹的小鸟,速度极快。",
          "灵雀族最低阶的雏鸟,刚学会飞。母亲是一只死于猎鹰之爪的灵雀。",
          ["item_feather_white", "item_qi_dust"]),
    Enemy("bird_02", "彩翎雀", "灵雀飞鸟族", "low", 8,
          120, 19, 5, 135, 0.22, 60, 30, "🐦",
          "羽毛在阳光下变幻七色。",
          "群体觅食的彩翎雀,常成百上千聚集,蔚为壮观。",
          ["item_feather_white", "item_focus_pill"]),
    Enemy("bird_03", "金喙隼", "灵雀飞鸟族", "low", 12,
          200, 28, 7, 140, 0.24, 100, 50, "🦅",
          "喙坚硬如金,捕食小兽。",
          "山顶猎鹰族的首领,曾啄瞎一位修士的眼睛而被悬赏。",
          ["item_feather_white", "item_focus_pill", "item_eagle_eye"]),
    Enemy("bird_04", "幻翼蝶", "灵雀飞鸟族", "mid", 18,
          380, 40, 11, 145, 0.26, 200, 100, "🦋",
          "翅膀上有催眠纹路的巨蝶。",
          "灵雀族的远房表亲,虽为蝶身却血脉相通。会用翅膀粉末迷晕修士。",
          ["item_feather_rainbow", "item_charm_doll"]),
    Enemy("bird_05", "雷击鹰", "灵雀飞鸟族", "mid", 25,
          700, 60, 16, 150, 0.28, 360, 180, "🦅",
          "羽翼带电,翱翔时云中带闪电。",
          "祖上曾被雷劫劈中却不死,得雷之神通。族内长老,性格暴烈。",
          ["item_feather_rainbow", "item_lingdan_basic", "item_thunder_core"]),
    Enemy("bird_06", "孔雀仙翎", "灵雀飞鸟族", "mid", 33,
          1300, 85, 23, 155, 0.30, 600, 300, "🦚",
          "拥有孔雀王血脉的高阶妖修。",
          "凤凰之翎陨落的余韵,化为这只孔雀仙翎。一身屏开惊艳天地。",
          ["item_feather_rainbow", "item_yaodan", "item_charm_doll"]),
    Enemy("bird_07", "鹰王", "灵雀飞鸟族", "high", 48,
          3200, 145, 38, 160, 0.32, 1400, 700, "🦅",
          "山岳之王,百鸟朝拜。",
          "金喙隼的祖父,鹰族最长老。曾追杀一只九尾狐三天三夜未果。",
          ["item_feather_phoenix", "item_yaodan", "item_eagle_eye"]),
    Enemy("bird_08", "凤雏", "灵雀飞鸟族", "high", 65,
          8000, 230, 60, 165, 0.34, 3500, 1750, "🦃",
          "尚未羽化的凤凰之子。",
          "凤凰已陨,留下唯一血脉。被灵雀族藏匿千年,渡劫日近。",
          ["item_feather_phoenix", "item_dragon_scale", "item_pill_breakthrough"]),
    Enemy("bird_09", "朱雀之裔", "灵雀飞鸟族", "myth", 85,
          20000, 420, 110, 170, 0.36, 9000, 4500, "🐦",
          "朱雀正统血脉,百年现一只。",
          "上一代朱雀飞升后留下的最后一只直系后裔。烈火加身,焚天煮海。",
          ["item_feather_phoenix", "item_dragon_scale", "item_pill_immortal"]),
]

# ========================================================================
# 族 3 · 蛇蟒族(筑基-金丹)
# 设定:玄武座下水族,水蛇白蟒一脉相承,擅水擅毒
# ========================================================================
CLAN_SERPENT = [
    Enemy("serp_01", "水蛇", "蛇蟒族", "low", 5, 100, 13, 5, 80, 0.08, 40, 20, "🐍",
          "山溪里常见的小水蛇。",
          "蛇蟒族最末等的水蛇。它的母亲是一条受了重伤的白蟒。",
          ["item_serpent_skin", "item_qi_dust"]),
    Enemy("serp_02", "草丛青蛇", "蛇蟒族", "low", 9, 160, 18, 7, 85, 0.09, 70, 35, "🐍",
          "潜伏在草丛里的毒蛇。",
          "灵性微弱的青蛇,擅长伪装。已学会偷食人类祭品。",
          ["item_serpent_skin", "item_focus_pill"]),
    Enemy("serp_03", "毒齿乌蛇", "蛇蟒族", "low", 14, 280, 26, 10, 90, 0.10, 110, 55, "🐍",
          "齿尖有剧毒的乌蛇。",
          "曾咬死过一位修真小有名气的丹师,从此被同门追杀。藏身于深谷。",
          ["item_serpent_skin", "item_poison_sac"]),
    Enemy("serp_04", "山蟒", "蛇蟒族", "mid", 21, 550, 42, 15, 88, 0.11, 240, 120, "🐍",
          "盘踞山头的巨型蟒蛇。",
          "已活了三百年,身长十丈。曾吞过一头猛虎,因此修为大增。",
          ["item_serpent_skin", "item_poison_sac", "item_lingdan_basic"]),
    Enemy("serp_05", "毒蟒王", "蛇蟒族", "mid", 30, 1100, 70, 24, 92, 0.13, 460, 230, "🐍",
          "毒液能腐蚀灵骨的蟒王。",
          "毒齿乌蛇的后代,继承母系绝技。它的毒可融化一切金石,唯惧雷电。",
          ["item_serpent_skin", "item_poison_sac", "item_yaodan"]),
    Enemy("serp_06", "九头蛇魔", "蛇蟒族", "mid", 38, 2200, 105, 35, 95, 0.14, 850, 425, "🐍",
          "九个头颅各有意识的蛇魔。",
          "上古凶兽相柳的远房后裔。九头各持一术:火/水/雷/风/毒/惑/眠/魇/灭。",
          ["item_serpent_skin", "item_poison_sac", "item_yaodan", "item_lingdan_mid"]),
    Enemy("serp_07", "白蟒精", "蛇蟒族", "high", 52, 5000, 175, 55, 100, 0.16, 1800, 900, "🐍",
          "千年白蟒化形,已能幻人。",
          "传说中的白娘子血脉远亲。曾化身少女嫁入凡间,被法海一伙撞破。",
          ["item_serpent_scale_white", "item_yaodan", "item_pill_breakthrough"]),
    Enemy("serp_08", "玄武之裔", "蛇蟒族", "high", 70, 11000, 280, 80, 105, 0.18, 4200, 2100, "🐍",
          "蛇缠龟身的玄武血脉。",
          "玄武四神兽的直系血脉,北方水神之裔。喜静,常守一处不动。",
          ["item_serpent_scale_white", "item_dragon_scale", "item_pill_breakthrough"]),
    Enemy("serp_09", "应龙化蛇", "蛇蟒族", "myth", 90, 25000, 480, 130, 110, 0.20, 10000, 5000, "🐉",
          "化为蛇形的应龙幼崽。",
          "应龙渡劫失败,残魂寄居于一条普通水蛇身上,慢慢恢复神威。",
          ["item_dragon_scale", "item_yaodan", "item_pill_immortal"]),
]

# ========================================================================
# 族 4 · 兽类族 - 虎豹狼(筑基-元婴)
# 设定:东方白虎血脉散落人间,虎豹狼三脉皆其旁系
# ========================================================================
CLAN_BEAST = [
    Enemy("beast_01", "幼狼", "猛兽族", "low", 6, 110, 17, 6, 105, 0.10, 45, 22, "🐺",
          "刚成年的山林小狼。",
          "母狼为护它而被猎人射杀。它发誓长大要复仇,从此专找人类下手。",
          ["item_beast_fur", "item_qi_dust"]),
    Enemy("beast_02", "灰狼", "猛兽族", "low", 11, 200, 25, 9, 110, 0.12, 90, 45, "🐺",
          "群居的草原灰狼。",
          "幼狼的兄长,狼群副首领。冷静狡黠,知道何时撤退。",
          ["item_beast_fur", "item_focus_pill"]),
    Enemy("beast_03", "山豹", "猛兽族", "low", 15, 320, 38, 12, 125, 0.16, 140, 70, "🐆",
          "速度极快的山豹。",
          "白虎旁支血脉,擅长突袭。曾叼走过一只五尾媚妖的幼崽,引来狐族围剿。",
          ["item_beast_fur", "item_focus_pill", "item_swift_claw"]),
    Enemy("beast_04", "雪豹仙", "猛兽族", "mid", 24, 650, 55, 18, 130, 0.18, 280, 140, "🐆",
          "雪山顶上的灵豹。",
          "白虎之灵的化身之一,体内蕴含太阴之力。极少现身,见者必有大事发生。",
          ["item_beast_fur", "item_yaodan"]),
    Enemy("beast_05", "怒虎", "猛兽族", "mid", 32, 1300, 85, 28, 120, 0.15, 520, 260, "🐅",
          "金色斑纹的灵虎。",
          "白虎在世间的化身之一。它认为自己注定要重铸白虎之威,继承四神兽位。",
          ["item_beast_fur", "item_yaodan", "item_swift_claw"]),
    Enemy("beast_06", "金毛獬豸", "猛兽族", "mid", 40, 2400, 120, 40, 125, 0.17, 950, 475, "🦁",
          "传说能辨善恶的神兽幼崽。",
          "獬豸一族在远古曾辅佐皋陶断案,后随天庭败落而隐居。",
          ["item_beast_fur", "item_yaodan", "item_lingdan_mid"]),
    Enemy("beast_07", "白虎魂", "猛兽族", "high", 55, 5800, 210, 65, 130, 0.20, 2000, 1000, "🐅",
          "白虎残魂凝聚的灵体。",
          "上代白虎陨落后,魂魄不散,游荡千年,渐入悟道之境。",
          ["item_beast_fur", "item_yaodan", "item_pill_breakthrough"]),
    Enemy("beast_08", "虎王相柳", "猛兽族", "high", 72, 13000, 330, 100, 135, 0.22, 4800, 2400, "🐅",
          "九尾蛇族与白虎杂交后裔。",
          "母亲是相柳之孙,父亲是白虎旁支。双血脉冲突,使它性情极不稳定。",
          ["item_beast_fur", "item_dragon_scale", "item_pill_breakthrough"]),
    Enemy("beast_09", "白虎正神", "猛兽族", "myth", 92, 28000, 550, 150, 140, 0.24, 11000, 5500, "🐅",
          "西方白虎正统降世。",
          "新一代白虎神兽,千年才能孕育一只。已注定要参与天庭重建。",
          ["item_dragon_scale", "item_yaodan", "item_pill_immortal"]),
]

# ========================================================================
# 族 5 · 灵物族 - 草木精怪(炼气-金丹)
# 设定:神农百草本草之灵,因吸食药丹而异变
# ========================================================================
CLAN_HERB = [
    Enemy("herb_01", "灵芝童子", "草木精怪族", "low", 4, 75, 11, 5, 70, 0.08, 30, 15, "🍄",
          "活了百年的灵芝化形。",
          "终南山深处的千年灵芝,被一位采药老人无意中养出灵性。",
          ["item_herb_basic", "item_qi_dust"]),
    Enemy("herb_02", "藤蔓魔", "草木精怪族", "low", 9, 160, 17, 8, 65, 0.07, 65, 32, "🌿",
          "缠住猎物的食人藤。",
          "原是普通藤蔓,因吸了一位修士的血,渐渐异化为肉食藤魔。",
          ["item_herb_basic", "item_focus_pill"]),
    Enemy("herb_03", "桃花妖", "草木精怪族", "low", 13, 230, 24, 11, 75, 0.10, 95, 47, "🌸",
          "千年桃树化形的女妖。",
          "桃园里最老的桃树,因女主人死后埋骨于树下,化得女子之魂。",
          ["item_herb_basic", "item_charm_doll"]),
    Enemy("herb_04", "丹木老人", "草木精怪族", "mid", 20, 480, 35, 18, 70, 0.09, 200, 100, "🌳",
          "已有四百年道行的木精。",
          "曾被一代丹师埋了一炉九转金丹,树根吸食药力,渐成精怪。",
          ["item_herb_mid", "item_lingdan_basic"]),
    Enemy("herb_05", "百花娘子", "草木精怪族", "mid", 28, 900, 55, 28, 80, 0.12, 380, 190, "🌷",
          "百花之精合一的妖修。",
          "由桃花妖、梨花女、菊仙等百花精灵融合而成,性情飘忽不定。",
          ["item_herb_mid", "item_charm_doll", "item_yaodan"]),
    Enemy("herb_06", "千年树王", "草木精怪族", "mid", 36, 1850, 90, 45, 75, 0.10, 700, 350, "🌳",
          "森林中央的镇山之树。",
          "见证了无数王朝兴衰,扎根深处与地脉相通。被妖兽奉为山神。",
          ["item_herb_mid", "item_yaodan", "item_lingdan_mid"]),
    Enemy("herb_07", "人参精", "草木精怪族", "high", 50, 4400, 145, 70, 90, 0.14, 1600, 800, "🥕",
          "万年人参化形的童子。",
          "传说中长白山深处的万年人参,见到人就跑。捕到一只可延寿百年。",
          ["item_herb_high", "item_pill_breakthrough"]),
    Enemy("herb_08", "灵芝祖宗", "草木精怪族", "high", 68, 9500, 240, 110, 85, 0.13, 3800, 1900, "🍄",
          "灵芝童子的祖先,菩萨座下灵药。",
          "曾被观音菩萨座下的童子带下凡间,失踪后扎根此处千年。",
          ["item_herb_high", "item_dragon_scale", "item_pill_breakthrough"]),
    Enemy("herb_09", "神农魂木", "草木精怪族", "myth", 88, 22000, 420, 180, 95, 0.16, 9000, 4500, "🌲",
          "神农尝百草留下的最后一棵神木。",
          "据说神农百草的所有知识皆寄于此木。砍倒它便能得百草真传。",
          ["item_herb_high", "item_pill_immortal", "item_dragon_scale"]),
]

# ========================================================================
# 族 6 · 鬼族 - 阴煞(金丹-元婴)
# 设定:阴曹地府的逃囚,各有恩怨情仇
# ========================================================================
CLAN_GHOST = [
    Enemy("ghost_01", "野鬼", "鬼族", "low", 8, 90, 22, 4, 100, 0.18, 50, 25, "👻",
          "无家可归的孤魂野鬼。",
          "战乱中死去的农夫,生前未能回家,死后游荡找寻家人。",
          ["item_ghost_essence", "item_qi_dust"]),
    Enemy("ghost_02", "怨灵", "鬼族", "low", 13, 180, 32, 6, 105, 0.20, 95, 47, "👻",
          "充满怨气的灵魂。",
          "被丈夫毒杀的妇人,亡魂不散,夜夜在丈夫坟前哀嚎。",
          ["item_ghost_essence", "item_charm_doll"]),
    Enemy("ghost_03", "厉鬼", "鬼族", "low", 18, 320, 48, 9, 110, 0.22, 160, 80, "👻",
          "怨气滔天的强大厉鬼。",
          "被冤杀的县令,临死前发下毒誓必要全县陪葬。",
          ["item_ghost_essence", "item_charm_doll", "item_lingdan_basic"]),
    Enemy("ghost_04", "阴煞鬼将", "鬼族", "mid", 26, 720, 78, 16, 115, 0.24, 320, 160, "👹",
          "披着阴气铠甲的鬼将军。",
          "三国乱世中战死的悍将,被阎罗收为麾下,后逃出地府重返人间。",
          ["item_ghost_essence", "item_yaodan"]),
    Enemy("ghost_05", "无头将军", "鬼族", "mid", 34, 1500, 115, 26, 120, 0.26, 580, 290, "💀",
          "被砍头后仍能作战的怨将。",
          "明朝大将,被冤杀斩首。死后头颅与身体分离,各自寻找仇人。",
          ["item_ghost_essence", "item_yaodan", "item_swift_claw"]),
    Enemy("ghost_06", "牛头马面", "鬼族", "mid", 42, 2700, 165, 40, 125, 0.27, 1000, 500, "🐂",
          "地府逃囚,本是勾魂使者。",
          "因私放亲属之魂被罚下界,在人间躲藏。",
          ["item_ghost_essence", "item_yaodan", "item_lingdan_mid"]),
    Enemy("ghost_07", "白无常", "鬼族", "high", 58, 6500, 270, 75, 130, 0.30, 2300, 1150, "💀",
          "笑容渗人的勾魂使者。",
          "曾经勾过太多无辜之魂,自责难安,弃职逃离地府。",
          ["item_ghost_essence", "item_pill_breakthrough"]),
    Enemy("ghost_08", "黑无常", "鬼族", "high", 76, 14500, 380, 115, 135, 0.32, 5300, 2650, "💀",
          "杀气腾腾的索命使者。",
          "白无常的搭档,与白同时逃出。两鬼性格相反,常常争吵。",
          ["item_ghost_essence", "item_dragon_scale", "item_pill_breakthrough"]),
    Enemy("ghost_09", "阎罗代行", "鬼族", "myth", 95, 30000, 600, 180, 140, 0.34, 12000, 6000, "👑",
          "代行阎王职权的鬼帝。",
          "因阎王闭关,代为执掌地府百年。已生出篡位之心。",
          ["item_dragon_scale", "item_yaodan", "item_pill_immortal"]),
]

# ========================================================================
# 族 7 · 龙族(元婴-合体)
# 设定:四海龙王后裔,血脉高贵,因天庭败落而散落人间
# ========================================================================
CLAN_DRAGON = [
    Enemy("dragon_01", "蛟", "龙族", "mid", 35, 1700, 95, 35, 100, 0.16, 700, 350, "🐲",
          "未化龙的水中蛟。",
          "本是普通水蛇,得龙王眷顾化为蛟。已修了五百年,差临门一脚化龙。",
          ["item_dragon_scale", "item_yaodan"]),
    Enemy("dragon_02", "蜃龙", "龙族", "mid", 45, 3100, 145, 55, 110, 0.18, 1300, 650, "🐉",
          "能吐海市蜃楼的龙类。",
          "东海龙王第七子,因爱用幻象戏弄凡人被父逐出龙宫。",
          ["item_dragon_scale", "item_yaodan", "item_charm_doll"]),
    Enemy("dragon_03", "螭龙", "龙族", "high", 55, 5500, 215, 80, 115, 0.20, 2200, 1100, "🐉",
          "无角龙,常居岩石之间。",
          "北海龙王长孙,因不爱龙宫繁文缛节而独自下凡修行。",
          ["item_dragon_scale", "item_yaodan", "item_pill_breakthrough"]),
    Enemy("dragon_04", "应龙", "龙族", "high", 65, 9000, 295, 110, 120, 0.22, 3500, 1750, "🐉",
          "有翼之龙,曾佐黄帝战蚩尤。",
          "上古应龙之孙,因祖辈功劳大而获封侯。然年代久远,封号已失效。",
          ["item_dragon_scale", "item_dragon_essence", "item_pill_breakthrough"]),
    Enemy("dragon_05", "螳螂龙", "龙族", "high", 75, 13500, 380, 145, 125, 0.24, 5100, 2550, "🐉",
          "螳螂头颅龙身的异种龙。",
          "应龙的远亲,被族人嘲笑相貌怪异,逃离族群。",
          ["item_dragon_scale", "item_dragon_essence", "item_pill_breakthrough"]),
    Enemy("dragon_06", "墨龙", "龙族", "myth", 88, 22000, 510, 200, 130, 0.26, 8800, 4400, "🐉",
          "通体墨黑的神龙,擅水墨之术。",
          "沧澜剑派太祖的坐骑,主人飞升后留在凡间守护一方。",
          ["item_dragon_scale", "item_dragon_essence", "item_pill_immortal"]),
    Enemy("dragon_07", "青龙", "龙族", "myth", 100, 35000, 720, 280, 135, 0.28, 14000, 7000, "🐲",
          "东方青龙正神,四神之首。",
          "上一代青龙飞升前留下的传承,新一代尚在修炼,血气方刚。",
          ["item_dragon_essence", "item_pill_immortal", "item_starlight"]),
    Enemy("dragon_08", "祖龙残魂", "龙族", "myth", 110, 50000, 950, 380, 140, 0.30, 18000, 9000, "🐉",
          "最初之龙的残存意识。",
          "天地初开之时的第一条龙,陨落后残魂寄居于一颗龙珠之内,等待重生。",
          ["item_dragon_essence", "item_pill_immortal", "item_starlight"]),
    Enemy("dragon_09", "真龙天子", "龙族", "myth", 130, 75000, 1300, 520, 150, 0.32, 28000, 14000, "🐲",
          "九五至尊之龙,人间帝王化身。",
          "汉武帝之魂在地府百年后,被龙气吸引重新转世为龙。",
          ["item_dragon_essence", "item_pill_immortal", "item_starlight"]),
]

# ========================================================================
# 族 8 · 神兽族 - 四圣(化神-大乘)
# 设定:四方神兽朱雀玄武青龙白虎以及它们的旁支
# ========================================================================
CLAN_DIVINE = [
    Enemy("div_01", "朱雀雏", "神兽族", "high", 50, 4500, 175, 60, 130, 0.20, 1800, 900, "🐦",
          "朱雀正神的雏鸟。",
          "上代朱雀的女儿,刚刚破壳。性情火爆,见人就喷火。",
          ["item_dragon_scale", "item_phoenix_feather", "item_pill_breakthrough"]),
    Enemy("div_02", "玄武幼龟", "神兽族", "high", 60, 8000, 220, 90, 95, 0.15, 2800, 1400, "🐢",
          "玄武正神的子嗣。",
          "千岁玄武新孵的幼龟,蛇头还在缩在壳中睡觉。",
          ["item_dragon_scale", "item_xuanwu_shell", "item_pill_breakthrough"]),
    Enemy("div_03", "白虎兽", "神兽族", "high", 70, 11000, 280, 115, 145, 0.25, 4000, 2000, "🐅",
          "白虎正神之裔。",
          "上代白虎陨落后,血脉散落,这是被找回的第一只直系后裔。",
          ["item_dragon_scale", "item_baihu_claw", "item_pill_breakthrough"]),
    Enemy("div_04", "青龙幼苗", "神兽族", "high", 75, 13000, 320, 130, 135, 0.23, 4800, 2400, "🐲",
          "青龙正神托生的人形。",
          "上代青龙飞升前以人形托生,这副身躯尚未觉醒龙身。",
          ["item_dragon_scale", "item_qinglong_horn", "item_pill_breakthrough"]),
    Enemy("div_05", "麒麟驹", "神兽族", "myth", 85, 19000, 420, 170, 130, 0.24, 7500, 3750, "🦄",
          "麒麟新生子,未生角。",
          "祥瑞之兽麒麟的幼崽,见之者寿命延长,但麒麟极少出现。",
          ["item_dragon_essence", "item_pill_immortal"]),
    Enemy("div_06", "孔雀明王坐骑", "神兽族", "myth", 95, 27000, 540, 220, 125, 0.22, 11000, 5500, "🦚",
          "佛门孔雀明王的坐骑。",
          "明王离开后留在人间,被一山修士供奉为山神。",
          ["item_dragon_essence", "item_phoenix_feather", "item_pill_immortal"]),
    Enemy("div_07", "九尾天狐(神兽级)", "神兽族", "myth", 105, 38000, 700, 280, 145, 0.26, 16000, 8000, "🦊",
          "九尾老祖,狐族至尊。",
          "终南山九尾老祖,八尾妖王的母亲。已活了一万年。",
          ["item_dragon_essence", "item_pill_immortal", "item_starlight"]),
    Enemy("div_08", "应龙正神", "神兽族", "myth", 115, 52000, 880, 350, 150, 0.28, 22000, 11000, "🐉",
          "曾辅黄帝的应龙转世。",
          "应龙之孙的祖父——应龙正神本尊。从未真正陨落,只是隐居数千年。",
          ["item_dragon_essence", "item_pill_immortal", "item_starlight"]),
    Enemy("div_09", "凤凰涅槃", "神兽族", "myth", 125, 70000, 1100, 450, 155, 0.30, 30000, 15000, "🔥",
          "千年涅槃一次的凤凰。",
          "上代凤凰已陨,这只是浴火重生的下一代。烈火加身、焚天煮海。",
          ["item_dragon_essence", "item_phoenix_feather", "item_pill_immortal"]),
]

# ========================================================================
# 族 9 · 上古凶兽族(合体-渡劫)
# 设定:鸿蒙初开时的远古凶兽,各有上古恩怨
# ========================================================================
CLAN_ANCIENT = [
    Enemy("anc_01", "穷奇幼崽", "上古凶兽族", "high", 65, 8500, 250, 95, 140, 0.22, 3300, 1650, "🦂",
          "凶兽穷奇的后代。",
          "上古穷奇曾因好斗被罚下界,后代散落山林。这是其中一支。",
          ["item_dragon_scale", "item_ancient_horn", "item_pill_breakthrough"]),
    Enemy("anc_02", "饕餮", "上古凶兽族", "myth", 85, 18000, 410, 170, 110, 0.16, 7400, 3700, "👹",
          "贪食成性的凶兽。",
          "传说能吞下整个城池,贪食至死也未曾停止。被天庭剥皮挂于天门外示众。",
          ["item_ancient_horn", "item_dragon_essence", "item_pill_immortal"]),
    Enemy("anc_03", "梼杌", "上古凶兽族", "myth", 95, 26000, 520, 210, 125, 0.20, 10500, 5250, "👺",
          "凶残嗜杀的远古凶兽。",
          "曾袭击天庭被女娲所镇,千年沉睡之后破封而出。",
          ["item_ancient_horn", "item_dragon_essence", "item_pill_immortal"]),
    Enemy("anc_04", "混沌", "上古凶兽族", "myth", 105, 36000, 660, 270, 100, 0.14, 14500, 7250, "🌀",
          "形体不明的远古凶兽。",
          "无头无目无耳无口的肉身,代表混沌本身。曾被盘古劈开,残余至今。",
          ["item_ancient_horn", "item_dragon_essence", "item_pill_immortal"]),
    Enemy("anc_05", "九婴", "上古凶兽族", "myth", 115, 48000, 800, 330, 130, 0.22, 19000, 9500, "🐲",
          "九头蛇身的远古凶兽。",
          "夏代为后羿所射,九头落地化为九座山。今日复合,再战人间。",
          ["item_ancient_horn", "item_dragon_essence", "item_pill_immortal", "item_starlight"]),
    Enemy("anc_06", "相柳", "上古凶兽族", "myth", 125, 62000, 990, 410, 135, 0.24, 25000, 12500, "🐍",
          "共工之相,九头蛇神。",
          "共工怒触不周山时的得力部下。共工死后,相柳在人间游荡数千年。",
          ["item_ancient_horn", "item_dragon_essence", "item_pill_immortal", "item_starlight"]),
    Enemy("anc_07", "蚩尤之灵", "上古凶兽族", "myth", 135, 80000, 1200, 510, 145, 0.26, 32000, 16000, "👹",
          "上古战神蚩尤的残灵。",
          "曾与黄帝大战,败死涿鹿。魂魄不散,游荡千年,现已凝聚成形。",
          ["item_ancient_horn", "item_dragon_essence", "item_pill_immortal", "item_starlight"]),
    Enemy("anc_08", "夸父之心", "上古凶兽族", "myth", 145, 100000, 1500, 640, 155, 0.28, 40000, 20000, "❤️",
          "追日夸父留下的心脏。",
          "夸父逐日而死,心脏仍在追逐落日的方向。化为巨大凶兽形态。",
          ["item_dragon_essence", "item_pill_immortal", "item_starlight"]),
    Enemy("anc_09", "盘古残魂", "上古凶兽族", "myth", 160, 130000, 1900, 800, 165, 0.30, 55000, 27500, "👑",
          "开天辟地后留下的微弱残魂。",
          "盘古身躯化为山河,意识散于天地。最后一缕残魂渐渐凝聚,欲再开新天。",
          ["item_dragon_essence", "item_pill_immortal", "item_starlight"]),
]

# ========================================================================
# 族 10 · 灵魂魔修族(化神-大乘)
# 设定:被自身心魔吞噬的修士,变成介于人和魔之间的存在
# ========================================================================
CLAN_DEMON = [
    Enemy("dem_01", "迷心人", "魔修族", "mid", 30, 1400, 75, 25, 110, 0.18, 580, 290, "😈",
          "心魔初现的修士。",
          "本是青冥派外门弟子,因走火入魔未能渡过,从此心魔渐生。",
          ["item_demon_blood", "item_yaodan"]),
    Enemy("dem_02", "嗜血修", "魔修族", "mid", 40, 2700, 130, 45, 115, 0.20, 1100, 550, "🩸",
          "嗜血成性的魔修。",
          "曾杀师灭祖,逐渐迷失。今日只为屠戮而活。",
          ["item_demon_blood", "item_yaodan", "item_pill_breakthrough"]),
    Enemy("dem_03", "傀儡师", "魔修族", "high", 55, 5800, 215, 75, 120, 0.22, 2200, 1100, "🎎",
          "操控尸体作战的魔修。",
          "天机阁叛徒,叛门后专修傀儡之术。",
          ["item_demon_blood", "item_charm_doll", "item_pill_breakthrough"]),
    Enemy("dem_04", "夺魂者", "魔修族", "high", 70, 11000, 295, 110, 125, 0.24, 4200, 2100, "👁️",
          "夺取他人之魂的魔修。",
          "他每次夺魂都让自己更强,但灵识却越来越混乱。已记不清自己的名字。",
          ["item_demon_blood", "item_dragon_scale", "item_pill_breakthrough"]),
    Enemy("dem_05", "黑袍人", "魔修族", "high", 80, 17000, 380, 145, 130, 0.25, 6500, 3250, "🥷",
          "全身黑袍的神秘魔修。",
          "无人见过他的真面目,只知他的剑曾断五大派门。",
          ["item_demon_blood", "item_dragon_scale", "item_pill_breakthrough"]),
    Enemy("dem_06", "魔尊化身", "魔修族", "myth", 95, 28000, 540, 220, 135, 0.27, 11500, 5750, "👹",
          "上古魔尊的化身之一。",
          "本体远在天外,只是借此化身在人间游历。",
          ["item_demon_blood", "item_dragon_essence", "item_pill_immortal"]),
    Enemy("dem_07", "嗜灵狂魔", "魔修族", "myth", 105, 38000, 700, 280, 140, 0.28, 16000, 8000, "🔮",
          "专门吸食灵气的疯狂魔修。",
          "他能将整片山的灵气吸干,所到之处寸草不生。",
          ["item_demon_blood", "item_dragon_essence", "item_pill_immortal"]),
    Enemy("dem_08", "魔界使者", "魔修族", "myth", 115, 52000, 880, 350, 145, 0.30, 22000, 11000, "🦇",
          "从魔界跨界而来的真魔。",
          "魔界破封,使者下来探查人间情况。已查到沧澜剑派的位置。",
          ["item_dragon_essence", "item_pill_immortal", "item_starlight"]),
    Enemy("dem_09", "降世魔王", "魔修族", "myth", 130, 78000, 1300, 510, 150, 0.32, 30000, 15000, "👹",
          "降临人间的魔界之王。",
          "魔界封印彻底破碎,魔王亲临。这是真正的大灾。",
          ["item_dragon_essence", "item_pill_immortal", "item_starlight"]),
]

# ========================================================================
# 族 11 · 仙器之灵族(渡劫期)
# 设定:上古遗失的法宝中孕育出的器灵,各有传奇故事
# ========================================================================
CLAN_ARTIFACT = [
    Enemy("art_01", "断剑残魂", "仙器之灵族", "high", 60, 7500, 240, 80, 125, 0.20, 2800, 1400, "🗡️",
          "古剑中残存的剑灵。",
          "本是一柄上古名剑,剑身已断,残魂寄居于断剑之内。",
          ["item_dragon_scale", "item_starlight", "item_pill_breakthrough"]),
    Enemy("art_02", "古镜怨灵", "仙器之灵族", "high", 70, 11500, 300, 105, 110, 0.18, 4500, 2250, "🪞",
          "封印在古镜内的怨灵。",
          "镜中曾照见一位绝世美人之死,镜便记下了那份哀怨。",
          ["item_dragon_scale", "item_starlight", "item_pill_breakthrough"]),
    Enemy("art_03", "玉佩仙子", "仙器之灵族", "high", 80, 17000, 380, 145, 130, 0.24, 6800, 3400, "💎",
          "佩戴千年的玉佩之灵。",
          "本是一位仙子的随身玉佩,仙子飞升后玉佩留下,渐生灵识。",
          ["item_dragon_scale", "item_starlight", "item_charm_doll"]),
    Enemy("art_04", "金钟巨灵", "仙器之灵族", "myth", 90, 25000, 480, 195, 100, 0.16, 10000, 5000, "🔔",
          "上古寺院的镇寺金钟之灵。",
          "无数僧人在它面前讲经,渐渐悟道。如今寺已倒塌,钟灵犹存。",
          ["item_dragon_essence", "item_starlight", "item_pill_immortal"]),
    Enemy("art_05", "墨笔仙翁", "仙器之灵族", "myth", 100, 35000, 600, 250, 120, 0.22, 14500, 7250, "🖌️",
          "执笔者祖师的真笔之灵。",
          "沧澜剑派开山祖师的随身毛笔,因主人飞升前未带走,留在剑派宝库千年。",
          ["item_dragon_essence", "item_starlight", "item_pill_immortal"]),
    Enemy("art_06", "九鼎之灵", "仙器之灵族", "myth", 110, 48000, 780, 320, 105, 0.18, 19500, 9750, "⚱️",
          "大禹铸九鼎之器灵。",
          "九鼎本是分散九州气运,然鼎灵自有意识,如今九鼎合一现身。",
          ["item_dragon_essence", "item_starlight", "item_pill_immortal"]),
    Enemy("art_07", "天瓶之灵", "仙器之灵族", "myth", 125, 65000, 1000, 420, 135, 0.26, 26000, 13000, "🏺",
          "盛装四海之水的天瓶之灵。",
          "观音菩萨净瓶的复刻品,佛门遗失千年。",
          ["item_dragon_essence", "item_starlight", "item_pill_immortal"]),
    Enemy("art_08", "炼丹炉魂", "仙器之灵族", "myth", 140, 85000, 1300, 540, 145, 0.28, 33000, 16500, "🍯",
          "太上老君炼丹炉的魂魄。",
          "老君下界办事,炼丹炉留在凡间一时间,渐生灵识自行修炼。",
          ["item_dragon_essence", "item_starlight", "item_pill_immortal"]),
    Enemy("art_09", "盘古斧灵", "仙器之灵族", "myth", 160, 120000, 1800, 750, 150, 0.30, 48000, 24000, "🪓",
          "开天辟地之斧的器灵。",
          "盘古化身万物后,劈天之斧留在世界尽头,劫数将至时方苏醒。",
          ["item_dragon_essence", "item_starlight", "item_pill_immortal"]),
]

# ========================================================================
# 族 12 · 异域生灵族(渡劫-飞升)
# 设定:从其它修真界跨界而来的异界存在,故事悬念之源
# ========================================================================
CLAN_ALIEN = [
    Enemy("alien_01", "异界刺客", "异域生灵族", "high", 70, 11000, 310, 105, 145, 0.28, 4200, 2100, "👤",
          "从未知之地来的刺客。",
          "通过空间裂缝而来,目的不明。它的武器似乎来自别的世界。",
          ["item_dragon_scale", "item_alien_essence", "item_pill_breakthrough"]),
    Enemy("alien_02", "迷雾行者", "异域生灵族", "high", 85, 19000, 420, 165, 140, 0.30, 8000, 4000, "🌫️",
          "形如雾气的异界生物。",
          "无固定形态,能渗入任何缝隙。已绑架过若干修真界知名人物。",
          ["item_alien_essence", "item_starlight"]),
    Enemy("alien_03", "晶族战士", "异域生灵族", "myth", 95, 28000, 540, 215, 130, 0.26, 11500, 5750, "💎",
          "通体水晶的高等异族。",
          "晶族文明远高于修真界,然不知为何派遣战士前来。",
          ["item_alien_essence", "item_starlight", "item_pill_immortal"]),
    Enemy("alien_04", "深渊使徒", "异域生灵族", "myth", 105, 38000, 690, 280, 125, 0.24, 16000, 8000, "🌀",
          "深渊另一边的使者。",
          "深渊本是修真界与魔界的分界,然这位使者声称来自更深处。",
          ["item_alien_essence", "item_starlight", "item_pill_immortal"]),
    Enemy("alien_05", "时间游者", "异域生灵族", "myth", 115, 50000, 850, 350, 155, 0.32, 21000, 10500, "⏳",
          "穿越时间的旅人。",
          "他来自未来,警告说本界面将被毁灭。然没有人相信他。",
          ["item_alien_essence", "item_starlight", "item_pill_immortal"]),
    Enemy("alien_06", "维度割裂者", "异域生灵族", "myth", 125, 65000, 1050, 430, 145, 0.30, 27000, 13500, "✂️",
          "撕裂世界界限的异族。",
          "本身就是空间裂缝的化身,所过之处现实开始崩溃。",
          ["item_alien_essence", "item_starlight", "item_pill_immortal"]),
    Enemy("alien_07", "星河使者", "异域生灵族", "myth", 140, 88000, 1350, 560, 150, 0.31, 35000, 17500, "🌌",
          "来自银河之外的存在。",
          "它的存在本身就让修士的灵识失去意义。看一眼便会迷失。",
          ["item_alien_essence", "item_starlight", "item_pill_immortal"]),
    Enemy("alien_08", "造物之主使徒", "异域生灵族", "myth", 155, 115000, 1700, 720, 160, 0.32, 45000, 22500, "🌟",
          "声称是创造者使者的存在。",
          "宣称将带本世界'回归源始'。无人理解其意。",
          ["item_alien_essence", "item_starlight", "item_pill_immortal"]),
    Enemy("alien_09", "界外神祇", "异域生灵族", "myth", 175, 150000, 2100, 900, 170, 0.34, 60000, 30000, "👁️",
          "凡人触之即灭的至高存在。",
          "本界天道不能限制它,本界众神在它面前如蝼蚁。它的目的至今无人知晓。",
          ["item_alien_essence", "item_starlight", "item_pill_immortal"]),
]


# ========================================================================
# 汇总所有怪物
# ========================================================================
ALL_CLANS = {
    "山林狐妖族": CLAN_FOX,
    "灵雀飞鸟族": CLAN_BIRD,
    "蛇蟒族": CLAN_SERPENT,
    "猛兽族": CLAN_BEAST,
    "草木精怪族": CLAN_HERB,
    "鬼族": CLAN_GHOST,
    "龙族": CLAN_DRAGON,
    "神兽族": CLAN_DIVINE,
    "上古凶兽族": CLAN_ANCIENT,
    "魔修族": CLAN_DEMON,
    "仙器之灵族": CLAN_ARTIFACT,
    "异域生灵族": CLAN_ALIEN,
}

ENEMIES = {}
ENEMY_CONTEXT = {}
for clan_name, members in ALL_CLANS.items():
    for idx, e in enumerate(members):
        if not any(item_id in SKILL_DROP_ITEM_IDS for item_id in e.drops):
            e.drops.append(skill_drop_item_for_enemy(e))
        # ★ 自动绑定立绘:enemy_id 直接对应文件名 (fox_01 → /images/portraits/enemies/fox_01.png)
        if not e.image_url:
            e.image_url = f"/images/portraits/enemies/{e.id}.png"
        ENEMIES[e.id] = e
        ENEMY_CONTEXT[e.id] = {"index": idx, "members": members}

# 维持原有的 5 个测试 ID 兼容旧测试
_legacy_aliases = {
    "wild_fox": "fox_01",
    "spirit_sparrow": "bird_01",
    "poison_serpent": "serp_05",
    "lightning_qilin": "div_03",
    "heavenly_demon_king": "anc_07",
}
for old, new in _legacy_aliases.items():
    if new in ENEMIES and old not in ENEMIES:
        ENEMIES[old] = ENEMIES[new]


def get_enemy(enemy_id: str):
    e = ENEMIES.get(enemy_id)
    if e:
        return e
    # Boss 也可作为战斗敌人
    from .bosses import BOSSES
    return BOSSES.get(enemy_id)


def list_enemies_for_level(level: int, span: int = 8):
    """返回该等级 ±span 范围内的怪物"""
    return [e for e in ENEMIES.values()
            if abs(e.level - level) <= span and not e.id.startswith(("wild_", "spirit_", "poison_", "lightning_", "heavenly_"))]


def enemy_to_dict(e, character: dict | None = None):
    """怪物转 dict — 使用统一战斗平衡数值,避免展示值与真实战斗脱节。"""
    stats = balanced_enemy_stats(e, character)
    context = ENEMY_CONTEXT.get(e.id, {"index": 0, "members": [e]})
    codex = get_enemy_codex_profile(e, context["index"], context["members"])
    data = {
        "id": e.id,
        "name": e.name,
        "clan": e.clan,
        "tier": e.tier,
        "level": e.level,
        "hp": stats["hp"],
        "max_hp": stats["max_hp"],
        "atk": stats["atk"],
        "def_": stats["def_"],
        "spd": stats["spd"],
        "evasion": stats["evasion"],
        "balance_profile": stats["profile"],
        "image_emoji": e.image_emoji,
        "image_url": e.image_url,
        "description": e.description,
        "lore": e.lore,
        "rewards": {"exp": stats["rewards_exp"], "qi": stats["rewards_qi"]},
        "drops": e.drops,
    }
    if getattr(e, "is_npc", False):
        data.update({
            "is_npc": True,
            "sect_id": getattr(e, "sect_id", ""),
            "sect_name": getattr(e, "sect_name", ""),
            "rank": getattr(e, "rank", ""),
            "portrait_kind": getattr(e, "portrait_kind", "player"),
            "portrait_id": getattr(e, "portrait_id", ""),
        })
    data.update(codex)
    return data


def count_enemies():
    """返回 (普通怪数量, 各族数量)"""
    return len(ENEMIES), {clan: len(members) for clan, members in ALL_CLANS.items()}
