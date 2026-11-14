# OPL 图像工坊

OPL 图像工坊是一款本地优先的 OPL 图像 MiniApp，提供文生图和自然语言编辑。标准 MCP App 与 Agent 工具调用同一任务 owner；推理使用单独安装的 ComfyUI。

公开仓库只包含应用、ComfyUI 适配器、模型配置、测试和安装工具。模型文件、提示词、原始照片、生成图像、任务历史和运行日志保存在用户选择的本机工作区，不纳入仓库。

## 功能

- 使用本机 Qwen Image Edit Rapid AIO 工作流文生图和编辑照片。
- 通过本机文件、粘贴、网页拖放或公开图片 URL 导入图像。
- 并排比较原图与结果，将结果用于下一轮编辑并下载 PNG。
- Agent 工具支持导入、生成、任务读取、历史、定向取消和服务控制。
- 以稳定任务 ID 重开结果，不重复提交。未知结果会查询原 ComfyUI `prompt_id`。
- 运行数据按用户隔离；ComfyUI 仅监听本机；运行或排队期间拒绝释放内存和停机。

## 安装

当前提供开发安装。建议先克隆源码并准备推理环境：

```sh
git clone https://github.com/gaofeng21cn/opl-image-lab.git
cd opl-image-lab
python3 scripts/setup.py --with-inference --download-model
codex plugin marketplace add "$PWD"
codex plugin add opl-image@opl-image-lab
```

在当前 OPL 对话的应用工作台刷新目录，然后打开 **OPL 图像工坊**，点击 **启动推理服务**。默认模型约 28.4 GB；`--with-inference` 安装依赖，`--download-model` 明确选择下载模型。

准备好运行环境后，也可以直接安装仓库中自带运行代码的预构建插件：

```sh
codex plugin marketplace add gaofeng21cn/opl-image-lab
codex plugin add opl-image@opl-image-lab
```

这是源码/开发分发，尚未发布正式 OPL OCI Package。

## 本机开发

需要 macOS 或 Linux、Python 3.12 以上、Node 22 以上和 ComfyUI checkout。参考硬件是 128 GB 统一内存的 M4 Max。macOS 自动使用 MPS 参数；其他平台或内存规格需在工作区 `settings.json` 配置合适的 `comfy_args`。Linux 合同测试不代表 GPU 推理验收；当前 POSIX 文件锁和进程管理尚不支持 Windows。

```sh
# 使用已有 ComfyUI 依赖的 Python 环境。
python3 -m pip install -r requirements.txt
python3 scripts/setup.py --comfy-source /path/to/ComfyUI
cd miniapp
npm ci
npm test
npm run build
```

设置 `OPL_IMAGE_WORKSPACE` 可指定运行数据目录。未设置时，macOS 默认 `~/Library/Application Support/OPL Image Lab`，Linux 默认 `$XDG_DATA_HOME/opl-image-lab`。源码与个人数据分开；`OPL_IMAGE_PYTHON` 可指定解释器。

运行 `python3 scripts/setup.py --with-inference --download-model` 可安装推理依赖并下载模型。ComfyUI 固定到记录的 revision，Python 依赖由 pip 解析，尚非完整环境锁定。模型精确 Hugging Face revision、文件大小和 SHA-256 见 [model-profile.json](model-profile.json)，下载后会校验。使用非默认工作区时，在 setup 和插件使用前设置同一个 `OPL_IMAGE_WORKSPACE`。

## 运行行为

默认 Qwen Rapid AIO NSFW v23，768 像素、4 步、CFG 1，支持文生图和照片编辑。模型与用户图像留在配置的本机。网络导入仅接受公开 HTTP(S) 地址，逐跳验证重定向目标，并限制文件大小和像素数。

所有打开的 MiniApp 共用一个 ComfyUI 队列。取消只针对指定任务 ID。释放模型内存与停止 ComfyUI 会影响所有页面，有运行或排队任务时会拒绝。关闭 MiniApp 不会停止任务。

节点图等高级用法继续通过 ComfyUI 完成。目前 MiniApp 尚未提供 PhotoCraft 完整的图层、选区或 PSD 编辑器。

## 测试与许可

运行 `npm --prefix miniapp test` 和 `python3 -m unittest discover -s tests -v`。生成 OPL Package 载体使用 `npm --prefix miniapp run build`。

应用使用 Apache-2.0。OPL DSH 主题和 SDK 依赖保留其上游许可证。ComfyUI 和 Qwen 模型另行安装并遵循各自许可证。详见 [NOTICE](NOTICE) 与[验证范围](docs/validation.md)。当前交互界面为中文，其他客户端可读取结构化工具结果。
