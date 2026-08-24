import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reconcile_ruleset_attestation.py"
WORKFLOW = ROOT / ".github" / "workflows" / "supernova-pr-target-admission.yml"
CONTROL = ROOT / "config" / "countable_control_set_v25.json"
STATUS_APP_INTEGRATION_ID = 4697060


def load_module():
    spec = importlib.util.spec_from_file_location("ruleset_attestation_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RulesetStatusAttestationTests(unittest.TestCase):
    @staticmethod
    def good_rules():
        return [
            {"type": "pull_request"},
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {
                "type": "required_status_checks",
                "parameters": {
                    "strict_required_status_checks_policy": True,
                    "required_status_checks": [
                        {"context": "supernova/static-control", "integration_id": STATUS_APP_INTEGRATION_ID},
                        {"context": "supernova/report-admission", "integration_id": STATUS_APP_INTEGRATION_ID},
                        {"context": "supernova/transition-admission", "integration_id": STATUS_APP_INTEGRATION_ID},
                    ]
                },
            },
        ]

    def test_positive_effective_rules_close_all_required_obligations(self):
        mod = load_module()
        result = mod.evaluate_rules(self.good_rules())
        for key in (
            "pr_required",
            "deletion_blocked",
            "non_fast_forward_blocked",
            "status_app",
            "static_bound",
            "report_bound",
            "transition_bound",
            "spoof_resistant",
            "strict_up_to_date",
        ):
            self.assertTrue(result[key], key)

    def test_wrong_source_fails_only_the_bound_claims_and_aggregate(self):
        mod = load_module()
        rules = self.good_rules()
        rows = rules[-1]["parameters"]["required_status_checks"]
        rows[1]["integration_id"] = -1
        result = mod.evaluate_rules(rules)
        self.assertTrue(result["static_bound"])
        self.assertFalse(result["report_bound"])
        self.assertTrue(result["transition_bound"])
        self.assertFalse(result["spoof_resistant"])

    def test_non_strict_status_policy_fails_cas_gate(self):
        mod=load_module();rules=self.good_rules();rules[-1]["parameters"]["strict_required_status_checks_policy"]=False
        result=mod.evaluate_rules(rules)
        self.assertFalse(result["strict_up_to_date"]);self.assertFalse(result["spoof_resistant"])

    def test_missing_or_wrong_rules_fail_closed(self):
        mod = load_module()
        result = mod.evaluate_rules(
            [{"type": "required_status_checks", "parameters": {"required_status_checks": []}}],
        )
        self.assertFalse(result["pr_required"])
        self.assertFalse(result["deletion_blocked"])
        self.assertFalse(result["non_fast_forward_blocked"])
        self.assertFalse(result["status_app"])
        self.assertFalse(result["spoof_resistant"])

    def test_existing_trusted_pr_target_workflow_invokes_accepted_main_attestor(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pull_request_target:", text)
        self.assertIn("git clone --filter=blob:none", text)
        self.assertIn("cd trusted && python scripts/reconcile_open_prs.py", text)
        self.assertIn("cd trusted && python scripts/reconcile_ruleset_attestation.py", text)
        self.assertNotIn("actions/checkout@", text)

    def test_attestor_assets_are_frozen_for_countable_cohorts(self):
        paths = set(json.loads(CONTROL.read_text(encoding="utf-8"))["required_control_paths"])
        self.assertIn("scripts/reconcile_ruleset_attestation.py", paths)
        self.assertIn("tests/test_ruleset_status_attestation.py", paths)


if __name__ == "__main__":
    unittest.main()
