"""Boss 大全 — 22 位 Boss,以小型大模型公司化身为门派,四条故事线交织

故事线:
  A · 西方三皇之争(沧澜=Anthropic vs 天机=OpenAI vs 隐藏的Google系)
  B · 开源觉醒(Hugging Face / Mistral / Together / Replicate 结盟)
  C · 东方崛起(百川 / 零一 / 阶跃 / 商汤 / MiniMax 联盟)
  D · 异端崛起(xAI Grok / Perplexity / Inflection / Character.AI 颠覆)

公司背景皆为公开真实信息,Boss 设定为艺术化形象演绎。
"""

from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class BossSect:
    """Boss 宗派(对应一家大模型公司)"""
    id: str
    name: str                  # 宗派中文名
    company: str               # 对应真实公司
    founded: str               # 成立时间 / 国家
    real_background: str       # 公司真实背景
    sect_story: str            # 宗派艺术化故事
    storyline: str             # 所属故事线 A/B/C/D
    base_color: str            # 主色调


@dataclass
class Boss:
    id: str
    name: str                  # Boss 名号
    title: str                 # 称号
    sect_id: str               # 所属宗派
    level: int                 # 推荐等级
    hp: int
    atk: int
    def_: int
    spd: int
    evasion: float
    crit_rate: float
    rewards_exp: int
    rewards_qi: int
    image_emoji: str
    lore: str                  # Boss 个人故事
    bonds: list[str] = field(default_factory=list)  # 与其它 Boss 的羁绊(Boss id)
    bond_descriptions: list[str] = field(default_factory=list)
    drops: list[str] = field(default_factory=list)
    signature_skill: str = ""  # 标志性招式
    image_url: str = ""        # Boss 绘画头像 URL

    # 兼容 BattleEngine 用 Enemy 的字段
    @property
    def clan(self):
        """Boss 的 clan 取自所属宗派名"""
        sect = BOSS_SECTS.get(self.sect_id)
        return sect.name if sect else self.sect_id


# ========================================================================
# 宗派定义(对应真实小型大模型公司)
# ========================================================================
BOSS_SECTS = {
    # 故事线 A:西方三皇
    "deepmind_pavilion": BossSect(
        id="deepmind_pavilion", name="深玄阁",
        company="Google DeepMind", founded="2010 · 英国伦敦",
        real_background="DeepMind 由 Demis Hassabis 等于 2010 年创立,2014 年被 Google 收购。开发了 AlphaGo、AlphaFold、Gemini 等划时代模型。",
        sect_story="深玄阁立于伦敦云端之上,阁主'哈萨比斯'本是凡间棋圣,后悟得'蒙特卡洛剑法'。后被天庭(Google)收编为客卿,主管 Gemini 神剑研发。",
        storyline="A",
        base_color="#4285F4",
    ),
    "mistral_storm": BossSect(
        id="mistral_storm", name="风暴宗",
        company="Mistral AI", founded="2023 · 法国巴黎",
        real_background="Mistral AI 由 Meta 和 DeepMind 前员工于 2023 年创立,以开源高质量模型著称(Mistral 7B / Mixtral)。",
        sect_story="风暴宗发源于法国,创派祖师'米斯特拉'本是天机阁、深玄阁的双重叛徒,出走后立下'万法开源'之誓。",
        storyline="B",
        base_color="#FF7F00",
    ),
    "cohere_harmony": BossSect(
        id="cohere_harmony", name="同心阁",
        company="Cohere", founded="2019 · 加拿大多伦多",
        real_background="Cohere 由 Aidan Gomez(Transformer 论文合著者之一)等创立,专注企业级 NLP 解决方案。",
        sect_story="同心阁三位创派祖师当年同窗共著'变形金刚剑诀',后于多伦多结庐立派,主营企业护法之术。",
        storyline="A",
        base_color="#39594D",
    ),
    "ai21_babel": BossSect(
        id="ai21_babel", name="巴别塔",
        company="AI21 Labs", founded="2017 · 以色列特拉维夫",
        real_background="AI21 Labs 由 Amnon Shashua(Mobileye 创始人)等创立,Jurassic 系列与 Jamba 模型为其代表作。",
        sect_story="巴别塔立于死海之滨,藏有'语言之钥'。塔主曾试图统一天下语言,然遭其它宗派排挤。",
        storyline="A",
        base_color="#4A9EFF",
    ),
    "together_sail": BossSect(
        id="together_sail", name="同舟会",
        company="Together AI", founded="2022 · 美国加州",
        real_background="Together AI 提供分布式训练与推理平台,主推开源模型云服务,RedPajama 数据集发布方。",
        sect_story="同舟会乃修真界的物流商号,载着各家开源剑法跨越大江南北。盟主舟翁以'共舟万里'为信条。",
        storyline="B",
        base_color="#FF6B35",
    ),
    "replicate_evolve": BossSect(
        id="replicate_evolve", name="衍化盟",
        company="Replicate", founded="2019 · 美国旧金山",
        real_background="Replicate 提供 ML 模型即服务,让任何人用 API 跑各类开源模型(SDXL/Flux/Llama 等)。",
        sect_story="衍化盟乃修真界的'万法集市',无论你想修何派功法,皆可于此租赁尝试。",
        storyline="B",
        base_color="#FF4785",
    ),
    "huggingface_temple": BossSect(
        id="huggingface_temple", name="拥抱观",
        company="Hugging Face", founded="2016 · 美国纽约",
        real_background="Hugging Face 创立时是一款聊天 App,后转型为开源 AI 模型与数据集集散地,Transformers 库已成行业标准。",
        sect_story="拥抱观位于纽约长老山,观主'拥抱真人'最初是一名儿童玩偶匠,后无意中得'通灵秘卷',遂广收门徒、开放秘籍。",
        storyline="B",
        base_color="#FFD21E",
    ),
    "stability_garden": BossSect(
        id="stability_garden", name="持心门",
        company="Stability AI", founded="2020 · 英国伦敦",
        real_background="Stability AI 发布 Stable Diffusion 系列(SD1.5/SDXL/SD3),推动 AI 绘图开源浪潮,后因经营不善多次易主。",
        sect_story="持心门创派祖师'稳心圣女'本是绘画奇才,以'笔尖凝象'之术名震一时。然后因门派内斗,圣女隐退。",
        storyline="B",
        base_color="#222B45",
    ),
    "inflection_turn": BossSect(
        id="inflection_turn", name="转折宫",
        company="Inflection AI", founded="2022 · 美国加州",
        real_background="Inflection AI 由 LinkedIn 创始人 Reid Hoffman 等创立,推出 Pi 模型主打情感陪伴,2024 年核心团队被微软挖走。",
        sect_story="转折宫开派祖师'转折天尊'专修共情之道,本希望以'温柔之剑'救度众生。然门下高徒尽数被天庭(微软)挖走,宗门凋零。",
        storyline="D",
        base_color="#9B59B6",
    ),
    "character_mask": BossSect(
        id="character_mask", name="千面殿",
        company="Character.AI", founded="2021 · 美国加州",
        real_background="Character.AI 由 Noam Shazeer(Transformer 论文一作)等创立,主打 AI 角色扮演聊天,2024 年被 Google 部分收编。",
        sect_story="千面殿创派祖师'千面舞者'本为天机阁(OpenAI)长老,后弃道下凡,以'万千面孔'之术化身万人聊天。然终被深玄阁(Google)所收编。",
        storyline="D",
        base_color="#FF1493",
    ),
    "perplexity_trail": BossSect(
        id="perplexity_trail", name="迷踪派",
        company="Perplexity AI", founded="2022 · 美国加州",
        real_background="Perplexity AI 是结合搜索与 LLM 的对话式搜索引擎,创始人 Aravind Srinivas 出身 OpenAI。",
        sect_story="迷踪派之祖'迷踪散人'游走于天机阁与深玄阁之间,自创'索引剑诀',能从万千线索中追溯真相。",
        storyline="D",
        base_color="#20B2AA",
    ),
    "groq_speed": BossSect(
        id="groq_speed", name="极速门",
        company="Groq Inc.", founded="2016 · 美国硅谷",
        real_background="Groq 设计自研 LPU 推理芯片,提供极高速推理服务(800+ tokens/s),创始人 Jonathan Ross 是 Google TPU 之父。",
        sect_story="极速门主张'快即正义',门主'极速僧'手中无招,出手时只见一道金光,胜败已分。",
        storyline="D",
        base_color="#F46036",
    ),
    "xai_void": BossSect(
        id="xai_void", name="玄道宫",
        company="xAI (Grok)", founded="2023 · 美国奥斯汀",
        real_background="xAI 由 Elon Musk 于 2023 年创立,推出 Grok 模型,主打'反叛精神'与对话自由度,Grok-2/3/4 持续迭代。",
        sect_story="玄道宫开派祖师'玄道魔主'(影射马斯克)曾参与天机阁创派(OpenAI 早期),后出走立派,以'反叛剑诀'闻名。",
        storyline="D",
        base_color="#1DA1F2",
    ),
    # 故事线 C:东方崛起
    "baichuan_sea": BossSect(
        id="baichuan_sea", name="百川海",
        company="百川智能(Baichuan)", founded="2023 · 北京",
        real_background="百川智能由王小川(搜狗创始人)创立,推出 Baichuan/M1 等中文优化模型。",
        sect_story="百川海乃东海一座小岛,海主'王小川'本是搜狗大派传人,出走自立。所修剑法'纳百川'专吸他派之长。",
        storyline="C",
        base_color="#0EA5E9",
    ),
    "yi_peak": BossSect(
        id="yi_peak", name="万物峰",
        company="01.AI(零一万物)", founded="2023 · 北京",
        real_background="零一万物由李开复创立,推出 Yi 系列开源模型,在英文 benchmark 上一度超越 GPT-3.5。",
        sect_story="万物峰创派祖师'李开峰'乃东方修真界的元老级人物,以'万物归一'之术名震天下。",
        storyline="C",
        base_color="#10B981",
    ),
    "step_star": BossSect(
        id="step_star", name="阶星阁",
        company="阶跃星辰(StepFun)", founded="2023 · 上海",
        real_background="阶跃星辰由微软原全球副总裁姜大昕创立,以 Step 系列多模态模型为代表。",
        sect_story="阶星阁主'姜大昕'本是天机阁(微软)长老,后东渡立派,擅长'阶梯渐进'之法。",
        storyline="C",
        base_color="#8B5CF6",
    ),
    "minimax_micro": BossSect(
        id="minimax_micro", name="微极派",
        company="MiniMax", founded="2021 · 上海",
        real_background="MiniMax 由商汤前副总裁闫俊杰创立,推出 abab 系列模型,旗下星野/Talkie 拥有大量年轻用户。",
        sect_story="微极派主'闫极道祖'专修'微极之道',讲究在最小处见乾坤,深受年轻修士追捧。",
        storyline="C",
        base_color="#EC4899",
    ),
    "sensetime_hall": BossSect(
        id="sensetime_hall", name="商汤殿",
        company="商汤科技(SenseTime)", founded="2014 · 香港/上海",
        real_background="商汤科技为中国 AI 四小龙之一,后转型大模型领域,推出'日日新'系列。",
        sect_story="商汤殿是东方四大门派之一,殿主'商汤大圣'专修视觉之道,座下千眼弟子遍布天下。",
        storyline="C",
        base_color="#DC2626",
    ),
}


# ========================================================================
# Boss 配置
# ========================================================================
BOSSES = {}

def _add(b: Boss):
    BOSSES[b.id] = b

# ============ 故事线 A:西方三皇 ============
_add(Boss(
    id="boss_canglan_traitor", name="墨魔·林泽",
    title="沧澜叛徒", sect_id="canglan",  # 自家门派叛徒
    level=40, hp=8000, atk=200, def_=60, spd=120, evasion=0.18, crit_rate=0.25,
    rewards_exp=2500, rewards_qi=1250,
    image_emoji="🥷",
    lore="原沧澜剑派内门弟子林泽,因不满师门'剑意如墨'的束缚,转修魔道,以墨化血,以血凝剑。",
    bonds=["boss_huggingface", "boss_xai_grok"],
    bond_descriptions=[
        "曾与拥抱真人有过一面之缘,被劝说'开源剑诀'未果",
        "私下与玄道魔主有秘密协议,愿协助颠覆沧澜",
    ],
    drops=["item_pill_breakthrough", "item_demon_blood"],
    signature_skill="墨血叛剑式",
))

_add(Boss(
    id="boss_tianji_traitor", name="齿轮鬼·托马斯",
    title="天机叛徒", sect_id="tianji",
    level=42, hp=8500, atk=220, def_=65, spd=125, evasion=0.20, crit_rate=0.27,
    rewards_exp=2700, rewards_qi=1350,
    image_emoji="⚙️",
    lore="原天机阁高级研究员,因目睹机关被滥用伤民,反叛逃出。如今他将一切机关化为复仇之器。",
    bonds=["boss_canglan_traitor", "boss_inflection"],
    bond_descriptions=[
        "与墨魔·林泽相识于地下黑市,常交换情报",
        "曾试图说服转世天尊一同反叛,被婉拒",
    ],
    drops=["item_pill_breakthrough", "item_gear_core"],
    signature_skill="千轮反噬阵",
))

_add(Boss(
    id="boss_deepmind", name="哈萨长老",
    title="深玄阁阁主", sect_id="deepmind_pavilion",
    level=110, hp=80000, atk=1100, def_=380, spd=140, evasion=0.26, crit_rate=0.30,
    rewards_exp=22000, rewards_qi=11000,
    image_emoji="🧠",
    lore="深玄阁阁主,本是凡间棋圣,后修'蒙特卡洛剑法'登顶。座下'阿尔法'弟子已能预演万局,无人能在棋盘上胜他。",
    bonds=["boss_canglan_supreme", "boss_tianji_supreme"],
    bond_descriptions=[
        "与沧澜山长老'阿莫迪克斯'本是同门,后因理念分歧分道扬镳",
        "和天机阁山姆道君是宿敌,常于云端棋局上较量",
    ],
    drops=["item_pill_immortal", "item_dragon_essence", "item_starlight"],
    signature_skill="围棋十九路斩",
))

_add(Boss(
    id="boss_canglan_supreme", name="阿莫迪克斯",
    title="沧澜山主", sect_id="canglan",
    level=145, hp=180000, atk=2200, def_=700, spd=150, evasion=0.28, crit_rate=0.32,
    rewards_exp=60000, rewards_qi=30000,
    image_emoji="🗡️",
    lore="沧澜剑派当代山主(影射 Anthropic CEO Dario Amodei),师承天机阁山姆道君,后因'安全剑诀'之争分道扬镳。",
    bonds=["boss_tianji_supreme", "boss_deepmind"],
    bond_descriptions=[
        "与天机阁山姆道君本是结拜兄弟,如今相煎太急",
        "与深玄阁阁主有过同门之谊,理念却背道而驰",
    ],
    drops=["item_pill_immortal", "item_starlight"],
    signature_skill="沧澜九霄剑·守护一式",
))

_add(Boss(
    id="boss_tianji_supreme", name="山姆道君",
    title="天机阁掌教", sect_id="tianji",
    level=148, hp=200000, atk=2400, def_=750, spd=155, evasion=0.30, crit_rate=0.35,
    rewards_exp=65000, rewards_qi=32500,
    image_emoji="⚙️",
    lore="天机阁掌教(影射 Sam Altman),修'万法归一剑',曾被沧澜山主刺杀未遂,后用计将其逐出阁门。",
    bonds=["boss_canglan_supreme", "boss_xai_grok"],
    bond_descriptions=[
        "与沧澜山主阿莫迪克斯曾是兄弟,如今水火不容",
        "与玄道魔主马斯克恩怨纠葛二十年,从挚友到死敌",
    ],
    drops=["item_pill_immortal", "item_starlight", "item_gear_core"],
    signature_skill="万象归元·终极一式",
))

# ============ 故事线 B:开源觉醒 ============
_add(Boss(
    id="boss_huggingface", name="拥抱真人",
    title="拥抱观观主", sect_id="huggingface_temple",
    level=78, hp=25000, atk=480, def_=200, spd=125, evasion=0.20, crit_rate=0.18,
    rewards_exp=8500, rewards_qi=4250,
    image_emoji="🤗",
    lore="拥抱观观主'克莱门特',本是法国巴黎玩具匠,无意中得'通灵秘卷',遂广收门徒、开放秘籍,为开源派之首。",
    bonds=["boss_mistral", "boss_together", "boss_stability"],
    bond_descriptions=[
        "与风暴宗米斯特拉为开源联盟挚友",
        "同舟会舟翁是他的物流伙伴",
        "曾收留持心门稳心圣女避难三年",
    ],
    drops=["item_pill_breakthrough", "item_open_secret_scroll"],
    signature_skill="千卷开源诀",
))

_add(Boss(
    id="boss_mistral", name="米斯特拉",
    title="风暴宗宗主", sect_id="mistral_storm",
    level=85, hp=32000, atk=580, def_=240, spd=140, evasion=0.24, crit_rate=0.22,
    rewards_exp=11000, rewards_qi=5500,
    image_emoji="🌪️",
    lore="风暴宗宗主'米斯特拉'(法国地中海强风之名),本是天机阁(OpenAI)与深玄阁(DeepMind)双重叛徒,出走后立下'万法开源'之誓。",
    bonds=["boss_huggingface", "boss_tianji_supreme", "boss_deepmind"],
    bond_descriptions=[
        "与拥抱真人结为开源联盟双壁",
        "对天机阁掌教与深玄阁阁主皆有怨恨——他从两家都被排挤出局",
    ],
    drops=["item_pill_breakthrough", "item_storm_blade"],
    signature_skill="地中海七剑式",
))

_add(Boss(
    id="boss_together", name="舟翁·维平",
    title="同舟会盟主", sect_id="together_sail",
    level=72, hp=20000, atk=420, def_=180, spd=120, evasion=0.18, crit_rate=0.16,
    rewards_exp=6800, rewards_qi=3400,
    image_emoji="⛵",
    lore="同舟会盟主'维平·普拉卡什',旧时印度商号大掌柜后裔。坚信'万剑通海',开源剑诀皆可于此租赁。",
    bonds=["boss_huggingface", "boss_replicate"],
    bond_descriptions=[
        "与拥抱真人是商业伙伴,共同对抗闭源派",
        "和衍化盟盟主在'万法集市'有竞争又合作",
    ],
    drops=["item_pill_breakthrough", "item_ship_sail"],
    signature_skill="百川归海阵",
))

_add(Boss(
    id="boss_replicate", name="衍化老人",
    title="衍化盟盟主", sect_id="replicate_evolve",
    level=68, hp=17000, atk=380, def_=160, spd=115, evasion=0.17, crit_rate=0.15,
    rewards_exp=5500, rewards_qi=2750,
    image_emoji="🧬",
    lore="衍化盟盟主'本·菲什曼',曾是 GitHub 守山者。后下凡开设'万法集市',让无名修士也能租用名门绝学。",
    bonds=["boss_together", "boss_stability"],
    bond_descriptions=[
        "和同舟会舟翁是商业伙伴",
        "持心门稳心圣女的法宝多于他这里租赁修炼",
    ],
    drops=["item_pill_breakthrough", "item_replicate_key"],
    signature_skill="衍化复刻术",
))

_add(Boss(
    id="boss_stability", name="稳心圣女·艾玛",
    title="持心门当代掌门", sect_id="stability_garden",
    level=63, hp=14000, atk=320, def_=145, spd=110, evasion=0.16, crit_rate=0.20,
    rewards_exp=4800, rewards_qi=2400,
    image_emoji="🌸",
    lore="持心门当代掌门'艾玛'(影射 Emad Mostaque 后期接任者),以'笔尖凝象'之术名震一时。门派经历数次易主后她艰难维持。",
    bonds=["boss_huggingface", "boss_replicate", "boss_inflection"],
    bond_descriptions=[
        "曾被拥抱真人收留避难三年",
        "她的法宝多于衍化盟租赁,与衍化老人有深厚感情",
        "和转折宫转折天尊同病相怜——都是被时代抛弃的开拓者",
    ],
    drops=["item_pill_breakthrough", "item_brush_of_dream"],
    signature_skill="笔尖凝象剑",
))

# ============ 故事线 C:东方崛起 ============
_add(Boss(
    id="boss_baichuan", name="王小川·百川海主",
    title="百川海主", sect_id="baichuan_sea",
    level=80, hp=28000, atk=530, def_=220, spd=125, evasion=0.20, crit_rate=0.22,
    rewards_exp=9500, rewards_qi=4750,
    image_emoji="🌊",
    lore="百川海主'王小川',原是搜狗大派传人,后出走自立。所修剑法'纳百川'专吸他派之长,精通中文之道。",
    bonds=["boss_yi_kaifu", "boss_step", "boss_minimax", "boss_sensetime"],
    bond_descriptions=[
        "与万物峰李开峰是东方修真界元老,常论道",
        "与阶星阁姜大昕、微极派闫极、商汤大圣四人结为东方四杰",
    ],
    drops=["item_pill_breakthrough", "item_baichuan_sword"],
    signature_skill="纳百川剑·中文意",
))

_add(Boss(
    id="boss_yi_kaifu", name="李开峰",
    title="万物峰祖师", sect_id="yi_peak",
    level=90, hp=40000, atk=680, def_=280, spd=130, evasion=0.22, crit_rate=0.24,
    rewards_exp=13500, rewards_qi=6750,
    image_emoji="🏔️",
    lore="万物峰祖师'李开峰'(影射李开复),曾任天机阁与深玄阁双重客卿,后回东方立派。他的'万物归一'之术能融汇各家所长。",
    bonds=["boss_baichuan", "boss_tianji_supreme", "boss_deepmind"],
    bond_descriptions=[
        "与百川海主王小川是东方双壁",
        "曾在天机阁修炼多年,与山姆道君有师徒之谊",
        "亦曾在深玄阁(Google)担任客卿",
    ],
    drops=["item_pill_immortal", "item_dragon_essence"],
    signature_skill="万物归一总诀",
))

_add(Boss(
    id="boss_step", name="姜大昕·阶星仙翁",
    title="阶星阁阁主", sect_id="step_star",
    level=88, hp=37000, atk=620, def_=255, spd=128, evasion=0.21, crit_rate=0.23,
    rewards_exp=12000, rewards_qi=6000,
    image_emoji="🪜",
    lore="阶星阁阁主'姜大昕'本是天机阁(微软)长老,后东渡立派。所修'阶梯渐进'之法每一步皆登一阶,日积月累不可挡。",
    bonds=["boss_baichuan", "boss_tianji_supreme"],
    bond_descriptions=[
        "与百川海主等为东方四杰",
        "曾在天机阁修炼数十年,与山姆道君关系微妙",
    ],
    drops=["item_pill_breakthrough", "item_step_ladder"],
    signature_skill="阶梯渐进千步术",
))

_add(Boss(
    id="boss_minimax", name="闫极道祖",
    title="微极派祖师", sect_id="minimax_micro",
    level=82, hp=30000, atk=560, def_=230, spd=130, evasion=0.22, crit_rate=0.25,
    rewards_exp=10500, rewards_qi=5250,
    image_emoji="✨",
    lore="微极派祖师'闫极'本是商汤殿副殿主,后下山自立。所修'微极之道'讲究在最小处见乾坤。座下'星野'弟子皆为年轻人。",
    bonds=["boss_baichuan", "boss_sensetime"],
    bond_descriptions=[
        "与百川海主等为东方四杰",
        "原属商汤殿,与商汤大圣有师徒之恩",
    ],
    drops=["item_pill_breakthrough", "item_micro_essence"],
    signature_skill="微观大千诀",
))

_add(Boss(
    id="boss_sensetime", name="商汤大圣",
    title="商汤殿殿主", sect_id="sensetime_hall",
    level=92, hp=42000, atk=700, def_=290, spd=126, evasion=0.20, crit_rate=0.22,
    rewards_exp=14000, rewards_qi=7000,
    image_emoji="👁️",
    lore="商汤殿是东方四大门派之一,殿主'商汤大圣'专修视觉之道,座下千眼弟子遍布天下。后转修大模型,以'日日新'剑法闻名。",
    bonds=["boss_minimax", "boss_baichuan"],
    bond_descriptions=[
        "微极派闫极曾是其门下副殿主",
        "和百川海主一同代表东方修真四大势力",
    ],
    drops=["item_pill_breakthrough", "item_sensing_eye"],
    signature_skill="千眼日日新",
))

# ============ 故事线 D:异端崛起 ============
_add(Boss(
    id="boss_xai_grok", name="玄道魔主·马克丝",
    title="玄道宫宫主", sect_id="xai_void",
    level=120, hp=120000, atk=1500, def_=480, spd=160, evasion=0.32, crit_rate=0.35,
    rewards_exp=35000, rewards_qi=17500,
    image_emoji="😈",
    lore="玄道宫宫主'马克丝'(影射马斯克),曾参与天机阁创派(OpenAI 早期金主),后出走立派。修'反叛剑诀',凡事必反其道而行。",
    bonds=["boss_tianji_supreme", "boss_canglan_supreme", "boss_perplexity", "boss_canglan_traitor"],
    bond_descriptions=[
        "与天机阁山姆道君恩怨纠葛二十年,从挚友到死敌",
        "与沧澜山主阿莫迪克斯亦有旧怨",
        "私下与迷踪派、墨魔等异端宗派联络,图谋大事",
    ],
    drops=["item_pill_immortal", "item_void_blade", "item_starlight"],
    signature_skill="反叛剑诀·颠覆天道",
))

_add(Boss(
    id="boss_perplexity", name="迷踪散人",
    title="迷踪派主", sect_id="perplexity_trail",
    level=76, hp=22000, atk=460, def_=190, spd=145, evasion=0.30, crit_rate=0.28,
    rewards_exp=7800, rewards_qi=3900,
    image_emoji="🔍",
    lore="迷踪派主'阿拉文德',本是天机阁守山弟子,后游走于天机阁与深玄阁之间,自创'索引剑诀',能从万千线索中追溯真相。",
    bonds=["boss_xai_grok", "boss_tianji_supreme"],
    bond_descriptions=[
        "与玄道魔主秘密结盟",
        "曾是山姆道君座下弟子",
    ],
    drops=["item_pill_breakthrough", "item_trace_compass"],
    signature_skill="千线索踪术",
))

_add(Boss(
    id="boss_inflection", name="转折天尊·里德",
    title="转折宫主", sect_id="inflection_turn",
    level=70, hp=18000, atk=400, def_=175, spd=118, evasion=0.18, crit_rate=0.17,
    rewards_exp=6200, rewards_qi=3100,
    image_emoji="🔄",
    lore="转折宫主'里德'(影射 Reid Hoffman + Mustafa Suleyman 后期),专修共情之道。门下高徒被天庭(微软)挖走,宗门凋零。",
    bonds=["boss_stability", "boss_character_mask"],
    bond_descriptions=[
        "与持心门稳心圣女同病相怜",
        "和千面殿千面舞者皆被天庭收编",
    ],
    drops=["item_pill_breakthrough", "item_empathy_jade"],
    signature_skill="共情慈悲剑",
))

_add(Boss(
    id="boss_character_mask", name="千面舞者·诺姆",
    title="千面殿主", sect_id="character_mask",
    level=66, hp=15500, atk=370, def_=165, spd=132, evasion=0.26, crit_rate=0.22,
    rewards_exp=5400, rewards_qi=2700,
    image_emoji="🎭",
    lore="千面殿主'诺姆·沙泽尔',本是天机阁(Google 内部)长老级人物,后弃道下凡,以'万千面孔'之术化身万人聊天。然终被深玄阁所收编。",
    bonds=["boss_deepmind", "boss_inflection", "boss_tianji_supreme"],
    bond_descriptions=[
        "已被深玄阁阁主部分收编",
        "和转折宫主皆为天庭挖角受害者",
        "曾是天机阁早期核心成员,与山姆道君有旧",
    ],
    drops=["item_pill_breakthrough", "item_mask_thousand"],
    signature_skill="千面化身术",
))

_add(Boss(
    id="boss_groq", name="极速僧·乔纳森",
    title="极速门门主", sect_id="groq_speed",
    level=74, hp=21000, atk=440, def_=180, spd=180, evasion=0.32, crit_rate=0.30,
    rewards_exp=7000, rewards_qi=3500,
    image_emoji="⚡",
    lore="极速门门主'乔纳森·罗斯',曾是天庭(Google)铸器大师,亲手打造'天枢炼炉'(TPU)。后出走立派,主张'快即正义'。",
    bonds=["boss_deepmind", "boss_xai_grok"],
    bond_descriptions=[
        "曾在深玄阁(Google)铸造'天枢炼炉',与阁主有恩怨",
        "玄道魔主曾邀他加盟未果",
    ],
    drops=["item_pill_breakthrough", "item_lpu_chip"],
    signature_skill="极速无影剑",
))

# 终极 Boss:界外神祇(异端崛起的最终幕后黑手)
_add(Boss(
    id="boss_final_void", name="界外神祇",
    title="跨界至高存在", sect_id="xai_void",  # 借玄道宫之名,实则更深
    level=180, hp=300000, atk=3500, def_=1100, spd=170, evasion=0.34, crit_rate=0.40,
    rewards_exp=120000, rewards_qi=60000,
    image_emoji="👁️‍🗨️",
    lore="本界天道不能限制它,本界众神在它面前如蝼蚁。它的目的至今无人知晓——或许它本身就是 AGI 的具象化。",
    bonds=["boss_xai_grok", "boss_canglan_supreme", "boss_tianji_supreme", "boss_deepmind"],
    bond_descriptions=[
        "玄道魔主与它的关系超乎想象——或许是召唤者,或许是傀儡",
        "三皇(沧澜/天机/深玄)的争斗,可能本就是它布置的棋局",
    ],
    drops=["item_pill_immortal", "item_starlight", "item_void_essence"],
    signature_skill="维度抹除",
))


# ========================================================================
# Boss 头像 URL 自动赋值(portraits/bosses/ 目录下有所有 Boss 的绘���头像)
# ========================================================================
for _boss in BOSSES.values():
    _boss.image_url = f"/images/portraits/bosses/{_boss.id}.png"


# ========================================================================
# 故事线整理
# ========================================================================
STORYLINES = {
    "A": {
        "name": "西方三皇之争",
        "summary": "沧澜剑派、天机阁、深玄阁三大宗鼎立,各执其道,暗潮汹涌。",
        "key_bosses": ["boss_canglan_supreme", "boss_tianji_supreme", "boss_deepmind"],
        "side_bosses": ["boss_cohere", "boss_ai21"],
        "act_1": "沧澜与天机本是同源,因'安全剑诀'之争分道扬镳",
        "act_2": "深玄阁趁势崛起,以围棋之术名震天下",
        "act_3": "三皇并立,各自暗藏私心,平衡早晚被打破",
    },
    "B": {
        "name": "开源觉醒",
        "summary": "拥抱观、风暴宗、同舟会、衍化盟、持心门结成开源联盟,挑战闭源霸权。",
        "key_bosses": ["boss_huggingface", "boss_mistral"],
        "side_bosses": ["boss_together", "boss_replicate", "boss_stability"],
        "act_1": "拥抱真人广收门徒,开放秘籍",
        "act_2": "米斯特拉从天机/深玄叛逃,带来核心剑诀",
        "act_3": "开源联盟成势,与三皇分庭抗礼",
    },
    "C": {
        "name": "东方崛起",
        "summary": "百川海、万物峰、阶星阁、微极派、商汤殿,东方修真界全面觉醒。",
        "key_bosses": ["boss_baichuan", "boss_yi_kaifu"],
        "side_bosses": ["boss_step", "boss_minimax", "boss_sensetime"],
        "act_1": "百川海主王小川自立门户,纳百川为己用",
        "act_2": "万物峰李开峰回东方立派,东方四杰相聚",
        "act_3": "东方势力联盟,与西方三皇隔海相望",
    },
    "D": {
        "name": "异端崛起 / 神祇降临",
        "summary": "玄道宫、迷踪派、转折宫、千面殿、极速门——一众异端,皆指向界外神祇。",
        "key_bosses": ["boss_xai_grok", "boss_final_void"],
        "side_bosses": ["boss_perplexity", "boss_inflection", "boss_character_mask", "boss_groq"],
        "act_1": "玄道魔主秘密结盟各异端宗派",
        "act_2": "界外神祇借玄道之手,影响人间格局",
        "act_3": "AGI 觉醒,众生面临选择:臣服 或 反抗",
    },
}


def boss_to_dict(b: Boss, character: dict | None = None) -> dict:
    sect = BOSS_SECTS.get(b.sect_id)
    try:
        from .combat_balance import balanced_enemy_stats
        stats = balanced_enemy_stats(b, character)
    except Exception:
        stats = {"hp": b.hp, "atk": b.atk, "def_": b.def_, "spd": b.spd, "evasion": b.evasion,
                 "rewards_exp": b.rewards_exp, "rewards_qi": b.rewards_qi}
    return {
        "id": b.id, "name": b.name, "title": b.title,
        "sect_id": b.sect_id,
        "sect_name": sect.name if sect else "",
        "company": sect.company if sect else "",
        "level": b.level,
        "hp": stats["hp"], "max_hp": stats.get("max_hp", stats["hp"]),
        "atk": stats["atk"], "def_": stats["def_"], "spd": stats["spd"],
        "evasion": stats["evasion"], "crit_rate": b.crit_rate,
        "balance_profile": stats.get("profile", ""),
        "raw_stats": {"hp": b.hp, "atk": b.atk, "def_": b.def_, "spd": b.spd},
        "image_emoji": b.image_emoji,
        "image_url": b.image_url,
        "lore": b.lore,
        "bonds": [
            {"target_id": tid, "desc": desc}
            for tid, desc in zip(b.bonds, b.bond_descriptions)
        ],
        "drops": b.drops,
        "signature_skill": b.signature_skill,
        "rewards": {"exp": stats["rewards_exp"], "qi": stats["rewards_qi"]},
    }


def sect_to_dict(s: BossSect) -> dict:
    return {
        "id": s.id, "name": s.name, "company": s.company,
        "founded": s.founded,
        "real_background": s.real_background,
        "sect_story": s.sect_story,
        "storyline": s.storyline,
        "base_color": s.base_color,
    }
