import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/supernova-rest-branch-reconciler.yml"
ADMISSION = ROOT / "scripts/reconcile_v25_admission.py"


class RestAdmissionDependencyTests(unittest.TestCase):
    def test_workflow_uses_exact_repository_checkout_and_frozen_environment(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for token in (
            "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683",
            "persist-credentials: false",
            "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
            "python-version: '3.13.15'",
            "--require-hashes -r requirements-validation.lock",
            "python scripts/assert_validator_environment.py",
            "python scripts/reconcile_branch_rest.py",
            "python scripts/reconcile_v25_admission.py",
        ):
            self.assertIn(token, text)

    def test_broken_two_file_tmp_loader_cannot_regress(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for forbidden in (
            "for name in ('reconcile_branch_rest.py','reconcile_v25_admission.py')",
            "/tmp/reconcile_branch_rest.py",
            "/tmp/reconcile_v25_admission.py",
            "raw.githubusercontent.com",
        ):
            self.assertNotIn(forbidden, text)

    def test_admission_import_resolves_from_repository_script_directory(self):
        text = ADMISSION.read_text(encoding="utf-8")
        self.assertIn("SCRIPT_DIR = pathlib.Path(__file__).resolve().parent", text)
        self.assertIn("sys.path.insert(0, str(SCRIPT_DIR))", text)
        self.assertIn("import strict_json", text)


if __name__ == "__main__":
    unittest.main()
