#!/usr/bin/env python3
"""Generate the monster story / bond design document from game data."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.enemies import ALL_CLANS, enemy_to_dict  # noqa: E402
from app.bosses import BOSSES, BOSS_SECTS, boss_to_dict, STORYLINES  # noqa: E402


OUT = ROOT / "docs" / "MONSTER_STORY_BONDS_CODEX.md"


def _line(text: str = "") -> str:
    return f"{text}\n"


def _fmt_list(items: list[str]) -> str:
    return "、".join([i for i in items if i]) or "无"


def build_doc() -> str:
    lines: list[str] = []
    lines.append(_line("# 灵枢笔录怪物志:背景故事、专属技能与羁绊设计"))
    lines.append(_line())
    lines.append(_line("> 版本:v0.3 · 目标:让每一个怪物都能成为本命书里的叙事素材,而不是只有生命值的战斗单位。"))
    lines.append(_line())
    lines.append(_line("## 设计原则"))
    lines.append(_line("- 每个普通怪物拥有完整故事、专属技能、属性、特性、弱点、羁绊与独特性。"))
    lines.append(_line("- 羁绊分为三层:同族谱系、跨族恩怨、Boss/道君因果。玩家击败或赠礼怪物后,这些关系都可作为后续章节素材。"))
    lines.append(_line("- 战斗数值仍由原战斗系统权威计算;怪物志字段只强化叙事、图鉴、角色卡与本命书写作。"))
    lines.append(_line("- 地图、战斗、图鉴中的怪物头像都应接入统一角色卡,展示完整怪物故事。"))
    lines.append(_line())
    lines.append(_line("## 字段说明"))
    lines.append(_line("| 字段 | 用途 |"))
    lines.append(_line("| --- | --- |"))
    lines.append(_line("| full_lore | 怪物完整背景故事,可直接用于角色卡与本命书章节参考。 |"))
    lines.append(_line("| signature_skill | 每个怪物独有的本命招式,名字由怪物名和族谱阶段生成。 |"))
    lines.append(_line("| skills | 专属技能 + 族群招式谱,战斗叙事可引用。 |"))
    lines.append(_line("| attributes | 五行/异相、性情、战斗定位、弱点、族谱位置。 |"))
    lines.append(_line("| traits | 怪物特性,用于图鉴、掉落、章节风格与未来战斗机制。 |"))
    lines.append(_line("| bonds | 指向其它怪物或 Boss 的羁绊,包含关系名和关系描述。 |"))
    lines.append(_line("| unique_hook | 一句话说明该怪物不可替代的独特性。 |"))
    lines.append(_line())

    lines.append(_line("## 怪物族群总览"))
    for clan, members in ALL_CLANS.items():
        first = enemy_to_dict(members[0])
        lines.append(_line(f"- **{clan}**: {len(members)} 个阶段 · {first.get('element')} · {first.get('battle_role')} · 弱点:{first.get('weakness')}"))
    lines.append(_line())

    lines.append(_line("## 普通怪物完整设定"))
    lines.append(_line())

    for clan, members in ALL_CLANS.items():
        lines.append(_line(f"### {clan}"))
        lines.append(_line())
        for enemy in members:
            d = enemy_to_dict(enemy)
            attrs = {item["name"]: item["value"] for item in d.get("attributes", [])}
            sig = d.get("signature_skill", {})
            lines.append(_line(f"#### {d['name']} ({d['id']})"))
            lines.append(_line(f"- 基础:Lv.{d['level']} · {d['tier']} · HP {d['hp']} · 攻 {d['atk']} · 防 {d['def_']} · 速 {d['spd']} · 闪避 {int(d['evasion'] * 100)}%"))
            lines.append(_line(f"- 属性:{attrs.get('五行/异相')} · 性情:{attrs.get('性情')} · 定位:{attrs.get('战斗定位')} · 弱点:{attrs.get('弱点')}"))
            lines.append(_line(f"- 专属技能:{sig.get('name')} ({sig.get('tier_name')}) — {sig.get('description')}"))
            lines.append(_line(f"- 特性:{_fmt_list([t['name'] for t in d.get('traits', [])])}"))
            lines.append(_line(f"- 独特性:{d.get('unique_hook')}"))
            lines.append(_line(f"- 背景:{d.get('full_lore')}"))
            if d.get("bonds"):
                lines.append(_line("- 羁绊:"))
                for bond in d["bonds"]:
                    lines.append(_line(f"  - {bond.get('relation')}: {bond.get('target_name') or bond.get('target_id')} — {bond.get('desc')}"))
            if d.get("skills"):
                lines.append(_line(f"- 招式谱:{_fmt_list([s['name'] for s in d['skills']])}"))
            lines.append(_line(f"- 掉落:{_fmt_list(d.get('drops', []))}"))
            lines.append(_line())

    lines.append(_line("## Boss/道君因果索引"))
    lines.append(_line())
    for key, story in STORYLINES.items():
        lines.append(_line(f"### 故事线 {key}: {story['name']}"))
        lines.append(_line(f"- 概述:{story['summary']}"))
        lines.append(_line(f"- 关键 Boss:{_fmt_list(story.get('key_bosses', []))}"))
        lines.append(_line())

    for boss in BOSSES.values():
        d = boss_to_dict(boss)
        sect = BOSS_SECTS.get(boss.sect_id)
        lines.append(_line(f"#### {d['name']} ({d['id']})"))
        lines.append(_line(f"- 称号:{d['title']} · 宗派:{d['sect_name']} · Lv.{d['level']} · 标志性招式:{d.get('signature_skill')}"))
        if sect:
            lines.append(_line(f"- 宗派背景:{sect.sect_story}"))
        lines.append(_line(f"- 本纪:{d.get('lore')}"))
        if d.get("bonds"):
            lines.append(_line("- Boss 羁绊:"))
            for bond in d["bonds"]:
                target = BOSSES.get(bond["target_id"])
                lines.append(_line(f"  - {target.name if target else bond['target_id']}: {bond['desc']}"))
        lines.append(_line())

    lines.append(_line("## 落地清单"))
    lines.append(_line("- 地图怪物头像:点击打开统一怪物志。"))
    lines.append(_line("- 战斗敌方头像:点击打开当前怪物完整档案。"))
    lines.append(_line("- 山海经图鉴:详情面板展示专属技能、属性、特性、羁绊与掉落。"))
    lines.append(_line("- 本命书写作:战斗/赠礼/奇遇可引用 full_lore、signature_skill、bonds 生成更连续的章节。"))
    lines.append(_line())
    return "".join(lines)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_doc(), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
