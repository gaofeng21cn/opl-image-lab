---
name: opl-image
description: 使用本机 Qwen 生成图片、自然语言编辑用户指定的照片，并在 OPL 标准图片 MiniApp 中比较结果和继续编辑。
---

使用 `open_image_workbench` 打开工作台；有 task_id 或 image_ref 时携带同一引用。打开界面不会启动服务或生成图片。

Agent 主流程：`image_status` 核对环境；需要时 `image_control(action=start)` 后查询就绪；`image_import` 登记用户指定的文件或公开图片直链；`image_generate` 生成或编辑；`image_get_task` 查询同一任务；`image_list_tasks` 查看本工作台任务。结果的绝对路径可供图片读取工具查看。

每个新任务传入一个 UUID。提交返回 unknown 或工具超时时，先按原编号查询，不能换编号自动重试。input_ref/产物引用绑定当前对象，不能沿用另一任务的原图。对人像、细节保持和最终效果进行实际看图判断，工具成功不代表视觉要求满足。

`image_cancel_task` 只取消指定任务。释放内存和停止服务使用 `image_control`，会影响所有共用后台的页面，忙时拒绝。关闭 MiniApp 不取消任务、不卸载模型。

默认 768 像素、4 步、CFG 1。无 image_ref 是文生图；有 image_ref 是编辑。图片与指令在本机处理，不为完成本机任务自动切换云端模型。通过 image_status 返回的 workspace 定位输入、结果和运行状态；使用 OPL_IMAGE_WORKSPACE 可明确绑定本机数据目录。
