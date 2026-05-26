from __future__ import annotations

import hashlib
import json
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.bosses import BOSSES, BOSS_SECTS  # noqa: E402
from backend.app.enemies import ENEMIES  # noqa: E402
from backend.app.sects import ALL_SECTS  # noqa: E402


OUT_ROOT = ROOT / "frontend" / "public" / "images"
PORTRAIT_ROOT = OUT_ROOT / "portraits"
BACKGROUND_ROOT = OUT_ROOT / "backgrounds"
DOCS_ROOT = ROOT / "docs"

PORTRAIT_SIZE = (512, 768)
BACKGROUND_SIZE = (1920, 1080)

REALMS = [
    ("qi", "炼气"),
    ("foundation", "筑基"),
    ("golden", "金丹"),
    ("yuanying", "元婴"),
    ("huashen", "化神"),
    ("hetishi", "合体"),
    ("dacheng", "大乘"),
    ("dujie", "渡劫"),
    ("feisheng", "飞升"),
]

FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
]

SECT_SYMBOLS = {
    "canglan": "剑",
    "tianji": "机",
    "xuanji": "玄",
    "qingming": "青",
    "yueyin": "月",
}

SECT_POSE = {
    "canglan": "sword",
    "tianji": "gear",
    "xuanji": "mind",
    "qingming": "scroll",
    "yueyin": "moon",
}

REALM_META = {
    "qi": ("初入山门", "#7B8794", 0.55),
    "foundation": ("筑基成形", "#52B788", 0.65),
    "golden": ("金丹凝华", "#F0B64D", 0.76),
    "yuanying": ("元婴显象", "#8B5CF6", 0.86),
    "huashen": ("化神通玄", "#42C7D8", 0.98),
    "hetishi": ("合体归真", "#D95F5F", 1.08),
    "dacheng": ("大乘圆融", "#FFD36A", 1.2),
    "dujie": ("雷劫临身", "#E8F2FF", 1.34),
    "feisheng": ("飞升仙尊", "#FFFFFF", 1.5),
}

CLAN_STYLES = {
    "山林狐妖族": ("fox", "#D77B46", "狐"),
    "灵雀飞鸟族": ("bird", "#E4B45A", "雀"),
    "蛇蟒族": ("serpent", "#4FB78A", "蛇"),
    "猛兽族": ("beast", "#C89D68", "兽"),
    "草木精怪族": ("herb", "#66B66A", "木"),
    "鬼族": ("ghost", "#8CA0D8", "鬼"),
    "龙族": ("dragon", "#53BBD0", "龙"),
    "神兽族": ("divine", "#F3C96B", "神"),
    "上古凶兽族": ("ancient", "#C84A4A", "凶"),
    "魔修族": ("demon", "#9C4DCC", "魔"),
    "仙器之灵族": ("artifact", "#C9B27C", "器"),
    "异域生灵族": ("alien", "#62D6D1", "界"),
}

TIER_META = {
    "low": ("初阶", 0.58),
    "mid": ("中阶", 0.78),
    "high": ("高阶", 1.0),
    "myth": ("神话", 1.26),
    "boss": ("首领", 1.42),
}


def rng_for(key: str) -> random.Random:
    seed = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:16], 16)
    return random.Random(seed)


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


FONTS = {
    "seal": font(74),
    "title": font(40),
    "subtitle": font(26),
    "small": font(22),
    "tiny": font(18),
    "vertical": font(31),
    "bg_title": font(84),
}


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def rgba(color: str | tuple[int, int, int], alpha: int) -> tuple[int, int, int, int]:
    base = hex_to_rgb(color) if isinstance(color, str) else color
    return (*base, alpha)


def safe_name(text: str, max_len: int = 18) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def draw_center_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fnt: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    stroke_fill: tuple[int, int, int, int] | None = None,
    stroke_width: int = 0,
) -> None:
    w, h = text_size(draw, text, fnt)
    draw.text(
        (xy[0] - w / 2, xy[1] - h / 2),
        text,
        font=fnt,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=stroke_width,
    )


def draw_vertical_text(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    fnt: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    line_gap: int = 2,
) -> None:
    cy = y
    for ch in text:
        w, h = text_size(draw, ch, fnt)
        draw.text((x - w / 2, cy), ch, font=fnt, fill=fill)
        cy += h + line_gap


def vertical_gradient(
    size: tuple[int, int],
    top: tuple[int, int, int],
    bottom: tuple[int, int, int],
    alpha: int = 255,
) -> Image.Image:
    w, h = size
    img = Image.new("RGBA", size)
    pix = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        color = mix(top, bottom, t)
        for x in range(w):
            pix[x, y] = (*color, alpha)
    return img


def add_noise(img: Image.Image, opacity: int = 22, seed: int = 0) -> Image.Image:
    noise = Image.effect_noise(img.size, 75).convert("L")
    noise = ImageEnhance.Contrast(noise).enhance(1.4)
    layer = Image.new("RGBA", img.size, (255, 242, 210, 0))
    layer.putalpha(noise.point(lambda p: min(opacity, max(0, int((p - 128) * 0.16 + opacity / 2)))))
    return Image.alpha_composite(img, layer)


def soft_glow(size: tuple[int, int], center: tuple[int, int], color: str, radius: int, alpha: int) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse(
        (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius),
        fill=rgba(color, alpha),
    )
    return layer.filter(ImageFilter.GaussianBlur(radius // 2))


def draw_clouds(
    img: Image.Image,
    rnd: random.Random,
    color: tuple[int, int, int] = (234, 226, 205),
    count: int = 26,
    alpha: int = 22,
    band_y: tuple[int, int] = (100, 620),
) -> None:
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    w, h = img.size
    for _ in range(count):
        cx = rnd.randint(-120, w + 120)
        cy = rnd.randint(*band_y)
        rx = rnd.randint(90, 240)
        ry = rnd.randint(18, 54)
        draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=(*color, rnd.randint(9, alpha)))
        for _ in range(rnd.randint(2, 5)):
            ox = rnd.randint(-rx // 2, rx // 2)
            oy = rnd.randint(-ry, ry)
            rr = rnd.randint(35, 90)
            draw.ellipse((cx + ox - rr, cy + oy - rr // 3, cx + ox + rr, cy + oy + rr // 3), fill=(*color, rnd.randint(6, alpha)))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(12)))


def draw_mountains(img: Image.Image, rnd: random.Random, color: tuple[int, int, int], base_y: int, alpha: int) -> None:
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    w, h = img.size
    for row in range(3):
        points = [(-60, h + 40)]
        x = -40
        while x < w + 80:
            peak_y = base_y - row * 55 - rnd.randint(20, 110)
            points.append((x, peak_y))
            x += rnd.randint(70, 135)
        points.append((w + 80, h + 40))
        shade = mix(color, (0, 0, 0), 0.15 + row * 0.16)
        draw.polygon(points, fill=(*shade, max(10, alpha - row * 16)))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(1.1)))


def draw_card_frame(img: Image.Image, accent: str, title: str, subtitle: str, seal: str, rarity: float = 1.0) -> None:
    draw = ImageDraw.Draw(img)
    w, h = img.size
    gold = rgba("#D6B46E", 150)
    bright = rgba("#FFE0A3", int(95 + min(70, rarity * 28)))
    red = rgba("#8E2D2D", 154)

    draw.rounded_rectangle((18, 18, w - 18, h - 18), radius=24, outline=gold, width=3)
    draw.rounded_rectangle((31, 31, w - 31, h - 31), radius=18, outline=rgba(accent, 112), width=1)
    draw.line((62, 34, 168, 34), fill=bright, width=2)
    draw.line((w - 168, h - 34, w - 62, h - 34), fill=bright, width=2)
    draw.arc((35, 35, 125, 125), 180, 270, fill=gold, width=2)
    draw.arc((w - 125, 35, w - 35, 125), 270, 360, fill=gold, width=2)
    draw.arc((35, h - 125, 125, h - 35), 90, 180, fill=gold, width=2)
    draw.arc((w - 125, h - 125, w - 35, h - 35), 0, 90, fill=gold, width=2)

    draw.rounded_rectangle((38, 588, w - 38, 718), radius=18, fill=(9, 8, 12, 108), outline=rgba(accent, 86), width=1)
    draw_center_text(draw, (w // 2, 628), safe_name(title, 12), FONTS["title"], rgba("#F7E4B6", 236), rgba("#070707", 190), 2)
    draw_center_text(draw, (w // 2, 678), safe_name(subtitle, 16), FONTS["small"], rgba("#C9D5D2", 198))

    draw.rounded_rectangle((382, 50, 454, 150), radius=8, fill=red, outline=rgba("#F5D58E", 120), width=1)
    draw_center_text(draw, (418, 100), seal, FONTS["seal"], rgba("#F7E7C0", 230), rgba("#3A0D0D", 170), 1)


def base_card(key: str, primary: str, accent: str, title: str, subtitle: str, seal: str, rarity: float = 1.0) -> Image.Image:
    rnd = rng_for(key)
    primary_rgb = hex_to_rgb(primary)
    accent_rgb = hex_to_rgb(accent)
    top = mix(primary_rgb, (0, 0, 0), 0.28)
    bottom = mix(primary_rgb, (0, 0, 0), 0.62)
    img = vertical_gradient(PORTRAIT_SIZE, top, bottom)
    img = add_noise(img, opacity=24, seed=rnd.randint(0, 9999))
    img.alpha_composite(soft_glow(PORTRAIT_SIZE, (256, 260), accent, int(150 + rarity * 30), int(42 + rarity * 12)))
    img.alpha_composite(soft_glow(PORTRAIT_SIZE, (120, 92), "#F5E0AA", 110, 22))
    draw_mountains(img, rnd, mix(accent_rgb, (30, 34, 38), 0.55), 480, 44)
    draw_clouds(img, rnd, alpha=24, band_y=(80, 470))
    draw_card_frame(img, accent, title, subtitle, seal, rarity)
    return img


def polygon_regular(center: tuple[int, int], radius: int, sides: int, rotation: float = 0) -> list[tuple[int, int]]:
    return [
        (
            int(center[0] + math.cos(rotation + i * math.tau / sides) * radius),
            int(center[1] + math.sin(rotation + i * math.tau / sides) * radius),
        )
        for i in range(sides)
    ]


def draw_robed_cultivator(
    img: Image.Image,
    accent: str,
    pose: str,
    realm_slug: str,
    name_seed: str,
    power: float,
) -> None:
    rnd = rng_for("player:" + name_seed)
    draw = ImageDraw.Draw(img)
    w, _ = img.size
    accent_rgb = hex_to_rgb(accent)
    skin = (210, 180, 145, 225)
    robe_dark = mix(accent_rgb, (7, 8, 12), 0.72)
    robe_mid = mix(accent_rgb, (242, 228, 186), 0.18)
    aura_alpha = int(70 + power * 34)
    halo_r = int(112 + power * 20)
    img.alpha_composite(soft_glow(img.size, (256, 310), accent, halo_r, aura_alpha))
    if realm_slug in {"dujie", "feisheng"}:
        lightning = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ldraw = ImageDraw.Draw(lightning)
        for i in range(5):
            x = rnd.randint(95, 410)
            pts = [(x, 88)]
            y = 88
            for _ in range(5):
                y += rnd.randint(34, 60)
                x += rnd.randint(-30, 30)
                pts.append((x, y))
            ldraw.line(pts, fill=(220, 236, 255, 72), width=2)
        img.alpha_composite(lightning.filter(ImageFilter.GaussianBlur(0.5)))

    # Cloak shadow
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.ellipse((160, 520, 352, 560), fill=(0, 0, 0, 80))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14)))

    # Hair, face and body
    draw.ellipse((205, 164, 307, 270), fill=(25, 20, 18, 235))
    draw.ellipse((214, 178, 298, 264), fill=skin)
    draw.pieslice((201, 145, 312, 244), 180, 360, fill=(18, 17, 18, 235))
    draw.rounded_rectangle((249, 124, 263, 177), radius=7, fill=(18, 17, 18, 235))
    draw.ellipse((235, 116, 277, 148), fill=(18, 17, 18, 235))
    draw.line((233, 214, 244, 216), fill=(40, 22, 20, 160), width=2)
    draw.line((279, 216, 290, 214), fill=(40, 22, 20, 160), width=2)

    robe = [(160, 540), (204, 292), (256, 270), (308, 292), (354, 540)]
    draw.polygon(robe, fill=(*robe_dark, 234))
    draw.polygon([(190, 540), (222, 315), (256, 356), (290, 315), (322, 540)], fill=(*robe_mid, 202))
    draw.line((256, 286, 256, 535), fill=rgba("#F8DFA4", 130), width=3)
    draw.line((210, 330, 303, 446), fill=rgba("#F8DFA4", 105), width=3)
    draw.line((302, 330, 211, 446), fill=rgba("#F8DFA4", 78), width=2)

    # Sleeves
    draw.polygon([(203, 330), (126, 418), (146, 474), (228, 392)], fill=(*robe_dark, 216))
    draw.polygon([(309, 330), (386, 418), (366, 474), (284, 392)], fill=(*robe_dark, 216))
    draw.ellipse((121, 456, 155, 489), fill=skin)
    draw.ellipse((357, 456, 391, 489), fill=skin)

    if pose == "sword":
        draw.line((132, 515, 386, 210), fill=rgba("#F7F2D0", 220), width=5)
        draw.line((145, 527, 399, 222), fill=rgba(accent, 110), width=2)
        draw.polygon([(386, 210), (406, 178), (397, 218)], fill=rgba("#FFFFFF", 230))
    elif pose == "gear":
        for r, a in [(74, 58), (50, 82)]:
            draw.ellipse((256 - r, 342 - r, 256 + r, 342 + r), outline=rgba(accent, a), width=4)
        for i in range(12):
            ang = i * math.tau / 12
            x = 256 + math.cos(ang) * 74
            y = 342 + math.sin(ang) * 74
            draw.rectangle((x - 5, y - 5, x + 5, y + 5), fill=rgba("#FFE0A3", 90))
    elif pose == "mind":
        for sides, rad in [(3, 82), (6, 62), (8, 43)]:
            draw.polygon(polygon_regular((256, 360), rad, sides, rotation=rnd.random()), outline=rgba(accent, 95))
    elif pose == "scroll":
        draw.rounded_rectangle((156, 360, 356, 454), radius=20, fill=rgba("#DED4B8", 174), outline=rgba(accent, 120), width=2)
        for y in range(382, 438, 18):
            draw.line((184, y, 328, y), fill=(72, 62, 45, 110), width=2)
    elif pose == "moon":
        draw.ellipse((170, 292, 342, 464), outline=rgba("#E8E1FF", 118), width=5)
        draw.ellipse((212, 266, 352, 432), fill=rgba("#101020", 155))

    # Realm floating beads
    for i in range(int(5 + power * 5)):
        ang = i * math.tau / int(5 + power * 5) + rnd.random() * 0.3
        rx = int(132 + math.sin(i) * 16)
        ry = int(166 + math.cos(i) * 10)
        x = 256 + math.cos(ang) * rx
        y = 338 + math.sin(ang) * ry
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=rgba("#FFE8B6", int(80 + power * 36)))


def draw_sect_gate(img: Image.Image, sect_id: str, accent: str) -> None:
    rnd = rng_for("sect:" + sect_id)
    draw = ImageDraw.Draw(img)
    accent_rgb = hex_to_rgb(accent)
    dark = mix(accent_rgb, (7, 7, 9), 0.78)
    img.alpha_composite(soft_glow(img.size, (256, 320), accent, 185, 82))
    # Mountain gate
    draw.polygon([(126, 355), (256, 255), (386, 355)], fill=(*dark, 222))
    draw.polygon([(94, 390), (256, 300), (418, 390)], fill=(*mix(accent_rgb, (0, 0, 0), 0.52), 188))
    draw.rectangle((136, 385, 376, 548), fill=(*dark, 226))
    draw.rectangle((166, 418, 208, 548), fill=rgba("#120E0B", 230))
    draw.rectangle((304, 418, 346, 548), fill=rgba("#120E0B", 230))
    draw.polygon([(104, 382), (408, 382), (360, 340), (152, 340)], fill=rgba("#1D1612", 236))
    draw.line((116, 382, 396, 382), fill=rgba("#F3D28A", 150), width=4)
    draw.line((152, 340, 360, 340), fill=rgba(accent, 150), width=3)
    for x in (162, 350):
        draw.line((x, 390, x, 548), fill=rgba("#F3D28A", 86), width=3)

    symbol = SECT_SYMBOLS.get(sect_id, "宗")
    draw.ellipse((196, 292, 316, 412), fill=rgba("#16110D", 188), outline=rgba("#F3D28A", 135), width=3)
    draw_center_text(draw, (256, 352), symbol, FONTS["seal"], rgba("#FFE4A4", 230), rgba("#32160A", 210), 2)
    if sect_id == "canglan":
        draw.line((256, 192, 256, 492), fill=rgba("#F7F2D0", 180), width=5)
        draw.polygon([(256, 182), (240, 222), (272, 222)], fill=rgba("#FFFFFF", 210))
    elif sect_id == "tianji":
        for r in (110, 76):
            draw.ellipse((256 - r, 350 - r, 256 + r, 350 + r), outline=rgba(accent, 90), width=4)
        for i in range(16):
            a = i * math.tau / 16
            x = 256 + math.cos(a) * 111
            y = 350 + math.sin(a) * 111
            draw.rectangle((x - 5, y - 5, x + 5, y + 5), fill=rgba("#FFE0A3", 90))
    elif sect_id == "yueyin":
        draw.ellipse((170, 196, 342, 368), outline=rgba("#EAE3FF", 118), width=6)
        draw.ellipse((220, 176, 372, 358), fill=rgba("#0B0B18", 160))
    elif sect_id == "qingming":
        for i in range(6):
            y = 250 + i * 28
            draw.arc((152, y, 360, y + 96), 190, 350, fill=rgba(accent, 82 + i * 4), width=2)
    else:
        for i in range(5):
            r = 72 + i * 24
            draw.polygon(polygon_regular((256, 344), r, 6, rotation=rnd.random()), outline=rgba(accent, 58 + i * 8))


def draw_enemy_subject(img: Image.Image, enemy_id: str, clan: str, tier: str, level: int, accent: str) -> None:
    rnd = rng_for("enemy:" + enemy_id)
    draw = ImageDraw.Draw(img)
    style, _, _ = CLAN_STYLES.get(clan, ("demon", accent, "妖"))
    _, scale = TIER_META.get(tier, ("", 1.0))
    color = hex_to_rgb(accent)
    dark = mix(color, (8, 8, 12), 0.7)
    light = mix(color, (255, 226, 168), 0.25)
    cx, cy = 256, 350
    img.alpha_composite(soft_glow(img.size, (cx, cy), accent, int(122 + scale * 52), int(56 + scale * 34)))

    def tail(angle: float, length: int, width: int, alpha: int = 130) -> None:
        x2 = cx + math.cos(angle) * length
        y2 = cy + math.sin(angle) * length
        draw.line((cx, cy + 60, x2, y2), fill=(*light, alpha), width=width)

    if style == "fox":
        n_tail = max(1, min(8, int(level / 12) + 1))
        for i in range(n_tail):
            angle = -2.6 + i * (1.8 / max(1, n_tail - 1))
            tail(angle, int(145 + scale * 18), int(16 + scale * 5), 80)
        draw.polygon([(188, 247), (214, 176), (236, 258)], fill=(*dark, 230))
        draw.polygon([(276, 258), (298, 176), (324, 247)], fill=(*dark, 230))
        draw.ellipse((176, 230, 336, 404), fill=(*dark, 236))
        draw.polygon([(196, 330), (256, 435), (316, 330)], fill=(*light, 168))
        draw.ellipse((218, 300, 234, 316), fill=(255, 224, 120, 230))
        draw.ellipse((278, 300, 294, 316), fill=(255, 224, 120, 230))
    elif style == "bird":
        draw.pieslice((72, 228, 270, 504), 112, 280, fill=(*dark, 190))
        draw.pieslice((242, 228, 440, 504), 260, 68, fill=(*dark, 190))
        draw.ellipse((190, 220, 322, 388), fill=(*light, 210))
        draw.polygon([(256, 250), (316, 300), (256, 314)], fill=rgba("#F6D385", 220))
        for i in range(6):
            draw.line((154 + i * 24, 376, 100 + i * 14, 486), fill=rgba("#FBE7B3", 88), width=3)
            draw.line((358 - i * 24, 376, 412 - i * 14, 486), fill=rgba("#FBE7B3", 88), width=3)
    elif style == "serpent":
        for i in range(4):
            bbox = (118 + i * 18, 300 + i * 38, 394 - i * 18, 478 + i * 38)
            draw.arc(bbox, 185, 540, fill=(*light, 172), width=int(22 + scale * 4))
        draw.ellipse((218, 184, 318, 286), fill=(*dark, 235))
        draw.polygon([(252, 270), (228, 320), (284, 320)], fill=(*dark, 220))
        draw.line((256, 262, 244, 292), fill=rgba("#FF6A6A", 190), width=3)
        draw.line((256, 262, 270, 292), fill=rgba("#FF6A6A", 190), width=3)
        draw.ellipse((236, 222, 246, 232), fill=(245, 225, 130, 230))
        draw.ellipse((268, 222, 278, 232), fill=(245, 225, 130, 230))
    elif style == "beast":
        draw.ellipse((150, 230, 362, 430), fill=(*dark, 236))
        draw.polygon([(174, 252), (188, 176), (234, 246)], fill=(*dark, 236))
        draw.polygon([(338, 252), (324, 176), (278, 246)], fill=(*dark, 236))
        draw.ellipse((200, 314, 312, 420), fill=(*light, 154))
        for x in (216, 288):
            draw.polygon([(x, 308), (x - 8, 338), (x + 8, 338)], fill=(246, 235, 184, 230))
        for i in range(5):
            draw.line((170 + i * 22, 272, 214 + i * 18, 300), fill=rgba("#F6D385", 80), width=5)
            draw.line((342 - i * 22, 272, 298 - i * 18, 300), fill=rgba("#F6D385", 80), width=5)
    elif style == "herb":
        draw.rounded_rectangle((228, 276, 284, 500), radius=26, fill=(*dark, 220))
        for i in range(8):
            a = i * math.tau / 8 + rnd.random() * 0.2
            x = cx + math.cos(a) * rnd.randint(58, 126)
            y = 320 + math.sin(a) * rnd.randint(42, 98)
            draw.ellipse((x - 48, y - 24, x + 48, y + 24), fill=(*light, rnd.randint(82, 156)))
        draw.ellipse((204, 190, 308, 294), fill=rgba("#F4C2D7", 132), outline=rgba("#FFE0A3", 82), width=2)
    elif style == "ghost":
        ghost = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(ghost)
        gdraw.ellipse((162, 188, 350, 418), fill=(*light, 128))
        gdraw.polygon([(162, 318), (186, 532), (228, 470), (256, 542), (288, 470), (330, 532), (350, 318)], fill=(*light, 116))
        gdraw.ellipse((216, 282, 236, 310), fill=(10, 10, 16, 180))
        gdraw.ellipse((276, 282, 296, 310), fill=(10, 10, 16, 180))
        img.alpha_composite(ghost.filter(ImageFilter.GaussianBlur(2)))
    elif style == "dragon":
        pts = []
        for i in range(18):
            t = i / 17
            x = 102 + t * 310
            y = 390 + math.sin(t * math.tau * 1.5) * 76
            pts.append((x, y))
        draw.line(pts, fill=(*light, 180), width=int(28 + scale * 6), joint="curve")
        draw.ellipse((194, 176, 330, 302), fill=(*dark, 235))
        draw.polygon([(210, 192), (176, 126), (242, 178)], fill=(*dark, 230))
        draw.polygon([(302, 192), (336, 126), (270, 178)], fill=(*dark, 230))
        for i in range(6):
            draw.line((220 + i * 16, 180, 204 + i * 18, 128), fill=rgba("#FFE0A3", 130), width=3)
    elif style == "divine":
        draw.ellipse((146, 220, 366, 430), fill=(*dark, 225))
        draw.polygon([(188, 238), (220, 154), (248, 236)], fill=(*light, 155))
        draw.polygon([(324, 238), (292, 154), (264, 236)], fill=(*light, 155))
        draw.ellipse((206, 296, 306, 388), fill=(*light, 132))
        for r in (142, 112, 82):
            draw.ellipse((256 - r, 316 - r, 256 + r, 316 + r), outline=rgba("#FFE0A3", 48), width=3)
    elif style == "ancient":
        draw.polygon([(152, 518), (194, 276), (256, 210), (318, 276), (360, 518)], fill=(*dark, 238))
        draw.polygon([(212, 238), (170, 138), (246, 218)], fill=(*dark, 238))
        draw.polygon([(300, 238), (342, 138), (266, 218)], fill=(*dark, 238))
        draw.ellipse((202, 220, 310, 340), fill=(*dark, 246))
        draw.ellipse((226, 270, 242, 290), fill=rgba("#FFB454", 230))
        draw.ellipse((270, 270, 286, 290), fill=rgba("#FFB454", 230))
        for i in range(7):
            draw.line((134 + i * 42, 514, 170 + i * 28, 430), fill=rgba("#EE6A56", 80), width=3)
    elif style == "artifact":
        draw.ellipse((136, 456, 376, 520), fill=(0, 0, 0, 70))
        draw.rounded_rectangle((182, 236, 330, 476), radius=28, fill=(*dark, 220), outline=(*light, 188), width=4)
        draw.polygon([(180, 272), (256, 174), (332, 272)], fill=(*dark, 230), outline=(*light, 160))
        draw.ellipse((214, 310, 298, 394), outline=rgba("#FFE0A3", 120), width=5)
        for i in range(6):
            draw.line((206 + i * 20, 260, 180 + i * 31, 190), fill=rgba("#FFE0A3", 74), width=2)
    elif style == "alien":
        for sides, rad in [(3, 128), (5, 104), (8, 76)]:
            draw.polygon(polygon_regular((cx, cy), rad, sides, rotation=rnd.random() * math.tau), outline=(*light, 102))
        draw.ellipse((190, 228, 322, 420), fill=(*dark, 214))
        draw.ellipse((214, 280, 298, 344), fill=rgba("#0A1116", 180), outline=rgba("#BFFFFA", 130), width=3)
        draw.ellipse((246, 300, 266, 324), fill=rgba("#BFFFFA", 220))
    else:
        draw.polygon([(162, 512), (202, 260), (256, 200), (310, 260), (350, 512)], fill=(*dark, 236))
        draw.ellipse((204, 210, 308, 328), fill=(*dark, 240))

    # Ground and power glyph
    draw.ellipse((112, 504, 400, 558), outline=rgba("#FFE0A3", 60), width=2)
    for i in range(int(4 + scale * 4)):
        a = rnd.random() * math.tau
        r = rnd.randint(95, 158)
        x = cx + math.cos(a) * r
        y = cy + math.sin(a) * r
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=rgba("#FFE0A3", rnd.randint(48, 112)))


def draw_boss_subject(img: Image.Image, boss_id: str, accent: str, story: str, level: int) -> None:
    rnd = rng_for("boss:" + boss_id)
    draw = ImageDraw.Draw(img)
    color = hex_to_rgb(accent)
    dark = mix(color, (8, 7, 11), 0.72)
    bright = mix(color, (255, 226, 168), 0.18)
    power = min(1.8, 0.7 + level / 140)
    img.alpha_composite(soft_glow(img.size, (256, 310), accent, int(170 + power * 30), int(78 + power * 28)))
    # Boss halo and seal geometry
    for i, (rad, sides) in enumerate([(168, 8), (132, 6), (96, 3)]):
        pts = polygon_regular((256, 332), rad, sides, rotation=rnd.random() * math.tau)
        draw.line(pts + [pts[0]], fill=rgba(accent, 60 + i * 20), width=3)
    if story == "B":
        for i in range(5):
            draw.arc((112 + i * 16, 176 + i * 10, 400 - i * 16, 492 - i * 10), 200, 342, fill=rgba("#FFE0A3", 44), width=2)
    elif story == "C":
        draw_mountains(img, rnd, mix(color, (80, 40, 30), 0.4), 465, 38)
    elif story == "D":
        for i in range(7):
            a = rnd.random() * math.tau
            draw.line((256, 330, 256 + math.cos(a) * 190, 330 + math.sin(a) * 190), fill=rgba("#A7F3FF", 42), width=2)

    # Figure
    draw.polygon([(142, 548), (188, 300), (256, 248), (324, 300), (370, 548)], fill=(*dark, 242))
    draw.polygon([(190, 548), (226, 322), (256, 374), (288, 322), (322, 548)], fill=(*bright, 196))
    draw.ellipse((198, 160, 314, 286), fill=(23, 20, 22, 245))
    draw.ellipse((212, 180, 300, 274), fill=(214, 178, 140, 230))
    # Boss crown
    draw.polygon([(202, 177), (228, 116), (250, 176), (270, 116), (306, 177)], fill=rgba("#1C1713", 238), outline=rgba("#FFE0A3", 132))
    draw.ellipse((232, 218, 248, 234), fill=rgba("#FFE0A3", 220))
    draw.ellipse((264, 218, 280, 234), fill=rgba("#FFE0A3", 220))
    draw.line((232, 250, 280, 250), fill=rgba("#6B1D1D", 180), width=3)
    # Sleeves and artifact
    draw.polygon([(188, 332), (92, 420), (122, 486), (236, 388)], fill=(*dark, 218))
    draw.polygon([(324, 332), (420, 420), (390, 486), (276, 388)], fill=(*dark, 218))
    if "xai" in boss_id or "void" in boss_id:
        draw.ellipse((206, 302, 306, 402), outline=rgba("#A7F3FF", 158), width=5)
        draw.ellipse((228, 332, 284, 372), fill=rgba("#070A12", 180), outline=rgba("#E8FFFF", 130), width=3)
    elif "tianji" in boss_id or "groq" in boss_id:
        for r in (66, 46):
            draw.ellipse((256 - r, 354 - r, 256 + r, 354 + r), outline=rgba(accent, 120), width=4)
    elif "canglan" in boss_id:
        draw.line((148, 520, 374, 206), fill=rgba("#F7F2D0", 220), width=5)
    else:
        draw.rounded_rectangle((212, 326, 300, 404), radius=18, outline=rgba("#FFE0A3", 116), width=4)
        draw_center_text(draw, (256, 362), str(rnd.randint(1, 9)), FONTS["subtitle"], rgba("#FFE0A3", 180))


def save_png(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)


def make_sect_portrait(sect) -> Image.Image:
    img = base_card(
        f"sect:{sect.id}",
        sect.color_primary,
        sect.color_accent,
        sect.name,
        "宗门道统",
        SECT_SYMBOLS.get(sect.id, "宗"),
        1.0,
    )
    draw_sect_gate(img, sect.id, sect.color_accent)
    return img


def make_player_portrait(sect, realm_slug: str, realm_name: str, index: int) -> Image.Image:
    realm_title, realm_color, power = REALM_META[realm_slug]
    accent = realm_color if index >= 2 else sect.color_accent
    img = base_card(
        f"player:{sect.id}:{realm_slug}",
        sect.color_primary,
        accent,
        f"{sect.name}弟子",
        f"{realm_name} · {realm_title}",
        SECT_SYMBOLS.get(sect.id, "修"),
        power,
    )
    draw_robed_cultivator(img, accent, SECT_POSE.get(sect.id, "sword"), realm_slug, f"{sect.id}:{realm_slug}", power)
    return img


def make_enemy_portrait(enemy_key: str, enemy) -> Image.Image:
    style, accent, seal = CLAN_STYLES.get(enemy.clan, ("demon", "#A36BD8", "妖"))
    tier_label, rarity = TIER_META.get(enemy.tier, ("妖物", 0.9))
    subtitle = f"{enemy.clan} · Lv.{enemy.level}"
    if enemy_key != enemy.id:
        subtitle = f"{subtitle} · 旧名录"
    img = base_card(
        f"enemy:{enemy_key}",
        "#17131F",
        accent,
        enemy.name,
        subtitle,
        seal,
        rarity,
    )
    draw_enemy_subject(img, enemy_key, enemy.clan, enemy.tier, enemy.level, accent)
    return img


def make_boss_portrait(boss) -> Image.Image:
    sect = BOSS_SECTS.get(boss.sect_id)
    if sect:
        accent = sect.base_color
        story = sect.storyline
        sect_name = sect.name
    else:
        player_sect = ALL_SECTS.get(boss.sect_id)
        accent = player_sect.color_accent if player_sect else "#D4A24C"
        story = "A"
        sect_name = player_sect.name if player_sect else "散修"
    seal = "尊" if boss.level >= 100 else "首"
    img = base_card(
        f"boss:{boss.id}",
        "#15101A",
        accent,
        boss.name,
        f"{boss.title} · {sect_name}",
        seal,
        1.45,
    )
    draw_boss_subject(img, boss.id, accent, story, boss.level)
    return img


def make_entry_background() -> Image.Image:
    w, h = BACKGROUND_SIZE
    rnd = rng_for("background:entry")
    img = vertical_gradient((w, h), (19, 25, 33), (7, 8, 14), 232)
    img = add_noise(img, opacity=14)
    draw = ImageDraw.Draw(img)

    # Distant sky and a soft crescent moon. The moon is intentionally muted so it
    # can sit under UI panels without becoming a competing focal point.
    img.alpha_composite(soft_glow((w, h), (1410, 190), "#F8E9C0", 260, 58))
    moon_mask = Image.new("L", (w, h), 0)
    mdraw = ImageDraw.Draw(moon_mask)
    mdraw.ellipse((1342, 92, 1480, 230), fill=74)
    mdraw.ellipse((1394, 70, 1520, 226), fill=0)
    moon = Image.new("RGBA", (w, h), (246, 224, 179, 0))
    moon.putalpha(moon_mask.filter(ImageFilter.GaussianBlur(1.4)))
    img.alpha_composite(moon)

    # Layered mountains and sea of clouds
    for row, base in enumerate([780, 850, 940]):
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ldraw = ImageDraw.Draw(layer)
        points = [(-80, h + 60)]
        x = -60
        while x < w + 100:
            peak = base - rnd.randint(120, 330) + row * 35
            points.append((x, peak))
            x += rnd.randint(130, 260)
        points.append((w + 100, h + 60))
        shade = [(42, 58, 64, 72), (25, 35, 44, 108), (12, 18, 26, 145)][row]
        ldraw.polygon(points, fill=shade)
        img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(row * 1.5)))

    cloud = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(cloud)
    for _ in range(88):
        cx = rnd.randint(-180, w + 180)
        cy = rnd.randint(530, 980)
        rx = rnd.randint(180, 420)
        ry = rnd.randint(32, 96)
        cdraw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=(232, 226, 211, rnd.randint(12, 34)))
    img.alpha_composite(cloud.filter(ImageFilter.GaussianBlur(18)))

    # Ancient immortal city silhouette, intentionally low contrast for UI readability.
    city = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    c = ImageDraw.Draw(city)
    base_y = 742
    dark = (12, 14, 20, 150)
    gold = (225, 181, 103, 92)
    def roof(x: int, y: int, width: int, depth: int = 46, alpha: int = 172) -> None:
        c.polygon(
            (
                x - 54,
                y + 10,
                x + width // 2,
                y - depth,
                x + width + 54,
                y + 10,
                x + width + 30,
                y + 18,
                x - 30,
                y + 18,
            ),
            fill=(9, 10, 16, alpha),
        )
        c.line((x - 42, y + 12, x + width + 42, y + 12), fill=gold, width=3)
        c.line((x + 8, y - 2, x + width - 8, y - 2), fill=(236, 208, 154, 38), width=1)

    for i, x in enumerate([410, 600, 795, 1046, 1252, 1450]):
        height = rnd.randint(116, 220)
        width = rnd.randint(88, 132)
        y = base_y - height
        c.rectangle((x, y, x + width, base_y), fill=dark)
        roof(x, y, width, 48, 160)
        if i in {1, 3, 5}:
            c.rectangle((x + 18, y + 54, x + width - 18, y + 112), fill=(10, 12, 18, 118))
            roof(x + 18, y + 56, width - 36, 30, 145)
        for floor in range(3):
            yy = y + 32 + floor * 48
            c.line((x + 12, yy, x + width - 12, yy), fill=(236, 208, 154, 40), width=2)
    c.rectangle((344, base_y, 1576, base_y + 36), fill=(9, 10, 16, 126))
    c.line((338, base_y, 1582, base_y), fill=(232, 188, 113, 70), width=4)
    # Main gate
    c.rectangle((846, 544, 1074, 782), fill=(9, 10, 16, 154))
    roof(802, 558, 316, 122, 180)
    c.rectangle((886, 466, 1034, 558), fill=(8, 10, 15, 128))
    roof(870, 466, 180, 64, 164)
    c.ellipse((900, 590, 1020, 710), outline=(236, 194, 120, 78), width=3)
    c.text((922, 617), "灵枢", font=FONTS["bg_title"], fill=(238, 217, 170, 72))
    # A light suspended bridge and two small lantern towers add old xianxia depth.
    c.arc((548, 650, 1372, 912), 196, 344, fill=(232, 188, 113, 44), width=2)
    for x in range(620, 1300, 92):
        c.line((x, 760, x, 792), fill=(232, 188, 113, 28), width=1)
    for x in (690, 1220):
        c.line((x, 610, x, 742), fill=(232, 188, 113, 38), width=2)
        c.ellipse((x - 9, 612, x + 9, 638), fill=(232, 188, 113, 32))
    img.alpha_composite(city.filter(ImageFilter.GaussianBlur(0.4)))

    # Flying sword traces
    for _ in range(12):
        x = rnd.randint(130, 1780)
        y = rnd.randint(230, 575)
        length = rnd.randint(80, 170)
        c1 = (238, 218, 165, rnd.randint(22, 48))
        draw.line((x, y, x + length, y - rnd.randint(28, 90)), fill=c1, width=2)
        draw.ellipse((x + length - 4, y - 4, x + length + 4, y + 4), fill=c1)

    # Dark vignette and clear center wash.
    vignette = Image.new("L", (w, h), 0)
    vdraw = ImageDraw.Draw(vignette)
    vdraw.rectangle((0, 0, w, h), fill=165)
    vdraw.ellipse((260, 80, 1660, 1040), fill=44)
    vignette = vignette.filter(ImageFilter.GaussianBlur(120))
    veil = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    veil.putalpha(vignette)
    img.alpha_composite(veil)

    return img


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def generate() -> dict:
    for folder in [
        PORTRAIT_ROOT / "sects",
        PORTRAIT_ROOT / "players",
        PORTRAIT_ROOT / "enemies",
        PORTRAIT_ROOT / "bosses",
        BACKGROUND_ROOT,
        DOCS_ROOT,
    ]:
        folder.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, list[dict] | dict] = {
        "meta": {
            "style": "国风修仙、水墨低对比、卡片竖版画像",
            "portrait_size": f"{PORTRAIT_SIZE[0]}x{PORTRAIT_SIZE[1]}",
            "background_size": f"{BACKGROUND_SIZE[0]}x{BACKGROUND_SIZE[1]}",
            "generated_by": "scripts/generate_xianxia_assets.py",
        },
        "sects": [],
        "players": [],
        "enemies": [],
        "bosses": [],
        "backgrounds": [],
    }

    for sect in ALL_SECTS.values():
        path = PORTRAIT_ROOT / "sects" / f"{sect.id}.png"
        save_png(make_sect_portrait(sect), path)
        manifest["sects"].append({"id": sect.id, "name": sect.name, "path": "/" + rel(path).split("frontend/public/")[-1]})

    for sect in ALL_SECTS.values():
        for index, (realm_slug, realm_name) in enumerate(REALMS):
            path = PORTRAIT_ROOT / "players" / sect.id / f"{realm_slug}.png"
            save_png(make_player_portrait(sect, realm_slug, realm_name, index), path)
            manifest["players"].append(
                {
                    "sect_id": sect.id,
                    "sect_name": sect.name,
                    "realm": realm_slug,
                    "realm_name": realm_name,
                    "path": "/" + rel(path).split("frontend/public/")[-1],
                }
            )

    for enemy_key, enemy in ENEMIES.items():
        path = PORTRAIT_ROOT / "enemies" / f"{enemy_key}.png"
        save_png(make_enemy_portrait(enemy_key, enemy), path)
        manifest["enemies"].append(
            {
                "key": enemy_key,
                "id": enemy.id,
                "is_legacy_alias": enemy_key != enemy.id,
                "name": enemy.name,
                "clan": enemy.clan,
                "tier": enemy.tier,
                "level": enemy.level,
                "path": "/" + rel(path).split("frontend/public/")[-1],
            }
        )

    for boss in BOSSES.values():
        path = PORTRAIT_ROOT / "bosses" / f"{boss.id}.png"
        save_png(make_boss_portrait(boss), path)
        manifest["bosses"].append(
            {
                "id": boss.id,
                "name": boss.name,
                "title": boss.title,
                "sect_id": boss.sect_id,
                "level": boss.level,
                "path": "/" + rel(path).split("frontend/public/")[-1],
            }
        )

    bg_path = BACKGROUND_ROOT / "entry-bg.png"
    save_png(make_entry_background(), bg_path)
    manifest["backgrounds"].append(
        {
            "id": "entry-bg",
            "name": "进入游戏背景",
            "path": "/" + rel(bg_path).split("frontend/public/")[-1],
            "note": "半透明低对比水墨仙城背景,适合作为 UI 底图。",
        }
    )

    manifest["meta"]["counts"] = {
        "sects": len(manifest["sects"]),
        "players": len(manifest["players"]),
        "enemies": len(manifest["enemies"]),
        "bosses": len(manifest["bosses"]),
        "portraits": len(manifest["sects"]) + len(manifest["players"]) + len(manifest["enemies"]) + len(manifest["bosses"]),
        "backgrounds": len(manifest["backgrounds"]),
        "total": len(manifest["sects"]) + len(manifest["players"]) + len(manifest["enemies"]) + len(manifest["bosses"]) + len(manifest["backgrounds"]),
    }

    manifest_path = PORTRAIT_ROOT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown_manifest(manifest)
    write_preview_sheet(manifest)
    return manifest


def write_markdown_manifest(manifest: dict) -> None:
    lines = [
        "# 修仙画像资产清单",
        "",
        "本清单由 `scripts/generate_xianxia_assets.py` 生成。画像统一为 512x768 PNG,进入游戏背景为 1920x1080 PNG。",
        "",
        "## 数量",
        "",
    ]
    counts = manifest["meta"]["counts"]
    for key, label in [
        ("sects", "宗门画像"),
        ("players", "主角画像"),
        ("enemies", "怪物画像"),
        ("bosses", "Boss 画像"),
        ("backgrounds", "背景图"),
        ("total", "总计"),
    ]:
        lines.append(f"- {label}: {counts[key]}")
    lines.extend(["", "## 保存位置", ""])
    lines.append("- 宗门: `frontend/public/images/portraits/sects/{sect_id}.png`")
    lines.append("- 主角: `frontend/public/images/portraits/players/{sect_id}/{realm}.png`")
    lines.append("- 怪物: `frontend/public/images/portraits/enemies/{enemy_id}.png`")
    lines.append("- Boss: `frontend/public/images/portraits/bosses/{boss_id}.png`")
    lines.append("- 进入游戏背景: `frontend/public/images/backgrounds/entry-bg.png`")
    lines.append("- JSON manifest: `frontend/public/images/portraits/manifest.json`")
    lines.extend(["", "## 宗门与主角", ""])
    for sect in manifest["sects"]:
        player_realms = [p for p in manifest["players"] if p["sect_id"] == sect["id"]]
        realm_names = "、".join(p["realm_name"] for p in player_realms)
        lines.append(f"- {sect['name']} `{sect['id']}`: 宗门图 `{sect['path']}`, 主角境界 {len(player_realms)} 张: {realm_names}")
    lines.extend(["", "## 怪物画像", ""])
    clans: dict[str, list[dict]] = {}
    for enemy in manifest["enemies"]:
        clans.setdefault(enemy["clan"], []).append(enemy)
    for clan, enemies in clans.items():
        names = "、".join(e["name"] for e in enemies[:8])
        suffix = "…" if len(enemies) > 8 else ""
        lines.append(f"- {clan}: {len(enemies)} 张, {names}{suffix}")
    lines.extend(["", "## Boss 画像", ""])
    for boss in manifest["bosses"]:
        lines.append(f"- {boss['name']} `{boss['id']}`: {boss['title']} · Lv.{boss['level']} · `{boss['path']}`")
    lines.append("")
    (DOCS_ROOT / "ASSET_MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")


def write_preview_sheet(manifest: dict) -> None:
    samples = []
    pick_paths = [
        manifest["sects"][0]["path"],
        manifest["players"][0]["path"],
        manifest["players"][8]["path"],
        manifest["enemies"][0]["path"],
        manifest["enemies"][24]["path"],
        manifest["enemies"][72]["path"],
        manifest["bosses"][0]["path"],
        manifest["bosses"][-1]["path"],
    ]
    for public_path in pick_paths:
        samples.append(ROOT / "frontend" / "public" / public_path.lstrip("/"))
    thumb_w, thumb_h = 192, 288
    gutter = 20
    sheet = Image.new("RGBA", (gutter + 4 * (thumb_w + gutter), gutter + 2 * (thumb_h + gutter)), (12, 11, 16, 255))
    for i, path in enumerate(samples):
        im = Image.open(path).convert("RGBA").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = gutter + (i % 4) * (thumb_w + gutter)
        y = gutter + (i // 4) * (thumb_h + gutter)
        sheet.alpha_composite(im, (x, y))
    save_png(sheet, DOCS_ROOT / "asset-preview.png")


if __name__ == "__main__":
    result = generate()
    print(json.dumps(result["meta"]["counts"], ensure_ascii=False, indent=2))
