import pathlib
import unittest
from unittest import mock

from scripts import scheduler_admission_guard as guard


HEX = "a" * 40


class SchedulerActivePhaseValidationTests(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(".")
        self.manifest = {
            "protocol_version": "2.5",
            "task_network_plan_id": "plan",
            "candidate_nonce": "nonce",
            "cohort_id": "cohort",
            "generation_root_sha": "b" * 40,
            "tasks": [{"role_id": "MM06", "challenge_occurrences_utc": ["occurrence"]}],
        }
        self.source = {
            "protocol_version": "2.5",
            "task_network_plan_id": "plan",
            "candidate_nonce": "nonce",
            "cohort_id": "cohort",
            "generation_root_sha": "b" * 40,
            "generation_head_sha": "c" * 40,
            "scheduler_manifest_git_identity": HEX,
            "preactivation_results": [
                {"role_id": role} for role in sorted(guard.PREACTIVATION_ROLES)
            ],
            "partition_exhaustive_verified": True,
            "admission_verdict": "SCHEDULER_ADMISSION_PASS",
            "mm06_challenge_occurrence_utc": "occurrence",
        }

    def test_durable_active_validation_allows_production_to_advance(self):
        """Active validation must authenticate the source without requiring refs == G."""
        with (
            mock.patch.object(guard, "schema_errors", return_value=[]),
            mock.patch.object(guard, "_scan_public"),
            mock.patch.object(guard, "validate_preactivation_sources", return_value=[]) as sources,
            mock.patch.object(
                guard,
                "validate_production_ref_fence",
                side_effect=AssertionError("active production refs have legitimately advanced"),
            ) as fence,
        ):
            errors = guard.validate_mm06_scheduler_admission(
                self.root,
                self.manifest,
                self.source,
                observed_manifest_blob=HEX,
            )
        self.assertEqual(errors, [])
        sources.assert_called_once()
        fence.assert_not_called()

    def test_transition_validation_retains_exact_generation_fence(self):
        def run_fenced_validation(root, manifest, generation_head, callback):
            self.assertEqual(generation_head, "c" * 40)
            return callback()

        with (
            mock.patch.object(guard, "schema_errors", return_value=[]),
            mock.patch.object(guard, "_scan_public"),
            mock.patch.object(guard, "validate_preactivation_sources", return_value=[]) as sources,
            mock.patch.object(
                guard,
                "validate_production_ref_fence",
                side_effect=run_fenced_validation,
            ) as fence,
        ):
            errors = guard.validate_mm06_scheduler_admission(
                self.root,
                self.manifest,
                self.source,
                observed_manifest_blob=HEX,
                require_inactive_production_fence=True,
            )
        self.assertEqual(errors, [])
        fence.assert_called_once()
        sources.assert_called_once()

    def test_create_and_promotion_callers_request_transition_fence(self):
        source = pathlib.Path("scripts/reconcile_open_prs.py").read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count("require_inactive_production_fence=True"), 3)
        self.assertIn("_remote_inactive_production_snapshot(manifest,G)!=production_snapshot", source)


if __name__ == "__main__":
    unittest.main()
