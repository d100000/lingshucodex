"""模型健康检查 — 验证 BYOK 提交的 base_url + api_key 能调用所有该派模型"""

import time
import asyncio
import json
import httpx
from typing import AsyncGenerator
from .sects import get_sect, ALL_SECTS, resolve_model_for_sect


def httpx_json_loads(raw_bytes):
    """安全 JSON 解码 — bytes/str 都能吃"""
    if isinstance(raw_bytes, bytes):
        raw_bytes = raw_bytes.decode("utf-8", "ignore")
    return json.loads(raw_bytes)


# ================================================================
# 入门首次探测 — 拉 models 列表 + 按门派算可用性
# ================================================================

PROBE_TIMEOUT = 15


async def list_available_models(base_url: str, api_key: str) -> tuple[list[str], str]:
    """调 GET {base_url}/models 拉 key 的可用模型列表。

    返回 (model_ids, error_msg)。失败时 model_ids 为空。
    """
    url = f"{base_url.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                try:
                    body = resp.json()
                    err = body.get("error", {})
                    msg = f"HTTP {resp.status_code}: {err.get('message') or resp.text[:120]}"
                except Exception:
                    msg = f"HTTP {resp.status_code}: {resp.text[:120]}"
                return [], msg
            try:
                body = resp.json()
            except Exception as e:
                return [], f"上游返回非 JSON (前 80 字符: {resp.text[:80]})"
            data = body.get("data") or []
            ids = [item.get("id") for item in data if item.get("id")]
            return ids, ""
    except httpx.TimeoutException:
        return [], "请求超时,请检查 API 地址"
    except httpx.ConnectError as e:
        return [], f"连接失败:{e}"
    except Exception as e:
        return [], f"{type(e).__name__}: {str(e)[:120]}"


async def probe_byok(base_url: str, api_key: str) -> dict:
    """探测 key 能用什么 + 能选哪些门派。

    返回:
    {
      ok: bool,
      models: ["claude-haiku-4-5", "gpt-5.4", ...],
      total_models: int,
      sects: [
        { id, name, available_in_runtime, can_choose, required, missing, available_ratio },
        ...
      ],
      available_sect_ids: ["canglan", "tianji"],
      error: ""  # 仅 ok=False 时
    }
    """
    models, err = await list_available_models(base_url, api_key)
    if err:
        return {
            "ok": False,
            "models": [],
            "total_models": 0,
            "sects": [],
            "available_sect_ids": [],
            "error": err,
        }

    model_set = set(models)
    models_lower = [m.lower() for m in models]
    sect_results = []
    available_ids = []

    for sect in ALL_SECTS.values():
        # 该派 tiers 用到的模型(去重)
        required = []
        seen = set()
        for t in sect.tiers:
            if t.model not in seen:
                seen.add(t.model)
                required.append(t.model)

        if not required:
            sect_results.append({
                "id": sect.id,
                "name": sect.name,
                "provider_display": sect.provider_display,
                "available_in_runtime": False,
                "can_choose": False,
                "required": [], "missing": [], "have": [],
                "matched_models": [],
                "available_ratio": 0,
                "reason": "该派灵脉尚未开通(配置中无模型梯度)",
            })
            continue

        # 精确匹配:tier 写明的模型是否都在 key 里
        have_exact = [m for m in required if m in model_set]
        missing_exact = [m for m in required if m not in model_set]

        # ★ 模糊匹配:key 中只要有任一模型 ID 包含该派 provider_keywords 任一关键词,
        # 即视为该派可用(运行时会 fallback 找具体模型)
        keywords = [kw.lower() for kw in (sect.provider_keywords or [])]
        matched_models = [
            models[i] for i, ml in enumerate(models_lower)
            if any(kw in ml for kw in keywords)
        ] if keywords else []

        # 决策:精确全有 OR(模糊匹配命中)→ 可选
        can_choose = sect.available and (
            len(missing_exact) == 0 or len(matched_models) > 0
        )

        if can_choose:
            available_ids.append(sect.id)

        if not sect.available:
            reason = "该派尚未开放"
        elif can_choose and missing_exact:
            reason = f"已匹配同源模型 {len(matched_models)} 个:" + ", ".join(matched_models[:3])
        elif can_choose:
            reason = ""
        else:
            reason = f"key 中无匹配模型(需含: {', '.join(keywords[:3])})"

        sect_results.append({
            "id": sect.id,
            "name": sect.name,
            "provider_display": sect.provider_display,
            "available_in_runtime": sect.available,
            "can_choose": can_choose,
            "required": required,
            "have": have_exact,
            "missing": missing_exact,
            "matched_models": matched_models,  # ★ 模糊匹配命中的模型
            "available_ratio": round(len(have_exact) / len(required) * 100) if required else 0,
            "reason": reason,
        })

    return {
        "ok": True,
        "models": models,
        "total_models": len(models),
        "sects": sect_results,
        "available_sect_ids": available_ids,
        "error": "",
    }


# ================================================================
# 单模型测试参数(用于 verify-key 流式精细验证)
# ================================================================
TEST_MAX_TOKENS = 8
TEST_MESSAGE = [{"role": "user", "content": "ping"}]
TEST_TIMEOUT = 20  # 单次请求超时
MAX_ATTEMPTS = 3   # 单模型最多尝试次数(含首次)
RETRY_DELAYS = [0.5, 1.5]  # 重试间隔(秒)


class _NeedNonStreamFallback(Exception):
    """流式失败/无数据时,降级到非流式 POST"""


def _use_responses_api(model: str) -> bool:
    """判断该模型是否应用 OpenAI Responses API(新版推理模型)
    gpt-5+ / o1 / o3 / o4 系列默认用 /responses,其他走 /chat/completions"""
    m = (model or "").lower()
    if m.startswith(("gpt-5", "gpt-6", "o1", "o3", "o4", "o5")):
        return True
    return False


async def _test_one_model(
    base_url: str,
    api_key: str,
    model: str,
) -> tuple:
    """单次测试一个模型,返回 (success, error_msg, duration_ms, http_status)

    ★ 智能路由:
      - gpt-5+/o-系列  → POST /v1/responses + stream=true (SSE)
      - 其他模型       → POST /v1/chat/completions + stream=true (SSE)
    收到首个非空 chunk 即视为通过(快速验证,不等完整生成)
    """
    use_responses = _use_responses_api(model)
    base = base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    if use_responses:
        url = f"{base}/responses"
        payload = {
            "model": model,
            "input": "ping",
            "stream": True,
            "max_output_tokens": 16,
        }
    else:
        url = f"{base}/chat/completions"
        payload = {
            "model": model,
            "messages": TEST_MESSAGE,
            "max_tokens": TEST_MAX_TOKENS,
            "stream": True,
        }

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                if resp.status_code != 200:
                    # 错误响应:读完整 body 解析
                    err_body = await resp.aread()
                    duration_ms = int((time.time() - start) * 1000)
                    try:
                        err_json = httpx_json_loads(err_body)
                        e = err_json.get("error", {}) if isinstance(err_json, dict) else {}
                        msg = f"{e.get('code','?')}: {e.get('message','?')[:120]}"
                    except Exception:
                        msg = err_body.decode("utf-8", "ignore")[:150] or f"HTTP {resp.status_code} 无内容"
                    # 部分网关对 gpt-5 系列在 /chat/completions 上会拒绝 → fallback 提示
                    if resp.status_code in (400, 404) and not use_responses and "gpt" in model.lower():
                        msg += " (尝试使用 /v1/responses 端点)"
                    return False, msg, duration_ms, resp.status_code

                # 200:读 SSE 流,只要拿到第一个非空 chunk 即认为通过
                got_chunk = False
                first_line_buf = []
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    # SSE 注释行 / event: 行 跳过,只看 data:
                    if line.startswith(":"):
                        continue
                    if line.startswith("event:"):
                        continue
                    if line.startswith("data:"):
                        data_part = line[5:].strip()
                        if not data_part or data_part == "[DONE]":
                            # 暂时只是结束,不算通过证据;继续等下一帧
                            if data_part == "[DONE]" and got_chunk:
                                break
                            continue
                        # 拿到 data 即认为通了
                        got_chunk = True
                        first_line_buf.append(data_part[:60])
                        break  # 早停,不需读完
                    # 非 SSE 标准格式 (部分网关直接返非流式 JSON)
                    if line.strip().startswith("{"):
                        got_chunk = True
                        first_line_buf.append(line[:60])
                        break

                duration_ms = int((time.time() - start) * 1000)
                if got_chunk:
                    return True, "", duration_ms, 200
                # 200 但流式无数据 → 触发下方 fallback(走非流式 POST)
                raise _NeedNonStreamFallback()
    except _NeedNonStreamFallback:
        pass  # 进入下方非流式 fallback
    except httpx.TimeoutException:
        # 流式超时 → 自动降级非流式(部分网关如 GLM/Kimi 不支持 SSE)
        pass
    except httpx.ConnectError as e:
        return False, f"连接失败: {e}", int((time.time() - start) * 1000), 0
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:120]}", int((time.time() - start) * 1000), 0

    # ─── Fallback: 非流式 POST(给不支持 SSE 的网关一次机会)─────
    try:
        payload.pop("stream", None)
        # responses API 也支持 stream=false
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            resp = await client.post(url, headers={"Authorization": f"Bearer {api_key}",
                                                    "Content-Type": "application/json"},
                                     json=payload)
            duration_ms = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                try:
                    body = resp.json()
                except Exception:
                    return (True, "", duration_ms, 200) if resp.text else (False, "200 空响应", duration_ms, 200)
                if isinstance(body, dict):
                    if body.get("choices") or body.get("output_text") or body.get("response"):
                        return True, "", duration_ms, 200
                    if body.get("error"):
                        e = body["error"]
                        return False, f"{e.get('code','?')}: {str(e.get('message','?'))[:100]}", duration_ms, 200
                    # 兜底:200 有 dict 内容认为通
                    return True, "", duration_ms, 200
                return True, "", duration_ms, 200
            else:
                try:
                    err_body = resp.json()
                    e = err_body.get("error", {})
                    msg = f"{e.get('code','?')}: {e.get('message','?')[:120]}"
                except Exception:
                    msg = resp.text[:150] or f"HTTP {resp.status_code}"
                return False, msg, duration_ms, resp.status_code
    except httpx.TimeoutException:
        return False, "请求超时(流式+非流式均失败)", int((time.time() - start) * 1000), 0
    except Exception as e:
        return False, f"fallback 失败 {type(e).__name__}: {str(e)[:100]}", int((time.time() - start) * 1000), 0


def _is_retryable(http_status: int, error_msg: str) -> bool:
    """判断是否可重试"""
    if http_status == 0:  # 网络错误
        return True
    if http_status == 429:  # 限速
        return True
    if http_status >= 500:  # 服务器错误
        return True
    # 401/403/404/422 这种 → 配置问题,不要重试
    return False


# ★ 并发上限:多模型同步测试,但用 semaphore 防止打爆上游限流
MAX_CONCURRENCY = 5


async def stream_verify_sect_models(
    sect_id: str,
    base_url: str,
    api_key: str,
) -> AsyncGenerator[dict, None]:
    """流式验证某派所有(去重后的)模型 — 并发版本。

    所有模型同时启动,事件按完成时间(而非启动顺序)实时 push 给客户端。
    每个模型内部仍保留 attempt 1/2/3 重试,但模型之间并发跑。

    产出 dict 事件:
      {event:"start", models:[...]}
      {event:"testing", model:..., attempt:N}
      {event:"result", model:..., ok:bool, error:..., duration_ms:..., final:bool}
      {event:"done", all_ok:bool, results:{model: {...}}}
    """
    sect = get_sect(sect_id)
    if not sect:
        yield {"event": "error", "message": f"门派 {sect_id} 不存在"}
        return
    if not sect.available:
        yield {"event": "error", "message": f"门派 {sect.name} 暂未开放"}
        return

    # ★ 先拉用户可用模型列表,用于 resolve fallback
    user_models, _err = await list_available_models(base_url, api_key)

    # 去重该派所有 tier 用到的模型 — tier.model 不在 key 中时 fallback 到同 provider
    seen = set()
    models = []
    for t in sect.tiers:
        # 运行时实际用的模型(精确命中 → 用 tier.model;否则 → 同 provider 的第一个)
        actual = resolve_model_for_sect(sect_id, t.model, user_models)
        if actual not in seen:
            seen.add(actual)
            covers = [tt.name for tt in sect.tiers
                      if resolve_model_for_sect(sect_id, tt.model, user_models) == actual]
            models.append({
                "model": actual,
                "covers": covers,
                "label": f"{covers[0]}—{covers[-1]}" if len(covers) > 1 else covers[0],
            })

    yield {
        "event": "start",
        "sect_id": sect_id,
        "sect_name": sect.name,
        "total": len(models),
        "models": models,
        "mode": "parallel",  # 前端可据此调整 UI 文案
    }

    # 事件队列 — 所有 worker 往里 put,主协程消费 yield
    queue: asyncio.Queue = asyncio.Queue()
    results: dict = {}
    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    # sentinel:每个 worker 结束都 push 一个,主循环靠它知道 "全跑完了"
    DONE = object()

    async def _run_one(m: dict):
        """跑一个模型的所有 attempt,事件全部 put 到 queue。"""
        model = m["model"]
        label = m["label"]
        success = False
        last_error = ""
        last_status = 0
        last_duration = 0

        try:
            async with sem:  # 并发上限保护
                for attempt in range(1, MAX_ATTEMPTS + 1):
                    await queue.put({
                        "event": "testing",
                        "model": model,
                        "label": label,
                        "attempt": attempt,
                        "max_attempts": MAX_ATTEMPTS,
                    })

                    ok, error, duration_ms, http_status = await _test_one_model(
                        base_url, api_key, model
                    )
                    last_duration = duration_ms
                    last_status = http_status

                    if ok:
                        success = True
                        last_error = ""
                        await queue.put({
                            "event": "result",
                            "model": model,
                            "label": label,
                            "ok": True,
                            "attempt": attempt,
                            "duration_ms": duration_ms,
                            "final": True,
                        })
                        break

                    last_error = error
                    if attempt < MAX_ATTEMPTS and _is_retryable(http_status, error):
                        delay = RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)]
                        await queue.put({
                            "event": "retrying",
                            "model": model,
                            "label": label,
                            "attempt": attempt,
                            "error": error,
                            "next_delay": delay,
                        })
                        await asyncio.sleep(delay)
                    else:
                        break

                if not success:
                    await queue.put({
                        "event": "result",
                        "model": model,
                        "label": label,
                        "ok": False,
                        "error": last_error,
                        "http_status": last_status,
                        "duration_ms": last_duration,
                        "final": True,
                    })
        except Exception as e:
            # worker 异常 — 报告失败而不是吞掉
            await queue.put({
                "event": "result",
                "model": model,
                "label": label,
                "ok": False,
                "error": f"内部错误: {type(e).__name__}: {str(e)[:120]}",
                "http_status": 0,
                "duration_ms": last_duration,
                "final": True,
            })
        finally:
            results[model] = {
                "ok": success,
                "error": last_error if not success else "",
                "duration_ms": last_duration,
            }
            await queue.put(DONE)

    # 启动所有 worker(不 await,让它们并发跑)
    tasks = [asyncio.create_task(_run_one(m)) for m in models]
    remaining = len(models)

    # 主循环:每收到一个事件就 yield,直到所有 worker 都喷了 DONE
    while remaining > 0:
        evt = await queue.get()
        if evt is DONE:
            remaining -= 1
            continue
        yield evt

    # 收尾(理论上 task 已都完成,但 gather 保险一下)
    await asyncio.gather(*tasks, return_exceptions=True)

    all_ok = all(r["ok"] for r in results.values())
    yield {
        "event": "done",
        "all_ok": all_ok,
        "results": results,
        "next_action": "create_character" if all_ok else "retry",
    }
