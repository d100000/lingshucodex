"""Generate disciple data from the character bible.

This is the deterministic local asset pass for the five-sect disciple system.
It extracts the 200 disciple templates and relationship briefs from
docs/SECT_DISCIPLE_CHARACTER_BIBLE.md and writes a frontend JSON data module.

Project rule:
  Local placeholder portrait rendering is disabled. All character portraits
  must be generated with gpt-image-2 via scripts/generate_disciple_image2_portraits.py.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIBLE = ROOT / "docs" / "SECT_DISCIPLE_CHARACTER_BIBLE.md"
OUT_JSON = ROOT / "frontend" / "src" / "data" / "disciples.json"
OUT_PORTRAITS = ROOT / "frontend" / "public" / "images" / "portraits" / "disciples"

SECTS = {
    "canglan": {"name": "沧澜剑派", "color": (212, 162, 76), "dark": (18, 28, 48)},
    "tianji": {"name": "天机阁", "color": (255, 180, 84), "dark": (47, 30, 22)},
    "xuanji": {"name": "玄机宗", "color": (155, 89, 182), "dark": (34, 25, 55)},
    "qingming": {"name": "青冥派", "color": (82, 183, 136), "dark": (20, 48, 39)},
    "yueyin": {"name": "月隐宫", "color": (181, 156, 255), "dark": (30, 24, 50)},
}

SECTION_TO_SECT = {
    "沧澜剑派": "canglan",
    "天机阁": "tianji",
    "玄机宗": "xuanji",
    "青冥派": "qingming",
    "月隐宫": "yueyin",
}


def stable_int(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


def clamp(v: int) -> int:
    return max(0, min(255, int(v)))


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(clamp(a[i] * (1 - t) + b[i] * t) for i in range(3))


def parse_disciple_rows(markdown: str) -> list[dict]:
    disciples: list[dict] = []
    active_sect = None
    row_re = re.compile(
        r"^\|\s*(?P<id>[a-z]+_\d+)\s*\|\s*(?P<name>[^|]+?)\s*\|\s*(?P<gender>[^|]+?)\s*\|"
        r"\s*(?P<rank>[^|]+?Lv(?P<level>\d+)/(?P<age>\d+)岁)\s*\|"
        r"\s*(?P<appearance>[^|]+?)\s*\|\s*(?P<personality>[^|]+?)\s*\|"
        r"\s*(?P<story>[^|]+?)\s*\|"
    )

    for line in markdown.splitlines():
        h = re.match(r"^##\s+(.+?)\s+40 人\s*$", line)
        if h:
            active_sect = SECTION_TO_SECT.get(h.group(1))
            continue
        if line.startswith("## ") and "40 人" not in line:
            active_sect = None
        if not active_sect:
            continue
        m = row_re.match(line)
        if not m:
            continue
        rank_text = m.group("rank").strip()
        rank = rank_text.split("Lv", 1)[0].strip()
        disciple_id = m.group("id").strip()
        disciples.append(
            {
                "id": disciple_id,
                "sect_id": active_sect,
                "sect_name": SECTS[active_sect]["name"],
                "name": m.group("name").strip(),
                "gender": m.group("gender").strip(),
                "rank": rank,
                "level": int(m.group("level")),
                "base_age_years": int(m.group("age")),
                "appearance": m.group("appearance").strip(),
                "personality": m.group("personality").strip(),
                "story_hook": m.group("story").strip(),
                "portrait_id": f"{active_sect}/{disciple_id}",
            }
        )
    return disciples


def parse_relationship_rows(markdown: str) -> dict[str, list[dict]]:
    relationships: dict[str, list[dict]] = {}
    row_re = re.compile(r"^\|\s*(?P<id>[a-z]+_\d+)\s*\|\s*[^|]+?\s*\|\s*(?P<body>.+?)\s*\|")
    entry_re = re.compile(r"\s*(?P<target>[^\[/;]+?)(?:/(?P<name>[^\[]+?))?\[(?P<note>[^\]]+)\]")
    for line in markdown.splitlines():
        m = row_re.match(line)
        if not m:
            continue
        source = m.group("id").strip()
        body = m.group("body").strip()
        entries = []
        for raw in body.split(";"):
            em = entry_re.match(raw.strip())
            if not em:
                continue
            note = em.group("note").strip()
            nums = re.findall(r"[-+]\d+", note)
            affinity = int(nums[0]) if nums else 0
            relation = re.sub(r"[,，]?\s*[-+]\d+(?:/[-+]\d+)?", "", note).strip(" ,，")
            target = em.group("target").strip()
            entries.append(
                {
                    "target_id": target,
                    "target_name": (em.group("name") or target).strip(),
                    "relation": relation or "旧识",
                    "affinity": affinity,
                }
            )
        if entries:
            relationships[source] = entries
    return relationships


def draw_portrait(disciple: dict, path: Path) -> None:
    raise RuntimeError(
        "本地占位绘制器已禁用。请使用 scripts/generate_disciple_image2_portraits.py 通过 gpt-image-2 生成头像。"
    )
    size = 512
    seed = stable_int(disciple["id"] + disciple["name"] + disciple["appearance"])
    sect = SECTS[disciple["sect_id"]]
    accent = sect["color"]
    dark = sect["dark"]
    rng = seed

    def rnd(a: int, b: int) -> int:
        nonlocal rng
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        return a + rng % (b - a + 1)

    img = Image.new("RGB", (size, size), dark)
    px = img.load()
    for y in range(size):
        for x in range(size):
            dx = (x - size / 2) / size
            dy = (y - size / 2) / size
            radial = max(0, 1 - math.sqrt(dx * dx + dy * dy) * 2.1)
            vertical = y / size
            c = mix(dark, accent, 0.12 + radial * 0.32)
            c = mix(c, (5, 8, 16), vertical * 0.34)
            px[x, y] = c

    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r, alpha in [(230, 40), (170, 50), (110, 70)]:
        gd.ellipse((256 - r, 226 - r, 256 + r, 226 + r), fill=(*accent, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(img)

    # Sect sigils / back ornaments.
    for i in range(6):
        a = rnd(0, 360) * math.pi / 180
        r = rnd(130, 220)
        x = 256 + math.cos(a) * r
        y = 245 + math.sin(a) * r
        d.line((256, 256, x, y), fill=(*accent, 35), width=rnd(1, 3))
    if disciple["sect_id"] in {"tianji", "xuanji"}:
        for r in (88, 126, 164):
            d.ellipse((256 - r, 246 - r, 256 + r, 246 + r), outline=(*accent, 54), width=2)
    if disciple["sect_id"] == "canglan":
        for off in (-34, 0, 34):
            d.line((256 + off, 86, 212 + off, 378), fill=(*accent, 70), width=4)
    if disciple["sect_id"] == "qingming":
        for off in (-70, -35, 0, 35, 70):
            d.rounded_rectangle((196 + off, 120, 216 + off, 372), radius=7, outline=(*accent, 55), width=2)
    if disciple["sect_id"] == "yueyin":
        d.arc((112, 66, 400, 354), 245, 74, fill=(*accent, 90), width=8)

    # Body.
    is_female = disciple["gender"] == "女"
    face = (232 + rnd(-16, 8), 198 + rnd(-10, 14), 168 + rnd(-12, 18))
    hair_base = (22 + rnd(0, 35), 20 + rnd(0, 25), 28 + rnd(0, 55))
    if "白发" in disciple["appearance"] or "银发" in disciple["appearance"]:
        hair_base = (205 + rnd(-10, 20), 210 + rnd(-20, 20), 220 + rnd(-20, 25))
    elif "红" in disciple["appearance"]:
        hair_base = (86, 32, 42)

    robe = mix(accent, (18, 20, 31), 0.45)
    if "白" in disciple["appearance"]:
        robe = mix(robe, (230, 232, 222), 0.25)
    if "黑" in disciple["appearance"] or "暗" in disciple["appearance"]:
        robe = mix(robe, (8, 9, 14), 0.35)
    if "青" in disciple["appearance"] or "绿" in disciple["appearance"]:
        robe = mix(robe, (54, 145, 118), 0.28)
    if "蓝" in disciple["appearance"]:
        robe = mix(robe, (55, 108, 170), 0.25)
    if "紫" in disciple["appearance"]:
        robe = mix(robe, (118, 74, 170), 0.26)

    shoulder_y = 332 + rnd(-6, 8)
    d.pieslice((126, shoulder_y - 30, 386, 590), 190, 350, fill=(*robe, 245))
    d.polygon([(256, 292), (188, 500), (324, 500)], fill=(*mix(robe, (255, 255, 255), 0.16), 230))
    d.line((256, 308, 256 + rnd(-20, 20), 504), fill=(*accent, 110), width=3)
    for off in (-58, 58):
        d.line((256, 318, 256 + off, 492), fill=(*accent, 70), width=2)

    # Neck / face.
    d.rounded_rectangle((226, 268, 286, 342), radius=22, fill=(*face, 255))
    face_box = (189, 126, 323, 300)
    d.ellipse(face_box, fill=(*face, 255))

    # Hair.
    d.pieslice((176, 82, 336, 240), 180, 360, fill=(*hair_base, 255))
    d.rectangle((176, 158, 336, 216), fill=(*hair_base, 255))
    hair_len = 360 if is_female else 306
    d.rounded_rectangle((166, 148, 210, hair_len), radius=25, fill=(*hair_base, 245))
    d.rounded_rectangle((302, 148, 346, hair_len), radius=25, fill=(*hair_base, 245))
    if "高马尾" in disciple["appearance"] or ("长发" in disciple["appearance"] and is_female):
        d.rounded_rectangle((238, 56, 282, 166), radius=20, fill=(*hair_base, 250))
    if "面纱" in disciple["appearance"] or "黑纱" in disciple["appearance"]:
        d.rounded_rectangle((188, 218, 324, 286), radius=20, fill=(12, 13, 22, 138))

    # Eyes / brows.
    eye_color = mix(accent, (240, 240, 220), 0.25)
    if "金瞳" in disciple["appearance"]:
        eye_color = (240, 194, 72)
    if "银瞳" in disciple["appearance"]:
        eye_color = (207, 216, 232)
    d.line((215, 204, 248, 200), fill=(35, 28, 31, 240), width=3)
    d.line((264, 200, 297, 204), fill=(35, 28, 31, 240), width=3)
    d.ellipse((226, 214, 238, 224), fill=(*eye_color, 255))
    d.ellipse((274, 214, 286, 224), fill=(*eye_color, 255))
    d.arc((235, 238, 277, 270), 20, 160, fill=(110, 54, 58, 190), width=2)

    # Accessories by keywords.
    app = disciple["appearance"]
    if "剑" in app:
        d.line((118, 406, 390, 92), fill=(228, 230, 224, 185), width=6)
        d.line((132, 420, 168, 382), fill=(*accent, 210), width=10)
    if "机关" in app or "齿轮" in app:
        for cx, cy in [(146, 155), (360, 344)]:
            rr = 28
            d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(*accent, 150), width=4)
            for k in range(8):
                aa = k * math.pi / 4
                d.line((cx, cy, cx + math.cos(aa) * rr, cy + math.sin(aa) * rr), fill=(*accent, 95), width=2)
    if "书" in app or "卷" in app or "简" in app:
        d.rounded_rectangle((95, 312, 164, 410), radius=8, fill=(226, 208, 164, 190), outline=(*accent, 160), width=3)
        for yy in range(330, 392, 16):
            d.line((110, yy, 150, yy), fill=(88, 58, 36, 120), width=2)
    if "月" in app:
        d.arc((350, 88, 452, 190), 80, 285, fill=(230, 230, 255, 155), width=7)
    if "药" in app:
        d.ellipse((106, 374, 162, 430), fill=(72, 140, 94, 190), outline=(*accent, 130), width=2)
    if "面具" in app:
        d.rounded_rectangle((206, 182, 306, 248), radius=24, fill=(232, 228, 218, 150), outline=(*accent, 130), width=2)

    # Rank badge dots, no text to avoid font dependency.
    rank_dots = {"外门": 1, "内门": 2, "核心": 3, "真传": 4, "护法": 5, "长老": 6}.get(disciple["rank"], 2)
    for i in range(rank_dots):
        d.ellipse((36 + i * 18, 452, 48 + i * 18, 464), fill=(*accent, 210))

    # Vignette and frame.
    vign = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vign)
    vd.rectangle((0, 0, size, size), outline=(*accent, 210), width=6)
    vd.rectangle((10, 10, size - 10, size - 10), outline=(255, 235, 180, 55), width=2)
    img = Image.alpha_composite(img, vign)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(path, "PNG", optimize=True)


def main() -> None:
    markdown = BIBLE.read_text(encoding="utf-8")
    disciples = parse_disciple_rows(markdown)
    relationships = parse_relationship_rows(markdown)
    by_id = {d["id"]: d for d in disciples}
    for d in disciples:
        d["relationships"] = relationships.get(d["id"], [])

    payload = {
        "sects": SECTS,
        "disciples": disciples,
        "disciples_by_id": by_id,
        "generated_from": str(BIBLE.relative_to(ROOT)),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"generated disciples: {len(disciples)}")
    print(f"json: {OUT_JSON}")
    print("portraits: skipped; use scripts/generate_disciple_image2_portraits.py (gpt-image-2 only)")


if __name__ == "__main__":
    main()
