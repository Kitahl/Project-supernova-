import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("scheduler_completion_frontier_guard", ROOT / "scripts/scheduler_admission_guard.py")
GUARD = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(GUARD)


def write_json(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


class SchedulerCompletionFrontierConstructionTests(unittest.TestCase):
    def test_schema_valid_candidate_passes_cli_and_early_frontier_fails(self):
        cohort = "CAL-BR-013-v25-completion-frontier"
        nonce = "a" * 64
        generation_root = "b" * 40
        production_not_before = "2026-01-15T08:04:30Z"
        admission_cutoff = "2026-01-15T08:04:00Z"
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            for relative in (
                "config/task_registry_v25.json",
                "config/worker_auth.json",
                "config/scheduler_attestation_authority_v25.json",
                "schemas/control.schema.json",
                "schemas/assignment.schema.json",
                "schemas/cohort_liveness_contract.schema.json",
                "schemas/scheduler_manifest.schema.json",
            ):
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, destination)

            control = {
                "control_manifest_id": "CTRL-" + cohort,
                "task_network_plan_id": GUARD.PLAN,
                "cohort_id": cohort,
                "protocol_version": "2.5",
                "generation_seq": 13,
                "parent_state_git_identity": "c" * 40,
                "control_release_commit_sha": generation_root,
                "control_release_tree_sha": "d" * 40,
                "expected_base_head": generation_root,
                "generation_root_sha": generation_root,
                "candidate_nonce": nonce,
                "scheduler_manifest_path": f"scheduler/{cohort}.json",
                "scheduler_admission_required": True,
                "required_control_paths": [f"frozen/path/{index}" for index in range(20)],
                "purpose": "Constructive Root11 completion-frontier proof",
                "calibration_countable": True,
                "fresh_allowed": False,
                "repo_policy_required": True,
                "worker_auth_scheme": "PS-HMAC-SHA256-CANONICAL-REPORT-2",
                "deep_research_owner": "BIL00",
            }
            control_path = root / f"control/{cohort}.json"
            write_json(control_path, control)
            control_blob = GUARD.git_blob_sha(control_path)

            registry = json.loads((root / "config/task_registry_v25.json").read_text(encoding="utf-8"))
            registry_rows = {row["role_id"]: row for row in registry["tasks"]}
            workers = {}
            for role in GUARD.WORKERS:
                workers[role] = {
                    "worker_branch": f"ps/work/{cohort}/{role}",
                    "fresh_allowed": False,
                    "role": "Replay evidence",
                    "goal": "Produce one deterministic replay-only report",
                    "target_program": registry_rows[role]["target_program"],
                    "visibility_token": "1" * 32,
                    "opaque_evidence_ids": [],
                    "private_manifest_id": None,
                    "private_manifest_git_identity": None,
                    "constraints": ["SAFE_REPLAY_ONLY"],
                }
            assignment = {
                "task_network_plan_id": GUARD.PLAN,
                "cohort_id": cohort,
                "assignment_id": "ASSIGN-" + cohort,
                "generation_seq": 13,
                "parent_state_git_identity": "c" * 40,
                "control_manifest_id": control["control_manifest_id"],
                "control_manifest_path": f"control/{cohort}.json",
                "control_manifest_git_identity": control_blob,
                "network_checkpoint_id": "e" * 64,
                "runtime_state_id": "f" * 64,
                "network_mode": "GITHUB_BRANCH_CALIBRATION",
                "phase": "T0_COUNTABLE_REPLAY_COHORT_1",
                "purpose": "Constructive Root11 completion-frontier proof",
                "short_test": False,
                "calibration_countable": True,
                "repo_policy_required": True,
                "benchmark_program": None,
                "benchmark_suite_id": None,
                "candidate_nonce": nonce,
                "generation_branch": f"ps/gen/{cohort}",
                "generation_root_sha": generation_root,
                "workers": workers,
                "verifier_branch": f"ps/verify/{cohort}",
                "integrator_branch": f"ps/integrate/{cohort}",
                "consolidation_branch": f"ps/consolidate/{cohort}",
                "sealed_slots": [],
            }
            assignment_path = root / f"assignments/{cohort}.json"
            write_json(assignment_path, assignment)
            assignment_blob = GUARD.git_blob_sha(assignment_path)

            lane_rows = []
            for role in GUARD.WORKERS:
                registry_row = registry_rows[role]
                schedule = f'TZID=America/Vancouver;FREQ=HOURLY;BYMINUTE={registry_row["minute"]:02d}'
                first, _ = GUARD.derive_hourly_occurrences(schedule, registry_row["minute"], production_not_before)
                lane_rows.append({
                    "lane_id": role,
                    "branch": f"ps/work/{cohort}/{role}",
                    "path": f"reports/{cohort}/{role}.json",
                    "expected_window_start_utc": GUARD._utc_z(first),
                    "deadline_utc": GUARD._utc_z(first + GUARD.timedelta(seconds=4260)),
                    "eligible_before_deadline": True,
                })
            liveness = {
                "schema_version": "PS-COHORT-LIVENESS-2.5-2",
                "protocol_version": "2.5",
                "task_network_plan_id": GUARD.PLAN,
                "cohort_id": cohort,
                "candidate_nonce": nonce,
                "generation_seq": 13,
                "generation_root_sha": generation_root,
                "control_manifest_id": control["control_manifest_id"],
                "control_manifest_git_identity": control_blob,
                "assignment_id": assignment["assignment_id"],
                "assignment_git_identity": assignment_blob,
                "lanes": lane_rows,
            }
            liveness_path = root / f"liveness/{cohort}.json"
            write_json(liveness_path, liveness)

            task_schedules = {
                role: {
                    "normalized_schedule": f'TZID=America/Vancouver;FREQ=HOURLY;BYMINUTE={row["minute"]:02d}'
                }
                for role, row in registry_rows.items()
            }
            lane_by_role = {row["lane_id"]: row for row in lane_rows}
            occurrences, _ = GUARD.derive_countable_occurrences(
                task_schedules, registry_rows, lane_by_role, production_not_before
            )
            self.assertEqual(GUARD._utc_z(occurrences["MM06"][0]), "2026-01-15T09:35:00Z")
            self.assertEqual(GUARD._utc_z(occurrences["MF06"][0]), "2026-01-15T10:45:00Z")
            self.assertEqual(GUARD._utc_z(occurrences["BIL00"][0]), "2026-01-15T10:58:00Z")

            commitments = json.loads((root / "config/worker_auth.json").read_text(encoding="utf-8"))["commitments"]
            tasks = []
            for role in GUARD.ROLES:
                registry_row = registry_rows[role]
                first, second = occurrences[role]
                if role in GUARD.WORKERS:
                    production_branch = lane_by_role[role]["branch"]
                    production_path = lane_by_role[role]["path"]
                    worker_commitment = commitments[role]
                else:
                    production_branch = f"ps/{role.lower()}/{cohort}"
                    production_path = f"receipts/{cohort}/{role}.json"
                    worker_commitment = None
                tasks.append({
                    "role_id": role,
                    "canonical_title": registry_row["title"],
                    "scheduler_task_id": registry_row["scheduler_task_id"],
                    "enabled": True,
                    "behavioral_config_sha256": "2" * 64,
                    "prompt_sha256": "3" * 64,
                    "timing_mode": "exact_schedule",
                    "default_timezone": "America/Vancouver",
                    "normalized_schedule": task_schedules[role]["normalized_schedule"],
                    "normalized_first_production_utc": GUARD._utc_z(first),
                    "normalized_second_production_utc": GUARD._utc_z(second),
                    "production_branch": production_branch,
                    "production_path": production_path,
                    "execution_mode": "SAFE_REPLAY_ONLY",
                    "preactivation_inactive_result": "PREACTIVATION_WAIT",
                    "worker_auth_commitment": worker_commitment,
                    "preactivation_branch": f"ps/preactivate/{cohort}/{role}",
                    "preactivation_path": f"preactivation/{cohort}/{role}.json",
                    "challenge_occurrences_utc": [GUARD._utc_z(first - GUARD.timedelta(hours=4))],
                })
            manifest = {
                "schema_version": "PS-SCHEDULER-MANIFEST-2.5-2",
                "protocol_version": "2.5",
                "task_network_plan_id": GUARD.PLAN,
                "candidate_nonce": nonce,
                "cohort_id": cohort,
                "generation_root_sha": generation_root,
                "generation_branch": assignment["generation_branch"],
                "control_manifest_id": control["control_manifest_id"],
                "control_manifest_git_identity": control_blob,
                "assignment_id": assignment["assignment_id"],
                "assignment_git_identity": assignment_blob,
                "liveness_git_identity": GUARD.git_blob_sha(liveness_path),
                "runtime_state_id": assignment["runtime_state_id"],
                "task_registry_git_identity": GUARD.git_blob_sha(root / "config/task_registry_v25.json"),
                "timezone": "America/Vancouver",
                "scheduler_cadence_seconds": 3600,
                "max_attempt_duration_seconds": 600,
                "scheduler_jitter_budget_seconds": 60,
                "production_not_before_utc": production_not_before,
                "admission_cutoff_utc": admission_cutoff,
                "tasks": tasks,
                "behavioral_config_projection": list(GUARD.BEHAVIORAL_PROJECTION),
                "mutable_runtime_fields_excluded": sorted(GUARD.MUTABLE_RUNTIME_FIELDS),
                "active_cohort_constructive_repair": "FORBIDDEN",
                "stage_admit_promote": "THREE_DISTINCT_TRANSACTIONS",
                "raw_auth_material_publication": "FORBIDDEN",
            }
            manifest_path = root / f"scheduler/{cohort}.json"
            write_json(manifest_path, manifest)

            for schema_path, value in (
                ("schemas/control.schema.json", control),
                ("schemas/assignment.schema.json", assignment),
                ("schemas/cohort_liveness_contract.schema.json", liveness),
                ("schemas/scheduler_manifest.schema.json", manifest),
            ):
                self.assertEqual(GUARD.schema_errors(root, schema_path, value), [], schema_path)

            command = [
                sys.executable, str(ROOT / "scripts/scheduler_admission_guard.py"),
                "--root", str(root), "--cohort", cohort, "--no-admission",
            ]
            passed = subprocess.run(command, text=True, capture_output=True, check=False, timeout=30)
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
            self.assertEqual(passed.stdout.strip(), "SCHEDULER ADMISSION PASS")

            mf06 = next(row for row in manifest["tasks"] if row["role_id"] == "MF06")
            mf06["normalized_first_production_utc"] = "2026-01-15T09:45:00Z"
            mf06["normalized_second_production_utc"] = "2026-01-15T10:45:00Z"
            write_json(manifest_path, manifest)
            rejected = subprocess.run(command, text=True, capture_output=True, check=False, timeout=30)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("post-completion MF06", rejected.stdout)

            mf06["normalized_first_production_utc"] = "2026-01-15T10:45:00Z"
            mf06["normalized_second_production_utc"] = "2026-01-15T11:45:00Z"
            manifest["max_attempt_duration_seconds"] = 601
            write_json(manifest_path, manifest)
            widened = subprocess.run(command, text=True, capture_output=True, check=False, timeout=30)
            self.assertNotEqual(widened.returncode, 0)
            self.assertIn("scheduler manifest retry budget differs from accepted-main exact value", widened.stdout)


if __name__ == "__main__":
    unittest.main()
