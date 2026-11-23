# Local development access

OPL Image Lab runs for the current OS user. Installed code is resolved relative
to the plugin payload. `OPL_IMAGE_WORKSPACE` selects runtime data; otherwise the
documented per-user application-data directory is used. The selected Python
interpreter and ComfyUI checkout are recorded in local `settings.json`.

The app has no cloud credentials. ComfyUI listens on loopback. The MCP client
grants access to declared tools. Import reads explicitly supplied files, public
image URLs, or image bytes. History and asset tools read objects registered by
this workbench. Selected-task cancellation does not issue a global interrupt.

This source carrier is a development installation. It is not an OCI release or
a declaration of native OPL Host acceptance.
