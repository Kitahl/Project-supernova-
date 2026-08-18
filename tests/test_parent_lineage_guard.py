import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "parent_lineage_guard.py"
SPEC = importlib.util.spec_from_file_location("parent_lineage_guard", SCRIPT)
parent_lineage_guard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(parent_lineage_guard)


def git(root, *args, check=True):
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.stdout.strip()


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class ParentLineageGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        git(self.root, "init")
        git(self.root, "config", "user.email", "lineage@example.invalid")
        git(self.root, "config", "user.name", "Supernova Lineage Test")

        self.old = "CAL-TEST-OLD"
        self.new = "CAL-TEST-NEW"
        self.runtime = {
            "base_runtime_state_id": "base-runtime",
            "runtime_state_id": "runtime-1",
            "foundry_sha256": "f" * 64,
            "mastermind_sha256": "m" * 64,
            "actual_runtime_plan_id": "plan-runtime",
            "canonical_bus_repo": "owner/repo",
            "private_vault_repo": "owner/private",
        }

        parent_state = {
            "generation_seq": 1,
            "active_cohort_id": self.old,
            "active_parent_state_git_identity": "0" * 40,
            "superseded_cohorts": [],
            **self.runtime,
        }
        write_json(self.root / "state" / "CURRENT.json", parent_state)
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "parent state")
        self.parent_blob = git(self.root, "hash-object", "state/CURRENT.json")

        self.control_path = self.root / "control" / f"{self.new}.json"
        self.assignment_path = self.root / "assignments" / f"{self.new}.json"
        write_json(
            self.control_path,
            {
                "cohort_id": self.new,
                "generation_seq": 2,
                "parent_state_git_identity": self.parent_blob,
            },
        )
        write_json(
            self.assignment_path,
            {
                "cohort_id": self.new,
                "generation_seq": 2,
                "parent_state_git_identity": self.parent_blob,
                "workers": {},
            },
        )
        self.current_state = {
            "generation_seq": 2,
            "active_cohort_id": self.new,
            "active_parent_state_git_identity": self.parent_blob,
            "active_control_manifest_path": f"control/{self.new}.json",
            "active_assignment_path": f"assignments/{self.new}.json",
            "superseded_cohorts": [],
            **self.runtime,
        }
        write_json(self.root / "state" / "CURRENT.json", self.current_state)
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "current state")

    def tearDown(self):
        self.tmp.cleanup()

    def rewrite_current(self, state=None, control=None, assignment=None):
        if state is not None:
            write_json(self.root / "state" / "CURRENT.json", state)
        if control is not None:
            write_json(self.control_path, control)
        if assignment is not None:
            write_json(self.assignment_path, assignment)

    def test_valid_historical_parent_passes(self):
        self.assertEqual(parent_lineage_guard.validate(self.root), [])

    def test_nonexistent_parent_is_rejected(self):
        bad = dict(self.current_state)
        bad["active_parent_state_git_identity"] = "0" * 40
        control = json.loads(self.control_path.read_text())
        assignment = json.loads(self.assignment_path.read_text())
        control["parent_state_git_identity"] = "0" * 40
        assignment["parent_state_git_identity"] = "0" * 40
        self.rewrite_current(bad, control, assignment)
        errors = parent_lineage_guard.validate(self.root)
        self.assertTrue(any("does not resolve" in e for e in errors), errors)

    def test_existing_unrelated_blob_is_not_a_valid_parent(self):
        unrelated = self.root / "unrelated.json"
        write_json(unrelated, {"generation_seq": 1, "active_cohort_id": "OTHER", **self.runtime})
        blob = git(self.root, "hash-object", "-w", str(unrelated))
        bad = dict(self.current_state)
        bad["active_parent_state_git_identity"] = blob
        control = json.loads(self.control_path.read_text())
        assignment = json.loads(self.assignment_path.read_text())
        control["parent_state_git_identity"] = blob
        assignment["parent_state_git_identity"] = blob
        self.rewrite_current(bad, control, assignment)
        errors = parent_lineage_guard.validate(self.root)
        self.assertTrue(any("never a historical state/CURRENT.json" in e for e in errors), errors)

    def test_skipped_generation_is_rejected(self):
        bad = dict(self.current_state)
        bad["generation_seq"] = 3
        control = json.loads(self.control_path.read_text())
        assignment = json.loads(self.assignment_path.read_text())
        control["generation_seq"] = 3
        assignment["generation_seq"] = 3
        self.rewrite_current(bad, control, assignment)
        errors = parent_lineage_guard.validate(self.root)
        self.assertTrue(any("not exactly current-1" in e for e in errors), errors)

    def test_runtime_identity_drift_without_receipt_is_rejected(self):
        bad = dict(self.current_state)
        bad["runtime_state_id"] = "runtime-2"
        self.rewrite_current(bad)
        errors = parent_lineage_guard.validate(self.root)
        self.assertTrue(any("runtime-bound identity drift" in e for e in errors), errors)

    def test_control_parent_mismatch_is_rejected(self):
        control = json.loads(self.control_path.read_text())
        control["parent_state_git_identity"] = "1" * 40
        self.rewrite_current(control=control)
        errors = parent_lineage_guard.validate(self.root)
        self.assertTrue(any("does not bind the resolved parent blob" in e for e in errors), errors)

    def test_supersession_history_cannot_regress(self):
        # Rebuild the parent state blob as a real historical state with a superseded cohort.
        parent = {
            "generation_seq": 1,
            "active_cohort_id": self.old,
            "active_parent_state_git_identity": "0" * 40,
            "superseded_cohorts": ["CAL-FAILED"],
            **self.runtime,
        }
        write_json(self.root / "state" / "CURRENT.json", parent)
        git(self.root, "add", "state/CURRENT.json")
        git(self.root, "commit", "-m", "alternate historical parent")
        blob = git(self.root, "hash-object", "state/CURRENT.json")

        current = dict(self.current_state)
        current["active_parent_state_git_identity"] = blob
        current["superseded_cohorts"] = []
        control = json.loads(self.control_path.read_text())
        assignment = json.loads(self.assignment_path.read_text())
        control["parent_state_git_identity"] = blob
        assignment["parent_state_git_identity"] = blob
        self.rewrite_current(current, control, assignment)
        errors = parent_lineage_guard.validate(self.root)
        self.assertTrue(any("superseded cohort history regressed" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
