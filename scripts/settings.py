"""Locate installed code and per-user data without a checkout-specific path."""
import json
import os
from pathlib import Path
import sys

CODE_ROOT = Path(__file__).resolve().parents[1]


def default_workspace():
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/OPL Image Lab"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "opl-image-lab"


WORKSPACE = Path(os.environ.get("OPL_IMAGE_WORKSPACE") or default_workspace()).expanduser().resolve()
SETTINGS_FILE = WORKSPACE / "settings.json"
SETTINGS = json.loads(SETTINGS_FILE.read_text()) if SETTINGS_FILE.exists() else {}
PROFILE = json.loads((CODE_ROOT / "model-profile.json").read_text())


def port(name, default):
    value = SETTINGS.get(name, default)
    if type(value) is not int or not 1024 <= value <= 65535:
        raise ValueError(f"Invalid local port: {name}")
    return value


COMFY_PORT = port("comfy_port", 28189)
REDIRECT_PORT = port("redirect_port", 7861)
if COMFY_PORT == REDIRECT_PORT:
    raise ValueError("ComfyUI and redirect ports must be different.")
COMFY_URL = f"http://127.0.0.1:{COMFY_PORT}"
PYTHON = Path(os.environ.get("OPL_IMAGE_PYTHON") or SETTINGS.get("python_executable") or WORKSPACE / ".venv/bin/python")
COMFY_SOURCE = Path(SETTINGS.get("comfy_source") or WORKSPACE / "upstream/ComfyUI").expanduser().resolve()
