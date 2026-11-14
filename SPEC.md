# OPL Image Lab

OPL Image Lab owns the image-domain tools and a dedicated standard MCP App.
ComfyUI remains the owner of the execution queue, prompt IDs, inference, and
generated files. The Agent and UI call the same `scripts/image_tasks.py` JSON
owner; the app does not introduce another execution queue.

The UI supports text-to-image, explicit image import, natural-language edits,
comparison, continuation, downloads, and this workbench's registered history.
Each mutation is bound to its object. Unknown dispatch outcomes are queried by
the same ID, and cancellation targets that ID. Closing a view does not cancel
work. Model release and service stop are global operations with queue guards.

The official MCP Apps SDK owns App/AppBridge protocol behavior. DSH theme and
control styles retain the OPL App visual source and MIT attribution. Installed
code resolves from its payload; personal state, model weights and results live
in the user workspace. Local inference requires no cloud credentials, Connect
grant or private knowledge sources. Cloud provider integration is outside this
version; any later implementation must use the existing provider/Connect owner.

The Package ID `opl-image`, tool names, and UI resource URI remain compatible
with the original local workbench. Package manifests and native Codex plugin
installation provide discovery; no parallel registry is maintained. Current
distribution is a source/development carrier, without an official OCI release.

Full PhotoCraft layer/selection editing remains an optional future integration.
Professional node workflows remain in ComfyUI. Native Host interaction,
installed payload, source tests, and visual model quality are accepted separately.
