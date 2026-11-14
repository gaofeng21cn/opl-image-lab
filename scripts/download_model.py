"""下载固定版本权重，校验发布方 SHA-256。"""
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
from huggingface_hub import hf_hub_download

from settings import WORKSPACE as ROOT, PROFILE as config
path = Path(hf_hub_download(config["model_repo"], config["model_file"], revision=config["model_revision"], local_dir=ROOT / "models/checkpoints"))
if path.stat().st_size != config["model_bytes"]:
    raise SystemExit("模型文件大小不符。")
with path.open("rb") as stream:
    digest = hashlib.file_digest(stream, "sha256").hexdigest()
if digest != config["model_sha256"]:
    raise SystemExit("模型校验失败，请重新下载。")
print(f"NSFW 模型下载和校验完成：{path}")
