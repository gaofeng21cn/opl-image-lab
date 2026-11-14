"""Create a portable, per-user runtime and optionally install ComfyUI."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE / "scripts"))
from settings import WORKSPACE

DEFAULT_COMFY = "https://github.com/Comfy-Org/ComfyUI.git"


def run(command, *, cwd=None):
    subprocess.run(command, cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description="Set up OPL Image Lab without mixing runtime data into its code checkout.")
    parser.add_argument("--workspace", type=Path, default=WORKSPACE)
    parser.add_argument("--with-inference", action="store_true", help="Install ComfyUI and its Python runtime into the workspace.")
    parser.add_argument("--download-model", action="store_true", help="Download and verify the separate 28.4 GB reference model.")
    parser.add_argument("--comfy-source", type=Path, help="Use an existing ComfyUI checkout without modifying it.")
    args = parser.parse_args()
    workspace = args.workspace.expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    settings_path = workspace / "settings.json"
    settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    python = Path(sys.executable).absolute()
    if args.with_inference:
        import venv
        venv_path = workspace / ".venv"
        if not venv_path.exists():
            venv.EnvBuilder(with_pip=True, clear=False).create(venv_path)
        python = venv_path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        comfy = workspace / "upstream/ComfyUI"
        if not comfy.exists():
            comfy.parent.mkdir(parents=True, exist_ok=True)
            profile = json.loads((CODE / "model-profile.json").read_text())
            run(["git", "init", str(comfy)])
            run(["git", "remote", "add", "origin", DEFAULT_COMFY], cwd=comfy)
            run(["git", "fetch", "--depth", "1", "origin", profile["comfy_commit"]], cwd=comfy)
            run(["git", "checkout", "--detach", "FETCH_HEAD"], cwd=comfy)
        run([str(python), "-m", "pip", "install", "-r", str(comfy / "requirements.txt")])
        run([str(python), "-m", "pip", "install", "httpx>=0.28.1,<1", "safehttpx>=0.1.6,<1", "pillow>=11,<13", "psutil>=6,<8", "huggingface-hub>=0.34,<2"])
        settings["comfy_source"] = str(comfy)
    elif args.comfy_source:
        comfy = args.comfy_source.expanduser().resolve()
        if not (comfy / "main.py").is_file():
            raise SystemExit("--comfy-source must point at a ComfyUI checkout containing main.py.")
        settings["comfy_source"] = str(comfy)
    settings["python_executable"] = str(python)
    settings["workspace"] = str(workspace)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    settings_path.chmod(0o600)
    for directory in ["models/checkpoints", "inputs", "results", "runtime"]:
        (workspace / directory).mkdir(parents=True, exist_ok=True)
    if args.download_model:
        subprocess.run([str(python), str(CODE / "scripts/download_model.py")], check=True, env={**os.environ, "OPL_IMAGE_WORKSPACE": str(workspace)})
    print(json.dumps({"code": str(CODE), "workspace": str(workspace), "python": str(python), "comfy_source": settings.get("comfy_source"), "with_inference": args.with_inference, "platform": platform.platform()}, indent=2))


if __name__ == "__main__":
    main()
