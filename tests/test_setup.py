"""Exercise first-run setup without weights, network access, or a personal checkout."""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

CODE = Path(__file__).resolve().parents[1]


class PluginContract(unittest.TestCase):
    def test_root_plugin_layout_and_content_lock(self):
        self.assertFalse((CODE / "plugins/opl-image").exists())
        marketplace = json.loads((CODE / ".agents/plugins/marketplace.json").read_text())
        self.assertEqual(marketplace["plugins"][0]["source"]["path"], ".")
        mcp = json.loads((CODE / "mcp.json").read_text())
        self.assertEqual(mcp["mcpServers"]["opl-image"]["args"], ["${PLUGIN_ROOT}/miniapp/dist/server.mjs"])
        self.assertEqual(mcp["mcpServers"]["opl-image"]["cwd"], "${PLUGIN_ROOT}")
        for required in ("plugin.json", "LOCAL_ACCESS.md", "skills/opl-image/SKILL.md", "opl-package.json"):
            self.assertTrue((CODE / required).is_file(), f"missing {required}")
        manifest = json.loads((CODE / "opl-package.json").read_text())
        self.assertEqual(manifest["codex_surface"]["plugin_source_path"], ".")
        self.assertTrue((CODE / manifest["presentation"]["icon_ref"]).is_file())
        digest = hashlib.sha256()
        for rel in manifest["content_lock"]["paths"]:
            path = CODE / rel
            self.assertTrue(path.is_file(), f"missing locked file: {rel}")
            for value in (rel.encode("utf-8"), path.read_bytes()):
                digest.update(struct.pack(">Q", len(value)))
                digest.update(value)
        self.assertEqual("sha256:" + digest.hexdigest(), manifest["content_lock"]["digest"])


class PortableSetup(unittest.TestCase):
    def test_environment_selected_workspace_is_used_and_preserved(self):
        with tempfile.TemporaryDirectory(prefix="opl image setup ") as temp:
            workspace = Path(temp) / "personal data"
            environment = {**os.environ, "OPL_IMAGE_WORKSPACE": str(workspace), "OPL_IMAGE_PYTHON": sys.executable}
            result = subprocess.run([sys.executable, str(CODE / "scripts/setup.py")], env=environment, check=True, capture_output=True, text=True)
            receipt = json.loads(result.stdout)
            self.assertEqual(receipt["workspace"], str(workspace.resolve()))
            self.assertFalse((workspace / "upstream").exists())
            settings = workspace / "settings.json"
            current = json.loads(settings.read_text())
            current["comfy_port"] = 29345
            settings.write_text(json.dumps(current))
            subprocess.run([sys.executable, str(CODE / "scripts/setup.py")], env=environment, check=True, capture_output=True, text=True)
            self.assertEqual(json.loads(settings.read_text())["comfy_port"], 29345)
            status = subprocess.run([sys.executable, str(CODE / "scripts/image_tasks.py")], input='{"operation":"status"}', env=environment, check=True, capture_output=True, text=True)
            data = json.loads(status.stdout)["result"]
            self.assertEqual(data["workspace"], str(workspace.resolve()))
            self.assertEqual(data["advanced_url"], "http://127.0.0.1:29345")


if __name__ == "__main__": unittest.main()
