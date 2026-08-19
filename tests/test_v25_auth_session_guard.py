import importlib.util
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_branch_bus_v251.py"
AUTH = ROOT / "config" / "worker_auth.json"
HMAC2 = "PS-HMAC-SHA256-CANONICAL-REPORT-2"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_branch_bus_v251", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class V25AuthSessionGuardTests(unittest.TestCase):
    def test_worker_auth_metadata_is_canonical_report_hmac2(self):
        auth = json.loads(AUTH.read_text(encoding="utf-8"))
        self.assertEqual(auth["scheme"], HMAC2)
        self.assertEqual(auth["canonicalization"]["remove_field"], "worker_auth_proof")
        self.assertTrue(auth["canonicalization"]["sort_keys"])
        self.assertTrue(auth["canonicalization"]["compact_separators"])
        self.assertEqual(auth["canonicalization"]["encoding"], "UTF-8")
        self.assertFalse(auth["canonicalization"]["ensure_ascii"])

    def test_matching_replay_modes_pass(self):
        mod = load_validator()
        report = {
            "mode": "SAFE_REPLAY_ONLY",
            "session_header": {"execution_mode": "SAFE_REPLAY_ONLY"},
        }
        assignment = {"network_mode": "GITHUB_BRANCH_CALIBRATION"}
        self.assertEqual(mod.execution_mode_errors(report, assignment), [])

    def test_header_fresh_report_replay_is_rejected(self):
        mod = load_validator()
        report = {
            "mode": "SAFE_REPLAY_ONLY",
            "session_header": {"execution_mode": "FRESH_EXECUTION"},
        }
        assignment = {"network_mode": "GITHUB_BRANCH_CALIBRATION"}
        errors = mod.execution_mode_errors(report, assignment)
        self.assertIn("session_header.execution_mode != report.mode", errors)
        self.assertIn("calibration session execution_mode != SAFE_REPLAY_ONLY", errors)

    def test_report_fresh_header_replay_is_rejected(self):
        mod = load_validator()
        report = {
            "mode": "FRESH_EXECUTION",
            "session_header": {"execution_mode": "SAFE_REPLAY_ONLY"},
        }
        assignment = {"network_mode": "GITHUB_BRANCH_CALIBRATION"}
        errors = mod.execution_mode_errors(report, assignment)
        self.assertIn("session_header.execution_mode != report.mode", errors)
        self.assertIn("calibration report mode != SAFE_REPLAY_ONLY", errors)

    def test_both_fresh_modes_are_rejected_during_calibration(self):
        mod = load_validator()
        report = {
            "mode": "FRESH_EXECUTION",
            "session_header": {"execution_mode": "FRESH_EXECUTION"},
        }
        assignment = {"network_mode": "GITHUB_BRANCH_CALIBRATION"}
        errors = mod.execution_mode_errors(report, assignment)
        self.assertNotIn("session_header.execution_mode != report.mode", errors)
        self.assertIn("calibration session execution_mode != SAFE_REPLAY_ONLY", errors)
        self.assertIn("calibration report mode != SAFE_REPLAY_ONLY", errors)


if __name__ == "__main__":
    unittest.main()
