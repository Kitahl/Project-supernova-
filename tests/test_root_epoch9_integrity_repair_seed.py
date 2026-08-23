import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "config" / "root_epoch9_integrity_repair_seed_v25.json"
SCRIPT = ROOT / "scripts" / "reconcile_root_epoch9_integrity_repair_seed.py"
WORKFLOW = ROOT / ".github" / "workflows" / "supernova-root-epoch9-integrity-repair-seed.yml"


class RootEpoch9IntegrityRepairSeedTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.script = SCRIPT.read_text(encoding="utf-8")
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_seed_is_one_shot_epoch8_to_epoch9_and_zero_credit(self):
        p = self.policy
        self.assertEqual(p["schema_version"], "PS-ROOT-EPOCH9-INTEGRITY-REPAIR-SEED-2.5-1")
        self.assertEqual(p["required_current_root_epoch"], 8)
        self.assertEqual(p["target_root_epoch"], 9)
        self.assertEqual(p["required_active_cohort"], "CAL-BR-011-v25-27955ce6")
        self.assertEqual(p["required_generation_head"], "3bb1425d18dbff2f83d69b0738c7151bf4a47355")
        self.assertEqual(p["required_verifier_head"], "a58939b12e66ab4604b8f2e5f2033bd70d5c0bd3")
        self.assertEqual(p["required_verifier_verdict"], "INVALID")
        self.assertFalse(p["required_verifier_calibration_pass"])
        self.assertEqual(p["calibration_streak_required"], 0)
        self.assertFalse(p["fresh_allowed_globally_required"])
        self.assertEqual(p["seed_self_modification"], "FORBIDDEN")
        self.assertEqual(p["failure_semantics"], "FAIL_CLOSED")

    def test_seed_closes_exact_integrity_repair_surface(self):
        p = self.policy
        allowed = set(p["allowed_root_candidate_paths"])
        required = set(p["required_root_candidate_paths"])
        self.assertEqual(allowed, required)
        for path in (
            "branch/CONFIG.json",
            "schemas/branch_report.schema.json",
            "schemas/mastermind_mm04_replay_payload.schema.json",
            "scripts/strict_json.py",
            "scripts/validate_bus.py",
            "scripts/validate_branch_bus_v251.py",
            "scripts/reconcile_open_prs.py",
            "scripts/liveness_contract_guard.py",
            ".github/workflows/supernova-pr-target-admission.yml",
            ".github/workflows/supernova-comment-admission.yml",
            ".github/workflows/supernova-open-pr-reconciler.yml",
            "tests/test_strict_json_contract.py",
            "tests/test_gen11_zero_credit_terminal_transition.py",
            "config/root_epoch9_integrity_repair_epoch_v25.json",
        ):
            self.assertIn(path, required)
        for prefix in ("state/", "control/", "assignments/", "reports/", "verification/", "integration/", "history/", "runtime/", "benchmark/", "research/"):
            self.assertIn(prefix, p["forbidden_candidate_prefixes"])

    def test_seed_requires_terminal_gen11_evidence_and_strict_candidate_checks(self):
        for needle in (
            "terminal MM06 receipt",
            "12 SAFE / 0 quarantine / 0 missing",
            "GEN11-EXACT-G-LIVENESS-NONCLEAN",
            "PS-MF04-NONFINITEJSON-001",
            "MM03-RPT-TYPED-MISSING-006",
            "MM04-T0-MM04-ROLE-NONVACUITY-SCHEMA-001",
            "MM04-T0-PRIVILEGED-VALIDATOR-ENV-ASSERTION-001",
            "strict JSON",
            "exact_gen11_zero_credit_terminal_parent",
            "minimum_worker_liveness_window_minutes",
        ):
            self.assertIn(needle, self.script)
        self.assertIn("parse_constant=_reject_constant", self.script)
        self.assertIn("object_pairs_hook=_unique_pairs", self.script)
        self.assertIn("allow_nan=False", self.script)

    def test_privileged_seed_workflow_is_separated_and_environment_bound(self):
        text = self.workflow
        candidate, trusted = text.split("  trusted-seed:", 1)
        self.assertIn("pull_request_target:", text)
        self.assertNotIn("workflow_dispatch:", text)
        self.assertNotIn("statuses: write", candidate)
        self.assertIn('GITHUB_TOKEN: ""', candidate)
        self.assertIn("persist-credentials: false", candidate)
        self.assertIn("runs-on: ubuntu-24.04", candidate)
        self.assertIn("python-version: '3.13.15'", candidate)
        self.assertIn("assert_validator_environment.py", candidate)
        self.assertIn("needs: candidate-diagnostics", trusted)
        self.assertIn("statuses: write", trusted)
        self.assertNotIn("contents: write", trusted)
        self.assertIn("runs-on: ubuntu-24.04", trusted)
        self.assertIn("python-version: '3.13.15'", trusted)
        self.assertIn("assert_validator_environment.py", trusted)
        self.assertIn("scripts/reconcile_root_epoch9_integrity_repair_seed.py", trusted)


if __name__ == "__main__":
    unittest.main()
