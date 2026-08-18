import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "ci_guard.py"
SPEC = importlib.util.spec_from_file_location("ci_guard", SCRIPT)
ci_guard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ci_guard)


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class CIGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        git(self.root, "init")
        git(self.root, "config", "user.email", "guard@example.invalid")
        git(self.root, "config", "user.name", "Supernova Guard Test")

        self.cohort = "CAL-TEST-001"
        self.worker = "MF01"
        write_json(
            self.root / "state" / "CURRENT.json",
            {"superseded_cohorts": [], "active_cohort_id": self.cohort},
        )
        write_json(
            self.root / "assignments" / f"{self.cohort}.json",
            {"workers": {self.worker: {"goal": "test"}}},
        )
        self.report_path = self.root / "reports" / self.cohort / f"{self.worker}.json"
        write_json(
            self.report_path,
            {"cohort_id": self.cohort, "worker_id": self.worker, "payload": "immutable"},
        )
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "create immutable report")
        self.report_commit = git(self.root, "rev-parse", "HEAD")
        self.report_blob = ci_guard.git_blob_sha(self.report_path)

        self.verification_path = self.root / "verification" / f"{self.cohort}.json"

    def tearDown(self):
        self.tmp.cleanup()

    def manifest(self):
        return {
            "cohort_id": self.cohort,
            "safe_report_refs": [
                {
                    "worker_id": self.worker,
                    "path": f"reports/{self.cohort}/{self.worker}.json",
                    "blob_sha": self.report_blob,
                    "commit_sha": self.report_commit,
                    "verifier_reread_verified": True,
                    "schema_valid": True,
                    "auth_valid": True,
                    "public_safety_valid": True,
                }
            ],
            "quarantined_report_refs": [],
            "missing_workers": [],
            "worker_auth_verification": {self.worker: "PASS"},
            "calibration_pass": True,
            "verdict": "VERIFIED_COMPLETE",
            "ci_observation": "CI_NOT_OBSERVED",
        }

    def test_valid_binding_passes_even_when_self_ci_is_not_yet_observed(self):
        write_json(self.verification_path, self.manifest())
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "add verifier receipt")
        self.assertEqual(ci_guard.validate(self.root), [])

    def test_wrong_blob_is_rejected(self):
        manifest = self.manifest()
        manifest["safe_report_refs"][0]["blob_sha"] = "0" * 40
        write_json(self.verification_path, manifest)
        errors = ci_guard.validate(self.root)
        self.assertTrue(any("blob mismatch" in e for e in errors), errors)

    def test_wrong_creation_commit_is_rejected(self):
        write_json(self.verification_path, self.manifest())
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "unrelated verification commit")
        wrong = git(self.root, "rev-parse", "HEAD")
        manifest = self.manifest()
        manifest["safe_report_refs"][0]["commit_sha"] = wrong
        write_json(self.verification_path, manifest)
        errors = ci_guard.validate(self.root)
        self.assertTrue(
            any("claimed creation commit" in e or "creation commit mismatch" in e for e in errors),
            errors,
        )

    def test_modified_report_breaks_create_once_invariant(self):
        report = json.loads(self.report_path.read_text(encoding="utf-8"))
        report["payload"] = "mutated"
        write_json(self.report_path, report)
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "illegal report mutation")
        manifest = self.manifest()
        manifest["safe_report_refs"][0]["blob_sha"] = ci_guard.git_blob_sha(self.report_path)
        write_json(self.verification_path, manifest)
        errors = ci_guard.validate(self.root)
        self.assertTrue(any("not create-once immutable" in e for e in errors), errors)

    def test_complete_verdict_cannot_hide_missing_worker(self):
        manifest = self.manifest()
        manifest["safe_report_refs"] = []
        manifest["missing_workers"] = [self.worker]
        write_json(self.verification_path, manifest)
        errors = ci_guard.validate(self.root)
        self.assertTrue(any("requires every assigned worker safe" in e for e in errors), errors)
        self.assertTrue(any("cannot contain quarantined or missing workers" in e for e in errors), errors)

    def test_quarantine_entry_must_name_worker(self):
        manifest = self.manifest()
        manifest["calibration_pass"] = False
        manifest["verdict"] = "VERIFIED_WITH_QUARANTINES"
        manifest["safe_report_refs"] = []
        manifest["quarantined_report_refs"] = [{"reason": "bad receipt"}]
        write_json(self.verification_path, manifest)
        errors = ci_guard.validate(self.root)
        self.assertTrue(any("must identify worker_id" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
