import base64
import importlib.util
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reconcile_branch_rest.py"


def load_reconciler():
    spec = importlib.util.spec_from_file_location("reconcile_branch_rest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReconcileBranchRestNonJsonGuard(unittest.TestCase):
    def test_raw_frozen_control_file_does_not_require_json(self):
        mod = load_reconciler()
        raw = b"# frozen protocol markdown\nnot json\n"

        def fake_req(path, method="GET", data=None):
            return {
                "type": "file",
                "sha": "a" * 40,
                "content": base64.b64encode(raw).decode("ascii"),
            }

        mod.req = fake_req
        meta, text = mod.file_text("PROTOCOL.md", "deadbeef")
        self.assertEqual(meta["sha"], "a" * 40)
        self.assertEqual(text.encode("utf-8"), raw)
        with self.assertRaises(json.JSONDecodeError):
            mod.content("PROTOCOL.md", "deadbeef")

    def test_frozen_identity_loop_uses_raw_file_helper(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("a,_=file_text(p,root);b,_=file_text(p,G)", source)
        self.assertNotIn("a,_=content(p,root);b,_=content(p,G)", source)


if __name__ == "__main__":
    unittest.main()
