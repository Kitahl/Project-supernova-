import copy
import json
import pathlib
import unittest
from unittest.mock import call, patch

from jsonschema import Draft202012Validator

from scripts import reconcile_open_prs as MOD


ROOT = pathlib.Path(__file__).resolve().parents[1]
COHORT = "CAL-BR-013-v25-root11"
G = "a" * 40
BASE = "b" * 40
VH = "c" * 40
VB = "d" * 40
IH = "e" * 40
IB = "f" * 40


def root11_receipt():
    return {
        "schema_version": MOD.ROOT11_CONSOLIDATION_SCHEMA,
        "task_network_plan_id": MOD.PLAN,
        "cohort_id": COHORT,
        "consolidation_id": "PS-BIL00-CAL-BR-013-ROOT11",
        "generation_head_sha": G,
        "verification_branch": f"ps/verify/{COHORT}",
        "verification_head_sha": VH,
        "integration_branch": f"ps/integrate/{COHORT}",
        "integration_head_sha": IH,
        "expected_main_head": BASE,
        "safe_history_refs": [
            f"generation-head:{G}",
            f"verification/{COHORT}.json@{VH}#{VB}",
            f"integration/{COHORT}.json@{IH}#{IB}",
            f"github-status:{G}:supernova/active-static-control=success",
            f"github-status:{VH}:supernova/branch-verify=success",
            f"github-status:{VH}:supernova/branch-report-admission=success",
            f"github-status:{IH}:supernova/branch-integrate=success",
        ],
        "next_state_path": "state/CURRENT.json",
        "calibration_counted": True,
        "repo_policy_observed_protected": True,
        "repo_policy_source_bound_contexts_verified": True,
        "static_control_context": {
            "context": "supernova/active-static-control",
            "status": "PASS",
            "generation_head_sha": G,
        },
        "report_admission_context": {
            "context": "supernova/branch-report-admission",
            "status": "PASS",
            "verification_head_sha": VH,
        },
        "transition_admission_context": {
            "context": "supernova/branch-transition-admission",
            "required_on_exact_consolidation_head": True,
            "expected_main_head": BASE,
        },
        "benchmark_actions": [],
        "next_action": "Promote the admitted successor under exact main CAS.",
    }


class Root11ConsolidationEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / "schemas/branch_consolidation.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema)

    def assertValid(self, value):
        self.assertEqual(list(self.validator.iter_errors(value)), [])

    def assertInvalid(self, value):
        self.assertTrue(list(self.validator.iter_errors(value)))

    def test_historical_legacy_receipt_remains_schema_valid(self):
        legacy = json.loads((ROOT / "history/CAL-BR-010-v25-fe539297-r2/CONSOLIDATION.json").read_text(encoding="utf-8"))
        self.assertNotIn("schema_version", legacy)
        self.assertValid(legacy)

    def test_root11_schema_alternative_accepts_only_closed_root11_contexts(self):
        receipt = root11_receipt()
        self.assertValid(receipt)
        mutations = []
        for field, legacy_context in (
            ("static_control_context", "supernova/static-control"),
            ("report_admission_context", "supernova/report-admission"),
            ("transition_admission_context", "supernova/transition-admission"),
        ):
            changed = copy.deepcopy(receipt)
            changed[field]["context"] = legacy_context
            mutations.append((field, changed))
        missing_generation_binding = copy.deepcopy(receipt)
        del missing_generation_binding["static_control_context"]["generation_head_sha"]
        mutations.append(("missing generation binding", missing_generation_binding))
        extra_transition_field = copy.deepcopy(receipt)
        extra_transition_field["transition_admission_context"]["unbound"] = True
        mutations.append(("open transition object", extra_transition_field))
        for label, changed in mutations:
            with self.subTest(label=label):
                self.assertInvalid(changed)

    def test_exact_evidence_rejects_each_moved_head_blob_status_or_extra_ref(self):
        old = {"active_cohort_id": COHORT, "generation_head_sha": G}
        terminal = {
            "verification_head": VH,
            "verification_blob": VB,
            "integration_head": IH,
            "integration_blob": IB,
        }
        receipt = root11_receipt()
        self.assertTrue(MOD._root11_consolidation_evidence_matches(receipt, old, BASE, terminal))
        mutations = []
        wrong_static = copy.deepcopy(receipt)
        wrong_static["static_control_context"]["generation_head_sha"] = "0" * 40
        mutations.append(("static G", wrong_static, terminal))
        wrong_report = copy.deepcopy(receipt)
        wrong_report["report_admission_context"]["verification_head_sha"] = "0" * 40
        mutations.append(("report VH", wrong_report, terminal))
        wrong_transition = copy.deepcopy(receipt)
        wrong_transition["transition_admission_context"]["expected_main_head"] = "0" * 40
        mutations.append(("transition base", wrong_transition, terminal))
        wrong_status = copy.deepcopy(receipt)
        wrong_status["safe_history_refs"][5] = f"github-status:{VH}:supernova/report-admission=success"
        mutations.append(("status context", wrong_status, terminal))
        extra_ref = copy.deepcopy(receipt)
        extra_ref["safe_history_refs"].append("issue:#unbound")
        mutations.append(("extra ref", extra_ref, terminal))
        moved_blob = copy.deepcopy(terminal)
        moved_blob["integration_blob"] = "0" * 40
        mutations.append(("integration blob", receipt, moved_blob))
        for label, changed_receipt, changed_terminal in mutations:
            with self.subTest(label=label):
                self.assertFalse(MOD._root11_consolidation_evidence_matches(changed_receipt, old, BASE, changed_terminal))

    def test_gen12_root11_rebinding_returns_exact_blobs_only_with_trusted_statuses(self):
        old = {"active_cohort_id": MOD.GEN12_COHORT, "generation_head_sha": MOD.GEN12_G}
        branches = {
            f"ps/verify/{MOD.GEN12_COHORT}": VH,
            f"ps/integrate/{MOD.GEN12_COHORT}": IH,
        }

        def remote_json(path, head):
            if path.startswith("verification/"):
                return VB, {"verdict": "INCOMPLETE"}
            if path.startswith("integration/"):
                return IB, {"calibration_pass": False}
            raise AssertionError((path, head))

        with patch.object(MOD, "_gen12_terminal_chain_valid", return_value=True), \
             patch.object(MOD, "_remote_branch_head", side_effect=lambda branch: branches[branch]), \
             patch.object(MOD, "_remote_json", side_effect=remote_json), \
             patch.object(MOD, "_trusted_workflow_status", return_value=True) as trusted:
            terminal = MOD._root11_gen12_terminal(old)
        self.assertEqual(terminal["verification_blob"], VB)
        self.assertEqual(terminal["integration_blob"], IB)
        trusted.assert_has_calls([
            call(MOD.GEN12_G, "supernova/active-static-control", MOD.REST_RECONCILER_WORKFLOW, {"schedule", "push", "repository_dispatch"}),
            call(VH, "supernova/branch-verify", MOD.BRANCH_RECONCILER_WORKFLOW, {"schedule", "push", "repository_dispatch"}),
            call(VH, "supernova/branch-report-admission", MOD.REST_RECONCILER_WORKFLOW, {"schedule", "push", "repository_dispatch"}),
            call(IH, "supernova/branch-integrate", MOD.BRANCH_RECONCILER_WORKFLOW, {"schedule", "push", "repository_dispatch"}),
        ])


if __name__ == "__main__":
    unittest.main()
