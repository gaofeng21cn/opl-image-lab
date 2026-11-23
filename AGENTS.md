# OPL Image Lab

- This repository owns the image-domain tools, standard MCP App, and ComfyUI adapter. Follow the OPL Agent Apps standard in Framework; use the official MCP Apps SDK and existing DSH styles.
- Preserve stable identity `opl-image`, tool names, and `ui://opl-image/workbench.html`. The product name is OPL Image Lab.
- Code and runtime data are separate. Resolve code relative to the installed payload, runtime from `OPL_IMAGE_WORKSPACE` or the documented per-user default. Do not embed a developer checkout path.
- ComfyUI owns the execution queue and outputs. Reuse `prompt_id`; never automatically redispatch an unknown outcome or globally interrupt a selected task.
- Do not commit models, user images, prompts, task history, local settings, virtual environments, logs, or installation receipts. Test with synthetic inputs and isolated workspaces.
- Source publication, OCI Package distribution, local installation, native Host acceptance, and visual quality are separate claims. Current distribution is an explicit development carrier.
- New GitHub-facing text uses English. Keep README.md in English and README.zh-CN.md in Chinese; update both for installation and behavior changes.
- Validate with `npm --prefix miniapp run build`, `npm --prefix miniapp test`, and `python3 -m unittest discover -s tests -v`. Build outputs go to gitignored `miniapp/dist/`; commit `opl-package.json` if locked source changes update its content lock.
