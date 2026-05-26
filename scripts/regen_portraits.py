"""
真·LLM 立绘批量生成 — 用 gpt-image-2 (bobdong.cn)

覆盖:
  - 5 派 × 9 境界 = 45 张玩家立绘 (players/{sect}/{realm}.png)
  - 12 族 × 9 个    = 108 张怪物立绘 (enemies/{enemy_id}.png)
  - 21 张 Boss 立绘 (bosses/{boss_id}.png)
  - 5 张宗派代表立绘 (sects/{id}.png)
  合计 179 张

用法:
  cd /Users/bobdong/项目/LingshuCodex
  source backend/.venv/bin/activate
  python scripts/regen_portraits.py [--only players|enemies|bosses|sects] [--concurrency N]
"""
from __future__ import annotations
import argparse
import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# 显式加载 .env(脚本独立运行时需要)
from dotenv import load_dotenv
load_dotenv(ROOT / "backend" / ".env")

from app.image_gen import generate_image, ImageGenError  # noqa: E402
from app.sects import ALL_SECTS  # noqa: E402
from app.enemies import ALL_CLANS  # noqa: E402
from app.bosses import BOSSES  # noqa: E402


PORTRAIT_ROOT = ROOT / "frontend" / "public" / "images" / "portraits"


# ─────────────────────────────────────────────────────────────────────────
# 通用风格 prefix
# ─────────────────────────────────────────────────────────────────────────
STYLE_BASE = (
    "国风仙侠卡牌立绘,中国传统水墨与重彩结合,半透明烟雾环绕,"
    "深色背景配高对比色光晕,人物居中,接近全身或半身竖构图,"
    "唯美精致,细节丰富,无文字无水印,可作游戏卡牌正面图。"
)

# ─────────────────────────────────────────────────────────────────────────
# 5 派配色 / 风格
# ─────────────────────────────────────────────────────────────────────────
SECT_META = {
    "canglan": {
        "name": "沧澜剑派",
        "theme": "金黑配色,玄色长袍配金线纹饰,佩长剑,剑气如墨,沉静深邃",
        "weapon": "古朴长剑,剑刃寒光",
        "tone": "深沉文学化",
    },
    "tianji": {
        "name": "天机阁",
        "theme": "暗橙赤色,玄色羽袍配金属铆钉,身后浮现齿轮机关与符箓",
        "weapon": "机关法器,齿轮浮空",
        "tone": "诡谲精巧",
    },
    "xuanji": {
        "name": "玄机宗",
        "theme": "紫紺色,深紫长袍配银纹,周身浮现数据光纹与符箓",
        "weapon": "无形剑意,光纹流动",
        "tone": "深思极简",
    },
    "qingming": {
        "name": "青冥派",
        "theme": "墨绿青色,儒生书袍配玉佩,身后古卷飞舞",
        "weapon": "古卷书简,墨笔",
        "tone": "博学典雅",
    },
    "yueyin": {
        "name": "月隐宫",
        "theme": "深紫银白,月华纱袍配银面饰,身边浮月光与残影",
        "weapon": "弯月匕首,月牙弧光",
        "tone": "幽暗诡谲",
    },
}

# 9 境界对应人物气场
REALM_AURA = {
    "qi":         ("炼气期", "少年初入修行,清秀单纯,服饰朴素,周身淡淡灵气流转"),
    "foundation": ("筑基期", "青年弟子,神情坚毅,服饰整洁,体内灵气稳定可见"),
    "golden":     ("金丹期", "壮年修士,目光锐利,服饰华美,丹田金光隐现"),
    "yuanying":   ("元婴期", "中年高人,气度从容,服饰精绣,身后元婴影若隐若现"),
    "huashen":    ("化神期", "宗师风范,银须微现,服饰玄妙,周身罡气化形"),
    "hetishi":    ("合体期", "长者修为,神光内蕴,服饰繁复,周身天地交合之气"),
    "dacheng":    ("大乘期", "传说之姿,白发苍颜,法相庄严,身后浮现万千道纹"),
    "dujie":      ("渡劫期", "近仙之态,神光夺目,雷云盘绕,衣袂翻飞,劫云压顶"),
    "feisheng":   ("飞升期", "飞升至高,金光普照,衣袂虚化,身后仙桥若隐,凡眼难视全貌"),
}


# ─────────────────────────────────────────────────────────────────────────
# Prompt 生成
# ─────────────────────────────────────────────────────────────────────────
def prompt_player(sect_id: str, realm_key: str) -> str:
    s = SECT_META[sect_id]
    realm_name, aura = REALM_AURA[realm_key]
    return (
        f"{STYLE_BASE}\n\n"
        f"角色:{s['name']}弟子·{realm_name}\n"
        f"门派风格:{s['theme']};配 {s['weapon']};整体调性{s['tone']}。\n"
        f"境界气质:{aura}\n"
        f"构图要求:人物居中,半身或全身,面部清晰,衣袂飘动,"
        f"背景留有门派意象但不抢主角。深色背景,适合做圆形头像截取。"
    )


# 12 族意象
CLAN_VISUAL = {
    "山林狐妖族":   "白狐 / 多尾狐妖,毛色白红渐变,媚态狡黠",
    "灵雀飞鸟族":   "灵雀凤雏类妖鸟,五彩翎羽,飞翔之姿",
    "蛇蟒族":       "巨蟒蛇妖,鳞片闪烁,蛇眼幽冷",
    "猛兽族":       "猛虎狼豹,兽形或半人半兽,肌肉虬结,獠牙森冷",
    "草木精怪族":   "草木化形,藤蔓盘绕,花瓣或叶子点缀全身,灵芝桃花",
    "鬼族":         "阴气环绕,半透明鬼影,白衣红眸,森森幽气",
    "龙族":         "蛟龙蜃龙,鳞甲生辉,角须分明,周身水气或云气",
    "神兽族":       "朱雀玄武白虎青龙等四象,神光浩然,云中显影",
    "上古凶兽族":   "上古凶兽,如饕餮梼杌混沌,凶狠雄壮,雷云压境",
    "魔修族":       "黑袍魔修,妖瞳血纹,身后魔气化形",
    "仙器之灵族":   "由古剑、铜镜、玉佩等仙器化形,半人半器,光晕浩瀚",
    "异域生灵族":   "异界生物,晶体或异色皮肤,身后浮现星辰或维度裂缝",
}

TIER_INTENSITY = {
    "low":  "气势温和,妖力初现",
    "mid":  "气势凛冽,妖力雄壮",
    "high": "气势骇人,妖力滔天",
    "myth": "神话级气场,天地为之变色,周身万象法相",
}


def prompt_enemy(enemy) -> str:
    clan_visual = CLAN_VISUAL.get(enemy.clan, "妖兽形态")
    tier_intensity = TIER_INTENSITY.get(enemy.tier, "气势凛然")
    return (
        f"{STYLE_BASE}\n\n"
        f"妖兽:{enemy.name}(等级 Lv {enemy.level},{enemy.clan})\n"
        f"族群外观:{clan_visual}\n"
        f"等级气场:{tier_intensity}\n"
        f"背景设定:{enemy.description}\n"
        f"构图要求:妖兽居中,半身或全身突出,姿态有压迫感,"
        f"背景烟雾或灵气环绕,深色基调,适合做圆形头像截取。"
    )


def prompt_boss(boss) -> str:
    return (
        f"{STYLE_BASE}\n\n"
        f"BOSS 立绘:{boss.name} · {boss.title}(Lv {boss.level})\n"
        f"角色设定:{boss.description if hasattr(boss,'description') else boss.name}\n"
        f"风格:史诗级 BOSS,人物或妖魔形态,气场远超常修,"
        f"周身道纹或魔气盘旋,衣袍华美或妖异,"
        f"面部表情有戏剧张力。\n"
        f"构图要求:半身或全身居中,深色背景配主题色光晕,"
        f"震慑感强,适合做圆形头像与卡片大图截取。"
    )


def prompt_sect_rep(sect_id: str) -> str:
    s = SECT_META[sect_id]
    return (
        f"{STYLE_BASE}\n\n"
        f"门派代表立绘:{s['name']}\n"
        f"风格:{s['theme']};{s['weapon']};{s['tone']}。\n"
        f"构图:门派核心人物(掌门或代表弟子)的全身立绘,"
        f"气场宏大,适合作为选派页中央展示。"
        f"背景可融入门派标志意象(山川、阵法、机关、月夜等)。"
    )


# ─────────────────────────────────────────────────────────────────────────
# 任务收集
# ─────────────────────────────────────────────────────────────────────────
def collect_tasks(only: str | None = None) -> list[dict]:
    """返回 [{kind, path, prompt}] 列表,只包括缺失的图"""
    tasks = []

    # 1. 玩家
    if only in (None, "players"):
        for sk in SECT_META.keys():
            for rk in REALM_AURA.keys():
                p = PORTRAIT_ROOT / "players" / sk / f"{rk}.png"
                if not p.exists():
                    tasks.append({"kind": "player", "path": p, "prompt": prompt_player(sk, rk),
                                  "label": f"{SECT_META[sk]['name']}-{REALM_AURA[rk][0]}"})

    # 2. 怪物
    if only in (None, "enemies"):
        for clan, members in ALL_CLANS.items():
            for e in members:
                p = PORTRAIT_ROOT / "enemies" / f"{e.id}.png"
                if not p.exists():
                    tasks.append({"kind": "enemy", "path": p, "prompt": prompt_enemy(e),
                                  "label": f"{e.id}-{e.name}"})

    # 3. Boss
    if only in (None, "bosses"):
        for bid, boss in BOSSES.items():
            p = PORTRAIT_ROOT / "bosses" / f"{bid}.png"
            if not p.exists():
                tasks.append({"kind": "boss", "path": p, "prompt": prompt_boss(boss),
                              "label": f"{bid}-{boss.name}"})

    # 4. 宗派代表
    if only in (None, "sects"):
        for sk in SECT_META.keys():
            p = PORTRAIT_ROOT / "sects" / f"{sk}.png"
            if not p.exists():
                tasks.append({"kind": "sect", "path": p, "prompt": prompt_sect_rep(sk),
                              "label": f"sect-{SECT_META[sk]['name']}"})

    return tasks


# ─────────────────────────────────────────────────────────────────────────
# 异步执行
# ─────────────────────────────────────────────────────────────────────────
async def gen_one(task: dict, sem: asyncio.Semaphore, idx: int, total: int) -> dict:
    """生成单张图,带语义锁限并发"""
    async with sem:
        start = time.time()
        try:
            results = await generate_image(
                prompt=task["prompt"],
                size="1024x1536",          # 竖构图,适合人物立绘
                quality="auto",
                output_format="png",
                save_to=str(task["path"].parent),
                filename_prefix=task["path"].stem,
            )
            # save_to 会按 prefix_ts_idx.png 命名,我们改成精确文件名
            if results and results[0].get("local_path"):
                src = Path(results[0]["local_path"])
                if src != task["path"]:
                    src.rename(task["path"])
            dur = time.time() - start
            print(f"  ✅ [{idx:3d}/{total}] {task['label']:30s}  ({dur:.1f}s)", flush=True)
            return {"ok": True, "task": task, "duration": dur}
        except ImageGenError as e:
            dur = time.time() - start
            print(f"  ❌ [{idx:3d}/{total}] {task['label']:30s}  {e}", flush=True)
            return {"ok": False, "task": task, "error": str(e), "duration": dur}
        except Exception as e:
            dur = time.time() - start
            print(f"  💥 [{idx:3d}/{total}] {task['label']:30s}  {type(e).__name__}: {e}", flush=True)
            return {"ok": False, "task": task, "error": f"{type(e).__name__}: {e}", "duration": dur}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["players", "enemies", "bosses", "sects"], default=None)
    parser.add_argument("--concurrency", type=int, default=4, help="并发数(上游限速,4 比较稳)")
    parser.add_argument("--dry-run", action="store_true", help="只列任务,不生成")
    args = parser.parse_args()

    tasks = collect_tasks(only=args.only)
    if not tasks:
        print("✅ 没有缺失图,无需生成")
        return

    print(f"📊 准备生成 {len(tasks)} 张图(并发 {args.concurrency})")
    if args.dry_run:
        for t in tasks[:20]:
            print(f"   - {t['kind']}: {t['label']}")
        if len(tasks) > 20:
            print(f"   ...还有 {len(tasks)-20} 张")
        return

    sem = asyncio.Semaphore(args.concurrency)
    overall_start = time.time()
    coros = [gen_one(t, sem, i+1, len(tasks)) for i, t in enumerate(tasks)]
    results = await asyncio.gather(*coros)

    ok = sum(1 for r in results if r["ok"])
    bad = len(results) - ok
    elapsed = time.time() - overall_start
    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ 成功 {ok} / 总 {len(results)}  耗时 {elapsed:.1f}s")
    if bad:
        print(f"❌ 失败 {bad}:")
        for r in results:
            if not r["ok"]:
                print(f"   - {r['task']['label']}: {r['error']}")


if __name__ == "__main__":
    asyncio.run(main())
