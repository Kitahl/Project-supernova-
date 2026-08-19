import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reconcile_v25_admission.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reconcile_v25_admission", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReconcileV25AdmissionStateTests(unittest.TestCase):
    def test_waiting_receipt_is_pending_not_failure(self):
        mod = load_module()
        self.assertEqual(mod.result_state(["receipt absent"], waiting=True), "pending")

    def test_real_error_remains_failure(self):
        mod = load_module()
        self.assertEqual(mod.result_state(["verdict not complete"], waiting=False), "failure")

    def test_clean_receipt_is_success(self):
        mod = load_module()
        self.assertEqual(mod.result_state([], waiting=False), "success")

    def test_main_distinguishes_unwritten_heads(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("v_wait=bool(vh and vh==G)", source)
        self.assertIn("i_wait=bool(ih and ih==G)", source)
        self.assertIn("c_wait=bool(ch and ch==G)", source)
        self.assertIn("if H==G:return H,['consolidation receipt absent']", source)


if __name__ == "__main__":
    unittest.main()
