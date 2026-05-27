"""
图片生成插件 — 封装 OpenAI 兼容的 /v1/images/generations 接口

特性:
  - 默认接 gpt-image-2(bobdong.cn 网关)
  - 自动重试 3 次,指数退避(网络/5xx/429 重试,4xx 配置错误立即抛)
  - 支持 b64_json 解码 + URL 下载两种返回方式
  - 可选自动保存到本地路径

用法:
    from .image_gen import generate_image

    # 最简单
    results = await generate_image("一只在月下抚琴的仙女")
    # results = [{ "b64_json": "...", "url": None, "revised_prompt": "..." }]

    # 保存到磁盘
    results = await generate_image(
        prompt="沧澜剑派主城,深金黑底,巨型台阶通浮空殿",
        size="1536x1024",
        save_to="/tmp/imgs",  # 自动 mkdir
    )
    # results[0]["local_path"] = "/tmp/imgs/img_1716540123_0.png"

    # 自定义参数
    results = await generate_image(
        prompt="...",
        n=2, quality="high", output_format="webp",
    )

环境变量(读 backend/.env):
    IMAGE_BASE_URL          默认 https://bobdong.cn/v1
    IMAGE_API_KEY           必填
    IMAGE_MODEL             默认 gpt-image-2
    IMAGE_MAX_RETRIES       默认 3
    IMAGE_RETRY_BASE_DELAY  默认 1.5(秒)
    IMAGE_RETRY_MAX_DELAY   默认 8.0(秒)
    IMAGE_TIMEOUT           默认 120(秒,图片生成耗时长)
"""

import os
import time
import base64
import asyncio
import httpx
from pathlib import Path
from typing import Optional, List, Dict, Any


class ImageGenError(Exception):
    """图片生成失败 — retryable=False 时调用方应立刻放弃(配置 / 内容审查)"""
    def __init__(self, msg: str, retryable: bool = True, http_status: int = 0):
        super().__init__(msg)
        self.retryable = retryable
        self.http_status = http_status


class ImageGenerator:
    """图片生成客户端 — OpenAI 兼容协议"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = (base_url or os.getenv("IMAGE_BASE_URL", "https://bobdong.cn/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("IMAGE_API_KEY", "")
        self.model = model or os.getenv("IMAGE_MODEL", "gpt-image-2")
        self.timeout = timeout if timeout is not None else float(os.getenv("IMAGE_TIMEOUT", "120"))
        self.max_retries = int(os.getenv("IMAGE_MAX_RETRIES", "3"))
        self.retry_base_delay = float(os.getenv("IMAGE_RETRY_BASE_DELAY", "1.5"))
        self.retry_max_delay = float(os.getenv("IMAGE_RETRY_MAX_DELAY", "8.0"))

        if not self.api_key:
            raise ValueError(
                "IMAGE_API_KEY 未配置 — 请在 backend/.env 里添加:\n"
                "  IMAGE_API_KEY=<your-image-api-key>"
            )

    # ------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------
    async def generate(
        self,
        prompt: str,
        n: int = 1,
        size: str = "1536x1024",
        quality: str = "auto",
        output_format: str = "png",
        save_to: Optional[str] = None,
        filename_prefix: str = "img",
        **extra,
    ) -> List[Dict[str, Any]]:
        """生成图片,带 3 次重试。

        Args:
            prompt: 图像描述
            n: 张数,默认 1
            size: '1024x1024' / '1536x1024' / '1024x1536' / 'auto'
            quality: 'low' / 'medium' / 'high' / 'auto'
            output_format: 'png' / 'jpeg' / 'webp'(部分网关可能忽略)
            save_to: 若给定,自动 mkdir 并把每张图存为 {prefix}_{ts}_{idx}.{ext}
            filename_prefix: save_to 模式下的文件名前缀
            **extra: 透传给 API(如 background='transparent', moderation='low')

        Returns:
            List of dicts:
              [
                {
                  "b64_json": "...",     # 原始 base64(若 API 返回)
                  "url": "...",          # 临时 URL(若 API 返回)
                  "revised_prompt": "",  # API 改写后的 prompt(可选)
                  "local_path": "..."    # 若 save_to,本地绝对路径
                },
                ...
              ]

        Raises:
            ImageGenError: 重试 3 次都失败,或遇到不可重试错误
        """
        url = f"{self.base_url}/images/generations"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "prompt": prompt,
            "n": n,
            "size": size,
            "quality": quality,
            "output_format": output_format,
            **extra,
        }

        last_error = ""

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, json=payload, headers=headers)

                # ─── 成功 ───
                if resp.status_code == 200:
                    body = resp.json()
                    images = []
                    for idx, item in enumerate(body.get("data", [])):
                        rec = {
                            "b64_json": item.get("b64_json"),
                            "url": item.get("url"),
                            "revised_prompt": item.get("revised_prompt") or "",
                        }
                        if save_to:
                            rec["local_path"] = await self._save_one(
                                item, save_to, filename_prefix, idx, output_format
                            )
                        images.append(rec)

                    if not images:
                        # 200 但没有图,通常是 prompt 被审查
                        raise ImageGenError(
                            "API 返回 200 但 data 为空(可能被内容审查屏蔽)",
                            retryable=False,
                            http_status=200,
                        )
                    return images

                # ─── 不可重试错误 ───
                if resp.status_code in (400, 401, 403, 404, 422):
                    try:
                        body = resp.json()
                        err_msg = (body.get("error") or {}).get("message") or resp.text[:200]
                    except Exception:
                        err_msg = resp.text[:200]
                    raise ImageGenError(
                        f"HTTP {resp.status_code}: {err_msg}",
                        retryable=False,
                        http_status=resp.status_code,
                    )

                # ─── 可重试错误(5xx / 429 / 其他)───
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                print(f"[ImageGen Retry {attempt}/{self.max_retries}] {last_error}")

            except ImageGenError as e:
                if not e.retryable:
                    raise
                last_error = str(e)
                print(f"[ImageGen Retry {attempt}/{self.max_retries}] {last_error}")

            except httpx.TimeoutException:
                last_error = f"超时({self.timeout}s)"
                print(f"[ImageGen Retry {attempt}/{self.max_retries}] {last_error}")
            except httpx.ConnectError as e:
                last_error = f"连接失败: {e}"
                print(f"[ImageGen Retry {attempt}/{self.max_retries}] {last_error}")
            except Exception as e:
                last_error = f"{type(e).__name__}: {str(e)[:200]}"
                print(f"[ImageGen Retry {attempt}/{self.max_retries}] {last_error}")

            # ─── 指数退避 ───
            if attempt < self.max_retries:
                delay = min(
                    self.retry_base_delay * (2 ** (attempt - 1)),
                    self.retry_max_delay,
                )
                await asyncio.sleep(delay)

        raise ImageGenError(
            f"重试 {self.max_retries} 次仍失败: {last_error}",
            retryable=False,
        )

    async def generate_with_references(
        self,
        prompt: str,
        reference_paths: List[str],
        n: int = 1,
        size: str = "1536x1024",
        quality: str = "auto",
        output_format: str = "png",
        save_to: Optional[str] = None,
        filename_prefix: str = "img",
        **extra,
    ) -> List[Dict[str, Any]]:
        """Generate/edit an image using reference image files.

        This uses the OpenAI-compatible /images/edits multipart endpoint.
        It is intended for production character art that needs a real visual
        reference, such as a sect flag. If the upstream gateway does not support
        image references for the configured model, this method raises instead of
        silently falling back to text-only generation.
        """
        if not reference_paths:
            return await self.generate(
                prompt=prompt,
                n=n,
                size=size,
                quality=quality,
                output_format=output_format,
                save_to=save_to,
                filename_prefix=filename_prefix,
                **extra,
            )

        url = f"{self.base_url}/images/edits"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {
            "model": self.model,
            "prompt": prompt,
            "n": str(n),
            "size": size,
            "quality": quality,
            "output_format": output_format,
            **{k: str(v) for k, v in extra.items()},
        }

        refs = [Path(p).expanduser().resolve() for p in reference_paths]
        for p in refs:
            if not p.exists():
                raise ImageGenError(f"参考图不存在: {p}", retryable=False)

        async def _post_once(image_field: str):
            files = []
            try:
                for p in refs:
                    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
                    files.append((image_field, (p.name, p.read_bytes(), mime)))
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    return await client.post(url, data=data, files=files, headers=headers)
            finally:
                files.clear()

        last_error = ""
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = await _post_once("image[]")
                if resp.status_code in (400, 422):
                    # Some OpenAI-compatible gateways accept a single "image"
                    # field instead of the SDK-style "image[]" field.
                    alt = await _post_once("image")
                    if alt.status_code < 500:
                        resp = alt

                if resp.status_code == 200:
                    body = resp.json()
                    images = []
                    for idx, item in enumerate(body.get("data", [])):
                        rec = {
                            "b64_json": item.get("b64_json"),
                            "url": item.get("url"),
                            "revised_prompt": item.get("revised_prompt") or "",
                        }
                        if save_to:
                            rec["local_path"] = await self._save_one(
                                item, save_to, filename_prefix, idx, output_format
                            )
                        images.append(rec)
                    if not images:
                        raise ImageGenError(
                            "API 返回 200 但 data 为空(可能被内容审查屏蔽)",
                            retryable=False,
                            http_status=200,
                        )
                    return images

                if resp.status_code in (400, 401, 403, 404, 422):
                    try:
                        body = resp.json()
                        err_msg = (body.get("error") or {}).get("message") or resp.text[:200]
                    except Exception:
                        err_msg = resp.text[:200]
                    raise ImageGenError(
                        f"参考图生图失败 HTTP {resp.status_code}: {err_msg}",
                        retryable=False,
                        http_status=resp.status_code,
                    )

                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                print(f"[ImageGen Reference Retry {attempt}/{self.max_retries}] {last_error}")

            except ImageGenError as e:
                if not e.retryable:
                    raise
                last_error = str(e)
                print(f"[ImageGen Reference Retry {attempt}/{self.max_retries}] {last_error}")
            except httpx.TimeoutException:
                last_error = f"超时({self.timeout}s)"
                print(f"[ImageGen Reference Retry {attempt}/{self.max_retries}] {last_error}")
            except httpx.ConnectError as e:
                last_error = f"连接失败: {e}"
                print(f"[ImageGen Reference Retry {attempt}/{self.max_retries}] {last_error}")
            except Exception as e:
                last_error = f"{type(e).__name__}: {str(e)[:200]}"
                print(f"[ImageGen Reference Retry {attempt}/{self.max_retries}] {last_error}")

            if attempt < self.max_retries:
                delay = min(self.retry_base_delay * (2 ** (attempt - 1)), self.retry_max_delay)
                await asyncio.sleep(delay)

        raise ImageGenError(
            f"参考图生图重试 {self.max_retries} 次仍失败: {last_error}",
            retryable=False,
        )

    # ------------------------------------------------------------
    # 本地保存
    # ------------------------------------------------------------
    async def _save_one(
        self,
        item: dict,
        dir_path: str,
        prefix: str,
        idx: int,
        output_format: str,
    ) -> str:
        """把一张返回的图存到本地;优先 b64_json,fallback URL 下载"""
        dest_dir = Path(dir_path).expanduser().resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)
        ext = output_format.lower() if output_format else "png"
        ts = int(time.time())
        filename = f"{prefix}_{ts}_{idx}.{ext}"
        path = dest_dir / filename

        if item.get("b64_json"):
            data = base64.b64decode(item["b64_json"])
            path.write_bytes(data)
        elif item.get("url"):
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(item["url"])
                r.raise_for_status()
                path.write_bytes(r.content)
        else:
            raise ImageGenError("响应里既无 b64_json 也无 url,无法保存", retryable=False)

        return str(path)


# ============================================================
# 全局便捷接口
# ============================================================
_default_client: Optional[ImageGenerator] = None


def get_image_client() -> ImageGenerator:
    """全局单例,首次调用时初始化"""
    global _default_client
    if _default_client is None:
        _default_client = ImageGenerator()
    return _default_client


async def generate_image(prompt: str, **kwargs) -> List[Dict[str, Any]]:
    """便捷函数 — 等价于 get_image_client().generate(prompt, **kwargs)"""
    return await get_image_client().generate(prompt, **kwargs)


async def generate_image_with_references(
    prompt: str,
    reference_paths: List[str],
    **kwargs,
) -> List[Dict[str, Any]]:
    """便捷函数 — 使用参考图生成,不支持时会显式报错。"""
    return await get_image_client().generate_with_references(prompt, reference_paths, **kwargs)
