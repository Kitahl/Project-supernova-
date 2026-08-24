import sys
import types
import unittest
from unittest.mock import patch


# The production checks are mock-driven here; retain test executability in the
# local focused harness when the separately supplied validator wheel is absent.
try:
    import jsonschema  # noqa: F401
except ModuleNotFoundError:
    jsonschema = types.ModuleType("jsonschema")

    class Draft202012Validator:
        def __init__(self, *args, **kwargs):
            pass

        @classmethod
        def check_schema(cls, *args, **kwargs):
            return None

        def iter_errors(self, *args, **kwargs):
            return []

    class FormatChecker:
        pass

    jsonschema.Draft202012Validator = Draft202012Validator
    jsonschema.FormatChecker = FormatChecker
    sys.modules["jsonschema"] = jsonschema

from scripts import reconcile_open_prs as MOD


COHORT = "CAL-R11-REMOTE"
GENERATION = "a" * 40
HEADS = {role: (f"{index:x}" * 40)[:40] for index, role in enumerate(sorted(MOD.WORKERS), 1)}


def state():
    return {
        "active_cohort_id": COHORT,
        "generation_head_sha": GENERATION,
        "worker_branches": {role: f"ps/work/{COHORT}/{role}" for role in MOD.WORKERS},
        "generation_seq": 13,
        "calibration_countable_current": True,
        "active_staged_candidate_path": f"staging/{COHORT}.json",
        "active_staged_candidate_git_identity": "p" * 40,
        "verifier_branch": f"ps/verify/{COHORT}",
        "integrator_branch": f"ps/integrate/{COHORT}",
    }


def reports_and_verification():
    refs, reports = [], {}
    for role, head in HEADS.items():
        branch = f"ps/work/{COHORT}/{role}"
        path = f"reports/{COHORT}/{role}.json"
        blob = f"b-{role}"
        refs.append({"worker_id": role, "branch": branch, "branch_head_sha": head,
                     "report_creation_commit_sha": head, "path": path, "blob_sha": blob})
        reports[(path, head)] = (blob, {
            "task_network_plan_id": MOD.PLAN, "cohort_id": COHORT, "worker_id": role,
            "generation_head_sha": GENERATION, "worker_branch": branch,
            "worker_auth_scheme": "PS-HMAC-SHA256-CANONICAL-REPORT-2",
            "worker_auth_commitment": "commitment", "status": "VALID_ASSIGNED_REPORT",
            "public_safety_status": "PASS", "origin_reread_claim": False,
        })
    return {"safe_report_refs": refs}, reports


class Root11RemoteGateTests(unittest.TestCase):
    def test_remote_production_workers_require_exact_partition_and_trusted_status(self):
        verification, reports = reports_and_verification()
        with patch.object(MOD, "_remote_branch_head", side_effect=lambda branch: next(
                (head for role, head in HEADS.items() if branch.endswith("/" + role)), None)), \
             patch.object(MOD, "_remote_json", side_effect=lambda path, head: reports[(path, head)]), \
             patch.object(MOD, "_one_path_child", return_value=True), \
             patch.object(MOD, "_schema_valid", return_value=True), \
             patch.object(MOD, "_trusted_workflow_status", return_value=True):
            self.assertEqual(MOD._remote_production_worker_errors(verification, state()), [])

    def test_remote_production_workers_fail_closed_without_hmac_validating_status(self):
        verification, reports = reports_and_verification()
        with patch.object(MOD, "_remote_branch_head", side_effect=lambda branch: next(
                (head for role, head in HEADS.items() if branch.endswith("/" + role)), None)), \
             patch.object(MOD, "_remote_json", side_effect=lambda path, head: reports[(path, head)]), \
             patch.object(MOD, "_one_path_child", return_value=True), \
             patch.object(MOD, "_schema_valid", return_value=True), \
             patch.object(MOD, "_trusted_workflow_status", return_value=False):
            errors = MOD._remote_production_worker_errors(verification, state())
        self.assertEqual(len(errors), 12)
        self.assertTrue(all("trusted HMAC-validating branch-worker status" in error for error in errors))

    def test_remote_liveness_requires_server_status_inside_frozen_window_and_exact_rederivation(self):
        verification, _ = reports_and_verification()
        start, deadline, observed = "2026-08-23T00:00:00Z", "2026-08-23T01:00:00Z", "2026-08-23T00:30:00Z"
        lanes = [{"lane_id": role, "branch": f"ps/work/{COHORT}/{role}",
                  "path": f"reports/{COHORT}/{role}.json", "expected_window_start_utc": start,
                  "deadline_utc": deadline} for role in MOD.WORKERS]
        contract = {"lanes": lanes}
        expected = []
        for role in sorted(MOD.WORKERS):
            expected.append({"lane_id": role, "task_id": None, "associated_chat_ref": None,
                             "expected_window_start": start, "expected_window_end": deadline,
                             "observation_time": observed, "receipt_status": "RUN_OBSERVED",
                             "task_state": "TASK_STATE_UNKNOWN", "observation_source": "GITHUB_RECEIPT_MONITOR",
                             "receipt_ref": f"ps/work/{COHORT}/{role}:reports/{COHORT}/{role}.json",
                             "lateness_seconds": 0,
                             "notes": f"trusted branch-worker status id={role} created_at={observed}"})
        verification["lane_liveness_observations"] = expected
        with patch.object(MOD, "_remote_json", return_value=("liveness-blob", contract)), \
             patch.object(MOD, "_schema_valid", return_value=True), \
             patch.object(MOD, "_trusted_workflow_status_row", side_effect=lambda head, *args, **kwargs: {"id": next(role for role, value in HEADS.items() if value == head), "created_at": observed}):
            self.assertEqual(MOD._remote_production_liveness_errors(verification, state()), [])

    def test_remote_liveness_rejects_status_outside_frozen_window(self):
        verification, _ = reports_and_verification()
        contract = {"lanes": [{"lane_id": role, "branch": f"ps/work/{COHORT}/{role}",
                                "path": f"reports/{COHORT}/{role}.json",
                                "expected_window_start_utc": "2026-08-23T00:00:00Z",
                                "deadline_utc": "2026-08-23T01:00:00Z"} for role in MOD.WORKERS]}
        with patch.object(MOD, "_remote_json", return_value=("liveness-blob", contract)), \
             patch.object(MOD, "_schema_valid", return_value=True), \
             patch.object(MOD, "_trusted_workflow_status_row", return_value={"id": 7, "created_at": "2026-08-23T01:00:01Z"}):
            errors = MOD._remote_production_liveness_errors(verification, state())
        self.assertEqual(errors, ["EXT01 trusted branch-worker status is outside frozen production window"])

    def test_root11_clean_terminal_accepts_only_complete_remote_chain(self):
        old = state()
        pointer = {"candidate_cohort_id": COHORT, "generation_head_sha": GENERATION}
        verification = {"verdict": "VERIFIED_COMPLETE", "calibration_pass": True, "liveness_complete": True,
                        "safe_report_refs": [{}] * 12, "quarantined_report_refs": [], "missing_workers": []}
        integration = {"verification_head_sha": "v" * 40, "calibration_pass": True}
        trusted = types.SimpleNamespace(generation_check=lambda value: [],
                                        verification_semantic_errors=lambda value, old: [],
                                        integration_semantic_errors=lambda integration, verification, old: [])
        def remote_json(path, ref):
            if path == f"staging/{COHORT}.json": return "p" * 40, pointer
            if path == f"verification/{COHORT}.json": return "q" * 40, verification
            if path == f"integration/{COHORT}.json": return "r" * 40, integration
            raise AssertionError((path, ref))
        branches = {old["verifier_branch"]: "v" * 40, old["integrator_branch"]: "i" * 40}
        with patch.object(MOD, "_remote_json", side_effect=remote_json), \
             patch.object(MOD, "_remote_branch_head", side_effect=lambda branch: branches[branch]), \
             patch.object(MOD, "_one_path_child", return_value=True), \
             patch.object(MOD, "_schema_valid", return_value=True), \
             patch.object(MOD, "_trusted_v25_module", return_value=trusted), \
             patch.object(MOD, "_remote_production_worker_errors", return_value=[]), \
             patch.object(MOD, "_remote_production_liveness_errors", return_value=[]), \
             patch.object(MOD, "_trusted_workflow_status", return_value=True):
            terminal = MOD._root11_clean_terminal(old)
        self.assertEqual(terminal["verification_head"], "v" * 40)
        self.assertEqual(terminal["integration_head"], "i" * 40)

    def test_root11_clean_terminal_fails_closed_when_remote_worker_rederivation_fails(self):
        old = state()
        pointer = {"candidate_cohort_id": COHORT, "generation_head_sha": GENERATION}
        verification = {"verdict": "VERIFIED_COMPLETE", "calibration_pass": True, "liveness_complete": True,
                        "safe_report_refs": [{}] * 12, "quarantined_report_refs": [], "missing_workers": []}
        integration = {"verification_head_sha": "v" * 40, "calibration_pass": True}
        trusted = types.SimpleNamespace(generation_check=lambda value: [],
                                        verification_semantic_errors=lambda value, old: [],
                                        integration_semantic_errors=lambda integration, verification, old: [])
        def remote_json(path, ref):
            if path == f"staging/{COHORT}.json": return "p" * 40, pointer
            if path == f"verification/{COHORT}.json": return "q" * 40, verification
            if path == f"integration/{COHORT}.json": return "r" * 40, integration
            raise AssertionError((path, ref))
        branches = {old["verifier_branch"]: "v" * 40, old["integrator_branch"]: "i" * 40}
        with patch.object(MOD, "_remote_json", side_effect=remote_json), \
             patch.object(MOD, "_remote_branch_head", side_effect=lambda branch: branches[branch]), \
             patch.object(MOD, "_one_path_child", return_value=True), \
             patch.object(MOD, "_schema_valid", return_value=True), \
             patch.object(MOD, "_trusted_v25_module", return_value=trusted), \
             patch.object(MOD, "_remote_production_worker_errors", return_value=["MF01 HMAC invalid"]), \
             patch.object(MOD, "_remote_production_liveness_errors", return_value=[]), \
             patch.object(MOD, "_trusted_workflow_status", return_value=True):
            self.assertIsNone(MOD._root11_clean_terminal(old))

    def test_exact_root11_generic_gate_does_not_fall_through_for_gen12_or_unproven_clean_parent(self):
        gen12 = {"generation_seq": 12}
        with patch.object(MOD, "_state_blob", return_value=(0, "x" * 40)), \
             patch.object(MOD, "_gen12_terminal_chain_valid", return_value=False):
            self.assertFalse(MOD.exact_root11_successor_promotion("repo", "base", gen12, set()))
        gen13 = {"generation_seq": 13}
        with patch.object(MOD, "_state_blob", return_value=(0, "x" * 40)), \
             patch.object(MOD, "_root11_clean_terminal", return_value=None):
            self.assertFalse(MOD.exact_root11_successor_promotion("repo", "base", gen13, set()))

    def test_root11_clean_credit_streak_is_capped_and_only_two_enables_fresh(self):
        self.assertEqual(MOD._root11_next_streak(0, 1), 1)
        self.assertEqual(MOD._root11_next_streak(1, 1), 2)
        self.assertEqual(MOD._root11_next_streak(2, 1), 2)
        self.assertFalse(MOD._root11_next_streak(0, 1) == 2)
        self.assertTrue(MOD._root11_next_streak(1, 1) == 2)


if __name__ == "__main__":
    unittest.main()
