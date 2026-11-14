# Validation scope

The public `0.1.0` source is an early development MiniApp. Its stable Package ID
is `opl-image`, the resource is `ui://opl-image/workbench.html`, and the product
name is OPL Image Lab. No official OCI release is implied by the source version.

The original local deployment on an Apple M4 Max with 128 GB unified memory
completed text-to-image, then changed a yellow ceramic cup to blue through the
same result reference. An official MCP Apps SDK AppBridge with the Studio
sandbox policy exercised preview, comparison, continuation, PNG download,
task reopen, imports, and busy release refusal. These checks predate the public
source extraction; they establish the reference pipeline, not every clean
installation or accelerator.

The public extraction adds portable installed-code/runtime locations and a
self-contained plugin payload. Its contract tests cover one-dispatch task IDs,
changed-input refusal, unknown-result readback, targeted cancel, busy release,
asset isolation, import restrictions, and MCP resource/tool discovery from an
isolated workspace. CI runs without model weights or GPU access.

Native OPL Host UI acceptance remains separate. The original check was blocked
by another window owning the active conversation connection. Protocol/SDK
success and an installed directory entry do not establish native Host UI
acceptance. Physical cross-window drag gestures and model-running cancellation
were not separately accepted; the drop event and cancellation API contract were
tested.
