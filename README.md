# OPL Image Lab

OPL Image Lab is a local-first image-generation and natural-language editing MiniApp for OPL. It provides a standard MCP App and Agent tools over the same task owner, and uses a separately installed ComfyUI checkout for inference.

The public project contains the app, ComfyUI adapter, model-profile metadata, tests, and setup tools. Model files, prompts, source photos, generated images, task history, and runtime logs live in a user-selected local workspace and are not added to the repository.

## Features

- Text-to-image and image editing through the local Qwen Image Edit Rapid AIO workflow.
- Import a local image, paste one, drop an image from a web page, or fetch a public image URL.
- Compare original and output, continue editing the selected result, and download PNGs.
- Agent tools for import, generate, task readback, task history, targeted cancellation, and service control.
- Reopen a task by its stable ID without submitting it again. Unknown outcomes are reconciled against the same ComfyUI `prompt_id`.
- Per-user runtime data, a local-only ComfyUI listener, and busy-queue guards for release and shutdown.

## Install

The current source carrier is a development installation. Start with a checkout
so you can configure the inference runtime before enabling the plugin:

```sh
git clone https://github.com/gaofeng21cn/opl-image-lab.git
cd opl-image-lab
python3 scripts/setup.py --with-inference --download-model
codex plugin marketplace add "$PWD"
codex plugin add opl-image@opl-image-lab
```

Open the current OPL conversation's App workbench, refresh the catalog, and open **OPL Image Lab**. Click **启动推理服务** to start inference. The default model download is about 28.4 GB; `--with-inference` installs dependencies, and `--download-model` separately opts into the download.

Once the runtime is configured, the self-contained prebuilt plugin can also be installed from GitHub:

```sh
codex plugin marketplace add gaofeng21cn/opl-image-lab
codex plugin add opl-image@opl-image-lab
```

This is source/development distribution. An official OPL OCI Package release has not been published.

## Local development

Requirements: macOS or Linux, Python 3.12+, Node 22+, and a ComfyUI checkout. The reference hardware is an M4 Max with 128 GB unified memory. MPS optimizations are enabled on macOS; for other platforms or memory sizes set `comfy_args` in the workspace `settings.json`. Linux contract tests do not establish GPU inference support. Windows is not supported by the current POSIX file locking and process manager.

```sh
# Use a Python environment with the existing ComfyUI dependencies.
python3 -m pip install -r requirements.txt
python3 scripts/setup.py --comfy-source /path/to/ComfyUI
cd miniapp
npm ci
npm run build
npm test
```

When `OPL_IMAGE_WORKSPACE` is set, it selects the per-user data directory. Otherwise the default is `~/Library/Application Support/OPL Image Lab` on macOS or `$XDG_DATA_HOME/opl-image-lab` on Linux. Code checkout and personal data remain separate. `OPL_IMAGE_PYTHON` can select the runtime Python explicitly.

To install inference dependencies and the model into the selected workspace, run `python3 scripts/setup.py --with-inference --download-model`. Setup checks out the pinned ComfyUI revision. Its Python dependencies are resolved by pip; this is not a full reproducible environment lock. The weight's exact Hugging Face revision, size and SHA-256 are recorded in [model-profile.json](model-profile.json); the downloader verifies these before accepting the file. Set `OPL_IMAGE_WORKSPACE` before both setup and plugin use when choosing a nondefault workspace.

## Runtime behavior

The default model configuration is Qwen Rapid AIO NSFW v23, 768 px, 4 steps, CFG 1. It supports both text-to-image and image editing. Models and user images stay on the configured local machine. Image URL import accepts public HTTP(S) sources only, validates every redirect target, and enforces byte and pixel limits.

All open MiniApp pages share one ComfyUI queue. Cancellation targets one task ID. Releasing model memory and stopping ComfyUI are global operations and are refused while any task is running or queued. Closing the MiniApp leaves the task running.

For advanced node graphs, use the existing ComfyUI interface. The MiniApp does not yet provide PhotoCraft's full layer, selection, or PSD editor.

## Tests and licenses

Run the owner contract tests and MCP Apps SDK test with `npm --prefix miniapp test` and `python3 -m unittest discover -s tests -v`. The generated OPL Package payload is built by `npm --prefix miniapp run build`.

The application is Apache-2.0. The OPL DSH theme and SDK dependency notices retain their upstream licenses. ComfyUI and Qwen model weights are separately installed under their own licenses. See [NOTICE](NOTICE) and [validation scope](docs/validation.md). The current UI is Chinese; tools expose structured results to other clients.
