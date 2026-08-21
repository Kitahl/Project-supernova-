import ast
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
REST = ROOT / "scripts/reconcile_branch_rest.py"
REST_WORKFLOW = ROOT / ".github/workflows/supernova-rest-branch-reconciler.yml"
AUTHORITY = ROOT / "config/admission_authority.json"
EPOCH = ROOT / "config/structural_status_rotation_epoch_v25.json"


class StructuralStatusSingleWriterTests(unittest.TestCase):
    def test_rest_helper_has_no_status_write_capability(self):
        text = REST.read_text(encoding="utf-8")
        tree = ast.parse(text)
        self.assertNotIn("/statuses/", text)
        self.assertNotIn("method=\"POST\"", text)
        self.assertNotIn("method='POST'", text)
        self.assertNotIn('"supernova/branch-generation"', text)
        self.assertNotIn("'supernova/branch-generation'", text)
        self.assertNotIn('"supernova/branch-worker"', text)
        self.assertNotIn("'supernova/branch-worker'", text)
        functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        self.assertFalse({"status", "post_status", "publish_status"} & functions)

    def test_rest_diagnostics_use_distinct_non_authoritative_names(self):
        text = REST.read_text(encoding="utf-8")
        self.assertIn("supernova/rest-branch-generation-diagnostic", text)
        self.assertIn("supernova/rest-branch-worker-diagnostic", text)
        self.assertIn('"authoritative": False', text)
        self.assertIn('AUTHORITATIVE_WRITER = "scripts/reconcile_branch_statuses.py"', text)
        self.assertRegex(text, r"return 0\s+\n\s*\nif __name__")

    def test_rest_workflow_separates_diagnostics_from_status_writing_admission(self):
        text = REST_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 /tmp/reconcile_branch_rest.py", text)
        self.assertIn("python3 /tmp/reconcile_v25_admission.py", text)
        self.assertIn("GET-only", text)
        self.assertIn("only status-writing program", text)
        self.assertLess(
            text.index("python3 /tmp/reconcile_branch_rest.py"),
            text.index("python3 /tmp/reconcile_v25_admission.py"),
        )

    def test_authority_names_exactly_one_structural_writer(self):
        authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        self.assertEqual(authority["structural_status_writer_cardinality"], 1)
        self.assertEqual(
            authority["authoritative_structural_status_writer"],
            "scripts/reconcile_branch_statuses.py",
        )
        self.assertEqual(
            authority["non_authoritative_rest_diagnostic"],
            "scripts/reconcile_branch_rest.py",
        )
        self.assertIn(
            "supernova/rest-branch-generation-diagnostic",
            authority["non_authoritative_rest_diagnostic_contexts"],
        )
        self.assertIn(
            "supernova/rest-branch-worker-diagnostic",
            authority["non_authoritative_rest_diagnostic_contexts"],
        )

    def test_epoch_makes_one_shot_seed_inert_and_records_zero_credit(self):
        epoch = json.loads(EPOCH.read_text(encoding="utf-8"))
        self.assertEqual(epoch["authoritative_writer_cardinality"], 1)
        self.assertEqual(epoch["authoritative_writer"], "scripts/reconcile_branch_statuses.py")
        self.assertEqual(
            epoch["former_rest_writer_disposition"],
            "READ_ONLY_NON_AUTHORITATIVE_DIAGNOSTIC",
        )
        self.assertEqual(
            epoch["one_shot_seed_disposition"],
            "PERMANENTLY_INERT_AFTER_THIS_MARKER_IS_ACCEPTED",
        )
        self.assertIn("GEN9_REMAINS_ZERO_CREDIT", epoch["calibration_effect"])


if __name__ == "__main__":
    unittest.main()
