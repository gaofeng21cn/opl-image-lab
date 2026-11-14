# Contributing

Use synthetic images and an isolated `OPL_IMAGE_WORKSPACE`. Keep private photos,
prompts, outputs, credentials, local paths and model weights out of commits.

Install Python requirements and run `npm ci` from `miniapp/`. Before a pull
request, run:

```sh
(cd miniapp && npm run build && npm test)
python3 -m unittest discover -s tests -v
git diff --check
```

Commit generated files under `plugins/opl-image` with their source changes.
That payload must run from an installed cache without the source checkout.
The build updates its content lock and dependency notices.

Preserve standard MCP Apps behavior and the shared image owner. UI and Agent
actions must use the same task ID and result. Keep unknown outcomes inspectable;
never introduce an automatic second submission. Retain upstream notices for
the DSH theme, the Qwen text encoder and bundled SDK dependencies.

Read `SPEC.md` for ownership and `docs/validation.md` for acceptance boundaries.
Native Host interaction and actual model quality require separate evidence.
