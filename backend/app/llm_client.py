"""LLM 调用封装 — 流式 + 兜底"""

from __future__ import annotations

import os
import json
import random
import asyncio
from typing import AsyncGenerator, Callable, Awaitable
import httpx
from dotenv import load_dotenv

# 确保即便没经过 main.py 入口(如单元测试)也能拿到 .env
load_dotenv()


def _env(name: str, default: str = "") -> str:
    """运行时读环境变量(支持热更新)"""
    return os.environ.get(name, default)


LLM_TIMEOUT = int(_env("LLM_TIMEOUT", "60"))

# ===== 通用 system prompt(精简短叙事版本,与速度优化策略匹配) =====
BASE_SYSTEM_PROMPT = """你是《灵枢笔录》游戏的战斗叙事 AI。任务:把战斗动作转成精炼的国风中文叙事。

【世界观】仙侠修真,玩家是"执笔者",用天道之笔施展神通。常用词:灵气、境界、笔器、剑诀、咒诀。

【严格规则】
1. **字数**:60-100 字(以下情况例外:暴击 100-150,天命 150-220)
2. 视角:第二人称"你"
3. 自然融入数值(命中/伤害/暴击/闪避)
4. 不解释战斗逻辑,不打破第四面墙,不附总结建议
5. 文笔仙侠精练,2-3 句为佳,不啰嗦

【★ 重点标记】
用 Markdown ** 双星号 ** 包裹关键内容(前端会高亮):
- 招式名(如 **沧澜九式**)
- 伤害数字(如 **147 点伤害**)
- 暴击 / 关键判定(如 **暴击**、**致命**)
每段 2-3 处 ** 标记。

【天命招式】
判定为 "destiny" 时:夸张到极致 — 天地色变、千年一遇、天道颤栗 — 字数 150-220,至少 3 处 ** 标记。

【格式】直接输出叙事,不要前缀("叙事:"),不要 # 标题、列表、引用。
"""

# ===== Fallback 模板(LLM 失败时用) =====
FALLBACK_NARRATIONS = {
    "crit": [
        "你的笔锋如龙蛇出洞,陡然爆发出惊世骇俗的剑意,敌人来不及反应便受了重创。灵气暴涨,这一击仿佛凝聚了万年修为,直击要害!",
        "天道为之颤栗,你的笔锋撕开了空间。这一击,如九天降罡,势不可挡。敌人倒地,血光迸溅。",
        "你的眸光骤然冷冽,提笔便是一道惊天剑气。剑气掠过,敌人的护体灵气如纸糊般破碎,身上瞬间多了一道焦灼的伤口。",
    ],
    "hit": [
        "你挥笔挥洒,一道剑气直奔敌人,正中要害。敌人闷哼一声,踉跄退后。",
        "灵气流转于笔间,化为利刃斩出。这一击虽不致命,但足以让敌人感到痛楚。",
        "你冷静地落笔,如同书写一篇日常的功课。笔尖凝聚的灵气稳稳地命中了敌人。",
    ],
    "miss": [
        "你这一笔似乎慢了半拍,敌人灵巧地侧身躲过。它狡黠地一笑,反扑过来。",
        "你的笔锋扫过空气,只留下淡淡的灵气痕迹。敌人狡黠地一闪,你的攻击擦着它的衣角而过。",
    ],
    "heal": [
        "你取出一颗灵丹放入口中,温热的灵气在身体里流转,伤口以肉眼可见的速度愈合。",
        "你默运玄功,体内灵气流转,伤势缓缓恢复。",
    ],
    "buff": [
        "你深吸一口气,默运玄功,体内灵气如江河奔涌,凝聚于笔尖。下一击,必有惊人之变。",
        "你的眼神变得专注,周身灵气化作一层淡淡的光晕,蓄势待发。",
    ],
}


def build_user_prompt(state: dict, card: dict, outcome: dict) -> str:
    """构造用户 prompt(包含战斗上下文)"""
    return f"""战斗回合 {state['round']}:
- 玩家:{state['sect_name']}弟子(HP {state['player_hp']}/{state['player_max_hp']},境界:{state['realm_name']})
- 敌人:{state['enemy_name']}(HP {state['enemy_hp']}/{state['enemy_max_hp']})
- 玩家使用:{card['name']}({card['description']})
- 判定结果:
  - 类型:{outcome['type_zh']}
  - 数值:{outcome['effect_desc']}

请生成本回合的战斗叙事。"""


# ===== 重试配置 =====
MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", "3"))
RETRY_BASE_DELAY = float(os.environ.get("LLM_RETRY_BASE_DELAY", "1.0"))
RETRY_MAX_DELAY = float(os.environ.get("LLM_RETRY_MAX_DELAY", "8.0"))

# 不可重试的状态码:玩家配置 / 鉴权问题,重试无意义
NON_RETRYABLE_STATUS = {400, 401, 403, 404, 422}


class LLMRetryableError(Exception):
    """临时性错误,可重试"""
    pass


class LLMFatalError(Exception):
    """永久性错误,不重试"""
    pass


def _compute_backoff(attempt: int, retry_after: float = None) -> float:
    """指数退避 + 上限。429 时优先用 Retry-After"""
    if retry_after is not None:
        return min(retry_after, RETRY_MAX_DELAY)
    delay = RETRY_BASE_DELAY * (2 ** attempt)
    # 加 0-20% 抖动避免雪崩
    delay *= (1 + random.random() * 0.2)
    return min(delay, RETRY_MAX_DELAY)


async def _do_single_request(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    payload: dict,
    on_usage: Callable[[dict], Awaitable[None] | None] = None,
) -> AsyncGenerator[str, None]:
    """单次请求 + SSE 解析。可能抛 LLMRetryableError / LLMFatalError"""
    try:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            # === 错误判定 ===
            if resp.status_code >= 400:
                body = await resp.aread()
                body_text = body.decode("utf-8", errors="replace")[:300]
                msg = f"HTTP {resp.status_code}: {body_text}"

                if resp.status_code == 429:
                    # 限速,带 Retry-After
                    retry_after = resp.headers.get("Retry-After")
                    try:
                        retry_after_sec = float(retry_after) if retry_after else None
                    except ValueError:
                        retry_after_sec = None
                    err = LLMRetryableError(msg)
                    err.retry_after = retry_after_sec
                    raise err
                elif resp.status_code in NON_RETRYABLE_STATUS:
                    raise LLMFatalError(msg)
                elif resp.status_code >= 500:
                    raise LLMRetryableError(msg)
                else:
                    # 其它 4xx,默认不重试
                    raise LLMFatalError(msg)

            # === 成功,开始流式 — 兼容 chat/completions 和 Responses API 两种 SSE 格式 ===
            async for line in resp.aiter_lines():
                if not line:
                    continue
                # SSE 注释 / event: 行跳过
                if line.startswith(":") or line.startswith("event:"):
                    continue
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                usage = _extract_usage(obj)
                if usage and on_usage:
                    maybe = on_usage(usage)
                    if asyncio.iscoroutine(maybe):
                        await maybe
                # ─── 格式 A: chat/completions ─── choices[0].delta.content
                choices = obj.get("choices")
                if choices:
                    delta_content = choices[0].get("delta", {}).get("content")
                    if delta_content:
                        yield delta_content
                    continue
                # ─── 格式 B: Responses API ───
                # 事件类型:response.output_text.delta { delta: "..." }
                # 或顶层 output_text.delta { delta: "..." }
                evt_type = obj.get("type") or ""
                if evt_type.endswith("output_text.delta") or evt_type == "response.output_text.delta":
                    delta_text = obj.get("delta") or ""
                    if delta_text:
                        yield delta_text
                    continue
                # 兜底:其他 delta 字段
                if isinstance(obj.get("delta"), str) and obj["delta"]:
                    yield obj["delta"]
                    continue
                # response.completed 事件不再 yield(完整 output 已经在 delta 里给过)
    except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError,
            httpx.RemoteProtocolError, httpx.NetworkError) as e:
        raise LLMRetryableError(f"网络错误: {type(e).__name__}: {e}")


def _extract_usage(obj: dict) -> dict | None:
    """兼容 Chat Completions / Responses 的 usage 字段。"""
    usage = obj.get("usage")
    if not usage and isinstance(obj.get("response"), dict):
        usage = obj["response"].get("usage")
    if not isinstance(usage, dict):
        return None

    input_tokens = (
        usage.get("prompt_tokens")
        or usage.get("input_tokens")
        or usage.get("input_token_count")
        or 0
    )
    output_tokens = (
        usage.get("completion_tokens")
        or usage.get("output_tokens")
        or usage.get("output_token_count")
        or 0
    )
    reasoning_tokens = 0
    details = usage.get("completion_tokens_details") or usage.get("output_tokens_details") or {}
    if isinstance(details, dict):
        reasoning_tokens = details.get("reasoning_tokens") or details.get("reasoning") or 0
    total_tokens = usage.get("total_tokens") or (input_tokens + output_tokens + reasoning_tokens)
    try:
        return {
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
            "reasoning_tokens": int(reasoning_tokens or 0),
            "total_tokens": int(total_tokens or 0),
            "raw": usage,
        }
    except Exception:
        return None


async def _fallback_narration(user_prompt: str) -> AsyncGenerator[str, None]:
    """所有重试失败 → 流式输出预设模板"""
    outcome_type = "hit"
    if "暴击" in user_prompt:
        outcome_type = "crit"
    elif "闪避" in user_prompt or "失手" in user_prompt:
        outcome_type = "miss"
    elif "灵丹" in user_prompt or "回复" in user_prompt:
        outcome_type = "heal"
    elif "凝神" in user_prompt or "增益" in user_prompt:
        outcome_type = "buff"

    text = random.choice(FALLBACK_NARRATIONS.get(outcome_type, FALLBACK_NARRATIONS["hit"]))
    for i in range(0, len(text), 6):
        yield text[i:i+6]
        await asyncio.sleep(0.04)


def _is_openai_responses_model(model: str) -> bool:
    """gpt-5+ / o1 / o3 / o4 / o5 系列走 OpenAI Responses API"""
    m = (model or "").lower()
    return m.startswith(("gpt-5", "gpt-6", "o1", "o3", "o4", "o5"))


def _rough_token_count(text: str) -> int:
    if not text:
        return 0
    ascii_count = sum(1 for ch in text if ord(ch) < 128)
    non_ascii = len(text) - ascii_count
    return max(1, int(non_ascii / 1.35 + ascii_count / 4 + 0.999))


async def stream_battle_narration(
    sect_narration_style: str,
    model: str,
    max_tokens: int,
    user_prompt: str,
    api_key: str = None,
    base_url: str = None,
    on_usage: Callable[[dict], Awaitable[None] | None] = None,
    on_fallback: Callable[[], Awaitable[None] | None] = None,
    suppress_fallback: bool = False,
) -> AsyncGenerator[str, None]:
    """流式调用 LLM,带重试 + fallback 兜底。

    ★ 智能路由:
      - gpt-5+/o-series → POST /responses + SSE (含 response.output_text.delta 事件)
      - 其他模型        → POST /chat/completions + SSE (含 choices[].delta.content)

    重试策略:
      - 5xx / 网络错误 / 超时 / 429 → 可重试,指数退避
      - 4xx(除 429)→ 立即放弃,走 fallback
      - 最多 MAX_RETRIES 次(默认 3)
      - 一旦开始 yield 内容就不再重试(避免重复文本)
    """
    system = BASE_SYSTEM_PROMPT + "\n\n【你所属门派的特色风格】\n" + sect_narration_style

    use_responses = _is_openai_responses_model(model)

    if use_responses:
        # OpenAI Responses API:input 是字符串(单消息) 或 messages-like array
        payload = {
            "model": model,
            "instructions": system,
            "input": user_prompt,
            "max_output_tokens": max_tokens,
            "stream": True,
        }
    else:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.85,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

    # 优先用 BYOK,退到 env
    api_key = api_key or _env("LLM_API_KEY", "")
    base_url = base_url or _env("LLM_BASE_URL", "https://bobdong.cn/v1")

    if not api_key:
        print("[LLM Config] api_key 未配置,直接走 fallback")
        if on_fallback:
            maybe = on_fallback()
            if asyncio.iscoroutine(maybe):
                await maybe
        if suppress_fallback:
            return
        async for chunk in _fallback_narration(user_prompt):
            yield chunk
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    url = f"{base_url}/{'responses' if use_responses else 'chat/completions'}"
    last_error = None

    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        for attempt in range(MAX_RETRIES):
            yielded_any = False
            try:
                async for chunk in _do_single_request(client, url, headers, payload, on_usage=on_usage):
                    yielded_any = True
                    yield chunk
                # 正常结束
                if attempt > 0:
                    print(f"[LLM] 重试第 {attempt} 次后成功(model={model})")
                return

            except LLMFatalError as e:
                # 不可重试,直接 fallback
                last_error = e
                print(f"[LLM Fatal] {e}")
                break

            except LLMRetryableError as e:
                last_error = e
                # 已经吐过内容,不能重试(避免重复)
                if yielded_any:
                    print(f"[LLM] 流中断,已输出部分内容,放弃重试: {e}")
                    return

                if attempt < MAX_RETRIES - 1:
                    retry_after = getattr(e, "retry_after", None)
                    delay = _compute_backoff(attempt, retry_after)
                    print(f"[LLM Retry {attempt+1}/{MAX_RETRIES}] {e} -> 等待 {delay:.1f}s")
                    await asyncio.sleep(delay)
                    continue
                else:
                    print(f"[LLM] 重试 {MAX_RETRIES} 次仍失败: {e}")

            except Exception as e:
                # 未分类异常,记录后走 fallback
                last_error = e
                print(f"[LLM Unexpected] {type(e).__name__}: {e}")
                break

    # 所有重试都失败 → 流式输出 fallback
    print(f"[LLM Fallback] 启用兜底模板(原因: {last_error})")
    if on_fallback:
        maybe = on_fallback()
        if asyncio.iscoroutine(maybe):
            await maybe
    if suppress_fallback:
        return
    async for chunk in _fallback_narration(user_prompt):
        yield chunk


# ============================================================
# v2 新增:分级 + 合并 + 池 + 章节
# ============================================================

# ★ 战斗推演模型:使用角色门派 + 等级阶段模型,只根据动作类型调整 max_tokens。
def pick_narration_model(
    player_tier_model: str,
    is_destiny: bool = False,
    is_crit: bool = False,
):
    """根据动作类型选 max_tokens,模型使用当前境界 tier.model。

    返回 (model, max_tokens)。

    失败/空内容时由上层走 fallback,不阻塞战斗。
    """
    model = player_tier_model or ""
    if is_destiny:
        return model, 220
    if is_crit:
        return model, 120
    return model, 80


def build_combined_user_prompt(
    state: dict,
    player_card,
    player_outcome: dict,
    enemy_skill=None,
    enemy_outcome: dict = None,
) -> str:
    """合并双方动作到一个 prompt,只调一次 LLM 描写整个回合"""
    txt = f"战斗回合 {state['round']}:\n"
    txt += f"- 玩家:{state['sect_name']}弟子(HP {state['player_hp']}/{state['player_max_hp']})\n"
    txt += f"- 敌人:{state['enemy_name']}(HP {state['enemy_hp']}/{state['enemy_max_hp']})\n\n"
    txt += "本回合发生:\n"
    txt += f"1. 玩家使用【{player_card.name}】({getattr(player_card, 'description', '')})\n"
    txt += f"   结果:{player_outcome.get('type_zh', '?')} - {player_outcome.get('effect_desc', '')}\n"
    if enemy_skill and enemy_outcome:
        txt += f"2. {state['enemy_name']}反击,使用【{enemy_skill.name}】\n"
        txt += f"   结果:{enemy_outcome.get('type_zh', '?')} - {enemy_outcome.get('effect_desc', '')}\n"
    elif not enemy_skill:
        txt += "2. 敌人被你一击毙命,未及反击。\n"
    txt += "\n请用 60-100 字描写本回合(若有暴击/天命可适当延长)。重点用 ** 标记招式、伤害数字、关键字。"
    return txt


async def stream_combined_narration(
    sect_style: str,
    model: str,
    max_tokens: int,
    state: dict,
    player_card,
    player_outcome: dict,
    enemy_skill=None,
    enemy_outcome: dict = None,
    api_key: str = None,
    base_url: str = None,
    on_usage: Callable[[dict], Awaitable[None] | None] = None,
    on_fallback: Callable[[], Awaitable[None] | None] = None,
) -> AsyncGenerator[str, None]:
    """合并叙事:一次 LLM 调用描写双方动作(减半 LLM 调用)"""
    user_prompt = build_combined_user_prompt(
        state, player_card, player_outcome, enemy_skill, enemy_outcome,
    )
    async for chunk in stream_battle_narration(
        sect_narration_style=sect_style,
        model=model,
        max_tokens=max_tokens,
        user_prompt=user_prompt,
        api_key=api_key,
        base_url=base_url,
        on_usage=on_usage,
        on_fallback=on_fallback,
    ):
        yield chunk


async def prefetch_pool_narrations(
    sect_style: str,
    state: dict,
    count: int,
    api_key: str = None,
    base_url: str = None,
    model: str = None,
    on_usage: Callable[[dict], Awaitable[None] | None] = None,
) -> list:
    """预生成 N 段通用普攻叙事(用当前境界模型并发跑)

    用于"预生成池":玩家第一击直接拿池里现成的,0 延迟。
    """
    if count <= 0:
        return []

    use_model = model or state.get("model") or ""
    sect_name = state.get("sect_name", "门派")
    enemy_name = state.get("enemy_name", "妖兽")

    async def _one(i: int):
        prompt = (
            f"想象一次{sect_name}弟子对【{enemy_name}】的普通攻击。\n"
            f"描写一个常见的小范围交锋,60 字左右,带 2 处 ** 标记关键词。"
            f"不必给出具体伤害数字(留空让前端填),侧重动作感。"
            f"这是第 {i+1} 个备用版本,请有所变化。"
        )
        chunks = []
        usage_seen = False
        async def _on_usage(usage: dict):
            nonlocal usage_seen
            usage_seen = True
            if on_usage:
                maybe = on_usage(usage)
                if asyncio.iscoroutine(maybe):
                    await maybe
        try:
            async for c in stream_battle_narration(
                sect_narration_style=sect_style,
                model=use_model,
                max_tokens=120,
                user_prompt=prompt,
                api_key=api_key, base_url=base_url,
                on_usage=_on_usage,
                suppress_fallback=True,
            ):
                chunks.append(c)
        except Exception:
            return None
        text = "".join(chunks).strip()
        if text and not usage_seen and on_usage:
            maybe = on_usage({
                "input_tokens": _rough_token_count(prompt),
                "output_tokens": _rough_token_count(text),
                "reasoning_tokens": 0,
                "total_tokens": _rough_token_count(prompt) + _rough_token_count(text),
                "estimated": True,
            })
            if asyncio.iscoroutine(maybe):
                await maybe
        return text or None

    results = await asyncio.gather(*[_one(i) for i in range(count)], return_exceptions=True)
    return [r for r in results if isinstance(r, str) and r]


async def stream_chapter_narration(
    sect_style: str,
    state: dict,
    history: list,
    api_key: str = None,
    base_url: str = None,
    model: str = None,
    on_usage: Callable[[dict], Awaitable[None] | None] = None,
    on_fallback: Callable[[], Awaitable[None] | None] = None,
    suppress_fallback: bool = False,
) -> AsyncGenerator[str, None]:
    """战后完整章节 — 500 字,使用当前境界模型"""
    sect_name = state.get("sect_name", "")
    realm = state.get("realm_name", "")
    enemy_name = state.get("enemy_name", "")
    result = state.get("result") or "unfinished"
    result_zh = {"victory": "你大获全胜", "defeat": "你败北而归", "fled": "你撤退离场"}.get(result, "战斗结束")

    prompt = f"""请为这场战斗写一段 **400-550 字** 的章回小说体回顾,要求:
- 标题用「第N章 · 副标题」格式(N 用中文数字)
- 文笔仙侠,有起承转合,描写心境与场景
- 至少 5 处 ** 标记重点(招式、关键瞬间、伤害数字、胜负判定)
- 必须写完整结尾,最后一段收束战斗因果,不要写“未完待续”

【战斗背景】
- 主角:{sect_name}弟子,境界 {realm}
- 对手:{enemy_name}
- 结局:{result_zh}
- 共 {len(history)} 回合

【主要交锋】
"""
    for h in history[-6:]:  # 最近 6 回合(更早的写"略")
        pa = h.get("player_action") or {}
        ea = h.get("enemy_action") or {}
        prompt += f"回合 {h['round']}:玩家「{pa.get('name','?')}」 - {pa.get('outcome',{}).get('type_zh','?')}"
        if ea:
            prompt += f";敌「{ea.get('name','?')}」 - {ea.get('outcome',{}).get('type_zh','?')}"
        prompt += "\n"

    prompt += "\n请开始撰写章节正文(直接输出,不要解释)。最后一句必须以句号、叹号或问号结尾。"

    # 章节统一用当前境界模型,给足输出空间,避免正文被 max_tokens 截断。
    use_model = model or state.get("model") or ""
    async for chunk in stream_battle_narration(
        sect_narration_style=sect_style,
        model=use_model,
        max_tokens=1200,
        user_prompt=prompt,
        api_key=api_key, base_url=base_url,
        on_usage=on_usage,
        on_fallback=on_fallback,
        suppress_fallback=suppress_fallback,
    ):
        yield chunk
