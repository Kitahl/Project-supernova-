import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class SourceBoundRepoPolicyTests(unittest.TestCase):
    def test_state_schema_admits_source_bound_status(self):
        schema = json.loads((ROOT / "schemas/state.schema.json").read_text(encoding="utf-8"))
        allowed = schema["properties"]["repo_policy_status"]["enum"]
        self.assertIn("VERIFIED_PROTECTED_SOURCE_BOUND", allowed)

    def test_canonical_validator_requires_source_bound_status_for_countable_and_fresh(self):
        text = (ROOT / "scripts/validate_bus.py").read_text(encoding="utf-8")
        self.assertIn("fresh enabled while source-bound repo policy unverified", text)
        self.assertIn("countable calibration while source-bound repo policy unverified", text)
        self.assertGreaterEqual(text.count("VERIFIED_PROTECTED_SOURCE_BOUND"), 2)

    def test_repo_policy_binds_three_contexts_to_actions_principal(self):
        policy = json.loads((ROOT / "config/repo_policy.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["required_main_status_contexts"], [
            "supernova/static-control",
            "supernova/report-admission",
            "supernova/transition-admission",
        ])
        self.assertEqual(policy["required_status_source_creator_logins"], ["github-actions[bot]"])
        self.assertTrue(policy["operational_source_binding_proof_required"])


if __name__ == "__main__":
    unittest.main()
