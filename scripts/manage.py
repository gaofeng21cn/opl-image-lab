"""启动和停止此目录拥有的两个本地服务。"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

import psutil

from settings import CODE_ROOT, WORKSPACE, PYTHON, COMFY_SOURCE, COMFY_PORT, REDIRECT_PORT, COMFY_URL, SETTINGS

ROOT = WORKSPACE
RUNTIME = ROOT / "runtime"
COMFY = COMFY_SOURCE
STATE = RUNTIME / "services.json"
DEFAULT_ARGS = ["--bf16-unet", "--bf16-text-enc", "--fp32-vae", "--reserve-vram", "24"] if sys.platform == "darwin" else []
EXTRA_ARGS = SETTINGS.get("comfy_args", DEFAULT_ARGS)
if not isinstance(EXTRA_ARGS, list) or not all(isinstance(x, str) for x in EXTRA_ARGS):
    raise ValueError("comfy_args must be a list of strings.")
COMMANDS = {
    "comfy": [str(PYTHON), str(COMFY / "main.py"), "--base-directory", str(ROOT / "runtime/comfy"), "--models-directory", str(ROOT / "models"), "--input-directory", str(ROOT / "inputs"), "--output-directory", str(ROOT / "results"), "--listen", "127.0.0.1", "--port", str(COMFY_PORT), *EXTRA_ARGS, "--disable-api-nodes", "--preview-method", "none"],
    "web": [str(PYTHON), str(CODE_ROOT / "scripts/redirect.py")],
}
URLS = {"comfy": COMFY_URL + "/system_stats", "web": f"http://127.0.0.1:{REDIRECT_PORT}/health"}


def owned(name, record):
    try:
        process = psutil.Process(record["pid"])
        return process if process.create_time() == record["created"] and process.cmdline() == COMMANDS[name] else None
    except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
        return None


def ready(name):
    try:
        with urllib.request.urlopen(URLS[name], timeout=2) as response:
            return response.status == 200
    except (OSError, TimeoutError):
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop", "status"])
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with (RUNTIME / "services.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(STATE.read_text()) if STATE.exists() else {}
        if args.action == "status":
            print(json.dumps({name: {"owned": bool(owned(name, state.get(name, {}))), "ready": ready(name)} for name in COMMANDS}, ensure_ascii=False))
            return
        if args.action == "stop":
            if owned("comfy", state.get("comfy", {})) and ready("comfy"):
                try:
                    with urllib.request.urlopen(COMFY_URL + "/queue", timeout=3) as response:
                        queue = json.load(response)
                    if queue.get("queue_running") or queue.get("queue_pending"):
                        raise SystemExit("还有正在运行或排队的任务；请先完成或取消，再停止服务。")
                except (OSError, TimeoutError):
                    raise SystemExit("无法核对生成队列，未停止服务；请检查后台状态。")
            for name in reversed(COMMANDS):
                process = owned(name, state.get(name, {}))
                if process:
                    process.terminate()
                    try:
                        process.wait(timeout=20)
                    except psutil.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                    state.pop(name, None)
            STATE.write_text(json.dumps(state, indent=2))
            print("已停止本工作台，释放模型占用的内存。")
            return
        if not (COMFY / "main.py").is_file():
            raise SystemExit("ComfyUI is not configured. Run scripts/setup.py --with-inference or --comfy-source PATH.")
        env = dict(os.environ, OPL_IMAGE_WORKSPACE=str(ROOT), OPL_IMAGE_CODE_ROOT=str(CODE_ROOT), HF_HUB_DISABLE_TELEMETRY="1", PYTORCH_ENABLE_MPS_FALLBACK="1", PYTHONUNBUFFERED="1")
        for directory in ["models", "inputs", "results", "runtime/comfy/user", "runtime/comfy/custom_nodes"]:
            (ROOT / directory).mkdir(parents=True, exist_ok=True)
        node_link = ROOT / "runtime/comfy/custom_nodes/qwen_rapid"
        target = CODE_ROOT / "custom_nodes/qwen_rapid"
        if node_link.is_symlink() and node_link.resolve() != target.resolve():
            node_link.unlink()
        if not node_link.exists():
            node_link.symlink_to(target)
        for name, command in COMMANDS.items():
            process = owned(name, state.get(name, {}))
            if not process:
                if ready(name):
                    raise SystemExit(f"{name} 端口被其他服务占用；未接管该服务。")
                with (RUNTIME / f"{name}.log").open("a") as log:
                    child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                process = psutil.Process(child.pid)
                state[name] = {"pid": child.pid, "created": process.create_time()}
                STATE.write_text(json.dumps(state, indent=2))
            deadline = time.monotonic() + 90
            while not ready(name):
                if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
                    raise SystemExit(f"{name} 启动失败，请查看 {RUNTIME / (name + '.log')}")
                if time.monotonic() > deadline:
                    raise SystemExit(f"{name} 仍未就绪，请查看日志；进程已保留。")
                time.sleep(1)
            print(f"{name} 已就绪。", flush=True)
        if not args.no_browser:
            import webbrowser
            webbrowser.open(COMFY_URL)
        print("ComfyUI: " + COMFY_URL)


if __name__ == "__main__":
    main()
