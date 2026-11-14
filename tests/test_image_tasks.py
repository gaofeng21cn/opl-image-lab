import copy
import importlib.util
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
import uuid
import sys

from PIL import Image

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE / "scripts"))
spec = importlib.util.spec_from_file_location("image_tasks", SOURCE / "scripts/image_tasks.py")
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)


class OwnerContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        owner.ROOT = self.root
        owner.CODE_ROOT = SOURCE
        owner.STATE = self.root / "runtime/agent-app"
        (self.root / "workflows").mkdir()
        (self.root / "workflows/edit-api.json").write_bytes((SOURCE / "workflows/edit-api.json").read_bytes())
        self.pending, self.running, self.history, self.calls = [], [], {}, []
        test = self
        class API(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                if self.path == "/queue": data = {"queue_running": test.running, "queue_pending": test.pending}
                elif self.path.startswith("/history/"): data = test.history
                else: data = {}
                self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(data).encode())
            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                test.calls.append((self.path, data))
                if self.path == "/prompt":
                    test.pending.append([0, data["prompt_id"], data["prompt"], {}, []])
                    result = {"prompt_id": data["prompt_id"]}
                else: result = {}
                self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(result).encode())
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), API)
        owner.COMFY = "http://127.0.0.1:" + str(self.server.server_port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.temp.cleanup()

    def execute(self, operation, **data):
        return owner.execute({"operation": operation, **data})

    def request(self):
        return {"task_id": str(uuid.uuid4()), "prompt": "一只黄色陶瓷杯", "width": 768, "height": 768}

    def test_same_identity_does_not_generate_twice_and_changed_input_rejected(self):
        request = self.request()
        self.execute("submit", **request)
        self.execute("submit", **request)
        self.assertEqual(len([x for x in self.calls if x[0] == "/prompt"]), 1)
        with self.assertRaises(ValueError): self.execute("submit", **{**request, "prompt": "另一只杯子"})

    def test_unknown_result_is_reconciled_without_resubmission(self):
        request = self.request(); self.execute("submit", **request)
        self.pending.clear()
        self.assertEqual(self.execute("submit", **request)["status"], "unknown")
        self.assertEqual(len(self.calls), 1)

    def test_running_cancel_targets_one_prompt_and_busy_release_is_rejected(self):
        request = self.request(); self.execute("submit", **request)
        self.running = self.pending; self.pending = []
        self.running.append([1, str(uuid.uuid4()), {}, {}, []])
        with self.assertRaises(ValueError): self.execute("control", action="release")
        self.execute("cancel", task_id=request["task_id"])
        self.assertEqual(self.calls[-1], ("/interrupt", {"prompt_id": request["task_id"]}))
        self.assertFalse(any(route == "/free" for route, _ in self.calls))

    def test_queue_cancel_deletes_only_selected_task(self):
        request = self.request(); self.execute("submit", **request)
        self.execute("cancel", task_id=request["task_id"])
        self.assertEqual(self.calls[-1], ("/queue", {"delete": [request["task_id"]]}))

    def test_output_readback_and_edit_reuse(self):
        request = self.request(); self.execute("submit", **request)
        path = self.root / "results/agent-app/result.png"; path.parent.mkdir(parents=True)
        Image.new("RGB", (768, 768), "yellow").save(path)
        self.history = {request["task_id"]: {"status": {"status_str": "success"}, "outputs": {"8": {"images": [{"type": "output", "filename": "result.png", "subfolder": "agent-app"}]}}}}
        done = self.execute("get", task_id=request["task_id"])
        self.assertEqual(done["status"], "completed")
        next_request = self.request(); next_request["image_ref"] = done["output"]["asset_ref"]
        self.execute("submit", **next_request)
        graph = self.calls[-1][1]["prompt"]
        self.assertTrue(graph["2"]["inputs"]["image"].startswith("agent-app/"))
        self.assertEqual(len(self.execute("list")["tasks"]), 2)
        self.assertTrue(self.execute("asset", asset_ref=done["output"]["asset_ref"])["data_uri"].startswith("data:image/jpeg"))

    def test_unregistered_assets_and_network_private_targets_rejected(self):
        with self.assertRaises(ValueError): self.execute("asset", asset_ref="../../private.png")
        with self.assertRaises(ValueError): self.execute("import", url="file:///etc/passwd")
        with self.assertRaises(ValueError): self.execute("import", url="http://127.0.0.1/secret")
        with self.assertRaises(ValueError): self.execute("get", task_id=str(uuid.uuid4()))


if __name__ == "__main__": unittest.main()
