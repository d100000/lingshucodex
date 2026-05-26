"""墨炉队列 — token 成章并实时转修为。

这是燃灵成章方案的后端最小闭环:
- 玩法系统只创建 cultivation_task。
- 墨炉后台流式写章节。
- 估算 token 写入 ledger,同步增加角色修为。
- 完成后生成 novel_chapters。
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from datetime import datetime

from .attributes import check_level_up
from .llm_client import stream_battle_narration, stream_chapter_narration
from .sects import get_sect, get_tier_for_level
from .store import (
    add_journal_entry,
    add_task_input_tokens,
    add_token_ledger,
    append_task_content,
    create_cultivation_task,
    create_novel_chapter,
    get_character,
    get_cultivation_task,
    get_next_queued_task,
    list_pending_cultivation_user_ids,
    list_cultivation_tasks,
    reset_interrupted_cultivation_tasks,
    save_character,
    update_cultivation_task,
)

CHAPTER_INITIAL_RETRY_LIMIT = 3
CHAPTER_REPAIR_LIMIT = 4
CHAPTER_REPAIR_MAX_TOKENS = 700
SENTENCE_ENDINGS = set("。！？.!?")
CLOSING_ENDINGS = "」』”’）】》"
INCOMPLETE_ENDINGS = ("，", "、", "；", "：", ",", ";", ":", "——", "-", "「", "『", "“", "‘", "（", "(", "【", "《")

_active_users: set[str] = set()


def estimate_tokens(text: str) -> int:
    """轻量 token 估算。中文文本通常接近 1~2 字/token,这里偏保守计费。"""
    if not text:
        return 0
    ascii_count = sum(1 for ch in text if ord(ch) < 128)
    non_ascii = len(text) - ascii_count
    return max(1, math.ceil(non_ascii / 1.35 + ascii_count / 4))


def ensure_cultivation_fields(char: dict) -> dict:
    base = int(char.get("cultivation_total", char.get("exp", 0) or 0))
    char.setdefault("cultivation_total", base)
    char.setdefault("token_total", int(char.get("token_total", base)))
    char.setdefault("novel_words_total", 0)
    char.setdefault("chapters_count", 0)
    char.setdefault("current_volume", 1)
    char.setdefault("current_chapter_no", 0)
    char.setdefault("daily_token_used", 0)
    char.setdefault("monthly_token_used", 0)
    char["budget_chapter"] = 0
    char["budget_daily"] = 0
    char["budget_monthly"] = 0
    char["budget_confirm_required"] = False
    char.setdefault("daily_token_date", datetime.now().strftime("%Y-%m-%d"))
    char.setdefault("monthly_token_month", datetime.now().strftime("%Y-%m"))
    return char


def _roll_token_windows(char: dict) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")
    if char.get("daily_token_date") != today:
        char["daily_token_date"] = today
        char["daily_token_used"] = 0
    if char.get("monthly_token_month") != month:
        char["monthly_token_month"] = month
        char["monthly_token_used"] = 0


def apply_cultivation_gain(user_id: str, delta_tokens: int, task_id: str, source: str, model: str = "",
                           input_tokens: int = 0, output_tokens: int = 0,
                           reasoning_tokens: int = 0, usage_source: str = "estimated") -> dict:
    if delta_tokens <= 0:
        return {"level_up": []}

    char = get_character(user_id)
    if not char:
        return {"level_up": []}
    ensure_cultivation_fields(char)
    _roll_token_windows(char)

    char["cultivation_total"] = int(char.get("cultivation_total", 0)) + delta_tokens
    char["token_total"] = int(char.get("token_total", 0)) + delta_tokens
    char["daily_token_used"] = int(char.get("daily_token_used", 0)) + delta_tokens
    char["monthly_token_used"] = int(char.get("monthly_token_used", 0)) + delta_tokens
    char["exp"] = int(char.get("exp", 0)) + delta_tokens
    leveled = check_level_up(char)
    save_character(user_id, char)

    add_token_ledger(
        user_id=user_id,
        task_id=task_id,
        source=source,
        delta_tokens=delta_tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
        usage_source=usage_source,
        model=model,
    )

    if leveled:
        for lvl in leveled:
            title = f"突破至 {lvl['new_realm']}" if lvl.get("new_realm") else f"升级至 Lv.{lvl['level']}"
            add_journal_entry(
                user_id,
                "level_up",
                title,
                f"墨炉燃灵,修为累积至 Lv.{lvl['level']}",
                {"tags": ["突破", "燃灵"]},
            )
            if lvl.get("new_realm"):
                try:
                    create_cultivation_task(
                        user_id=user_id,
                        task_type="breakthrough",
                        title=f"劫章 · {lvl['new_realm']}",
                        prompt_payload={
                            "level": lvl.get("level"),
                            "new_realm": lvl.get("new_realm"),
                            "newly_learned_skills": lvl.get("newly_learned_skills", []),
                        },
                        source_type="level_up",
                        source_id=str(lvl.get("level")),
                        priority=6,
                        model=model,
                    )
                    schedule_user_queue(user_id)
                except Exception as exc:
                    print(f"[cultivation] enqueue breakthrough failed: {exc}")
    return {"level_up": leveled}


def enqueue_task(
    user_id: str,
    task_type: str,
    title: str,
    prompt_payload: dict | None = None,
    source_type: str = "",
    source_id: str = "",
    priority: int = 0,
    model: str = "",
) -> dict:
    task = create_cultivation_task(
        user_id=user_id,
        task_type=task_type,
        title=title,
        prompt_payload=prompt_payload or {},
        source_type=source_type,
        source_id=source_id,
        priority=priority,
        model=model,
    )
    schedule_user_queue(user_id)
    return task


def schedule_user_queue(user_id: str) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    if user_id in _active_users:
        return
    loop.create_task(_run_user_queue(user_id))


async def _run_user_queue(user_id: str) -> None:
    if user_id in _active_users:
        return
    _active_users.add(user_id)
    try:
        while True:
            task = get_next_queued_task(user_id)
            if not task:
                return
            await run_task(task["id"])
            latest = get_cultivation_task(task["id"])
            if latest and latest.get("status") == "paused":
                return
    finally:
        _active_users.discard(user_id)


def _task_title(task_type: str, payload: dict) -> str:
    enemy_name = (payload.get("state") or {}).get("enemy_name") or payload.get("enemy_name")
    if task_type == "battle_victory":
        return f"正传章 · {enemy_name or '战斗'}"
    if task_type == "battle_defeat":
        return f"败笔章 · {enemy_name or '战斗'}"
    if task_type == "battle_flee":
        return f"撤离章 · {enemy_name or '战斗'}"
    if task_type == "battle_pacify":
        return f"人情章 · {enemy_name or '赠礼'}"
    if task_type == "npc_spar":
        return f"切磋章 · {enemy_name or '同道'}"
    if task_type == "fortune":
        return f"外传章 · {payload.get('name') or '奇遇'}"
    if task_type == "boss_chapter":
        return f"道君外传 · {payload.get('boss_name') or '天外道君'}"
    if task_type == "breakthrough":
        return f"劫章 · {payload.get('new_realm') or '破境'}"
    if task_type == "retreat_long":
        return "闭关章 · 墨炉长明"
    return "内景章 · 灵台生墨"


def make_battle_task(user_id: str, result: str, state: dict, history: list, rewards: dict | None = None,
                     drops: list | None = None) -> dict:
    mapping = {
        "victory": "battle_victory",
        "defeat": "battle_defeat",
        "fled": "battle_flee",
        "pacified": "battle_pacify",
        "spar_win": "npc_spar",
        "spar_loss": "npc_spar",
    }
    task_type = mapping.get(result, "battle_victory")
    payload = {
        "state": state,
        "history": history,
        "rewards": rewards or {},
        "drops": drops or [],
        "result": result,
    }
    title = _task_title(task_type, payload)
    return enqueue_task(
        user_id=user_id,
        task_type=task_type,
        title=title,
        prompt_payload=payload,
        source_type="battle",
        source_id=state.get("battle_id", ""),
        priority=5 if task_type.startswith("battle") else 3,
        model=state.get("model", ""),
    )


async def run_task(task_id: str) -> None:
    task = get_cultivation_task(task_id)
    if not task or task["status"] not in ("queued", "running"):
        return

    user_id = task["user_id"]
    char = get_character(user_id)
    if not char:
        update_cultivation_task(task_id, status="failed", error="角色不存在", finished_at=datetime.now().isoformat())
        return
    ensure_cultivation_fields(char)
    save_character(user_id, char)

    update_cultivation_task(task_id, status="running", started_at=task.get("started_at") or datetime.now().isoformat())
    task = get_cultivation_task(task_id)

    try:
        prompt_seed = json.dumps(task.get("prompt_payload") or {}, ensure_ascii=False)
        input_tokens = estimate_tokens(prompt_seed)

        usage_holder = {"usage": None, "fallback": False}
        wrote_initial = await _write_initial_chapter_with_retries(task_id, task, input_tokens, usage_holder)
        latest = get_cultivation_task(task_id)
        if latest and latest.get("status") != "running":
            return
        if not wrote_initial:
            update_cultivation_task(task_id, status="failed", error="墨炉多次重试后仍未落字", finished_at=datetime.now().isoformat())
            return

        finished = get_cultivation_task(task_id)
        if usage_holder.get("fallback"):
            update_cultivation_task(task_id, status="failed", error="LLM fallback 不计修为,章节未入本命书",
                                    finished_at=datetime.now().isoformat())
            return

        await _repair_unfinished_chapter(task_id, task, usage_holder)
        latest = get_cultivation_task(task_id)
        if latest and latest.get("status") != "running":
            return
        finished = latest or get_cultivation_task(task_id)

        if usage_holder.get("usage"):
            _reconcile_provider_usage(user_id, task_id, usage_holder["usage"], (finished or {}).get("model") or task.get("model") or "")
            finished = get_cultivation_task(task_id)
        content = (finished or {}).get("content_partial", "").strip()
        if not content:
            update_cultivation_task(task_id, status="failed", error="墨炉未能落字", finished_at=datetime.now().isoformat())
            return
        is_partial = _chapter_needs_continuation(content)

        chapter = create_novel_chapter(
            user_id=user_id,
            chapter_type=task["task_type"],
            title=_extract_title(content) or task["title"],
            content=content,
            task_id=task_id,
            source_type=task.get("source_type") or "",
            source_id=task.get("source_id") or "",
            battle_id=(task.get("prompt_payload") or {}).get("state", {}).get("battle_id", ""),
            enemy_id=(task.get("prompt_payload") or {}).get("state", {}).get("enemy_id", ""),
            token_count=finished["estimated_tokens"],
            input_tokens=finished["input_tokens"],
            output_tokens=finished["output_tokens"],
            reasoning_tokens=finished["reasoning_tokens"],
            cultivation_gained=finished["cultivation_gained"],
            model=finished.get("model") or "",
            usage_source=finished.get("usage_source") or "estimated",
            is_partial=is_partial,
        )
        _mark_character_chapter(user_id, chapter)
        update_cultivation_task(
            task_id,
            status="partial" if is_partial else "completed",
            settled_tokens=finished["estimated_tokens"],
            finished_at=datetime.now().isoformat(),
            error="章节疑似未收束,已作为断章入书" if is_partial else None,
        )
        add_journal_entry(
            user_id,
            "novel_chapter",
            f"本命书成章·{chapter['title']}",
            f"燃灵 {chapter['token_count']} token,修为 +{chapter['cultivation_gained']}",
            {"tags": ["本命书", "燃灵"], "chapter_id": chapter["id"], "task_id": task_id},
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        partial = (get_cultivation_task(task_id) or {}).get("content_partial", "")
        if partial.strip():
            chapter = create_novel_chapter(
                user_id=user_id,
                chapter_type=task["task_type"],
                title=f"断章 · {task['title'].split('·')[-1].strip()}",
                content=partial,
                task_id=task_id,
                source_type=task.get("source_type") or "",
                source_id=task.get("source_id") or "",
                token_count=(get_cultivation_task(task_id) or {}).get("estimated_tokens", 0),
                cultivation_gained=(get_cultivation_task(task_id) or {}).get("cultivation_gained", 0),
                model=(get_cultivation_task(task_id) or {}).get("model") or task.get("model") or "",
                is_partial=True,
            )
            _mark_character_chapter(user_id, chapter)
            update_cultivation_task(task_id, status="partial", error=str(exc)[:300], finished_at=datetime.now().isoformat())
        else:
            update_cultivation_task(task_id, status="failed", error=str(exc)[:300], finished_at=datetime.now().isoformat())


async def _write_initial_chapter_with_retries(
    task_id: str,
    task: dict,
    input_tokens: int,
    usage_holder: dict,
) -> bool:
    for attempt in range(CHAPTER_INITIAL_RETRY_LIMIT):
        usage_holder["fallback"] = False
        wrote_any = await _append_stream_to_task(
            task_id=task_id,
            task=task,
            stream=_stream_task_chunks(task, usage_holder),
            input_tokens=input_tokens,
            input_source="prompt" if attempt == 0 else "prompt_retry",
            output_source="chapter_delta" if attempt == 0 else "chapter_retry_delta",
        )
        current = get_cultivation_task(task_id)
        if not current or current.get("status") != "running":
            return wrote_any
        if wrote_any:
            return True
        if attempt < CHAPTER_INITIAL_RETRY_LIMIT - 1:
            await asyncio.sleep(0.8 * (attempt + 1))
    return False


async def _append_stream_to_task(
    task_id: str,
    task: dict,
    stream,
    input_tokens: int,
    input_source: str,
    output_source: str,
) -> bool:
    user_id = task["user_id"]
    input_tokens_applied = False
    wrote_any = False

    async for chunk in stream:
        if not chunk:
            continue
        current = get_cultivation_task(task_id)
        if not current or current["status"] != "running":
            return wrote_any
        used_model = current.get("model") or task.get("model") or ""

        if not input_tokens_applied and input_tokens > 0:
            add_task_input_tokens(task_id, input_tokens)
            apply_cultivation_gain(
                user_id, input_tokens, task_id, input_source,
                model=used_model, input_tokens=input_tokens,
            )
            input_tokens_applied = True

        output_tokens = estimate_tokens(chunk)
        append_task_content(task_id, chunk, output_tokens, output_tokens)
        apply_cultivation_gain(
            user_id, output_tokens, task_id, output_source,
            model=used_model, output_tokens=output_tokens,
        )
        wrote_any = True
    return wrote_any


async def _repair_unfinished_chapter(task_id: str, task: dict, usage_holder: dict) -> None:
    for attempt in range(CHAPTER_REPAIR_LIMIT):
        current = get_cultivation_task(task_id)
        if not current or current.get("status") != "running":
            return
        content = (current.get("content_partial") or "").strip()
        if not content or not _chapter_needs_continuation(content):
            return

        prompt = _build_continuation_prompt(task, content, attempt + 1)
        wrote_any = await _append_stream_to_task(
            task_id=task_id,
            task=task,
            stream=_stream_continuation_chunks(task, prompt, usage_holder),
            input_tokens=estimate_tokens(prompt),
            input_source="continuation_prompt",
            output_source="chapter_continuation",
        )
        if not wrote_any:
            await asyncio.sleep(0.8 * (attempt + 1))
            continue


def _record_usage(usage_holder: dict | None, usage: dict) -> None:
    if usage_holder is None or not usage:
        return
    current = usage_holder.get("usage") or {}
    input_tokens = int(current.get("input_tokens") or 0) + int(usage.get("input_tokens") or 0)
    output_tokens = int(current.get("output_tokens") or 0) + int(usage.get("output_tokens") or 0)
    reasoning_tokens = int(current.get("reasoning_tokens") or 0) + int(usage.get("reasoning_tokens") or 0)
    total_tokens = int(current.get("total_tokens") or 0) + int(
        usage.get("total_tokens") or (
            int(usage.get("input_tokens") or 0)
            + int(usage.get("output_tokens") or 0)
            + int(usage.get("reasoning_tokens") or 0)
        )
    )
    usage_holder["usage"] = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
        "raw": usage.get("raw") or usage,
    }


def _chapter_needs_continuation(content: str) -> bool:
    text = (content or "").strip()
    if not text:
        return False
    tail = text[-40:]
    if "未完待续" in tail or "待续" in tail:
        return True
    core = text.rstrip(CLOSING_ENDINGS)
    if not core:
        return False
    if core.endswith(INCOMPLETE_ENDINGS):
        return True
    return core[-1] not in SENTENCE_ENDINGS


def _build_continuation_prompt(task: dict, content: str, attempt: int) -> str:
    tail = content[-900:]
    return f"""下面是一段本命书章节的已有正文,最后疑似被截断。请沿着末尾继续写,只输出可直接拼接在后面的正文,不要重复标题或已有内容。

【章节】{task.get('title', '本命书章节')}
【续写轮次】{attempt}
【已有正文末尾】
{tail}

要求:
- 续写 180-320 字,补足当前场景的因果与情绪收束
- 最后一段必须让本章自然结束,最后一个字符必须是句号、叹号或问号
- 不要写“未完待续”,不要解释任务,不要输出列表
"""


async def _stream_continuation_chunks(task: dict, prompt: str, usage_holder: dict | None = None):
    char = get_character(task["user_id"]) or {}
    sect_id = char.get("sect", "canglan")
    sect = get_sect(sect_id)
    tier = get_tier_for_level(sect_id, char.get("level", 1))
    model = task.get("model") or (tier.model if tier else "")
    style = (sect.narration_style if sect else "国风修真,章回小说")
    if model and not task.get("model"):
        update_cultivation_task(task["id"], model=model)

    async def _on_usage(usage: dict):
        _record_usage(usage_holder, usage)

    async def _on_fallback():
        if usage_holder is not None:
            usage_holder["fallback"] = True

    async for chunk in stream_battle_narration(
        sect_narration_style=style,
        model=model,
        max_tokens=CHAPTER_REPAIR_MAX_TOKENS,
        user_prompt=prompt,
        api_key=char.get("api_key"),
        base_url=char.get("base_url"),
        on_usage=_on_usage,
        on_fallback=_on_fallback,
        suppress_fallback=True,
    ):
        yield chunk


def _reconcile_provider_usage(user_id: str, task_id: str, usage: dict, model: str = "") -> None:
    task = get_cultivation_task(task_id)
    if not task:
        return
    precise_total = int(usage.get("total_tokens") or 0)
    if precise_total <= 0:
        return
    estimated_before = int(task.get("estimated_tokens") or 0)
    cultivation_before = int(task.get("cultivation_gained") or 0)
    diff = 0
    final_total = max(estimated_before, precise_total)
    if precise_total > estimated_before:
        diff = precise_total - estimated_before
        apply_cultivation_gain(
            user_id,
            diff,
            task_id,
            "usage_reconcile",
            model=model,
            reasoning_tokens=int(usage.get("reasoning_tokens") or 0),
            usage_source="provider",
        )
    snapshot = task.get("budget_snapshot") or {}
    if precise_total < estimated_before:
        snapshot["tiandao_yumo"] = estimated_before - precise_total
    update_cultivation_task(
        task_id,
        estimated_tokens=final_total,
        input_tokens=int(usage.get("input_tokens") or task.get("input_tokens") or 0),
        output_tokens=int(usage.get("output_tokens") or task.get("output_tokens") or 0),
        reasoning_tokens=int(usage.get("reasoning_tokens") or 0),
        settled_tokens=final_total,
        cultivation_gained=cultivation_before + diff,
        usage_source="provider",
        budget_snapshot=snapshot,
    )


async def _stream_task_chunks(task: dict, usage_holder: dict | None = None):
    payload = task.get("prompt_payload") or {}
    char = get_character(task["user_id"]) or {}
    sect_id = char.get("sect", "canglan")
    sect = get_sect(sect_id)
    tier = get_tier_for_level(sect_id, char.get("level", 1))
    model = task.get("model") or (tier.model if tier else "")
    style = (sect.narration_style if sect else "国风修真,章回小说")
    if model and not task.get("model"):
        update_cultivation_task(task["id"], model=model)

    async def _on_usage(usage: dict):
        _record_usage(usage_holder, usage)

    async def _on_fallback():
        if usage_holder is not None:
            usage_holder["fallback"] = True

    if task["task_type"].startswith("battle") or task["task_type"] == "npc_spar":
        state = payload.get("state") or {}
        history = payload.get("history") or []
        async for chunk in stream_chapter_narration(
            sect_style=style,
            state=state,
            history=history,
            api_key=char.get("api_key"),
            base_url=char.get("base_url"),
            model=model,
            on_usage=_on_usage,
            on_fallback=_on_fallback,
            suppress_fallback=True,
        ):
            yield chunk
        return

    prompt = _build_freeform_prompt(task, char)
    async for chunk in stream_battle_narration(
        sect_narration_style=style,
        model=model,
        max_tokens=1400 if task["task_type"] == "retreat_long" else 900,
        user_prompt=prompt,
        api_key=char.get("api_key"),
        base_url=char.get("base_url"),
        on_usage=_on_usage,
        on_fallback=_on_fallback,
        suppress_fallback=True,
    ):
        yield chunk


def _build_freeform_prompt(task: dict, char: dict) -> str:
    payload = task.get("prompt_payload") or {}
    name = char.get("name", "执笔者")
    sect = char.get("sect_name", "")
    realm = char.get("realm_name", "")
    if task["task_type"] == "fortune":
        return f"""请写一段 300-500 字的本命书外传章。

【主角】{name},{sect}弟子,境界 {realm}
【奇遇】{payload.get('name','奇遇')}
【奇遇内容】{payload.get('narrative','')}
【效果】{json.dumps(payload.get('applied',{}), ensure_ascii=False)}

要求:章回小说体,标题用「第N章 · 副标题」格式,写出因果入书的感觉。必须完整收束,不要写“未完待续”,最后一句以句号、叹号或问号结尾。直接输出正文。"""

    if task["task_type"] == "boss_chapter":
        return f"""请写一段 600-800 字的本命书道君外传章。

【主角】{name},{sect}弟子,境界 {realm}
【天外道君】{payload.get('boss_name','未知道君')}
【称号】{payload.get('title','')}
【宗派/公司】{payload.get('sect_name','')} {payload.get('company','')}
【背景】{payload.get('lore','')}
【真实背景演绎】{payload.get('real_background','')}

要求:章回小说体,标题用「第N章 · 副标题」格式。把 Boss 写成天外道统投影,作为后续正传大章伏笔。必须完整收束,不要写“未完待续”,最后一句以句号、叹号或问号结尾。直接输出正文。"""

    if task["task_type"] == "breakthrough":
        return f"""请写一段 500-700 字的本命书劫章。

【主角】{name},{sect}弟子,境界 {realm}
【破境结果】Lv.{payload.get('level')} · {payload.get('new_realm','新境界')}
【新悟招式】{payload.get('newly_learned_skills', [])}

要求:章回小说体,标题用「第N章 · 副标题」格式。重点写墨炉燃灵、天书翻页、雷劫/心劫与境界稳定。必须完整收束,不要写“未完待续”,最后一句以句号、叹号或问号结尾。直接输出正文。"""

    if task["task_type"] == "retreat_long":
        return f"""请写一段 700-900 字的本命书闭关章。

【主角】{name},{sect}弟子,境界 {realm}
【闭关主题】{payload.get('theme','墨炉长明,灵台观照')}

要求:写内景、心魔、经脉、天书翻页与修为增长,不要提 API/token,用“燃灵墨”表达消耗。标题用「第N章 · 副标题」格式。必须完整收束,不要写“未完待续”,最后一句以句号、叹号或问号结尾。直接输出正文。"""

    return f"""请写一段 300-500 字的本命书内景章。

【主角】{name},{sect}弟子,境界 {realm}
【主题】{payload.get('theme','灵台生墨,入定成章')}

要求:章回小说体,标题用「第N章 · 副标题」格式。描写调息后的入定、灵台、经脉与本命书落字。不要提 API/token,用“燃灵墨”表达消耗。必须完整收束,不要写“未完待续”,最后一句以句号、叹号或问号结尾。直接输出正文。"""


def _extract_title(content: str) -> str:
    first = (content or "").strip().splitlines()[0].strip() if content else ""
    if len(first) <= 40 and ("章" in first or "断章" in first):
        return first.strip("# 「」")
    return ""


def _mark_character_chapter(user_id: str, chapter: dict) -> None:
    char = get_character(user_id)
    if not char:
        return
    ensure_cultivation_fields(char)
    char["novel_words_total"] = int(char.get("novel_words_total", 0)) + int(chapter.get("word_count", 0))
    char["chapters_count"] = int(char.get("chapters_count", 0)) + 1
    char["current_volume"] = chapter.get("volume_no", char.get("current_volume", 1))
    char["current_chapter_no"] = chapter.get("chapter_no", char.get("current_chapter_no", 0))
    char["last_chapter_id"] = chapter.get("id")
    save_character(user_id, char)


def cancel_running_task(task_id: str, user_id: str) -> dict:
    task = get_cultivation_task(task_id)
    if not task or task["user_id"] != user_id:
        raise ValueError("任务不存在")
    if task["status"] == "queued":
        return update_cultivation_task(task_id, status="cancelled", cancelled_at=datetime.now().isoformat())
    if task["status"] in ("running", "budget_blocked", "paused") and task.get("content_partial"):
        chapter = create_novel_chapter(
            user_id=user_id,
            chapter_type=task["task_type"],
            title=f"断章 · {task['title'].split('·')[-1].strip()}",
            content=task["content_partial"],
            task_id=task_id,
            source_type=task.get("source_type") or "",
            source_id=task.get("source_id") or "",
            token_count=task.get("estimated_tokens", 0),
            input_tokens=task.get("input_tokens", 0),
            output_tokens=task.get("output_tokens", 0),
            cultivation_gained=task.get("cultivation_gained", 0),
            model=task.get("model") or "",
            is_partial=True,
        )
        _mark_character_chapter(user_id, chapter)
        return update_cultivation_task(task_id, status="partial", cancelled_at=datetime.now().isoformat())
    return update_cultivation_task(task_id, status="cancelled", cancelled_at=datetime.now().isoformat())


def resume_task(task_id: str, user_id: str) -> dict:
    task = get_cultivation_task(task_id)
    if not task or task["user_id"] != user_id:
        raise ValueError("任务不存在")
    updated = update_cultivation_task(task_id, status="queued", error=None, paused_at=None)
    schedule_user_queue(user_id)
    return updated


def pause_task(task_id: str, user_id: str) -> dict:
    task = get_cultivation_task(task_id)
    if not task or task["user_id"] != user_id:
        raise ValueError("任务不存在")
    return update_cultivation_task(task_id, status="paused", paused_at=datetime.now().isoformat())


def queue_overview(user_id: str) -> dict:
    tasks = list_cultivation_tasks(user_id, include_done=False, limit=30)
    unblocked = False
    for task in tasks:
        if task["status"] == "budget_blocked":
            update_cultivation_task(task["id"], status="queued", error=None, paused_at=None)
            unblocked = True
    if unblocked:
        schedule_user_queue(user_id)
        tasks = list_cultivation_tasks(user_id, include_done=False, limit=30)
    return {
        "tasks": tasks,
        "running": next((t for t in tasks if t["status"] == "running"), None),
        "queued_count": sum(1 for t in tasks if t["status"] == "queued"),
        "active_count": len(tasks),
        "server_time": int(time.time()),
    }


def recover_all_queues() -> int:
    reset_interrupted_cultivation_tasks()
    user_ids = list_pending_cultivation_user_ids()
    for uid in user_ids:
        schedule_user_queue(uid)
    return len(user_ids)
