import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "supernova-ruleset-attestation.yml"
CONTROL = ROOT / "config" / "countable_control_set_v25.json"


class RulesetAttestationWorkflowTests(unittest.TestCase):
    def test_attestation_is_trusted_target_read_path_not_status_authority(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pull_request_target:", text)
        self.assertNotIn("workflow_dispatch:", text)
        self.assertNotIn("statuses: write", text)
        self.assertNotIn("contents: write", text)
        self.assertIn("issues: write", text)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", text)
        self.assertIn("github.event.pull_request.user.login == github.repository_owner", text)

    def test_attestation_queries_effective_rules_rulesets_and_actions_app(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("/rules/branches/main", text)
        self.assertIn("/rulesets/", text)
        self.assertIn("https://api.github.com/apps/github-actions", text)
        self.assertIn("SUPERNOVA_RULESET_ATTESTATION_V25_BEGIN", text)
        self.assertIn("PS-RULESET-ATTESTATION-1", text)

    def test_attestation_assets_are_frozen_for_countable_cohorts(self):
        control = json.loads(CONTROL.read_text(encoding="utf-8"))
        paths = set(control["required_control_paths"])
        self.assertIn(".github/workflows/supernova-ruleset-attestation.yml", paths)
        self.assertIn("tests/test_ruleset_attestation_workflow.py", paths)


if __name__ == "__main__":
    unittest.main()
