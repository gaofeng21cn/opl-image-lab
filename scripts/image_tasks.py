"""JSON owner for the local image App; ComfyUI remains the execution authority."""
import asyncio
import base64
import copy
import fcntl
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from settings import CODE_ROOT, WORKSPACE, COMFY_URL, PROFILE, PYTHON

ROOT = WORKSPACE
sys.path.insert(0, str(CODE_ROOT / "custom_nodes/qwen_rapid"))
from image_io import MAX_BYTES, download_public_image, normalize_image

STATE = ROOT / "runtime/agent-app"
COMFY = COMFY_URL
ACTIVE = {"submitting", "queued", "running", "unknown", "cancel_requested"}


def task_id(value):
    if not isinstance(value, str) or str(uuid.UUID(value)) != value:
        raise ValueError("任务编号无效。")
    return value


def record_path(value):
    return STATE / "tasks" / (task_id(value) + ".json")


def save(record):
    path = record_path(record["task_id"])
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False))
    temporary.chmod(0o600)
    temporary.replace(path)


def load(value):
    path = record_path(value)
    if not path.exists():
        raise ValueError("本工作台没有登记该任务。")
    return json.loads(path.read_text())


def api(method, route, **kwargs):
    with httpx.Client(base_url=COMFY, timeout=20, trust_env=False) as client:
        response = client.request(method, route, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else {}


def queue():
    return api("GET", "/queue")


def service_status():
    try:
        data = queue()
        return {"ready": True, "running": len(data.get("queue_running", [])), "pending": len(data.get("queue_pending", []))}
    except httpx.HTTPError:
        return {"ready": False, "running": 0, "pending": 0}


def resolve_asset(reference):
    if not isinstance(reference, str):
        raise ValueError("缺少图片引用。")
    if re.fullmatch(r"input:[a-f0-9]{64}", reference):
        path = ROOT / "inputs/agent-app" / (reference.split(":")[1] + ".png")
    elif reference.startswith("result:"):
        record = load(reference[7:])
        if record.get("status") != "completed" or not record.get("output"):
            raise ValueError("该任务还没有可用图片。")
        path = ROOT / "results" / record["output"]["relative_path"]
    else:
        raise ValueError("图片引用无效，请先导入图片。")
    allowed = ROOT / ("inputs/agent-app" if reference.startswith("input:") else "results")
    if not path.resolve().is_relative_to(allowed.resolve()) or not path.is_file():
        raise ValueError("图片不存在或已移出工作目录。")
    return path


def describe_asset(reference):
    path = resolve_asset(reference)
    with Image.open(path) as image:
        width, height = image.size
    return {"asset_ref": reference, "width": width, "height": height, "path": str(path)}


def import_image(data):
    sources = [key for key in ("url", "path", "base64") if data.get(key)]
    if len(sources) != 1:
        raise ValueError("请选择一个图片来源：文件、链接或图片数据。")
    source = sources[0]
    if source == "url":
        raw = asyncio.run(asyncio.wait_for(download_public_image(data["url"]), timeout=45))
    elif source == "path":
        path = Path(data["path"])
        if not path.is_absolute() or not path.is_file() or path.stat().st_size > MAX_BYTES:
            raise ValueError("请选择不超过 25 MB 的本机图片文件。")
        with path.open("rb") as file:
            raw = file.read(MAX_BYTES + 1)
    else:
        encoded = data["base64"]
        if not isinstance(encoded, str) or len(encoded) > (MAX_BYTES * 4 // 3 + 4):
            raise ValueError("图片超过 25 MB。")
        raw = base64.b64decode(encoded, validate=True)
    if len(raw) > MAX_BYTES:
        raise ValueError("图片超过 25 MB。")
    normalized = normalize_image(raw)
    digest = hashlib.sha256(normalized).hexdigest()
    path = ROOT / "inputs/agent-app" / (digest + ".png")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(normalized)
        path.chmod(0o600)
    return describe_asset("input:" + digest)


def build_workflow(request, ident):
    graph = copy.deepcopy(json.loads((CODE_ROOT / "workflows/edit-api.json").read_text()))
    graph["3"]["inputs"]["prompt"] = request["prompt"]
    graph["5"]["inputs"].update(width=request["width"], height=request["height"])
    graph["6"]["inputs"].update(seed=request["seed"], steps=request["steps"])
    graph["8"]["inputs"]["filename_prefix"] = "agent-app/" + ident
    if request.get("image_ref"):
        path = resolve_asset(request["image_ref"])
        # Result reuse is normalized through the same importer and never overwrites it.
        if request["image_ref"].startswith("result:"):
            imported = import_image({"path": str(path)})
            path = resolve_asset(imported["asset_ref"])
        graph["2"]["inputs"]["image"] = path.relative_to(ROOT / "inputs").as_posix()
    else:
        del graph["2"]
        for key in ("image1", "target_latent", "vae"):
            graph["3"]["inputs"].pop(key, None)
    return graph


def canonical_request(data):
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 8000:
        raise ValueError("请输入不超过 8000 字的图片描述。")
    request = {"prompt": prompt.strip(), "image_ref": data.get("image_ref") or None}
    for key, default, minimum, maximum in (("width", 768, 256, 1536), ("height", 768, 256, 1536), ("steps", 4, 1, 12), ("seed", 42, 0, 2**53 - 1)):
        value = data.get(key, default)
        if type(value) is not int or not minimum <= value <= maximum or (key in {"width", "height"} and value % 16):
            raise ValueError("尺寸需为 256–1536 的 16 倍数；步数 1–12；种子需为非负整数。")
        request[key] = value
    if request["width"] * request["height"] > 1536 * 1024:
        raise ValueError("首版最大画布为 1536×1024 像素。")
    if request["image_ref"]:
        resolve_asset(request["image_ref"])
    return request


def refresh(record):
    if record["status"] in {"completed", "failed", "cancelled"}:
        return record
    ident = record["task_id"]
    try:
        history = api("GET", "/history/" + ident).get(ident)
        if history:
            outputs = history.get("outputs", {})
            images = [image for node in outputs.values() for image in node.get("images", []) if image.get("type") == "output"]
            status = history.get("status", {})
            if images and status.get("status_str") == "success":
                image = images[0]
                path = ROOT / "results" / image.get("subfolder", "") / image["filename"]
                if not path.resolve().is_relative_to((ROOT / "results").resolve()) or not path.is_file():
                    raise ValueError("生成文件不可用，请检查结果目录。")
                with Image.open(path) as output:
                    dimensions = output.size
                record.update(status="completed", output={"asset_ref": "result:" + ident, "relative_path": path.relative_to(ROOT / "results").as_posix(), "path": str(path), "width": dimensions[0], "height": dimensions[1], "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            else:
                interrupted = any(event[0] == "execution_interrupted" for event in status.get("messages", []))
                record.update(status="cancelled" if interrupted else "failed", message="任务已取消。" if interrupted else "生成失败，请检查 ComfyUI 日志。")
        else:
            data = queue()
            if any(item[1] == ident for item in data.get("queue_running", [])):
                record["status"] = "running"
            elif any(item[1] == ident for item in data.get("queue_pending", [])):
                record["status"] = "queued"
            else:
                record.update(status="unknown", message="后台未找到此任务；保留原编号，未重复提交。")
    except httpx.HTTPError:
        record["backend_offline"] = True
        return record
    record.pop("backend_offline", None)
    save(record)
    return record


def submit(data):
    ident = task_id(data["task_id"])
    request = canonical_request(data)
    if record_path(ident).exists():
        record = load(ident)
        if record["request"] != request:
            raise ValueError("这个任务编号已经用于另一组参数，请新建任务。")
        return refresh(record)
    if not service_status()["ready"]:
        raise ValueError("本机推理服务尚未启动，请点击「启动推理服务」。")
    graph = build_workflow(request, ident)
    record = {"task_id": ident, "status": "submitting", "request": request, "created_at": time.time()}
    save(record)
    try:
        result = api("POST", "/prompt", json={"prompt_id": ident, "client_id": "opl-image-" + ident, "prompt": graph})
        if result.get("prompt_id") != ident:
            record.update(status="unknown", message="后台返回的任务编号不一致，请核对原任务。")
        else:
            record["status"] = "queued"
    except httpx.HTTPStatusError as error:
        record.update(status="failed" if error.response.status_code < 500 else "unknown", message="后台拒绝此工作流。" if error.response.status_code < 500 else "提交结果待核对，未重复发送。")
    except httpx.HTTPError:
        record.update(status="unknown", message="提交结果待核对，未重复发送。")
    save(record)
    return record


def cancel(data):
    record = refresh(load(data["task_id"]))
    if record["status"] not in ACTIVE:
        return record
    data = queue()
    ident = record["task_id"]
    if any(item[1] == ident for item in data.get("queue_pending", [])):
        api("POST", "/queue", json={"delete": [ident]})
        record.update(status="cancelled", message="已移除选中排队任务。")
    elif any(item[1] == ident for item in data.get("queue_running", [])):
        api("POST", "/interrupt", json={"prompt_id": ident})
        record.update(status="cancel_requested", message="已请求取消选中任务。")
    save(record)
    return record


def control(action):
    status = service_status()
    if action == "start":
        if not status["ready"]:
            with (ROOT / "runtime/agent-app-start.log").open("a") as log:
                subprocess.Popen([str(PYTHON), str(CODE_ROOT / "scripts/manage.py"), "start", "--no-browser"], stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        return {"status": "ready" if status["ready"] else "starting"}
    if not status["ready"]:
        return {"status": "stopped"}
    if status["running"] or status["pending"]:
        raise ValueError("还有正在运行或排队的任务，请完成或取消后再操作。")
    if action == "release":
        api("POST", "/free", json={"unload_models": True, "free_memory": True})
        return {"status": "release_requested", "message": "已请求卸载模型；下次生成会重新加载。"}
    if action == "stop":
        api("POST", "/qwen-workbench/stop", json={})
        return {"status": "stopping"}
    raise ValueError("未知服务操作。")


def execute(data):
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "tasks").mkdir(exist_ok=True)
    operation = data.get("operation")
    with (STATE / "owner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if operation == "status":
            return {"service": service_status(), "workspace": str(ROOT), "model": PROFILE["display_name"], "advanced_url": COMFY}
        if operation == "import":
            return import_image(data)
        if operation == "submit":
            return submit(data)
        if operation == "get":
            return refresh(load(data["task_id"]))
        if operation == "list":
            paths = sorted((STATE / "tasks").glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:40]
            return {"tasks": [json.loads(path.read_text()) for path in paths]}
        if operation == "cancel":
            return cancel(data)
        if operation == "control":
            return control(data["action"])
        if operation == "asset":
            reference = data["asset_ref"]
            path = resolve_asset(reference)
            if data.get("download"):
                if path.stat().st_size > 64 * 1024 * 1024:
                    raise ValueError("文件过大，请从结果目录读取。")
                return {**describe_asset(reference), "data_uri": "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()}
            with Image.open(path) as image:
                image.thumbnail((1024, 1024))
                preview = io.BytesIO()
                image.convert("RGB").save(preview, format="JPEG", quality=84)
            return {**describe_asset(reference), "data_uri": "data:image/jpeg;base64," + base64.b64encode(preview.getvalue()).decode()}
        raise ValueError("未知图片操作。")


if __name__ == "__main__":
    try:
        raw = sys.stdin.buffer.read(36 * 1024 * 1024 + 1)
        if len(raw) > 36 * 1024 * 1024:
            raise ValueError("请求过大。")
        result = execute(json.loads(raw))
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
    except Exception as error:
        message = str(error) if isinstance(error, (ValueError, FileNotFoundError)) else "操作未完成，请检查本机服务与输入。"
        print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
        sys.exit(1)
