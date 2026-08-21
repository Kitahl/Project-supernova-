import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("reconcile_open_prs_gen7_reset", ROOT / "scripts/reconcile_open_prs.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


class Gen7RepairResetTests(unittest.TestCase):
    base = "b" * 40
    cohort = "CAL-BR-008-v25-test"

    def old_state(self):
        return {
            "generation_seq": 7,
            "active_cohort_id": MOD.GEN7_INVALIDATED_COHORT,
            "generation_head_sha": MOD.GEN7_INVALIDATED_HEAD,
            "calibration_countable_current": True,
            "calibration_streak": 0,
            "fresh_allowed_globally": False,
            "repo_policy_status": "VERIFIED_PROTECTED_SOURCE_BOUND",
        }

    def candidate(self, root: pathlib.Path):
        control_path = f"control/{self.cohort}.json"
        assignment_path = f"assignments/{self.cohort}.json"
        liveness_path = f"liveness/{self.cohort}.json"
        superseded_path = f"superseded/{MOD.GEN7_INVALIDATED_COHORT}.json"
        for path in (control_path, assignment_path, liveness_path, superseded_path, "state/CURRENT.json"):
            (root / path).parent.mkdir(parents=True, exist_ok=True)

        (root / control_path).write_text(json.dumps({
            "cohort_id": self.cohort,
            "generation_seq": 8,
            "parent_state_git_identity": MOD.GEN7_INVALIDATED_STATE_BLOB,
            "calibration_countable": True,
            "expected_base_head": self.base,
        }))
        (root / assignment_path).write_text(json.dumps({
            "cohort_id": self.cohort,
            "generation_seq": 8,
            "parent_state_git_identity": MOD.GEN7_INVALIDATED_STATE_BLOB,
            "calibration_countable": True,
            "expected_base_head": self.base,
        }))
        (root / liveness_path).write_text(json.dumps({
            "cohort_id": self.cohort,
            "generation_seq": 8,
            "generation_root_sha": self.base,
            "control_manifest_git_identity": "c" * 40,
            "assignment_git_identity": "d" * 40,
            "lanes": [],
        }))
        (root / superseded_path).write_text(json.dumps({
            "cohort_id": MOD.GEN7_INVALIDATED_COHORT,
            "generation_seq": 7,
            "generation_head_sha": MOD.GEN7_INVALIDATED_HEAD,
            "state_blob": MOD.GEN7_INVALIDATED_STATE_BLOB,
            "disposition": MOD.GEN7_INVALIDATED_DISPOSITION,
            "clean_cohort_credit": 0,
            "calibration_streak_credit": 0,
            "fresh_evidence_credit": 0,
        }))
        (root / "state/CURRENT.json").write_text(json.dumps({
            "generation_seq": 8,
            "active_parent_state_git_identity": MOD.GEN7_INVALIDATED_STATE_BLOB,
            "active_cohort_id": self.cohort,
            "active_control_manifest_path": control_path,
            "active_assignment_path": assignment_path,
            "calibration_streak": 0,
            "calibration_countable_current": True,
            "fresh_allowed_globally": False,
            "repo_policy_status": "VERIFIED_PROTECTED_SOURCE_BOUND",
            "superseded_cohorts": [MOD.GEN7_INVALIDATED_COHORT],
            "expected_base_head": self.base,
        }))
        return ["state/CURRENT.json", control_path, assignment_path, liveness_path, superseded_path]

    def fake_run(self, old, blob=None):
        blob = MOD.GEN7_INVALIDATED_STATE_BLOB if blob is None else blob
        def call(cmd, cwd, env=None):
            if cmd[:2] == ["git", "show"]:
                return 0, json.dumps(old)
            if cmd[:2] == ["git", "rev-parse"]:
                return 0, blob
            raise AssertionError(cmd)
        return call

    def test_exact_invalidated_gen7_successor_passes_report_admission(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            changed = self.candidate(root)
            old = self.old_state()
            with mock.patch.object(MOD, "run", side_effect=self.fake_run(old)):
                self.assertTrue(MOD.exact_invalidated_gen7_repair_parent(root, self.base, old, changed))
                self.assertEqual(MOD.report_admission(root, self.base, changed), [])

    def test_wrong_base_state_blob_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td); changed = self.candidate(root); old = self.old_state()
            with mock.patch.object(MOD, "run", side_effect=self.fake_run(old, "0" * 40)):
                self.assertFalse(MOD.exact_invalidated_gen7_repair_parent(root, self.base, old, changed))

    def test_fresh_or_nonzero_streak_near_miss_fails(self):
        for field, value in (("fresh_allowed_globally", True), ("calibration_streak", 1)):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as td:
                root = pathlib.Path(td); changed = self.candidate(root); old = self.old_state(); old[field] = value
                with mock.patch.object(MOD, "run", side_effect=self.fake_run(old)):
                    self.assertFalse(MOD.exact_invalidated_gen7_repair_parent(root, self.base, old, changed))

    def test_successor_must_be_generation8_zero_streak_and_exact_parent(self):
        for field, value in (("generation_seq", 9), ("calibration_streak", 1), ("active_parent_state_git_identity", "0" * 40)):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as td:
                root = pathlib.Path(td); changed = self.candidate(root); old = self.old_state()
                state_path = root / "state/CURRENT.json"; state = json.loads(state_path.read_text()); state[field] = value; state_path.write_text(json.dumps(state))
                with mock.patch.object(MOD, "run", side_effect=self.fake_run(old)):
                    self.assertFalse(MOD.exact_invalidated_gen7_repair_parent(root, self.base, old, changed))

    def test_supersession_must_explicitly_record_zero_credit_disposition(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td); changed = self.candidate(root); old = self.old_state()
            path = root / f"superseded/{MOD.GEN7_INVALIDATED_COHORT}.json"
            obj = json.loads(path.read_text()); obj["disposition"] = "CLEAN"; path.write_text(json.dumps(obj))
            with mock.patch.object(MOD, "run", side_effect=self.fake_run(old)):
                self.assertFalse(MOD.exact_invalidated_gen7_repair_parent(root, self.base, old, changed))

    def test_extra_or_missing_transition_path_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td); changed = self.candidate(root); old = self.old_state()
            with mock.patch.object(MOD, "run", side_effect=self.fake_run(old)):
                self.assertFalse(MOD.exact_invalidated_gen7_repair_parent(root, self.base, old, changed + ["benchmark/registry.json"]))
                self.assertFalse(MOD.exact_invalidated_gen7_repair_parent(root, self.base, old, changed[:-1]))

    def test_source_contains_seed_required_nonvacuity_markers(self):
        text = (ROOT / "scripts/reconcile_open_prs.py").read_text(encoding="utf-8")
        self.assertIn("exact_invalidated_gen7_repair_parent", text)
        self.assertIn("INVALIDATED_ZERO_CREDIT_AUTHORITATIVE_CONTROL_DEFECTS", text)
        self.assertIn("superseded/CAL-BR-007-v25-c13b6ee4.json", text)


if __name__ == "__main__":
    unittest.main()
