"""Shared public-image import for the ComfyUI extension and Agent App owner."""
import io
from urllib.parse import urljoin, urlparse

import httpx
from PIL import Image, ImageOps
import safehttpx

MAX_BYTES = 25 * 1024 * 1024


async def download_public_image(url):
    for _ in range(6):
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("请输入公开图片的 HTTP 或 HTTPS 地址。")
        if parsed.port not in {None, 80, 443}:
            raise ValueError("图片地址需要使用标准 HTTP/HTTPS 端口。")
        ip = await safehttpx.async_validate_url(parsed.hostname)
        async with httpx.AsyncClient(transport=safehttpx.AsyncSecureTransport(ip), trust_env=False, timeout=20) as client:
            async with client.stream("GET", url, headers={"User-Agent": "QwenPhotoWorkbench/1.0"}) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers["location"])
                    continue
                response.raise_for_status()
                if int(response.headers.get("content-length", "0")) > MAX_BYTES:
                    raise ValueError("图片超过 25 MB。")
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_BYTES:
                        raise ValueError("图片超过 25 MB。")
        return bytes(data)
    raise ValueError("图片链接重定向次数过多。")


def normalize_image(data):
    with Image.open(io.BytesIO(data)) as image:
        if image.width * image.height > 40_000_000:
            raise ValueError("图片超过 4000 万像素。")
        image = ImageOps.exif_transpose(image).convert("RGB")
        out = io.BytesIO()
        image.save(out, format="PNG")
        return out.getvalue()
