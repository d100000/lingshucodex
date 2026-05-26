"""Generate the 200 disciple portraits with gpt-image-2.

This replaces the deterministic placeholder portraits created by
generate_disciple_assets.py while keeping the same stable asset paths:

  frontend/public/images/portraits/disciples/{sect_id}/{disciple_id}.png

Usage:
  cd /Users/bobdong/项目/LingshuCodex
  source backend/.venv/bin/activate
  python scripts/generate_disciple_image2_portraits.py --ids canglan_01 --replace
  python scripts/generate_disciple_image2_portraits.py --sect canglan --replace --concurrency 2
  python scripts/generate_disciple_image2_portraits.py --replace --concurrency 3
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
load_dotenv(ROOT / "backend" / ".env")

from app.image_gen import ImageGenError, generate_image, generate_image_with_references  # noqa: E402


DATA_PATH = ROOT / "frontend" / "src" / "data" / "disciples.json"
PORTRAIT_ROOT = ROOT / "frontend" / "public" / "images" / "portraits" / "disciples"
FLAG_ROOT = ROOT / "frontend" / "public" / "images" / "sects" / "flags"

SECT_STYLE: Dict[str, Dict[str, str]] = {
    "canglan": {
        "name": "沧澜剑派",
        "visual": "black and deep navy robes with restrained gold embroidery, ancient sword culture, tide-like sword aura, solemn literary temperament",
        "flag_motif": "black-gold sect banner motif, tide pattern, sword emblem, disciplined and restrained",
    },
    "tianji": {
        "name": "天机阁",
        "visual": "dark bronze and amber robes, mechanical astrolabes, floating gears, talisman engineering, clever artisan temperament",
        "flag_motif": "bronze-gold sect banner motif, gear emblem, astrolabe rings, precise mechanical order",
    },
    "xuanji": {
        "name": "玄机宗",
        "visual": "deep violet and silver robes, abstract array diagrams, chessboard geometry, quiet analytic temperament",
        "flag_motif": "violet-silver sect banner motif, geometric array emblem, chessboard and calculation marks",
    },
    "qingming": {
        "name": "青冥派",
        "visual": "dark green scholar robes, jade ornaments, ancient scrolls, medicinal valley atmosphere, steady learned temperament",
        "flag_motif": "dark green sect banner motif, scroll emblem, jade and bamboo pattern, scholarly calm",
    },
    "yueyin": {
        "name": "月隐宫",
        "visual": "moonlit purple and silver garments, veils, crescent blades, stealthy shadows, elegant secretive temperament",
        "flag_motif": "silver-purple sect banner motif, crescent moon emblem, veil and shadow pattern, secretive elegance",
    },
}


STYLE_BASE = (
    "Chinese xianxia mobile RPG character portrait, polished semi-realistic anime card art, "
    "clean painterly linework, refined facial features, elegant but readable costume design, "
    "single character centered, waist-up bust composition, full head and shoulders visible, "
    "face clear and not cropped, generous padding for circular avatar cropping, "
    "balanced soft lighting, clean dark fantasy background with subtle sect motif, "
    "not photorealistic, not horror, not over-dark, not smoky close-up, "
    "not Western fantasy, no text, no watermark, no logo, no UI frame."
)


def load_disciples() -> List[dict]:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return list(payload["disciples"])


def rank_visual(rank: str, level: int, age: int) -> str:
    if rank in {"外门"}:
        return (
            f"outer disciple, around {age} years old, youthful face, simple training robe, "
            "modest accessories, beginner cultivation aura, no crown, no luxury armor"
        )
    if rank in {"内门"}:
        return (
            f"inner disciple, around {age} years old, more confident bearing, practical sect robe, "
            "one or two refined accessories, controlled cultivation aura"
        )
    if rank in {"核心", "真传"}:
        return (
            f"elite disciple, apparent age younger than true age {age}, prestigious but not excessive robes, "
            "clear personal symbol, stronger aura, more complete weapon or artifact"
        )
    if rank in {"护法"}:
        return (
            f"guardian elder, true age around {age}, youthful immortal appearance, authoritative posture, "
            "formal sect robe, calm pressure, not old and frail"
        )
    return (
        f"sect elder, true age around {age}, ageless immortal appearance, dignified and mysterious, "
        "high-rank ceremonial robe, deep aura, still suitable as an NPC portrait"
    )


def flag_path_for(sect_id: str) -> Path:
    return FLAG_ROOT / f"{sect_id}.png"


def prompt_for(d: dict) -> str:
    sect = SECT_STYLE[d["sect_id"]]
    gender = "female" if d["gender"] == "女" else "male"
    flag_ref = flag_path_for(d["sect_id"])
    return (
        f"{STYLE_BASE}\n\n"
        "## 1. Reference image and background requirement\n"
        f"Use the provided reference image as the visual reference for the {sect['name']} sect flag.\n"
        f"Reference image path for the generation script: {flag_ref}.\n"
        "The portrait background must contain a visible but non-dominating sect banner / flag element inspired by the reference image.\n"
        f"Flag motif to echo in the background: {sect['flag_motif']}.\n"
        "The flag should appear as a hanging banner, distant standard, embroidered backdrop, or soft emblem behind the character. "
        "Do not copy any text; use only color, emblem shape, and symbolic motif.\n\n"
        "## 2. Character identity, gender, personality, and history\n"
        f"Name: {d['name']}.\n"
        f"Sect: {sect['name']}.\n"
        f"Gender: {gender}.\n"
        f"Rank and level: {d['rank']} disciple, Lv {d['level']}.\n"
        f"Personality keywords: {d['personality']}.\n"
        f"Past history / story wound: {d['story_hook']}.\n"
        "Use the personality and history to shape the facial expression, posture, eyes, and small props. "
        "The character should feel like a specific person, not a generic beautiful cultivator.\n\n"
        "## 3. Appearance keywords and individual visual traits\n"
        f"Required portrait keywords from the bible: {d['appearance']}.\n"
        f"Sect costume language: {sect['visual']}.\n"
        "Keep these individual traits visible and prioritize them over generic ornamentation.\n\n"
        "## 4. Age, rank, and hierarchy differentiation\n"
        f"Age/rank visual direction: {rank_visual(d['rank'], d['level'], d['base_age_years'])}.\n"
        "Outer and inner disciples should look simpler and younger; core, true disciples, guardians, and elders may have stronger aura and more formal clothing. "
        "Do not make every disciple look like an SSR protagonist.\n\n"
        "## 5. Composition and negative constraints\n"
        "Portrait must show one distinct person only, waist-up bust, head-to-waist visible, calm readable pose, "
        "full head and shoulders visible, face clear and not cropped, strong silhouette, clean avatar-safe background. "
        "No written Chinese characters, no text, no signature, no border, no extra people, no extreme face close-up, "
        "no luxury crown for low-rank disciples, no photorealistic celebrity face."
    )


def exact_path(d: dict) -> Path:
    return PORTRAIT_ROOT / d["sect_id"] / f"{d['id']}.png"


def collect_tasks(args) -> List[dict]:
    ids = set()
    if args.ids:
        ids = {x.strip() for x in args.ids.split(",") if x.strip()}
    tasks = []
    for d in load_disciples():
        if args.sect and d["sect_id"] != args.sect:
            continue
        if ids and d["id"] not in ids:
            continue
        path = exact_path(d)
        if path.exists() and not args.replace:
            continue
        tasks.append({"disciple": d, "path": path, "prompt": prompt_for(d), "flag_path": flag_path_for(d["sect_id"])})
    if args.limit:
        tasks = tasks[: args.limit]
    return tasks


async def generate_one(task: dict, idx: int, total: int, sem: asyncio.Semaphore) -> dict:
    d = task["disciple"]
    path = task["path"]
    async with sem:
        start = time.time()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            flag_path = task.get("flag_path")
            if flag_path and Path(flag_path).exists():
                result = await generate_image_with_references(
                    prompt=task["prompt"],
                    reference_paths=[str(flag_path)],
                    size="1024x1536",
                    quality="high",
                    output_format="png",
                    save_to=str(path.parent),
                    filename_prefix=path.stem,
                )
            else:
                result = await generate_image(
                    prompt=task["prompt"],
                    size="1024x1536",
                    quality="high",
                    output_format="png",
                    save_to=str(path.parent),
                    filename_prefix=path.stem,
                )
            if result and result[0].get("local_path"):
                src = Path(result[0]["local_path"])
                if src != path:
                    if path.exists():
                        path.unlink()
                    src.rename(path)
            elapsed = time.time() - start
            print(f"✅ [{idx:03d}/{total}] {d['id']} {d['name']} -> {path.name} ({elapsed:.1f}s)", flush=True)
            return {"ok": True, "id": d["id"], "path": str(path), "elapsed": elapsed}
        except ImageGenError as e:
            elapsed = time.time() - start
            print(f"❌ [{idx:03d}/{total}] {d['id']} {d['name']} {e}", flush=True)
            return {"ok": False, "id": d["id"], "error": str(e), "elapsed": elapsed}
        except Exception as e:
            elapsed = time.time() - start
            print(f"💥 [{idx:03d}/{total}] {d['id']} {d['name']} {type(e).__name__}: {e}", flush=True)
            return {"ok": False, "id": d["id"], "error": f"{type(e).__name__}: {e}", "elapsed": elapsed}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sect", choices=sorted(SECT_STYLE.keys()), default=None)
    parser.add_argument("--ids", default="", help="Comma separated disciple ids, e.g. canglan_01,canglan_02")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--print-prompt", action="store_true")
    args = parser.parse_args()

    tasks = collect_tasks(args)
    print(f"image2 disciple portrait tasks: {len(tasks)}")
    if args.dry_run:
        for task in tasks[:30]:
            d = task["disciple"]
            print(f"- {d['id']} {d['name']} -> {task['path']}")
            print(f"  flag_ref: {task['flag_path']}")
            if args.print_prompt:
                print(task["prompt"])
        return
    if not tasks:
        return

    sem = asyncio.Semaphore(max(1, args.concurrency))
    started = time.time()
    results = await asyncio.gather(*(generate_one(t, i + 1, len(tasks), sem) for i, t in enumerate(tasks)))
    ok = sum(1 for r in results if r["ok"])
    print(f"done: {ok}/{len(results)} in {time.time() - started:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
