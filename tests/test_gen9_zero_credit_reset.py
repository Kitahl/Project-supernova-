import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/reconcile_open_prs.py"
SPEC = importlib.util.spec_from_file_location("reconcile_open_prs_gen9_reset", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)

PLAN = "0aa341106cfc5b104ab9ca9c2ae116d490a258685e28d26d5435860c53bb12aa"
BASE = "b" * 40
HEAD = "c" * 40
CONTROL_BLOB = "d" * 40
ASSIGNMENT_BLOB = "e" * 40
WORKERS = (
    "MF01", "MF02", "MF03", "MF04", "MF05",
    "MM01", "MM02", "MM03", "MM04", "MM05", "MM07", "EXT01",
)


def old_state():
    return {
        "protocol_version": "2.5",
        "task_network_plan_id": PLAN,
        "generation_seq": 9,
        "active_cohort_id": MOD.GEN9_COHORT,
        "generation_head_sha": MOD.GEN9_G,
        "calibration_countable_current": True,
        "calibration_streak": 0,
        "fresh_allowed_globally": False,
        "repo_policy_status": "VERIFIED_PROTECTED_SOURCE_BOUND",
        "network_mode": "GITHUB_BRANCH_CALIBRATION",
        "foundry_sha256": MOD.MF311,
        "mastermind_sha256": MOD.MM4410,
        "runtime_state_id": MOD.RUNTIME,
        "runtime_update_receipt_path": MOD.STAGING_RECEIPT,
        "superseded_cohorts": ["OLD-A", "OLD-B"],
    }


def successor(cohort="CAL-BR-010-v25-test"):
    return {
        "protocol_version": "2.5",
        "task_network_plan_id": PLAN,
        "transport_mode": "BRANCH_GITOPS",
        "generation_seq": 10,
        "active_parent_state_git_identity": MOD.GEN9_STATE_BLOB,
        "active_cohort_id": cohort,
        "generation_branch": f"ps/gen/{cohort}",
        "generation_head_sha": HEAD,
        "active_control_manifest_path": f"control/{cohort}.json",
        "active_control_manifest_git_identity": CONTROL_BLOB,
        "active_assignment_path": f"assignments/{cohort}.json",
        "active_assignment_git_identity": ASSIGNMENT_BLOB,
        "worker_branches": {worker: f"ps/work/{cohort}/{worker}" for worker in WORKERS},
        "verifier_branch": f"ps/verify/{cohort}",
        "integrator_branch": f"ps/integrate/{cohort}",
        "consolidation_branch": f"ps/consolidate/{cohort}",
        "fresh_allowed_globally": False,
        "calibration_required_clean_cohorts": 2,
        "calibration_streak": 0,
        "calibration_countable_current": True,
        "repo_policy_status": "VERIFIED_PROTECTED_SOURCE_BOUND",
        "network_mode": "GITHUB_BRANCH_CALIBRATION",
        "foundry_sha256": MOD.MF311,
        "mastermind_sha256": MOD.MM4410,
        "runtime_state_id": MOD.RUNTIME,
        "runtime_update_receipt_path": MOD.STAGING_RECEIPT,
        "expected_base_head": BASE,
        "superseded_cohorts": ["OLD-A", "OLD-B", MOD.GEN9_COHORT],
        "current_runtime_blocker": "O-T0-TWO_CLEAN_COUNTABLE_V25_COHORTS",
        "goal1_status": "BLOCKED_T0",
        "goal2_status": "BLOCKED_BY_GOAL1",
    }


def write_candidate(root: pathlib.Path, new=None, receipt=None, marker=None):
    new = successor() if new is None else new
    cohort = new["active_cohort_id"]
    cp = f"control/{cohort}.json"
    ap = f"assignments/{cohort}.json"
    lp = f"liveness/{cohort}.json"
    marker = {
        "schema_version": "PS-GEN9-REPAIR-RESET-EPOCH-2.5-1",
        "old_state_blob": MOD.GEN9_STATE_BLOB,
        "old_cohort_id": MOD.GEN9_COHORT,
        "old_generation_head_sha": MOD.GEN9_G,
        "allowed_successor_generation_seq": 10,
        "allowed_successor_cohort_prefix": MOD.GEN10_COHORT_PREFIX,
        "supersession_disposition": MOD.GEN9_SUPERSESSION_DISPOSITION,
        "calibration_credit": 0,
        "fresh_evidence_consumed": False,
        "foundry_sha256": MOD.MF311,
        "mastermind_sha256": MOD.MM4410,
        "runtime_state_id": MOD.RUNTIME,
        "failure_semantics": "FAIL_CLOSED",
    } if marker is None else marker
    receipt = {
        "schema_version": "PS-COHORT-SUPERSESSION-1",
        "cohort_id": MOD.GEN9_COHORT,
        "generation_head_sha": MOD.GEN9_G,
        "state_blob_sha": MOD.GEN9_STATE_BLOB,
        "disposition": MOD.GEN9_SUPERSESSION_DISPOSITION,
        "calibration_credit": 0,
        "fresh_evidence_consumed": False,
        "replacement_generation_seq": 10,
        "replacement_countable": True,
    } if receipt is None else receipt
    control = {
        "control_manifest_id": f"CTRL-{cohort}",
        "task_network_plan_id": PLAN,
        "cohort_id": cohort,
        "generation_seq": 10,
        "parent_state_git_identity": MOD.GEN9_STATE_BLOB,
        "expected_base_head": BASE,
        "calibration_countable": True,
        "control_release_commit_sha": BASE,
    }
    assignment = {
        "assignment_id": f"PS-BRANCH-{cohort}",
        "task_network_plan_id": PLAN,
        "cohort_id": cohort,
        "generation_seq": 10,
        "parent_state_git_identity": MOD.GEN9_STATE_BLOB,
        "expected_base_head": BASE,
        "calibration_countable": True,
        "control_manifest_git_identity": CONTROL_BLOB,
        "generation_branch": f"ps/gen/{cohort}",
        "generation_root_sha": BASE,
    }
    liveness = {
        "cohort_id": cohort,
        "generation_seq": 10,
        "generation_root_sha": BASE,
        "control_manifest_id": control["control_manifest_id"],
        "control_manifest_git_identity": CONTROL_BLOB,
        "assignment_id": assignment["assignment_id"],
        "assignment_git_identity": ASSIGNMENT_BLOB,
    }
    files = {
        "state/CURRENT.json": new,
        MOD.GEN9_ZERO_CREDIT_RESET: marker,
        MOD.GEN9_SUPERSESSION_PATH: receipt,
        cp: control,
        ap: assignment,
        lp: liveness,
    }
    for rel, payload in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
    return sorted({"state/CURRENT.json", MOD.GEN9_SUPERSESSION_PATH, cp, ap, lp})


def fake_git(state_blob=MOD.GEN9_STATE_BLOB, control_blob=CONTROL_BLOB, assignment_blob=ASSIGNMENT_BLOB):
    def _run(cmd, cwd, env=None):
        if cmd[:2] == ["git", "rev-parse"]:
            spec = cmd[2]
            if spec.endswith(":state/CURRENT.json"):
                return 0, state_blob
            if spec.startswith("HEAD:control/"):
                return 0, control_blob
            if spec.startswith("HEAD:assignments/"):
                return 0, assignment_blob
        if cmd[:2] == ["git", "show"]:
            return 0, json.dumps(old_state())
        raise AssertionError(cmd)
    return _run


class Gen9ZeroCreditResetTests(unittest.TestCase):
    def admitted(self, root, old=None, changed=None, state_blob=None, control_blob=CONTROL_BLOB, assignment_blob=ASSIGNMENT_BLOB):
        old = old_state() if old is None else old
        changed = write_candidate(root) if changed is None else changed
        state_blob = MOD.GEN9_STATE_BLOB if state_blob is None else state_blob
        with mock.patch.object(MOD, "run", side_effect=fake_git(state_blob, control_blob, assignment_blob)):
            return MOD.exact_gen9_zero_credit_reset_parent(root, BASE, old, changed)

    def test_exact_transition_is_admitted(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(self.admitted(pathlib.Path(directory)))

    def test_wrong_predecessor_blob_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(self.admitted(pathlib.Path(directory), state_blob="0" * 40))

    def test_control_or_assignment_blob_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(self.admitted(pathlib.Path(directory), control_blob="0" * 40))
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(self.admitted(pathlib.Path(directory), assignment_blob="0" * 40))

    def test_old_credit_or_fresh_near_miss_fails_closed(self):
        for key, value in (("calibration_streak", 1), ("fresh_allowed_globally", True)):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory); old = old_state(); old[key] = value
                self.assertFalse(self.admitted(root, old=old))

    def test_successor_must_be_countable_streak_zero_and_fresh_off(self):
        for key, value in (("calibration_countable_current", False), ("calibration_streak", 1), ("fresh_allowed_globally", True)):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory); new = successor(); new[key] = value
                changed = write_candidate(root, new=new)
                with mock.patch.object(MOD, "run", side_effect=fake_git()):
                    self.assertFalse(MOD.exact_gen9_zero_credit_reset_parent(root, BASE, old_state(), changed))

    def test_exact_five_path_atomic_diff_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory); changed = write_candidate(root); changed.append("transitions/extra.json")
            with mock.patch.object(MOD, "run", side_effect=fake_git()):
                self.assertFalse(MOD.exact_gen9_zero_credit_reset_parent(root, BASE, old_state(), changed))

    def test_nonzero_credit_or_changed_substrate_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            receipt = {
                "schema_version": "PS-COHORT-SUPERSESSION-1", "cohort_id": MOD.GEN9_COHORT,
                "generation_head_sha": MOD.GEN9_G, "state_blob_sha": MOD.GEN9_STATE_BLOB,
                "disposition": MOD.GEN9_SUPERSESSION_DISPOSITION, "calibration_credit": 1,
                "fresh_evidence_consumed": False, "replacement_generation_seq": 10,
                "replacement_countable": True,
            }
            changed = write_candidate(root, receipt=receipt)
            with mock.patch.object(MOD, "run", side_effect=fake_git()):
                self.assertFalse(MOD.exact_gen9_zero_credit_reset_parent(root, BASE, old_state(), changed))
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory); new = successor(); new["foundry_sha256"] = "0" * 64
            changed = write_candidate(root, new=new)
            with mock.patch.object(MOD, "run", side_effect=fake_git()):
                self.assertFalse(MOD.exact_gen9_zero_credit_reset_parent(root, BASE, old_state(), changed))

    def test_report_admission_uses_exact_reset_without_fabricated_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory); changed = write_candidate(root)
            with mock.patch.object(MOD, "run", side_effect=fake_git()):
                self.assertEqual(MOD.report_admission(root, BASE, changed), [])


if __name__ == "__main__":
    unittest.main()
