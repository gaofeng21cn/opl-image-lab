"""Local image import and service controls for the native ComfyUI interface."""
import asyncio
import io
from pathlib import Path
import subprocess
import os
import sys

from aiohttp import web
import httpx
from PIL import Image, UnidentifiedImageError
from .image_io import download_public_image, normalize_image
from server import PromptServer

CODE_ROOT = Path(os.environ.get("OPL_IMAGE_CODE_ROOT") or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(CODE_ROOT / "scripts"))
from settings import WORKSPACE as ROOT, PYTHON, COMFY_URL
MAX_BYTES = 25 * 1024 * 1024
stopping = False


def check_request(request):
    origin = request.headers.get("Origin")
    if origin and origin != COMFY_URL:
        raise web.HTTPForbidden(text="只接受本机编辑页面的请求。")
    if request.content_type != "application/json":
        raise web.HTTPUnsupportedMediaType()


def queue_busy():
    running, pending = PromptServer.instance.prompt_queue.get_current_queue()
    return bool(running or pending)


@web.middleware
async def shutdown_guard(request, handler):
    if stopping and request.method == "POST" and request.path in {"/prompt", "/api/prompt"}:
        return web.json_response({"error": "服务正在停止，请重新启动后再生成。"}, status=503)
    return await handler(request)


PromptServer.instance.app.middlewares.append(shutdown_guard)


@PromptServer.instance.routes.post("/qwen-workbench/import-image")
async def import_image(request):
    check_request(request)
    try:
        data = await request.json()
        url = data.get("url", "")
        if not isinstance(url, str) or len(url) > 8192:
            raise ValueError("图片地址无效。")
        raw = await asyncio.wait_for(download_public_image(url), timeout=45)
        image = await asyncio.to_thread(normalize_image, raw)
        return web.Response(body=image, content_type="image/png", headers={"Cache-Control": "no-store"})
    except (ValueError, httpx.HTTPError, OSError, UnidentifiedImageError, TimeoutError, Image.DecompressionBombError):
        return web.json_response({"error": "无法导入该图片。请使用公开图片的直接链接（非网页地址），或将图片保存到本机后上传。最大 25 MB、4000 万像素。"}, status=400)


@PromptServer.instance.routes.post("/qwen-workbench/release")
async def release_memory(request):
    check_request(request)
    if queue_busy():
        return web.json_response({"error": "还有正在运行或排队的任务，请完成或取消后再释放内存。"}, status=409)
    PromptServer.instance.prompt_queue.set_flag("unload_models", True)
    PromptServer.instance.prompt_queue.set_flag("free_memory", True)
    return web.json_response({"message": "已请求卸载模型。页面保持可用，下次生成会重新加载。"})


@PromptServer.instance.routes.post("/qwen-workbench/stop")
async def stop_service(request):
    global stopping
    check_request(request)
    if queue_busy():
        return web.json_response({"error": "还有正在运行或排队的任务，请完成或取消后再停止服务。"}, status=409)
    if not stopping:
        stopping = True
        def stop():
            with (ROOT / "runtime/control.log").open("a") as log:
                subprocess.Popen([str(PYTHON), str(CODE_ROOT / "scripts/manage.py"), "stop"], stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        asyncio.get_running_loop().call_later(1.5, stop)
    return web.json_response({"message": "服务正在停止。再次使用时，双击工作目录中的「启动照片编辑.command」。"})
