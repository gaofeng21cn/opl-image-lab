"""Exercise first-run setup without weights, network access, or a personal checkout."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CODE = Path(__file__).resolve().parents[1]


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
